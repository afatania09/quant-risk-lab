import pandas as pd
import pytest

from quant_risk.country_risk import (
    assess_country,
    country_briefing,
    early_warnings,
    latest_country_values,
)

BASE = {
    "gdp_growth": 4.0,
    "inflation": 4.0,
    "current_account": -1.0,
    "reserves_months": 6.0,
    "external_debt_gni": 35.0,
    "political_stability": 0.0,
    "government_effectiveness": 0.2,
    "rule_of_law": 0.1,
}


def test_assessment_is_bounded_and_components_reconcile():
    result = assess_country(BASE)
    assert 0 <= result.score <= 100
    assert result.coverage == pytest.approx(1.0)
    assert result.components["effective_weight"].sum() == pytest.approx(1.0)
    assert result.components["weighted_contribution"].sum() == pytest.approx(result.score)


def test_deteriorating_inflation_increases_risk():
    stressed = BASE | {"inflation": 25.0}
    assert assess_country(stressed).score > assess_country(BASE).score


def test_missing_data_is_reweighted_and_disclosed():
    sparse = {"gdp_growth": 3.0, "inflation": 5.0}
    result = assess_country(sparse)
    assert result.coverage == pytest.approx(0.28)
    assert result.components["effective_weight"].sum() == pytest.approx(1.0)


def test_early_warning_thresholds():
    warnings = early_warnings({"inflation": 20, "reserves_months": 2.5})
    assert "Inflation above 15%" in warnings
    assert "Import cover below three months" in warnings


def test_latest_values_allow_different_release_vintages():
    panel = pd.DataFrame(
        [
            {"country": "Example", "indicator": "inflation", "year": 2023, "value": 5.0},
            {"country": "Example", "indicator": "inflation", "year": 2024, "value": 4.0},
            {"country": "Example", "indicator": "rule_of_law", "year": 2023, "value": 0.1},
        ]
    )
    values, oldest_vintage = latest_country_values(panel, "Example")
    assert values == {"inflation": 4.0, "rule_of_law": 0.1}
    assert oldest_vintage == 2023


def test_briefing_labels_independent_method_and_exposure():
    text = country_briefing("Example", assess_country(BASE), 125.0, 0.75, 2023)
    assert "Independent model score" in text
    assert "£125.0m" in text
    assert "not a sovereign rating" in text
