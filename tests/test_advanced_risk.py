import numpy as np
import pandas as pd
import pytest

from quant_risk.credit_portfolio import credit_var_es, migrate_ratings, simulate_credit_losses
from quant_risk.cva import bilateral_cva_dva, collateralised_exposure
from quant_risk.market import (
    component_parametric_var,
    filtered_historical_var_es,
    rolling_historical_var,
)
from quant_risk.validation import christoffersen_independence_test, kupiec_test


def test_component_var_reconciles_to_portfolio_var():
    rng = np.random.default_rng(1)
    returns = pd.DataFrame(rng.normal(0, 0.01, (2_000, 3)), columns=["A", "B", "C"])
    positions = np.array([1_000_000, 800_000, 600_000])
    components = component_parametric_var(returns, positions)
    covariance = returns.cov().to_numpy()
    expected = 2.326347874 * np.sqrt(positions @ covariance @ positions)
    assert components.sum() == pytest.approx(expected, rel=1e-6)


def test_rolling_var_does_not_use_same_day_return():
    returns = pd.DataFrame({"A": [0.01, -0.01, 0.02, -0.50]})
    forecast = rolling_historical_var(returns, np.array([100.0]), window=3, confidence=0.99)
    assert forecast.iloc[-1] < 10


def test_filtered_historical_es_is_at_least_var():
    rng = np.random.default_rng(2)
    returns = pd.DataFrame(rng.standard_t(5, (1_000, 2)) * 0.01)
    var, es = filtered_historical_var_es(returns, np.array([1_000_000, 1_000_000]))
    assert es >= var > 0


def test_kupiec_distinguishes_bad_coverage():
    good = kupiec_test(np.array([1] + [0] * 99), expected_rate=0.01)
    bad = kupiec_test(np.array([1] * 20 + [0] * 80), expected_rate=0.01)
    assert good["p_value"] > bad["p_value"]


def test_christoffersen_detects_clustering():
    independent = christoffersen_independence_test(np.array(([0] * 19 + [1]) * 10))
    clustered = christoffersen_independence_test(np.array(([0] * 18 + [1, 1]) * 10))
    assert independent["p_value"] > clustered["p_value"]


def test_rating_migration_is_reproducible():
    matrix = pd.DataFrame(
        [[0.9, 0.1], [0.2, 0.8]], index=["A", "D"], columns=["A", "D"]
    )
    first = migrate_ratings(["A", "A", "D"], matrix, seed=3)
    second = migrate_ratings(["A", "A", "D"], matrix, seed=3)
    assert first == second


def test_credit_simulation_expected_loss_is_reasonable():
    losses = simulate_credit_losses(
        np.array([0.02, 0.04]),
        np.array([0.5, 0.5]),
        np.array([1_000_000, 1_000_000]),
        simulations=200_000,
    )
    expected, unexpected, tail = credit_var_es(losses, confidence=0.99)
    assert expected == pytest.approx(30_000, rel=0.08)
    assert unexpected >= 0
    assert tail >= expected


def test_collateral_reduces_exposure_and_cva():
    mtm = np.array([100_000, 500_000, 1_000_000])
    collateralised = collateralised_exposure(mtm, threshold=100_000)
    assert np.all(collateralised <= mtm)
    result = bilateral_cva_dva(
        collateralised,
        np.array([0, -50_000, -100_000]),
        np.array([0.01, 0.02, 0.04]),
        np.array([0.01, 0.02, 0.03]),
        np.array([0.99, 0.97, 0.95]),
    )
    assert result["cva"] >= 0
    assert result["dva"] >= 0