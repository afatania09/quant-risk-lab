import pandas as pd
import pytest

from quant_risk.risk_appetite import (
    RiskAppetiteLimits,
    deal_early_warning_register,
    portfolio_risk_appetite,
    risk_appetite_report,
)


@pytest.fixture
def portfolio():
    return pd.read_csv("data/synthetic_export_credit_portfolio.csv")


def test_scorecard_has_complete_unique_controls(portfolio):
    result = portfolio_risk_appetite(
        portfolio,
        loss_var_gbp_m=450,
        expected_shortfall_gbp_m=550,
        loss_capacity_gbp_m=650,
    )
    assert len(result) == 8
    assert result["control_id"].is_unique
    assert set(result["status"]) <= {"Green", "Amber", "Red"}


def test_capacity_breach_is_red(portfolio):
    result = portfolio_risk_appetite(
        portfolio,
        loss_var_gbp_m=600,
        expected_shortfall_gbp_m=700,
        loss_capacity_gbp_m=650,
    ).set_index("control_id")
    assert result.loc["RA01", "status"] == "Red"
    assert result.loc["RA02", "status"] == "Red"


def test_invalid_thresholds_and_inputs_are_rejected(portfolio):
    with pytest.raises(ValueError):
        RiskAppetiteLimits(var_capacity_amber=0.9, var_capacity_red=0.8)
    with pytest.raises(ValueError):
        portfolio_risk_appetite(
            portfolio,
            loss_var_gbp_m=1,
            expected_shortfall_gbp_m=2,
            loss_capacity_gbp_m=0,
        )


def test_watchlist_detects_red_and_amber_triggers(portfolio):
    stressed = portfolio.copy()
    stressed.loc[0, ["pd", "ifrs9_stage", "country_risk_grade"]] = [0.06, 3, 7]
    result = deal_early_warning_register(stressed)
    first = result.loc[result["deal_id"].eq(stressed.loc[0, "deal_id"])].iloc[0]
    assert first["status"] == "Red"
    assert first["trigger_count"] >= 3
    assert "IFRS 9 Stage 3" in first["triggers"]


def test_report_contains_exceptions_and_governance(portfolio):
    scorecard = portfolio_risk_appetite(
        portfolio,
        loss_var_gbp_m=600,
        expected_shortfall_gbp_m=700,
        loss_capacity_gbp_m=650,
    )
    watchlist = deal_early_warning_register(portfolio)
    report = risk_appetite_report(scorecard, watchlist)
    assert "Overall portfolio status: Red" in report
    assert "Governance actions" in report
