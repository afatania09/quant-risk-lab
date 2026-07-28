"""Market-risk measures expressed as positive monetary losses."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def _portfolio_pnl(returns: pd.DataFrame, positions: np.ndarray) -> np.ndarray:
    returns = pd.DataFrame(returns).dropna()
    positions = np.asarray(positions, dtype=float)
    if returns.shape[1] != positions.size:
        raise ValueError("positions must contain one market value for each return series")
    if returns.empty:
        raise ValueError("returns cannot be empty")
    return returns.to_numpy() @ positions


def historical_var_es(
    returns: pd.DataFrame, positions: np.ndarray, confidence: float = 0.99
) -> tuple[float, float]:
    """Historical VaR and Expected Shortfall from observed portfolio P&L."""
    pnl = _portfolio_pnl(returns, positions)
    cutoff = np.quantile(pnl, 1.0 - confidence)
    return float(max(0.0, -cutoff)), float(max(0.0, -pnl[pnl <= cutoff].mean()))


def parametric_var_es(
    returns: pd.DataFrame, positions: np.ndarray, confidence: float = 0.99
) -> tuple[float, float]:
    """Delta-normal VaR and ES, retaining the estimated portfolio mean."""
    pnl = _portfolio_pnl(returns, positions)
    mean, sigma = pnl.mean(), pnl.std(ddof=1)
    z = norm.ppf(1.0 - confidence)
    var = -(mean + sigma * z)
    es = -(mean - sigma * norm.pdf(z) / (1.0 - confidence))
    return float(max(0.0, var)), float(max(0.0, es))


def monte_carlo_var_es(
    returns: pd.DataFrame,
    positions: np.ndarray,
    confidence: float = 0.99,
    simulations: int = 100_000,
    seed: int = 42,
) -> tuple[float, float]:
    """Correlated Gaussian Monte Carlo VaR and ES."""
    clean = pd.DataFrame(returns).dropna()
    if clean.shape[1] != np.asarray(positions).size:
        raise ValueError("positions must contain one market value for each return series")
    rng = np.random.default_rng(seed)
    simulated = rng.multivariate_normal(
        clean.mean().to_numpy(), clean.cov().to_numpy(), size=simulations
    )
    pnl = simulated @ np.asarray(positions, dtype=float)
    cutoff = np.quantile(pnl, 1.0 - confidence)
    return float(max(0.0, -cutoff)), float(max(0.0, -pnl[pnl <= cutoff].mean()))


def backtest_var(actual_pnl: np.ndarray, var_forecasts: np.ndarray) -> dict[str, float]:
    """Count VaR breaches and calculate Kupiec's unconditional-coverage statistic."""
    pnl = np.asarray(actual_pnl, dtype=float)
    forecasts = np.asarray(var_forecasts, dtype=float)
    if pnl.shape != forecasts.shape:
        raise ValueError("actual_pnl and var_forecasts must have equal shape")
    breaches = pnl < -forecasts
    n, x = pnl.size, int(breaches.sum())
    rate = x / n
    return {"observations": n, "breaches": x, "breach_rate": rate}


def rolling_historical_var(
    returns: pd.DataFrame,
    positions: np.ndarray,
    window: int = 250,
    confidence: float = 0.99,
) -> pd.Series:
    """One-day-ahead rolling historical VaR forecasts."""
    pnl = pd.Series(
        _portfolio_pnl(returns, positions),
        index=pd.DataFrame(returns).dropna().index,
        name="pnl",
    )
    return -pnl.rolling(window).quantile(1.0 - confidence).shift(1)


def filtered_historical_var_es(
    returns: pd.DataFrame,
    positions: np.ndarray,
    confidence: float = 0.99,
    decay: float = 0.94,
) -> tuple[float, float]:
    """Filtered historical simulation using EWMA volatility scaling."""
    pnl = _portfolio_pnl(returns, positions)
    variance = np.empty_like(pnl)
    variance[0] = np.var(pnl, ddof=1)
    for index in range(1, pnl.size):
        variance[index] = decay * variance[index - 1] + (1.0 - decay) * pnl[index - 1] ** 2
    volatility = np.sqrt(np.maximum(variance, np.finfo(float).eps))
    standardized = pnl / volatility
    scenarios = standardized * volatility[-1]
    cutoff = np.quantile(scenarios, 1.0 - confidence)
    return float(max(0.0, -cutoff)), float(max(0.0, -scenarios[scenarios <= cutoff].mean()))


def component_parametric_var(
    returns: pd.DataFrame,
    positions: np.ndarray,
    confidence: float = 0.99,
) -> pd.Series:
    """Euler decomposition of zero-mean delta-normal VaR by position."""
    clean = pd.DataFrame(returns).dropna()
    weights = np.asarray(positions, dtype=float)
    covariance = clean.cov().to_numpy()
    portfolio_sigma = float(np.sqrt(weights @ covariance @ weights))
    if portfolio_sigma == 0:
        raise ValueError("portfolio volatility must be positive")
    z = norm.ppf(confidence)
    contributions = z * weights * (covariance @ weights) / portfolio_sigma
    return pd.Series(contributions, index=clean.columns, name="component_var")