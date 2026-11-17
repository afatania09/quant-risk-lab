"""Portfolio risk-appetite limits, early-warning triggers and escalation reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .export_credit import concentration_report, country_limit_report, validate_export_portfolio


@dataclass(frozen=True)
class RiskAppetiteLimits:
    """Illustrative portfolio thresholds expressed as ratios."""

    var_capacity_amber: float = 0.70
    var_capacity_red: float = 0.85
    es_capacity_amber: float = 0.85
    es_capacity_red: float = 1.00
    expected_loss_amber: float = 0.025
    expected_loss_red: float = 0.035
    premium_cover_amber: float = 1.25
    premium_cover_red: float = 1.00
    top_country_amber: float = 0.20
    top_country_red: float = 0.25
    top_sector_amber: float = 0.30
    top_sector_red: float = 0.35
    country_hhi_amber: float = 0.12
    country_hhi_red: float = 0.18
    stage_2_3_amber: float = 0.20
    stage_2_3_red: float = 0.30

    def __post_init__(self) -> None:
        maximum_pairs = [
            (self.var_capacity_amber, self.var_capacity_red),
            (self.es_capacity_amber, self.es_capacity_red),
            (self.expected_loss_amber, self.expected_loss_red),
            (self.top_country_amber, self.top_country_red),
            (self.top_sector_amber, self.top_sector_red),
            (self.country_hhi_amber, self.country_hhi_red),
            (self.stage_2_3_amber, self.stage_2_3_red),
        ]
        if any(amber < 0 or red <= amber for amber, red in maximum_pairs):
            raise ValueError("maximum-risk thresholds require 0 <= amber < red")
        if not 0 < self.premium_cover_red < self.premium_cover_amber:
            raise ValueError("premium-cover thresholds require 0 < red < amber")


def _maximum_status(value: float, amber: float, red: float) -> tuple[str, float]:
    status = "Red" if value >= red else "Amber" if value >= amber else "Green"
    return status, red - value


def _minimum_status(value: float, amber: float, red: float) -> tuple[str, float]:
    status = "Red" if value <= red else "Amber" if value <= amber else "Green"
    return status, value - red


def portfolio_risk_appetite(
    portfolio: pd.DataFrame,
    *,
    loss_var_gbp_m: float,
    expected_shortfall_gbp_m: float,
    loss_capacity_gbp_m: float,
    limits: RiskAppetiteLimits | None = None,
) -> pd.DataFrame:
    """Assess core portfolio measures against explicit Green/Amber/Red thresholds."""
    if loss_var_gbp_m < 0 or expected_shortfall_gbp_m < 0 or loss_capacity_gbp_m <= 0:
        raise ValueError("loss measures must be non-negative and capacity positive")
    limits = limits or RiskAppetiteLimits()
    clean = validate_export_portfolio(portfolio)
    exposure = float(clean["covered_ead_gbp_m"].sum())
    expected_loss = float(clean["expected_loss_gbp_m"].sum())
    premium = float(clean["annual_premium_gbp_m"].sum())
    countries = concentration_report(clean, "country")
    sectors = concentration_report(clean, "sector")
    country_hhi = float(np.square(countries["portfolio_share"]).sum())
    if "ifrs9_stage" in clean:
        stage_share = float(
            clean.loc[clean["ifrs9_stage"].ge(2), "covered_ead_gbp_m"].sum() / exposure
        )
    else:
        stage_share = 0.0

    measures = [
        ("RA01", "Loss-at-risk / capacity", loss_var_gbp_m / loss_capacity_gbp_m,
         limits.var_capacity_amber, limits.var_capacity_red, "max",
         "Reduce exposure, transfer risk or increase approved capacity"),
        ("RA02", "Expected Shortfall / capacity", expected_shortfall_gbp_m / loss_capacity_gbp_m,
         limits.es_capacity_amber, limits.es_capacity_red, "max",
         "Review tail scenarios and risk-transfer options"),
        ("RA03", "Expected loss / covered exposure", expected_loss / exposure,
         limits.expected_loss_amber, limits.expected_loss_red, "max",
         "Review portfolio credit quality and pricing"),
        ("RA04", "Premium / expected loss", premium / expected_loss,
         limits.premium_cover_amber, limits.premium_cover_red, "min",
         "Reprice, restructure or document a strategic pricing exception"),
        ("RA05", "Largest country exposure share", float(countries.iloc[0]["portfolio_share"]),
         limits.top_country_amber, limits.top_country_red, "max",
         "Restrict incremental exposure or diversify by country"),
        ("RA06", "Largest sector exposure share", float(sectors.iloc[0]["portfolio_share"]),
         limits.top_sector_amber, limits.top_sector_red, "max",
         "Diversify origination or transfer concentrated sector risk"),
        ("RA07", "Country concentration HHI", country_hhi,
         limits.country_hhi_amber, limits.country_hhi_red, "max",
         "Review concentration overlay and correlated stress"),
        ("RA08", "Stage 2/3 covered exposure share", stage_share,
         limits.stage_2_3_amber, limits.stage_2_3_red, "max",
         "Escalate watch-list cases and refresh lifetime ECL"),
    ]
    rows: list[dict[str, Any]] = []
    for control_id, metric, value, amber, red, direction, action in measures:
        if direction == "max":
            status, headroom = _maximum_status(value, amber, red)
            threshold_text = f"Amber ≥ {amber:.1%}; Red ≥ {red:.1%}"
        else:
            status, headroom = _minimum_status(value, amber, red)
            threshold_text = f"Amber ≤ {amber:.2f}x; Red ≤ {red:.2f}x"
        rows.append(
            {
                "control_id": control_id,
                "metric": metric,
                "value": value,
                "status": status,
                "red_headroom": headroom,
                "threshold": threshold_text,
                "management_action": action,
            }
        )
    return pd.DataFrame(rows)


def deal_early_warning_register(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Create a deal watch list from credit, pricing, stage and country-limit triggers."""
    clean = validate_export_portfolio(portfolio)
    country_utilisation = country_limit_report(clean).set_index("country")["utilisation"]
    records: list[dict[str, Any]] = []
    for deal in clean.itertuples():
        red: list[str] = []
        amber: list[str] = []
        if deal.pd >= 0.05:
            red.append("PD ≥ 5%")
        elif deal.pd >= 0.03:
            amber.append("PD ≥ 3%")
        stage = int(getattr(deal, "ifrs9_stage", 1))
        if stage >= 3:
            red.append("IFRS 9 Stage 3")
        elif stage == 2:
            amber.append("IFRS 9 Stage 2")
        utilisation = float(country_utilisation.loc[deal.country])
        if utilisation >= 1.0:
            red.append("Country limit breached")
        elif utilisation >= 0.8:
            amber.append("Country utilisation ≥ 80%")
        pricing_cover = deal.premium_rate / (deal.pd * deal.lgd) if deal.pd * deal.lgd else np.inf
        if pricing_cover < 1.0:
            red.append("Premium below expected-loss rate")
        elif pricing_cover < 1.25:
            amber.append("Limited pricing headroom")
        grade = int(getattr(deal, "country_risk_grade", 1))
        if grade >= 7:
            red.append("Country grade 7")
        elif grade >= 6:
            amber.append("Country grade 6")
        status = "Red" if red else "Amber" if amber else "Green"
        triggers = red + amber
        records.append(
            {
                "deal_id": deal.deal_id,
                "project": getattr(deal, "project", deal.deal_id),
                "country": deal.country,
                "sector": deal.sector,
                "covered_ead_gbp_m": deal.covered_ead_gbp_m,
                "pd": deal.pd,
                "ifrs9_stage": stage,
                "country_utilisation": utilisation,
                "pricing_cover": pricing_cover,
                "status": status,
                "trigger_count": len(triggers),
                "triggers": "; ".join(triggers) if triggers else "None",
                "escalation": (
                    "Immediate owner review" if status == "Red" else
                    "Monitor monthly" if status == "Amber" else "Routine monitoring"
                ),
            }
        )
    order = {"Red": 0, "Amber": 1, "Green": 2}
    result = pd.DataFrame(records)
    result["_order"] = result["status"].map(order)
    return result.sort_values(
        ["_order", "trigger_count", "covered_ead_gbp_m"], ascending=[True, False, False]
    ).drop(columns="_order").reset_index(drop=True)


def risk_appetite_report(scorecard: pd.DataFrame, watchlist: pd.DataFrame) -> str:
    """Render a concise committee exception and escalation report."""
    counts = scorecard["status"].value_counts()
    watch_counts = watchlist["status"].value_counts()
    exceptions = scorecard.loc[scorecard["status"].ne("Green")]
    exception_text = (
        "\n".join(
            f"- **{row.status}:** {row.metric} ({row.value:.2%}) — {row.management_action}."
            for row in exceptions.itertuples()
        )
        if not exceptions.empty else "- No portfolio risk-appetite exceptions."
    )
    priority = watchlist.loc[watchlist["status"].eq("Red")].head(10)
    priority_text = (
        "\n".join(
            f"- {row.deal_id}, {row.country}: {row.triggers}."
            for row in priority.itertuples()
        )
        if not priority.empty else "- No Red deal-level early warnings."
    )
    overall = "Red" if counts.get("Red", 0) else "Amber" if counts.get("Amber", 0) else "Green"
    return f"""# Portfolio risk-appetite report

## Executive status

**Overall portfolio status: {overall}.** The scorecard has {counts.get('Red', 0)} Red,
{counts.get('Amber', 0)} Amber and {counts.get('Green', 0)} Green measures. The deal register has
{watch_counts.get('Red', 0)} Red and {watch_counts.get('Amber', 0)} Amber cases.

## Portfolio exceptions

{exception_text}

## Priority deal escalations

{priority_text}

## Governance actions

Red items require immediate owner review and a documented accept, mitigate, transfer or decline
decision. Amber items remain on monthly watch with named ownership and a review date. Thresholds are
illustrative and must be approved and calibrated before production use.
"""
