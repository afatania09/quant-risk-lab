import numpy as np
import pandas as pd

from quant_risk.liquidity import (
    liquidation_horizon,
    liquidity_adjusted_var,
    liquidity_profile,
    stressed_bid_ask_cost,
)
from quant_risk.portfolio import (
    concentration_metrics,
    diversification_ratio,
    drawdown_statistics,
    effective_number_of_bets,
    marginal_risk_contribution,
    portfolio_volatility,
)
from quant_risk.validation import basel_traffic_light, christoffersen_conditional_coverage_test


def sample_returns():
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        rng.multivariate_normal(
            [0.0002, 0.0001, 0.00015],
            [[0.0001, 0.00002, 0.00001], [0.00002, 0.00008, 0.000015], [0.00001, 0.000015, 0.00012]],
            size=600,
        ),
        columns=["equity", "rates", "credit"],
    )


def test_portfolio_risk_contributions_reconcile():
    returns = sample_returns()
    weights = np.array([0.5, 0.3, 0.2])
    sigma = portfolio_volatility(returns, weights)
    rc = marginal_risk_contribution(returns, weights)
    assert sigma > 0
    assert np.isclose(rc.sum(), sigma)
    assert diversification_ratio(returns, weights) >= 1.0
    assert 1.0 <= effective_number_of_bets(rc) <= 3.0


def test_concentration_metrics_equal_book():
    metrics = concentration_metrics(pd.Series([25.0, 25.0, 25.0, 25.0]))
    assert np.isclose(metrics["hhi"], 0.25)
    assert np.isclose(metrics["effective_positions"], 4.0)
    assert np.isclose(metrics["top_1_share"], 0.25)


def test_drawdown_statistics():
    returns = pd.Series([0.10, -0.05, -0.10, 0.20, 0.05])
    stats = drawdown_statistics(returns)
    assert stats["max_drawdown"] < 0
    assert stats["drawdown_duration_periods"] >= 1


def test_liquidity_metrics():
    assert np.isclose(liquidation_horizon(10_000_000, 5_000_000, 0.10), 20.0)
    assert np.isclose(liquidity_adjusted_var(1_000_000, 4), 2_000_000)
    positions = pd.Series({"A": 10_000_000, "B": 1_000_000})
    adv = pd.Series({"A": 5_000_000, "B": 10_000_000})
    profile = liquidity_profile(positions, adv)
    assert profile.loc["A", "liquidation_days"] > profile.loc["B", "liquidation_days"]
    spreads = pd.Series({"A": 20.0, "B": 10.0})
    assert stressed_bid_ask_cost(positions, spreads, 2.0) > 0


def test_backtesting_extensions():
    breaches = np.zeros(250, dtype=int)
    breaches[[25, 80, 140]] = 1
    result = christoffersen_conditional_coverage_test(breaches, expected_rate=0.01)
    assert result["statistic"] >= 0
    assert 0 <= result["p_value"] <= 1
    assert basel_traffic_light(3) == "green"
    assert basel_traffic_light(6) == "yellow"
    assert basel_traffic_light(10) == "red"
