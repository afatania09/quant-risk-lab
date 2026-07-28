"""Export-credit portfolio analytics for synthetic or user-supplied deal data."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm

REQUIRED_COLUMNS = {
    "deal_id",
    "country",
    "sector",
    "product",
    "ead_gbp_m",
    "pd",
    "lgd",
    "guarantee_share",
    "premium_rate",
    "country_limit_gbp_m",
}


@dataclass(frozen=True)
class PortfolioSimulation:
    """Simulation output with loss metrics expressed in GBP millions."""

    losses: np.ndarray
    expected_loss: float
    loss_var: float
    expected_shortfall: float
    unexpected_loss: float
    confidence: float


def validate_export_portfolio(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Validate and return a defensive copy of an export-credit portfolio."""
    missing = REQUIRED_COLUMNS - set(portfolio.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    clean = portfolio.copy()
    numeric = [
        "ead_gbp_m",
        "pd",
        "lgd",
        "guarantee_share",
        "premium_rate",
        "country_limit_gbp_m",
    ]
    clean[numeric] = clean[numeric].apply(pd.to_numeric)
    if clean["deal_id"].duplicated().any():
        raise ValueError("deal_id values must be unique")
    if (clean["ead_gbp_m"] < 0).any() or (clean["country_limit_gbp_m"] <= 0).any():
        raise ValueError("exposure must be non-negative and country limits positive")
    for column in ["pd", "lgd", "guarantee_share", "premium_rate"]:
        if ((clean[column] < 0) | (clean[column] > 1)).any():
            raise ValueError(f"{column} must be in [0, 1]")
    clean["covered_ead_gbp_m"] = clean["ead_gbp_m"] * clean["guarantee_share"]
    clean["expected_loss_gbp_m"] = clean["covered_ead_gbp_m"] * clean["pd"] * clean["lgd"]
    clean["annual_premium_gbp_m"] = clean["covered_ead_gbp_m"] * clean["premium_rate"]
    return clean


def concentration_report(portfolio: pd.DataFrame, by: str = "country") -> pd.DataFrame:
    """Aggregate covered exposure, expected loss and concentration by country or sector."""
    clean = validate_export_portfolio(portfolio)
    if by not in {"country", "sector", "product"}:
        raise ValueError("by must be country, sector or product")
    total = clean["covered_ead_gbp_m"].sum()
    report = (
        clean.groupby(by, as_index=False)
        .agg(
            exposure_gbp_m=("covered_ead_gbp_m", "sum"),
            expected_loss_gbp_m=("expected_loss_gbp_m", "sum"),
            annual_premium_gbp_m=("annual_premium_gbp_m", "sum"),
            deal_count=("deal_id", "count"),
        )
        .sort_values("exposure_gbp_m", ascending=False)
    )
    report["portfolio_share"] = report["exposure_gbp_m"] / total if total else 0.0
    return report.reset_index(drop=True)


def country_limit_report(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Monitor country exposure limits, headroom and red/amber/green status."""
    clean = validate_export_portfolio(portfolio)
    report = (
        clean.groupby("country", as_index=False)
        .agg(
            exposure_gbp_m=("covered_ead_gbp_m", "sum"),
            limit_gbp_m=("country_limit_gbp_m", "first"),
            expected_loss_gbp_m=("expected_loss_gbp_m", "sum"),
        )
        .sort_values("exposure_gbp_m", ascending=False)
    )
    report["utilisation"] = report["exposure_gbp_m"] / report["limit_gbp_m"]
    report["headroom_gbp_m"] = report["limit_gbp_m"] - report["exposure_gbp_m"]
    report["status"] = np.select(
        [report["utilisation"] >= 1.0, report["utilisation"] >= 0.8],
        ["Red", "Amber"],
        default="Green",
    )
    return report.reset_index(drop=True)


def simulate_export_credit_losses(
    portfolio: pd.DataFrame,
    simulations: int = 50_000,
    confidence: float = 0.995,
    global_correlation: float = 0.10,
    country_correlation: float = 0.18,
    sector_correlation: float = 0.10,
    seed: int = 42,
) -> PortfolioSimulation:
    """Simulate correlated claims with global, country, sector and idiosyncratic factors."""
    clean = validate_export_portfolio(portfolio)
    factor_sum = global_correlation + country_correlation + sector_correlation
    if factor_sum >= 1 or min(global_correlation, country_correlation, sector_correlation) < 0:
        raise ValueError("factor correlations must be non-negative and sum to less than one")
    if simulations <= 0 or not 0 < confidence < 1:
        raise ValueError("simulations must be positive and confidence in (0, 1)")

    countries, country_codes = np.unique(clean["country"], return_inverse=True)
    sectors, sector_codes = np.unique(clean["sector"], return_inverse=True)
    rng = np.random.default_rng(seed)
    global_factor = rng.standard_normal((simulations, 1))
    country_factors = rng.standard_normal((simulations, countries.size))
    sector_factors = rng.standard_normal((simulations, sectors.size))
    idiosyncratic = rng.standard_normal((simulations, len(clean)))
    latent = (
        np.sqrt(global_correlation) * global_factor
        + np.sqrt(country_correlation) * country_factors[:, country_codes]
        + np.sqrt(sector_correlation) * sector_factors[:, sector_codes]
        + np.sqrt(1.0 - factor_sum) * idiosyncratic
    )
    defaults = latent < norm.ppf(clean["pd"].to_numpy())
    severity = clean["covered_ead_gbp_m"].to_numpy() * clean["lgd"].to_numpy()
    losses = defaults @ severity
    expected = float(losses.mean())
    loss_var = float(np.quantile(losses, confidence))
    tail = losses[losses >= loss_var]
    expected_shortfall = float(tail.mean())
    return PortfolioSimulation(
        losses=losses,
        expected_loss=expected,
        loss_var=loss_var,
        expected_shortfall=expected_shortfall,
        unexpected_loss=max(0.0, loss_var - expected),
        confidence=confidence,
    )


def risk_contributions(
    portfolio: pd.DataFrame,
    simulations: int = 30_000,
    confidence: float = 0.995,
    seed: int = 42,
) -> pd.DataFrame:
    """Estimate deal contributions to tail loss using conditional default losses."""
    clean = validate_export_portfolio(portfolio)
    rng = np.random.default_rng(seed)
    common = rng.standard_normal((simulations, 1))
    idiosyncratic = rng.standard_normal((simulations, len(clean)))
    latent = np.sqrt(0.25) * common + np.sqrt(0.75) * idiosyncratic
    deal_losses = (latent < norm.ppf(clean["pd"].to_numpy())) * (
        clean["covered_ead_gbp_m"].to_numpy() * clean["lgd"].to_numpy()
    )
    total_losses = deal_losses.sum(axis=1)
    threshold = np.quantile(total_losses, confidence)
    contribution = deal_losses[total_losses >= threshold].mean(axis=0)
    result = clean[
        ["deal_id", "country", "sector", "covered_ead_gbp_m", "expected_loss_gbp_m"]
    ].copy()
    result["tail_contribution_gbp_m"] = contribution
    total = contribution.sum()
    result["tail_share"] = contribution / total if total else 0.0
    return result.sort_values("tail_contribution_gbp_m", ascending=False).reset_index(drop=True)


def reverse_stress_lgd_multiplier(
    portfolio: pd.DataFrame,
    loss_capacity_gbp_m: float,
    confidence: float = 0.995,
    simulations: int = 30_000,
    seed: int = 42,
) -> dict[str, float | str]:
    """Find the LGD multiplier that first pushes portfolio VaR above capacity."""
    if loss_capacity_gbp_m <= 0:
        raise ValueError("loss capacity must be positive")
    clean = validate_export_portfolio(portfolio)
    base = simulate_export_credit_losses(
        clean, simulations=simulations, confidence=confidence, seed=seed
    )
    if base.loss_var >= loss_capacity_gbp_m:
        return {
            "lgd_multiplier": 1.0,
            "stressed_var_gbp_m": base.loss_var,
            "status": "Capacity already exceeded",
        }
    low, high = 1.0, 4.0
    for _ in range(24):
        midpoint = (low + high) / 2
        stressed = clean.copy()
        stressed["lgd"] = np.minimum(stressed["lgd"] * midpoint, 1.0)
        result = simulate_export_credit_losses(
            stressed, simulations=simulations, confidence=confidence, seed=seed
        )
        if result.loss_var >= loss_capacity_gbp_m:
            high = midpoint
        else:
            low = midpoint
    stressed = clean.copy()
    stressed["lgd"] = np.minimum(stressed["lgd"] * high, 1.0)
    final = simulate_export_credit_losses(
        stressed, simulations=simulations, confidence=confidence, seed=seed
    )
    return {
        "lgd_multiplier": high,
        "stressed_var_gbp_m": final.loss_var,
        "status": "Capacity breached" if final.loss_var >= loss_capacity_gbp_m else "Not breached",
    }