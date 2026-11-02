"""Sovereign migration, macro scenarios and parameter uncertainty.

The calibrations in this module are transparent educational assumptions. They are
not official UKEF, OECD or credit-rating-agency transition matrices.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .export_credit import simulate_export_credit_losses, validate_export_portfolio

GRADE_STATES = tuple(range(1, 8))


def illustrative_transition_matrix() -> pd.DataFrame:
    """Return a transparent annual 1–7 country-grade transition matrix.

    Grade 1 is the strongest performing state, grade 7 the weakest, and default
    is absorbing. Probabilities are deliberately smooth and illustrative.
    """
    states: list[int | str] = [*GRADE_STATES, "D"]
    rows: list[list[float]] = []
    for grade in GRADE_STATES:
        default_probability = [0.0002, 0.0005, 0.0012, 0.0030, 0.0080, 0.0250, 0.0800][
            grade - 1
        ]
        downgrade = [0.025, 0.040, 0.060, 0.085, 0.110, 0.140, 0.0][grade - 1]
        upgrade = [0.0, 0.035, 0.050, 0.060, 0.060, 0.050, 0.035][grade - 1]
        row = np.zeros(len(states), dtype=float)
        if grade > 1:
            row[grade - 2] = upgrade
        if grade < 7:
            row[grade] = downgrade
        row[grade - 1] = 1.0 - default_probability - downgrade - upgrade
        row[-1] = default_probability
        rows.append(row.tolist())
    rows.append([0.0] * 7 + [1.0])
    return pd.DataFrame(rows, index=states, columns=states)


def stressed_transition_matrix(
    matrix: pd.DataFrame,
    downgrade_multiplier: float = 1.5,
    default_multiplier: float = 2.0,
) -> pd.DataFrame:
    """Create a row-stochastic stressed matrix by shifting mass from persistence."""
    if downgrade_multiplier < 1 or default_multiplier < 1:
        raise ValueError("stress multipliers must be at least one")
    stressed = matrix.copy().astype(float)
    for grade in GRADE_STATES:
        row = stressed.loc[grade].copy()
        downgrade_state = grade + 1 if grade < 7 else None
        original_default = row["D"]
        original_downgrade = row[downgrade_state] if downgrade_state else 0.0
        row["D"] = original_default * default_multiplier
        if downgrade_state:
            row[downgrade_state] = original_downgrade * downgrade_multiplier
        added = (row["D"] - original_default) + (
            row[downgrade_state] - original_downgrade if downgrade_state else 0.0
        )
        if added > row[grade]:
            raise ValueError("stress is too severe for the transition matrix")
        row[grade] -= added
        stressed.loc[grade] = row
    return stressed


def migration_projection(
    portfolio: pd.DataFrame,
    years: int = 5,
    simulations: int = 10_000,
    stressed: bool = False,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Project country-grade distributions and cumulative default exposure."""
    if years < 1 or simulations < 1:
        raise ValueError("years and simulations must be positive")
    clean = validate_export_portfolio(portfolio)
    matrix = illustrative_transition_matrix()
    if stressed:
        matrix = stressed_transition_matrix(matrix)
    states = matrix.columns.to_list()
    state_to_index = {state: index for index, state in enumerate(states)}
    probabilities = matrix.to_numpy(dtype=float)
    initial = clean["country_risk_grade"].astype(int).clip(1, 7).to_numpy()
    exposure = clean["covered_ead_gbp_m"].to_numpy(dtype=float)
    lgd = clean["lgd"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    state_indices = np.tile(
        np.array([state_to_index[grade] for grade in initial], dtype=int),
        (simulations, 1),
    )
    distribution_rows: list[dict[str, float | int | str]] = []
    default_rows: list[dict[str, float | int]] = []
    cumulative_default_loss = np.zeros(simulations)
    newly_defaulted = np.zeros_like(state_indices, dtype=bool)
    for year in range(1, years + 1):
        draws = rng.random(state_indices.shape)
        previous = state_indices.copy()
        for state_index in range(len(states)):
            mask = previous == state_index
            if not mask.any():
                continue
            cumulative = np.cumsum(probabilities[state_index])
            state_indices[mask] = np.searchsorted(cumulative, draws[mask], side="right")
        default_index = state_to_index["D"]
        newly_defaulted = (state_indices == default_index) & (previous != default_index)
        cumulative_default_loss += newly_defaulted @ (exposure * lgd)
        for state, state_index in state_to_index.items():
            share = float((state_indices == state_index).mean())
            distribution_rows.append(
                {"year": year, "grade": str(state), "portfolio_share": share}
            )
        default_rows.append(
            {
                "year": year,
                "mean_cumulative_default_loss_gbp_m": float(cumulative_default_loss.mean()),
                "p95_cumulative_default_loss_gbp_m": float(
                    np.quantile(cumulative_default_loss, 0.95)
                ),
                "defaulted_exposure_share": float(
                    ((state_indices == default_index) * exposure).sum(axis=1).mean()
                    / exposure.sum()
                ),
            }
        )
    return pd.DataFrame(distribution_rows), pd.DataFrame(default_rows)


def parameter_uncertainty(
    portfolio: pd.DataFrame,
    draws: int = 20_000,
    pd_strength: float = 250.0,
    lgd_strength: float = 80.0,
    seed: int = 42,
) -> dict[str, float | np.ndarray]:
    """Propagate beta-distributed PD and LGD estimation uncertainty into EL."""
    if draws < 1 or pd_strength <= 0 or lgd_strength <= 0:
        raise ValueError("draws and distribution strengths must be positive")
    clean = validate_export_portfolio(portfolio)
    pd_values = clean["pd"].to_numpy(dtype=float)
    lgd_values = clean["lgd"].to_numpy(dtype=float)
    exposure = clean["covered_ead_gbp_m"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    pd_draws = rng.beta(
        np.maximum(pd_values * pd_strength, 0.01),
        np.maximum((1.0 - pd_values) * pd_strength, 0.01),
        size=(draws, len(clean)),
    )
    lgd_draws = rng.beta(
        np.maximum(lgd_values * lgd_strength, 0.01),
        np.maximum((1.0 - lgd_values) * lgd_strength, 0.01),
        size=(draws, len(clean)),
    )
    expected_losses = (pd_draws * lgd_draws) @ exposure
    point_estimate = float((pd_values * lgd_values) @ exposure)
    return {
        "draws": expected_losses,
        "point_estimate_gbp_m": point_estimate,
        "mean_gbp_m": float(expected_losses.mean()),
        "p05_gbp_m": float(np.quantile(expected_losses, 0.05)),
        "p50_gbp_m": float(np.quantile(expected_losses, 0.50)),
        "p95_gbp_m": float(np.quantile(expected_losses, 0.95)),
    }


SCENARIOS: dict[str, dict[str, object]] = {
    "Base": {"pd": 1.0, "lgd": 1.0, "correlation": 1.0},
    "Global recession": {"pd": 1.65, "lgd": 1.15, "correlation": 1.35},
    "Sovereign debt shock": {
        "pd": 1.45,
        "lgd": 1.25,
        "correlation": 1.45,
        "regions": {"Africa": 1.25, "MENA": 1.20, "Europe and Central Asia": 1.15},
    },
    "Commodity-price collapse": {
        "pd": 1.25,
        "lgd": 1.10,
        "correlation": 1.20,
        "sectors": {"Mining": 2.0, "Energy": 1.8, "Power": 1.25},
    },
    "Physical-climate event": {
        "pd": 1.20,
        "lgd": 1.15,
        "correlation": 1.25,
        "sectors": {"Water": 1.75, "Transport": 1.30, "Agriculture": 1.60},
    },
}


def macro_scenario_comparison(
    portfolio: pd.DataFrame,
    simulations: int = 20_000,
    confidence: float = 0.995,
    seed: int = 42,
) -> pd.DataFrame:
    """Compare named macro-credit scenarios on a consistent loss basis."""
    clean = validate_export_portfolio(portfolio)
    results: list[dict[str, float | str]] = []
    base_var = 0.0
    for name, assumptions in SCENARIOS.items():
        stressed = clean.copy()
        multiplier = np.full(len(stressed), float(assumptions["pd"]))
        for region, value in dict(assumptions.get("regions", {})).items():
            multiplier[stressed["region"].eq(region).to_numpy()] *= float(value)
        for sector, value in dict(assumptions.get("sectors", {})).items():
            multiplier[stressed["sector"].eq(sector).to_numpy()] *= float(value)
        stressed["pd"] = np.minimum(stressed["pd"].to_numpy() * multiplier, 0.999)
        stressed["lgd"] = np.minimum(
            stressed["lgd"] * float(assumptions["lgd"]), 1.0
        )
        correlation_scale = float(assumptions["correlation"])
        result = simulate_export_credit_losses(
            stressed,
            simulations=simulations,
            confidence=confidence,
            global_correlation=min(0.10 * correlation_scale, 0.28),
            country_correlation=min(0.18 * correlation_scale, 0.38),
            sector_correlation=min(0.10 * correlation_scale, 0.22),
            seed=seed,
        )
        if name == "Base":
            base_var = result.loss_var
        results.append(
            {
                "scenario": name,
                "expected_loss_gbp_m": result.expected_loss,
                "loss_var_gbp_m": result.loss_var,
                "expected_shortfall_gbp_m": result.expected_shortfall,
            }
        )
    frame = pd.DataFrame(results)
    frame["change_in_var_gbp_m"] = frame["loss_var_gbp_m"] - base_var
    frame["change_in_var_pct"] = np.where(
        base_var, frame["loss_var_gbp_m"] / base_var - 1.0, 0.0
    )
    return frame.sort_values("loss_var_gbp_m", ascending=False).reset_index(drop=True)
