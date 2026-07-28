import numpy as np
import pandas as pd
import pytest

from quant_risk.credit import expected_credit_loss, merton_default_probability
from quant_risk.cva import unilateral_cva
from quant_risk.market import historical_var_es, monte_carlo_var_es, parametric_var_es
from quant_risk.stress import apply_factor_shocks


@pytest.fixture
def returns():
    rng = np.random.default_rng(7)
    return pd.DataFrame(rng.normal(0.0002, 0.01, size=(2_000, 3)))


def test_all_var_methods_produce_positive_tail_risk(returns):
    positions = np.array([1_000_000, 750_000, 500_000])
    for method in (historical_var_es, parametric_var_es, monte_carlo_var_es):
        var, es = method(returns, positions)
        assert var > 0
        assert es >= var


def test_expected_loss_identity():
    assert expected_credit_loss(0.02, 0.45, 10_000_000) == pytest.approx(90_000)


def test_safer_firm_has_lower_merton_pd():
    safe = merton_default_probability(200, 100, 0.2, 0.04)
    risky = merton_default_probability(120, 100, 0.4, 0.04)
    assert safe < risky


def test_cva_matches_discrete_formula():
    result = unilateral_cva(
        np.array([100, 80]), np.array([0.01, 0.03]), np.array([1.0, 0.95]), 0.4
    )
    assert result == pytest.approx(0.6 * (100 * 0.01 + 80 * 0.95 * 0.02))


def test_stress_contributions_reconcile():
    result = apply_factor_shocks(
        {"equity": 2_000_000, "rates": -50_000},
        {"equity": -0.2, "rates": 1.5},
    )
    assert result["total"] == result["equity"] + result["rates"]