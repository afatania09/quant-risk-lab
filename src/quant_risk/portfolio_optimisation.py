"""Constrained portfolio-risk transfer and challenger-model analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

from .credit_portfolio import credit_var_es, simulate_credit_losses
from .export_credit import (
    risk_contributions,
    simulate_export_credit_losses,
    validate_export_portfolio,
)


def optimise_risk_transfer(
    portfolio: pd.DataFrame,
    budget_gbp_m: float = 15.0,
    ceded_share: float = 0.50,
    price_rate: float = 0.012,
    max_country_budget_share: float = 0.35,
    max_sector_budget_share: float = 0.40,
    simulations: int = 12_000,
) -> pd.DataFrame:
    """Select whole-deal quota-share transfers subject to budget constraints.

    The binary optimiser maximises estimated tail-risk reduction. It limits spend
    in any one country or sector, creating a diversified risk-transfer programme.
    """
    if budget_gbp_m <= 0 or not 0 < ceded_share <= 1 or price_rate <= 0:
        raise ValueError("invalid reinsurance assumptions")
    if not 0 < max_country_budget_share <= 1 or not 0 < max_sector_budget_share <= 1:
        raise ValueError("budget concentration limits must be in (0, 1]")
    clean = validate_export_portfolio(portfolio)
    contributions = risk_contributions(clean, simulations=simulations).set_index("deal_id")
    candidates = clean[
        ["deal_id", "country", "sector", "covered_ead_gbp_m", "country_limit_gbp_m"]
    ].copy()
    candidates["cost_gbp_m"] = candidates["covered_ead_gbp_m"] * ceded_share * price_rate
    candidates["tail_risk_reduction_gbp_m"] = (
        candidates["deal_id"].map(contributions["tail_contribution_gbp_m"]) * ceded_share
    )
    candidates["country_headroom_created_gbp_m"] = (
        candidates["covered_ead_gbp_m"] * ceded_share
    )
    candidates["risk_reduction_per_cost"] = (
        candidates["tail_risk_reduction_gbp_m"] / candidates["cost_gbp_m"]
    )

    rows = [candidates["cost_gbp_m"].to_numpy(dtype=float)]
    upper = [budget_gbp_m]
    constraint_names = ["Total budget"]
    for country in candidates["country"].unique():
        rows.append(
            np.where(
                candidates["country"].eq(country),
                candidates["cost_gbp_m"],
                0.0,
            )
        )
        upper.append(budget_gbp_m * max_country_budget_share)
        constraint_names.append(f"Country: {country}")
    for sector in candidates["sector"].unique():
        rows.append(
            np.where(
                candidates["sector"].eq(sector),
                candidates["cost_gbp_m"],
                0.0,
            )
        )
        upper.append(budget_gbp_m * max_sector_budget_share)
        constraint_names.append(f"Sector: {sector}")
    matrix = np.vstack(rows)
    constraints = LinearConstraint(matrix, lb=np.zeros(len(rows)), ub=np.array(upper))
    result = milp(
        c=-candidates["tail_risk_reduction_gbp_m"].to_numpy(dtype=float),
        integrality=np.ones(len(candidates)),
        bounds=Bounds(np.zeros(len(candidates)), np.ones(len(candidates))),
        constraints=constraints,
        options={"time_limit": 10.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"risk-transfer optimisation failed: {result.message}")
    candidates["recommended"] = result.x > 0.5
    candidates["programme_cost_gbp_m"] = np.where(
        candidates["recommended"], candidates["cost_gbp_m"], 0.0
    )
    candidates["programme_tail_reduction_gbp_m"] = np.where(
        candidates["recommended"], candidates["tail_risk_reduction_gbp_m"], 0.0
    )
    candidates.attrs["solver_status"] = str(result.message)
    candidates.attrs["binding_constraints"] = constraint_names
    return candidates.sort_values(
        ["recommended", "risk_reduction_per_cost"], ascending=[False, False]
    ).reset_index(drop=True)


def risk_transfer_concentration(selected: pd.DataFrame) -> pd.DataFrame:
    """Summarise selected programme cost and risk reduction by country and sector."""
    chosen = selected.loc[selected["recommended"]].copy()
    if chosen.empty:
        return pd.DataFrame(
            columns=["dimension", "name", "cost_gbp_m", "tail_reduction_gbp_m", "cost_share"]
        )
    frames = []
    for dimension in ["country", "sector"]:
        summary = (
            chosen.groupby(dimension, as_index=False)
            .agg(
                cost_gbp_m=("cost_gbp_m", "sum"),
                tail_reduction_gbp_m=("tail_risk_reduction_gbp_m", "sum"),
            )
            .rename(columns={dimension: "name"})
        )
        summary.insert(0, "dimension", dimension.title())
        summary["cost_share"] = summary["cost_gbp_m"] / chosen["cost_gbp_m"].sum()
        frames.append(summary)
    return pd.concat(frames, ignore_index=True)


def challenger_model_comparison(
    portfolio: pd.DataFrame,
    simulations: int = 30_000,
    confidence: float = 0.995,
    seed: int = 42,
) -> pd.DataFrame:
    """Compare the production-style multi-factor engine with a one-factor challenger."""
    clean = validate_export_portfolio(portfolio)
    primary = simulate_export_credit_losses(
        clean, simulations=simulations, confidence=confidence, seed=seed
    )
    challenger_losses = simulate_credit_losses(
        clean["pd"].to_numpy(),
        clean["lgd"].to_numpy(),
        clean["covered_ead_gbp_m"].to_numpy(),
        asset_correlation=0.25,
        simulations=simulations,
        seed=seed,
    )
    challenger_el, challenger_ul, challenger_es = credit_var_es(
        challenger_losses, confidence=confidence
    )
    challenger_var = challenger_el + challenger_ul
    comparison = pd.DataFrame(
        [
            {
                "model": "Multi-factor primary",
                "expected_loss_gbp_m": primary.expected_loss,
                "loss_var_gbp_m": primary.loss_var,
                "expected_shortfall_gbp_m": primary.expected_shortfall,
            },
            {
                "model": "One-factor challenger",
                "expected_loss_gbp_m": challenger_el,
                "loss_var_gbp_m": challenger_var,
                "expected_shortfall_gbp_m": challenger_es,
            },
        ]
    )
    primary_row = comparison.iloc[0]
    for metric in ["expected_loss_gbp_m", "loss_var_gbp_m", "expected_shortfall_gbp_m"]:
        comparison[f"{metric}_difference_pct"] = (
            comparison[metric] / primary_row[metric] - 1.0
        )
    return comparison
