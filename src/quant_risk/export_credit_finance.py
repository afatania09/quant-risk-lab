"""IFRS 9, pricing, reinsurance and monthly movement analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .export_credit import validate_export_portfolio


def scenario_weighted_ecl(
    portfolio: pd.DataFrame,
    scenarios: pd.DataFrame,
    discount_rate: float = 0.04,
) -> pd.DataFrame:
    """Calculate illustrative IFRS 9 scenario-weighted lifetime ECL by deal."""
    clean = validate_export_portfolio(portfolio)
    required = {"scenario", "weight", "pd_multiplier", "lgd_multiplier"}
    missing = required - set(scenarios.columns)
    if missing:
        raise ValueError(f"missing scenario columns: {sorted(missing)}")
    if not np.isclose(scenarios["weight"].sum(), 1.0):
        raise ValueError("scenario weights must sum to one")
    records: list[dict[str, float | str]] = []
    for deal in clean.itertuples():
        maturity = max(int(getattr(deal, "maturity_years", 1)), 1)
        stage = int(getattr(deal, "ifrs9_stage", 1))
        horizon = 1 if stage == 1 else maturity
        deal_ecl = 0.0
        for scenario in scenarios.itertuples():
            annual_pd = min(deal.pd * scenario.pd_multiplier, 0.999)
            cumulative_pd = 1.0 - (1.0 - annual_pd) ** horizon
            lgd = min(deal.lgd * scenario.lgd_multiplier, 1.0)
            discount = 1.0 / (1.0 + discount_rate) ** (horizon / 2)
            deal_ecl += (
                scenario.weight * deal.covered_ead_gbp_m * cumulative_pd * lgd * discount
            )
        records.append(
            {
                "deal_id": deal.deal_id,
                "country": deal.country,
                "ifrs9_stage": stage,
                "horizon_years": horizon,
                "scenario_weighted_ecl_gbp_m": deal_ecl,
            }
        )
    return pd.DataFrame(records)


def premium_adequacy(
    portfolio: pd.DataFrame,
    capital_rate: float = 0.08,
    cost_of_capital: float = 0.10,
    operating_cost_rate: float = 0.0015,
) -> pd.DataFrame:
    """Compare annual premium with illustrative risk and operating costs."""
    clean = validate_export_portfolio(portfolio)
    result = clean[
        ["deal_id", "country", "sector", "covered_ead_gbp_m", "annual_premium_gbp_m"]
    ].copy()
    result["expected_loss_gbp_m"] = clean["expected_loss_gbp_m"]
    result["capital_cost_gbp_m"] = clean["covered_ead_gbp_m"] * capital_rate * cost_of_capital
    result["operating_cost_gbp_m"] = clean["covered_ead_gbp_m"] * operating_cost_rate
    result["required_premium_gbp_m"] = result[
        ["expected_loss_gbp_m", "capital_cost_gbp_m", "operating_cost_gbp_m"]
    ].sum(axis=1)
    result["premium_surplus_gbp_m"] = (
        result["annual_premium_gbp_m"] - result["required_premium_gbp_m"]
    )
    result["adequacy_ratio"] = (
        result["annual_premium_gbp_m"] / result["required_premium_gbp_m"]
    )
    return result.sort_values("premium_surplus_gbp_m").reset_index(drop=True)


def apply_reinsurance(
    losses: np.ndarray,
    structure: str,
    share: float = 0.30,
    attachment_gbp_m: float = 250.0,
    limit_gbp_m: float = 500.0,
    annual_premium_gbp_m: float = 12.0,
) -> pd.DataFrame:
    """Compare gross and net simulated losses for simple reinsurance structures."""
    gross = np.asarray(losses, dtype=float)
    if structure == "Quota share":
        if not 0 <= share <= 1:
            raise ValueError("share must be in [0, 1]")
        recovery = gross * share
    elif structure == "Excess of loss":
        recovery = np.minimum(np.maximum(gross - attachment_gbp_m, 0.0), limit_gbp_m)
    else:
        raise ValueError("structure must be Quota share or Excess of loss")
    return pd.DataFrame(
        {
            "gross_loss_gbp_m": gross,
            "reinsurance_recovery_gbp_m": recovery,
            "net_loss_gbp_m": gross - recovery + annual_premium_gbp_m,
        }
    )


def monthly_risk_bridge(
    previous: pd.DataFrame,
    current: pd.DataFrame,
) -> pd.DataFrame:
    """Attribute change in deterministic expected loss to portfolio movements."""
    old = validate_export_portfolio(previous).set_index("deal_id")
    new = validate_export_portfolio(current).set_index("deal_id")
    deal_ids = old.index.union(new.index)
    rows: list[dict[str, float | str]] = []
    for deal_id in deal_ids:
        if deal_id not in old.index:
            movement = "New business"
            change = float(new.loc[deal_id, "expected_loss_gbp_m"])
        elif deal_id not in new.index:
            movement = "Repayment/exit"
            change = -float(old.loc[deal_id, "expected_loss_gbp_m"])
        else:
            old_row, new_row = old.loc[deal_id], new.loc[deal_id]
            change = float(
                new_row["expected_loss_gbp_m"] - old_row["expected_loss_gbp_m"]
            )
            if not np.isclose(old_row["pd"], new_row["pd"]):
                movement = "Credit deterioration" if new_row["pd"] > old_row["pd"] else "Upgrade"
            elif not np.isclose(old_row["covered_ead_gbp_m"], new_row["covered_ead_gbp_m"]):
                movement = "Exposure movement"
            elif not np.isclose(old_row["lgd"], new_row["lgd"]):
                movement = "Recovery assumption"
            else:
                movement = "Other/no change"
        rows.append(
            {
                "deal_id": deal_id,
                "movement": movement,
                "expected_loss_change_gbp_m": change,
            }
        )
    return pd.DataFrame(rows).sort_values(
        "expected_loss_change_gbp_m", key=abs, ascending=False
    )