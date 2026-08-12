import pytest

from quant_risk.product_pricing import (
    amortisation_schedule,
    price_export_credit,
    shortlist_products,
)
from quant_risk.underwriting import assess_corporate_obligor, project_finance_pd


def assessment(**overrides):
    values = {
        "debt_to_ebitda": 2.5,
        "interest_coverage": 4.5,
        "debt_service_coverage": 1.5,
        "current_ratio": 1.4,
        "operating_margin": 0.12,
        "revenue_growth": 0.05,
        "country_risk_score": 40,
        "years_trading": 10,
    }
    return assess_corporate_obligor(**(values | overrides))


def test_obligor_components_reconcile_to_score():
    result = assessment()
    assert result.components["weight"].sum() == pytest.approx(1)
    assert result.components["contribution"].sum() == pytest.approx(result.score)
    assert 0 < result.one_year_pd < 1


def test_weaker_financials_increase_pd_and_generate_flags():
    weak = assessment(debt_to_ebitda=7, interest_coverage=1.2, debt_service_coverage=0.9)
    strong = assessment(debt_to_ebitda=1, interest_coverage=8, debt_service_coverage=2)
    assert weak.one_year_pd > strong.one_year_pd
    assert "High leverage" in weak.flags


def test_project_finance_overlays_behave_monotonically():
    strong = project_finance_pd(0.02, 1.8, "Low", "Strong")
    weak = project_finance_pd(0.02, 1.0, "High", "Weak")
    assert weak > strong


def test_equal_principal_schedule_amortises_fully():
    schedule = amortisation_schedule(100, 5, drawdown_years=1, payments_per_year=2)
    assert schedule.iloc[-1]["closing_exposure_gbp_m"] == pytest.approx(0)
    assert schedule["principal_gbp_m"].sum() == pytest.approx(100)


def test_higher_pd_increases_required_premium():
    common = {
        "product": "Buyer Credit Facility", "amount_gbp_m": 100, "lgd": 0.5,
        "tenor_years": 7, "drawdown_years": 1,
    }
    low = price_export_credit(**common, annual_pd=0.01)
    high = price_export_credit(**common, annual_pd=0.05)
    assert high.required_premium_gbp_m > low.required_premium_gbp_m


def test_external_floor_binds_quote_but_is_not_model_price():
    result = price_export_credit(
        product="Direct Lending Facility", amount_gbp_m=50, annual_pd=0.005,
        lgd=0.35, tenor_years=5, oecd_mpr_floor_rate=0.08,
    )
    assert result.quoted_upfront_rate == pytest.approx(0.08)
    assert result.floor_upfront_rate > result.model_upfront_rate


def test_product_default_cover_is_applied():
    result = price_export_credit(
        product="Export Insurance Policy", amount_gbp_m=20, annual_pd=0.02,
        lgd=0.5, tenor_years=3,
    )
    assert result.exposure_gbp_m == pytest.approx(19)


def test_product_shortlist_matches_transaction_need():
    result = shortlist_products("Support a contract bond", 10, 2)
    assert result.iloc[0]["product"] == "Bond Support Scheme"


def test_product_shortlist_flags_gef_scale():
    result = shortlist_products("Provide exporter working capital", 40, 3)
    gef = result.loc[result["product"] == "General Export Facility"].iloc[0]
    assert gef["fit_score"] < 90
    assert "£25m" in gef["rationale"]
