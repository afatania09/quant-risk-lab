"""Operational portfolio analytics for export-credit decision support."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd
from openpyxl.styles import Font, PatternFill

from .export_credit import (
    country_limit_report,
    risk_contributions,
    simulate_export_credit_losses,
    validate_export_portfolio,
)


def create_monthly_snapshot(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Create a deterministic prior-month snapshot for the demonstrator.

    The transformation is explicit and reproducible. It represents normal run-off,
    a small number of credit migrations, one exited deal and one current-month deal.
    """
    current = portfolio.copy().reset_index(drop=True)
    previous = current.copy()
    previous["ead_gbp_m"] = previous["ead_gbp_m"] / 0.985
    previous.loc[previous.index % 7 == 0, "pd"] /= 1.20
    previous.loc[previous.index % 9 == 0, "lgd"] /= 1.08
    if len(previous) > 1:
        previous = previous.iloc[:-1].copy()
    exited = current.iloc[[0]].copy()
    exited["deal_id"] = "EC000"
    exited["project"] = "Completed prior-month facility"
    exited["ead_gbp_m"] = 55.0
    exited["pd"] = 0.012
    previous = pd.concat([previous, exited], ignore_index=True)
    return previous


def risk_movement_attribution(previous: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """Exactly reconcile expected-loss movement into EAD, cover, PD and LGD drivers."""
    old = validate_export_portfolio(previous).set_index("deal_id")
    new = validate_export_portfolio(current).set_index("deal_id")
    rows: list[dict[str, float | str]] = []
    for deal_id in old.index.union(new.index):
        if deal_id not in old.index:
            value = float(new.loc[deal_id, "expected_loss_gbp_m"])
            drivers = {"New business": value}
        elif deal_id not in new.index:
            value = -float(old.loc[deal_id, "expected_loss_gbp_m"])
            drivers = {"Repayment / exit": value}
        else:
            o, n = old.loc[deal_id], new.loc[deal_id]
            e0, g0, p0, l0 = o["ead_gbp_m"], o["guarantee_share"], o["pd"], o["lgd"]
            e1, g1, p1, l1 = n["ead_gbp_m"], n["guarantee_share"], n["pd"], n["lgd"]
            drivers = {
                "Exposure / run-off": (e1 - e0) * g0 * p0 * l0,
                "Cover change": e1 * (g1 - g0) * p0 * l0,
                "PD / rating migration": e1 * g1 * (p1 - p0) * l0,
                "LGD / recovery": e1 * g1 * p1 * (l1 - l0),
            }
        for driver, change in drivers.items():
            rows.append({"deal_id": deal_id, "driver": driver, "change_gbp_m": change})
    detail = pd.DataFrame(rows)
    summary = detail.groupby("driver", as_index=False)["change_gbp_m"].sum()
    opening = float(old["expected_loss_gbp_m"].sum())
    closing = float(new["expected_loss_gbp_m"].sum())
    summary["opening_el_gbp_m"] = opening
    summary["closing_el_gbp_m"] = closing
    summary["reconciliation_difference_gbp_m"] = closing - opening - summary["change_gbp_m"].sum()
    return summary.sort_values("change_gbp_m", key=abs, ascending=False).reset_index(drop=True)


def multi_year_cashflows(
    portfolio: pd.DataFrame,
    horizon_years: int = 15,
    discount_rate: float = 0.04,
    recovery_lag_years: int = 2,
) -> pd.DataFrame:
    """Project exposure, premium, expected claims and delayed recoveries by year."""
    if horizon_years < 1 or discount_rate <= -1 or recovery_lag_years < 0:
        raise ValueError("invalid projection assumptions")
    clean = validate_export_portfolio(portfolio)
    years = np.arange(1, horizon_years + 1)
    claims = np.zeros(horizon_years)
    recoveries = np.zeros(horizon_years)
    exposure = np.zeros(horizon_years)
    premium = np.zeros(horizon_years)
    for deal in clean.itertuples():
        maturity = max(int(getattr(deal, "maturity_years", 1)), 1)
        for year in years:
            if year > maturity:
                continue
            start_ead = deal.covered_ead_gbp_m * (maturity - year + 1) / maturity
            survival = (1.0 - deal.pd) ** (year - 1)
            marginal_default = survival * deal.pd
            exposure[year - 1] += start_ead * survival
            premium[year - 1] += start_ead * deal.premium_rate * survival
            claim = start_ead * marginal_default * deal.lgd
            claims[year - 1] += claim
            recovery_year = year - 1 + recovery_lag_years
            if recovery_year < horizon_years:
                recoveries[recovery_year] += start_ead * marginal_default * (1.0 - deal.lgd)
    discount = 1.0 / (1.0 + discount_rate) ** years
    result = pd.DataFrame(
        {
            "year": years,
            "surviving_exposure_gbp_m": exposure,
            "premium_income_gbp_m": premium,
            "expected_claims_gbp_m": claims,
            "delayed_recoveries_gbp_m": recoveries,
        }
    )
    result["net_expected_cost_gbp_m"] = claims - recoveries - premium
    result["discounted_net_cost_gbp_m"] = result["net_expected_cost_gbp_m"] * discount
    return result


def optimise_reinsurance(
    portfolio: pd.DataFrame,
    budget_gbp_m: float = 15.0,
    ceded_share: float = 0.50,
    price_rate: float = 0.012,
    simulations: int = 12_000,
) -> pd.DataFrame:
    """Greedily allocate quota-share cover using tail-risk reduction per pound spent."""
    if budget_gbp_m <= 0 or not 0 < ceded_share <= 1 or price_rate <= 0:
        raise ValueError("invalid reinsurance assumptions")
    clean = validate_export_portfolio(portfolio)
    contrib = risk_contributions(clean, simulations=simulations).set_index("deal_id")
    candidates = clean[["deal_id", "country", "sector", "covered_ead_gbp_m"]].copy()
    candidates["cost_gbp_m"] = candidates["covered_ead_gbp_m"] * ceded_share * price_rate
    candidates["tail_risk_reduction_gbp_m"] = (
        candidates["deal_id"].map(contrib["tail_contribution_gbp_m"]) * ceded_share
    )
    candidates["risk_reduction_per_cost"] = (
        candidates["tail_risk_reduction_gbp_m"] / candidates["cost_gbp_m"]
    )
    candidates = candidates.sort_values("risk_reduction_per_cost", ascending=False)
    running = candidates["cost_gbp_m"].cumsum()
    candidates["recommended"] = running <= budget_gbp_m
    candidates["cumulative_cost_gbp_m"] = running
    return candidates.reset_index(drop=True)


def monte_carlo_convergence(
    portfolio: pd.DataFrame,
    sample_sizes: tuple[int, ...] = (2_000, 5_000, 10_000, 25_000),
    confidence: float = 0.995,
) -> pd.DataFrame:
    """Measure stability of portfolio tail metrics as simulation count increases."""
    rows = []
    for size in sample_sizes:
        result = simulate_export_credit_losses(
            portfolio, simulations=size, confidence=confidence, seed=42
        )
        rows.append(
            {"simulations": size, "expected_loss_gbp_m": result.expected_loss,
             "loss_var_gbp_m": result.loss_var, "expected_shortfall_gbp_m": result.expected_shortfall}
        )
    frame = pd.DataFrame(rows)
    benchmark = frame.iloc[-1]["loss_var_gbp_m"]
    frame["var_difference_from_benchmark_pct"] = np.where(
        benchmark, (frame["loss_var_gbp_m"] / benchmark - 1.0) * 100.0, 0.0
    )
    return frame


def management_workbook(
    portfolio: pd.DataFrame,
    movement: pd.DataFrame,
    cashflows: pd.DataFrame,
    reinsurance: pd.DataFrame,
    validation: pd.DataFrame,
) -> bytes:
    """Return a formatted Excel management-information pack."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        validate_export_portfolio(portfolio).to_excel(
            writer, sheet_name="Portfolio", index=False
        )
        country_limit_report(portfolio).to_excel(
            writer, sheet_name="Country Limits", index=False
        )
        movement.to_excel(writer, sheet_name="Monthly Movement", index=False)
        cashflows.to_excel(writer, sheet_name="Cashflow Forecast", index=False)
        reinsurance.to_excel(writer, sheet_name="APM Reinsurance", index=False)
        validation.to_excel(writer, sheet_name="Model Validation", index=False)
        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor="16344D")
            for column in sheet.columns:
                width = min(max(len(str(cell.value or "")) for cell in column) + 2, 32)
                sheet.column_dimensions[column[0].column_letter].width = width
    return output.getvalue()
