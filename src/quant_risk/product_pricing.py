"""Illustrative export-credit product selection and cash-flow pricing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

PRODUCTS = {
    "Buyer Credit Facility": {
        "purpose": "Bank loan to an overseas buyer purchasing from the UK",
        "risk_entity": "Overseas buyer / borrower",
        "typical_cover": 0.85,
        "pricing_basis": "Credit premium plus lender economics",
    },
    "Direct Lending Facility": {
        "purpose": "UKEF loan to an overseas buyer purchasing from the UK",
        "risk_entity": "Overseas buyer / borrower",
        "typical_cover": 1.00,
        "pricing_basis": "Interest and credit premium",
    },
    "Export Insurance Policy": {
        "purpose": "Exporter protection against buyer non-payment",
        "risk_entity": "Overseas buyer",
        "typical_cover": 0.95,
        "pricing_basis": "Insurance premium",
    },
    "General Export Facility": {
        "purpose": "Partial bank guarantee for an exporter's trade-finance facility",
        "risk_entity": "UK exporter",
        "typical_cover": 0.80,
        "pricing_basis": "Guarantee fee",
    },
    "Export Working Capital Scheme": {
        "purpose": "Bank guarantee supporting working capital for an export contract",
        "risk_entity": "UK exporter",
        "typical_cover": 0.80,
        "pricing_basis": "Guarantee fee",
    },
    "Bond Support Scheme": {
        "purpose": "Partial guarantee supporting an export contract bond",
        "risk_entity": "UK exporter",
        "typical_cover": 0.80,
        "pricing_basis": "Guarantee fee",
    },
}


@dataclass(frozen=True)
class PriceResult:
    """Economic price and supporting cash-flow schedule."""

    product: str
    exposure_gbp_m: float
    expected_loss_gbp_m: float
    economic_capital_gbp_m: float
    required_premium_gbp_m: float
    model_upfront_rate: float
    floor_upfront_rate: float
    quoted_upfront_rate: float
    equivalent_annual_spread_bps: float
    risk_adjusted_return: float
    schedule: pd.DataFrame


def amortisation_schedule(
    amount_gbp_m: float,
    tenor_years: float,
    drawdown_years: float = 1.0,
    payments_per_year: int = 2,
    profile: str = "Equal principal",
) -> pd.DataFrame:
    """Build a simplified exposure schedule including a drawdown period."""
    if amount_gbp_m <= 0 or tenor_years <= 0 or drawdown_years < 0:
        raise ValueError("amount and tenor must be positive; drawdown cannot be negative")
    periods = max(int(np.ceil(tenor_years * payments_per_year)), 1)
    draw_periods = min(int(np.ceil(drawdown_years * payments_per_year)), periods - 1)
    opening = amount_gbp_m
    rows = []
    repayment_periods = max(periods - draw_periods, 1)
    for period in range(1, periods + 1):
        if period <= draw_periods:
            principal = 0.0
        elif profile == "Bullet":
            principal = opening if period == periods else 0.0
        elif profile == "Equal principal":
            principal = amount_gbp_m / repayment_periods
        else:
            raise ValueError("profile must be Equal principal or Bullet")
        principal = min(principal, opening)
        closing = opening - principal
        rows.append(
            {
                "period": period,
                "year": period / payments_per_year,
                "opening_exposure_gbp_m": opening,
                "principal_gbp_m": principal,
                "closing_exposure_gbp_m": closing,
                "average_exposure_gbp_m": (opening + closing) / 2,
            }
        )
        opening = closing
    return pd.DataFrame(rows)


def price_export_credit(
    *,
    product: str,
    amount_gbp_m: float,
    annual_pd: float,
    lgd: float,
    tenor_years: float,
    guarantee_share: float | None = None,
    drawdown_years: float = 1.0,
    payments_per_year: int = 2,
    repayment_profile: str = "Equal principal",
    discount_rate: float = 0.04,
    capital_confidence: float = 0.995,
    cost_of_capital: float = 0.10,
    operating_cost_rate: float = 0.0015,
    oecd_mpr_floor_rate: float = 0.0,
    quoted_upfront_rate: float | None = None,
) -> PriceResult:
    """Price covered expected loss, economic capital and costs over deal cash flows.

    ``oecd_mpr_floor_rate`` is deliberately supplied by the user. The function does not
    claim to reproduce the official OECD MPR formula or UKEF's internal pricing model.
    """
    if product not in PRODUCTS:
        raise ValueError(f"unknown product: {product}")
    if not 0 <= annual_pd < 1 or not 0 <= lgd <= 1:
        raise ValueError("PD must be in [0, 1) and LGD in [0, 1]")
    share = PRODUCTS[product]["typical_cover"] if guarantee_share is None else guarantee_share
    if not 0 <= share <= 1 or oecd_mpr_floor_rate < 0:
        raise ValueError("cover must be in [0, 1] and floor non-negative")
    schedule = amortisation_schedule(
        amount_gbp_m, tenor_years, drawdown_years, payments_per_year, repayment_profile
    )
    dt = 1 / payments_per_year
    covered = schedule["average_exposure_gbp_m"] * share
    times = schedule["year"].to_numpy()
    survival_start = (1 - annual_pd) ** np.maximum(times - dt, 0)
    marginal_pd = survival_start * (1 - (1 - annual_pd) ** dt)
    discount = (1 + discount_rate) ** (-times)
    expected_loss = covered.to_numpy() * marginal_pd * lgd * discount

    systematic_rho = 0.15
    conditional_pd = norm.cdf(
        (norm.ppf(max(annual_pd, 1e-8)) + np.sqrt(systematic_rho) * norm.ppf(capital_confidence))
        / np.sqrt(1 - systematic_rho)
    )
    peak_covered = amount_gbp_m * share
    capital = peak_covered * lgd * max(conditional_pd - annual_pd, 0)
    average_life = float((covered * dt).sum() / peak_covered) if peak_covered else 0.0
    capital_cost = capital * cost_of_capital * average_life
    operating_cost = float((covered * operating_cost_rate * dt * discount).sum())
    total_el = float(expected_loss.sum())
    required = total_el + capital_cost + operating_cost
    model_rate = required / peak_covered if peak_covered else 0.0
    floor_rate = max(oecd_mpr_floor_rate, 0.0)
    quote = max(model_rate, floor_rate) if quoted_upfront_rate is None else quoted_upfront_rate
    quoted_premium = quote * peak_covered
    spread = quote / average_life * 10_000 if average_life else 0.0
    raroc = (
        (quoted_premium - total_el - operating_cost) / (capital * average_life)
        if capital > 0 and average_life > 0 else 0.0
    )
    schedule = schedule.assign(
        covered_average_exposure_gbp_m=covered,
        marginal_default_probability=marginal_pd,
        discounted_expected_loss_gbp_m=expected_loss,
    )
    return PriceResult(
        product=product,
        exposure_gbp_m=peak_covered,
        expected_loss_gbp_m=total_el,
        economic_capital_gbp_m=float(capital),
        required_premium_gbp_m=float(required),
        model_upfront_rate=float(model_rate),
        floor_upfront_rate=float(floor_rate),
        quoted_upfront_rate=float(quote),
        equivalent_annual_spread_bps=float(spread),
        risk_adjusted_return=float(raroc),
        schedule=schedule,
    )


def product_catalogue() -> pd.DataFrame:
    """Return the supported product decision catalogue."""
    return pd.DataFrame([{"product": name, **details} for name, details in PRODUCTS.items()])


def shortlist_products(
    need: str,
    amount_gbp_m: float,
    credit_term_years: float,
) -> pd.DataFrame:
    """Provide an explainable indicative shortlist, not an eligibility determination."""
    rules = {
        "Finance an overseas buyer": [
            ("Buyer Credit Facility", 95, "Bank-funded buyer finance, usually two years or more"),
            ("Direct Lending Facility", 85, "Direct buyer loan for larger transactions"),
        ],
        "Protect exporter from non-payment": [
            ("Export Insurance Policy", 95, "Insurance against buyer non-payment"),
            ("Buyer Credit Facility", 65, "Alternative structure that pays the exporter from financing"),
        ],
        "Provide exporter working capital": [
            ("General Export Facility", 90, "Flexible non-contract-specific trade finance"),
            ("Export Working Capital Scheme", 95, "Working capital linked to an export contract"),
        ],
        "Support a contract bond": [
            ("Bond Support Scheme", 100, "Designed to support an export contract bond"),
        ],
    }
    if need not in rules or amount_gbp_m <= 0 or credit_term_years <= 0:
        raise ValueError("invalid product-selection inputs")
    candidates = rules[need]
    rows = []
    for product, score, rationale in candidates:
        adjusted = score
        if product == "Direct Lending Facility" and amount_gbp_m < 50:
            adjusted -= 25
            rationale += "; scale may favour another buyer-finance route"
        if product == "General Export Facility" and amount_gbp_m > 25:
            adjusted -= 25
            rationale += "; published guidance indicates contacting UKEF above about £25m"
        if product in {"Buyer Credit Facility", "Direct Lending Facility"} and credit_term_years < 2:
            adjusted -= 30
            rationale += "; tenor is below the typical two-year buyer-credit horizon"
        rows.append({"product": product, "fit_score": max(adjusted, 0), "rationale": rationale})
    return pd.DataFrame(rows).sort_values("fit_score", ascending=False).reset_index(drop=True)
