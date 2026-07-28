from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_risk.export_credit import (
    concentration_report,
    country_limit_report,
    reverse_stress_lgd_multiplier,
    risk_contributions,
    simulate_export_credit_losses,
    validate_export_portfolio,
)
from quant_risk.export_credit_finance import (
    apply_reinsurance,
    monthly_risk_bridge,
    premium_adequacy,
    scenario_weighted_ecl,
)
from quant_risk.reporting import executive_risk_report

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def portfolio():
    return pd.read_csv(ROOT / "data" / "synthetic_export_credit_portfolio.csv")


@pytest.fixture
def scenarios():
    return pd.read_csv(ROOT / "data" / "ifrs9_scenarios.csv")


def test_portfolio_validation_derives_financial_fields(portfolio):
    clean = validate_export_portfolio(portfolio)
    first = clean.iloc[0]
    assert first["covered_ead_gbp_m"] == pytest.approx(
        first["ead_gbp_m"] * first["guarantee_share"]
    )
    assert first["expected_loss_gbp_m"] == pytest.approx(
        first["covered_ead_gbp_m"] * first["pd"] * first["lgd"]
    )


def test_concentrations_reconcile_to_total_exposure(portfolio):
    clean = validate_export_portfolio(portfolio)
    for dimension in ["country", "sector", "product"]:
        report = concentration_report(clean, dimension)
        assert report["exposure_gbp_m"].sum() == pytest.approx(
            clean["covered_ead_gbp_m"].sum()
        )
        assert report["portfolio_share"].sum() == pytest.approx(1.0)


def test_country_limit_status_and_headroom(portfolio):
    report = country_limit_report(portfolio)
    assert set(report["status"]) <= {"Green", "Amber", "Red"}
    assert np.allclose(
        report["headroom_gbp_m"], report["limit_gbp_m"] - report["exposure_gbp_m"]
    )


def test_export_credit_simulation_is_reproducible(portfolio):
    first = simulate_export_credit_losses(portfolio, simulations=10_000, seed=9)
    second = simulate_export_credit_losses(portfolio, simulations=10_000, seed=9)
    assert np.array_equal(first.losses, second.losses)
    assert first.expected_shortfall >= first.loss_var >= first.expected_loss


def test_simulated_mean_is_close_to_analytical_expected_loss(portfolio):
    clean = validate_export_portfolio(portfolio)
    result = simulate_export_credit_losses(portfolio, simulations=100_000, seed=1)
    analytical = clean["expected_loss_gbp_m"].sum()
    assert result.expected_loss == pytest.approx(analytical, rel=0.07)


def test_tail_contributions_reconcile(portfolio):
    result = risk_contributions(portfolio, simulations=15_000)
    assert result["tail_share"].sum() == pytest.approx(1.0)
    assert (result["tail_contribution_gbp_m"] >= 0).all()


def test_reverse_stress_returns_valid_multiplier(portfolio):
    result = reverse_stress_lgd_multiplier(
        portfolio, loss_capacity_gbp_m=600, simulations=8_000
    )
    assert result["lgd_multiplier"] >= 1
    assert result["stressed_var_gbp_m"] >= 0


def test_ifrs9_scenario_weights_and_stage_horizons(portfolio, scenarios):
    result = scenario_weighted_ecl(portfolio, scenarios)
    assert (result["scenario_weighted_ecl_gbp_m"] > 0).all()
    assert (result.loc[result["ifrs9_stage"] == 1, "horizon_years"] == 1).all()
    assert (
        result.loc[result["ifrs9_stage"] > 1, "horizon_years"]
        == portfolio.set_index("deal_id").loc[
            result.loc[result["ifrs9_stage"] > 1, "deal_id"], "maturity_years"
        ].to_numpy()
    ).all()


def test_premium_adequacy_reconciles(portfolio):
    result = premium_adequacy(portfolio)
    assert np.allclose(
        result["premium_surplus_gbp_m"],
        result["annual_premium_gbp_m"] - result["required_premium_gbp_m"],
    )


def test_reinsurance_never_increases_loss_before_premium():
    losses = np.array([0.0, 100.0, 300.0, 800.0])
    result = apply_reinsurance(
        losses, "Excess of loss", attachment_gbp_m=200, limit_gbp_m=400, annual_premium_gbp_m=0
    )
    assert (result["net_loss_gbp_m"] <= result["gross_loss_gbp_m"]).all()
    assert (result["reinsurance_recovery_gbp_m"] >= 0).all()


def test_monthly_bridge_identifies_new_and_exited_deals(portfolio):
    previous = portfolio.iloc[:5].copy()
    current = portfolio.iloc[1:6].copy()
    bridge = monthly_risk_bridge(previous, current)
    assert bridge.loc[bridge["deal_id"] == "EC001", "movement"].iloc[0] == "Repayment/exit"
    assert bridge.loc[bridge["deal_id"] == "EC006", "movement"].iloc[0] == "New business"


def test_executive_report_contains_decision_metrics(portfolio):
    simulation = simulate_export_credit_losses(portfolio, simulations=5_000)
    report = executive_risk_report(portfolio, simulation)
    assert "Executive assessment" in report
    assert "loss-at-risk" in report
    assert "UKEF's proprietary PRISM" in report