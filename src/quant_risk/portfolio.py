"""Portfolio-level diagnostics for market and multi-asset risk."""

from __future__ import annotations

import numpy as np
import pandas as pd


def portfolio_volatility(returns: pd.DataFrame, weights: np.ndarray) -> float:
    """Annualised portfolio volatility from daily returns and asset weights."""
    clean = pd.DataFrame(returns).dropna()
    w = np.asarray(weights, dtype=float)
    if clean.empty:
        raise ValueError("returns cannot be empty")
    if clean.shape[1] != w.size:
        raise ValueError("weights must contain one value for each return series")
    covariance = clean.cov().to_numpy() * 252.0
    variance = float(w @ covariance @ w)
    return float(np.sqrt(max(variance, 0.0)))


def marginal_risk_contribution(returns: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    """Euler contribution of each asset to annualised portfolio volatility."""
    clean = pd.DataFrame(returns).dropna()
    w = np.asarray(weights, dtype=float)
    if clean.shape[1] != w.size:
        raise ValueError("weights must contain one value for each return series")
    covariance = clean.cov().to_numpy() * 252.0
    sigma = float(np.sqrt(max(w @ covariance @ w, 0.0)))
    if sigma <= 0:
        raise ValueError("portfolio volatility must be positive")
    contribution = w * (covariance @ w) / sigma
    return pd.Series(contribution, index=clean.columns, name="volatility_contribution")


def diversification_ratio(returns: pd.DataFrame, weights: np.ndarray) -> float:
    """Weighted standalone volatility divided by portfolio volatility."""
    clean = pd.DataFrame(returns).dropna()
    w = np.asarray(weights, dtype=float)
    if clean.shape[1] != w.size:
        raise ValueError("weights must contain one value for each return series")
    standalone = clean.std(ddof=1).to_numpy() * np.sqrt(252.0)
    portfolio_sigma = portfolio_volatility(clean, w)
    if portfolio_sigma <= 0:
        raise ValueError("portfolio volatility must be positive")
    return float(np.sum(np.abs(w) * standalone) / portfolio_sigma)


def effective_number_of_bets(risk_contributions: pd.Series) -> float:
    """Herfindahl-based effective number of independent risk contributors."""
    rc = np.asarray(risk_contributions, dtype=float)
    rc = np.abs(rc)
    total = rc.sum()
    if total <= 0:
        raise ValueError("risk contributions must contain positive total risk")
    shares = rc / total
    return float(1.0 / np.sum(shares**2))


def drawdown_statistics(portfolio_returns: pd.Series) -> dict[str, float]:
    """Maximum drawdown, peak-to-trough duration and recovery diagnostics."""
    r = pd.Series(portfolio_returns, dtype=float).dropna()
    if r.empty:
        raise ValueError("portfolio_returns cannot be empty")
    wealth = (1.0 + r).cumprod()
    peaks = wealth.cummax()
    drawdowns = wealth / peaks - 1.0
    trough = drawdowns.idxmin()
    max_drawdown = float(drawdowns.loc[trough])
    peak_value = peaks.loc[trough]
    peak_candidates = wealth.loc[:trough]
    peak_date = peak_candidates[peak_candidates == peak_value].index[-1]
    after = wealth.loc[trough:]
    recovered = after[after >= peak_value]
    recovery_periods = float("nan") if recovered.empty else float(after.index.get_loc(recovered.index[0]))
    duration = float(wealth.loc[peak_date:trough].shape[0] - 1)
    return {
        "max_drawdown": max_drawdown,
        "drawdown_duration_periods": duration,
        "recovery_periods": recovery_periods,
    }


def concentration_metrics(exposures: pd.Series) -> dict[str, float]:
    """Exposure HHI, top-1/top-5 share and effective number of positions."""
    x = pd.Series(exposures, dtype=float).dropna()
    if x.empty or (x < 0).any() or x.sum() <= 0:
        raise ValueError("exposures must be non-negative with positive total exposure")
    shares = (x / x.sum()).sort_values(ascending=False)
    hhi = float(np.sum(shares.to_numpy() ** 2))
    return {
        "hhi": hhi,
        "effective_positions": float(1.0 / hhi),
        "top_1_share": float(shares.iloc[:1].sum()),
        "top_5_share": float(shares.iloc[:5].sum()),
    }
