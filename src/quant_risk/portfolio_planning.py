"""New-business pipeline evaluation and risk-capacity allocation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

from .export_credit import simulate_export_credit_losses, validate_export_portfolio


def evaluate_new_business_pipeline(
    current_portfolio: pd.DataFrame,
    pipeline: pd.DataFrame,
    simulations: int = 8_000,
    confidence: float = 0.995,
    seed: int = 42,
) -> pd.DataFrame:
    """Calculate incremental risk, value and capacity use for each candidate deal."""
    current = validate_export_portfolio(current_portfolio)
    candidates = validate_export_portfolio(pipeline)
    if "strategic_score" not in candidates.columns:
        raise ValueError("pipeline must contain strategic_score")
    if ((candidates["strategic_score"] < 0) | (candidates["strategic_score"] > 100)).any():
        raise ValueError("strategic_score must be in [0, 100]")
    base = simulate_export_credit_losses(
        current, simulations=simulations, confidence=confidence, seed=seed
    )
    rows: list[dict[str, float | str]] = []
    for candidate in candidates.itertuples(index=False):
        candidate_frame = candidates.loc[candidates["deal_id"] == candidate.deal_id]
        combined = pd.concat([current, candidate_frame], ignore_index=True)
        combined_result = simulate_export_credit_losses(
            combined, simulations=simulations, confidence=confidence, seed=seed
        )
        covered_ead = float(candidate.covered_ead_gbp_m)
        expected_loss = float(candidate.expected_loss_gbp_m)
        premium = float(candidate.annual_premium_gbp_m)
        capital_cost = covered_ead * 0.08 * 0.10
        operating_cost = covered_ead * 0.0015
        economic_value = premium - expected_loss - capital_cost - operating_cost
        rows.append(
            {
                "deal_id": candidate.deal_id,
                "project": candidate.project,
                "country": candidate.country,
                "sector": candidate.sector,
                "covered_ead_gbp_m": covered_ead,
                "incremental_expected_loss_gbp_m": expected_loss,
                "incremental_var_gbp_m": max(0.0, combined_result.loss_var - base.loss_var),
                "annual_premium_gbp_m": premium,
                "annual_economic_value_gbp_m": economic_value,
                "strategic_score": float(candidate.strategic_score),
                "country_limit_gbp_m": float(candidate.country_limit_gbp_m),
            }
        )
    result = pd.DataFrame(rows)
    result["value_per_var"] = np.where(
        result["incremental_var_gbp_m"] > 0,
        result["annual_economic_value_gbp_m"] / result["incremental_var_gbp_m"],
        np.inf,
    )
    return result.sort_values("value_per_var", ascending=False).reset_index(drop=True)


def optimise_new_business_plan(
    current_portfolio: pd.DataFrame,
    pipeline_evaluation: pd.DataFrame,
    commitment_budget_gbp_m: float,
    var_headroom_gbp_m: float,
    strategic_value_weight_gbp_m: float = 1.0,
) -> pd.DataFrame:
    """Select candidate deals within commitment, risk and country-limit constraints."""
    if commitment_budget_gbp_m < 0 or var_headroom_gbp_m < 0:
        raise ValueError("budgets must be non-negative")
    current = validate_export_portfolio(current_portfolio)
    required = {
        "deal_id",
        "country",
        "covered_ead_gbp_m",
        "incremental_var_gbp_m",
        "annual_economic_value_gbp_m",
        "strategic_score",
        "country_limit_gbp_m",
    }
    missing = required - set(pipeline_evaluation.columns)
    if missing:
        raise ValueError(f"missing pipeline evaluation columns: {sorted(missing)}")
    candidates = pipeline_evaluation.copy().reset_index(drop=True)
    objective_value = candidates["annual_economic_value_gbp_m"].to_numpy(dtype=float) + (
        candidates["strategic_score"].to_numpy(dtype=float) / 100.0
    ) * strategic_value_weight_gbp_m

    rows = [
        candidates["covered_ead_gbp_m"].to_numpy(dtype=float),
        candidates["incremental_var_gbp_m"].to_numpy(dtype=float),
    ]
    upper = [commitment_budget_gbp_m, var_headroom_gbp_m]
    current_country = current.groupby("country")["covered_ead_gbp_m"].sum()
    for country in candidates["country"].unique():
        existing = float(current_country.get(country, 0.0))
        limit = float(
            candidates.loc[candidates["country"] == country, "country_limit_gbp_m"].iloc[0]
        )
        rows.append(
            np.where(
                candidates["country"].eq(country),
                candidates["covered_ead_gbp_m"],
                0.0,
            )
        )
        upper.append(max(0.0, limit - existing))
    constraints = LinearConstraint(
        np.vstack(rows),
        lb=np.zeros(len(rows)),
        ub=np.array(upper, dtype=float),
    )
    result = milp(
        c=-objective_value,
        integrality=np.ones(len(candidates)),
        bounds=Bounds(np.zeros(len(candidates)), np.ones(len(candidates))),
        constraints=constraints,
        options={"time_limit": 10.0},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"new-business optimisation failed: {result.message}")
    candidates["approved"] = result.x > 0.5
    candidates["decision"] = np.where(candidates["approved"], "Approve", "Hold")
    candidates["objective_value_gbp_m"] = objective_value
    candidates.attrs["solver_status"] = str(result.message)
    return candidates.sort_values(
        ["approved", "objective_value_gbp_m"], ascending=[False, False]
    ).reset_index(drop=True)


def build_approved_portfolio(
    current_portfolio: pd.DataFrame,
    pipeline: pd.DataFrame,
    decisions: pd.DataFrame,
) -> pd.DataFrame:
    """Combine the current book with approved pipeline deals."""
    approved_ids = decisions.loc[decisions["approved"], "deal_id"]
    approved = pipeline.loc[pipeline["deal_id"].isin(approved_ids)]
    return pd.concat([current_portfolio, approved], ignore_index=True)
