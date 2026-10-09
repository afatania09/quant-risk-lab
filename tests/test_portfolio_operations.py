from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from quant_risk.export_credit import validate_export_portfolio
from quant_risk.portfolio_operations import (
    create_monthly_snapshot,
    management_workbook,
    monte_carlo_convergence,
    multi_year_cashflows,
    optimise_reinsurance,
    risk_movement_attribution,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def portfolio():
    return pd.read_csv(ROOT / "data" / "synthetic_export_credit_portfolio.csv")


def test_risk_movement_reconciles_exactly(portfolio):
    previous = create_monthly_snapshot(portfolio)
    bridge = risk_movement_attribution(previous, portfolio)
    opening = validate_export_portfolio(previous)["expected_loss_gbp_m"].sum()
    closing = validate_export_portfolio(portfolio)["expected_loss_gbp_m"].sum()
    assert bridge["change_gbp_m"].sum() == pytest.approx(closing - opening)
    assert bridge["reconciliation_difference_gbp_m"].abs().max() < 1e-10
    assert {"New business", "Repayment / exit", "PD / rating migration"} <= set(
        bridge["driver"]
    )


def test_multi_year_cashflows_run_off(portfolio):
    forecast = multi_year_cashflows(portfolio, horizon_years=15)
    assert len(forecast) == 15
    assert (forecast[["surviving_exposure_gbp_m", "premium_income_gbp_m"]] >= 0).all().all()
    assert forecast.iloc[-1]["surviving_exposure_gbp_m"] == pytest.approx(0.0)
    assert forecast["surviving_exposure_gbp_m"].is_monotonic_decreasing


def test_reinsurance_optimiser_respects_budget(portfolio):
    result = optimise_reinsurance(portfolio, budget_gbp_m=8.0, simulations=4_000)
    selected = result[result["recommended"]]
    assert selected["cost_gbp_m"].sum() <= 8.0
    assert (result["risk_reduction_per_cost"] >= 0).all()


def test_convergence_uses_largest_run_as_benchmark(portfolio):
    result = monte_carlo_convergence(portfolio, sample_sizes=(1_000, 2_000, 4_000))
    assert result.iloc[-1]["var_difference_from_benchmark_pct"] == pytest.approx(0.0)
    assert (result["expected_shortfall_gbp_m"] >= result["loss_var_gbp_m"]).all()


def test_management_workbook_contains_expected_sheets(portfolio):
    previous = create_monthly_snapshot(portfolio)
    movement = risk_movement_attribution(previous, portfolio)
    cashflows = multi_year_cashflows(portfolio, horizon_years=5)
    reinsurance = optimise_reinsurance(portfolio, simulations=2_000)
    validation = monte_carlo_convergence(portfolio, sample_sizes=(1_000, 2_000))
    payload = management_workbook(portfolio, movement, cashflows, reinsurance, validation)
    workbook = pd.ExcelFile(BytesIO(payload))
    assert {
        "Portfolio",
        "Country Limits",
        "Monthly Movement",
        "Cashflow Forecast",
        "APM Reinsurance",
        "Model Validation",
    } == set(workbook.sheet_names)
