"""Liquidity-risk measures for portfolios and stressed liquidation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def liquidation_horizon(position_value: float, average_daily_volume: float, participation_rate: float = 0.10) -> float:
    """Estimated trading days required to liquidate a position."""
    if position_value < 0 or average_daily_volume <= 0 or not 0 < participation_rate <= 1:
        raise ValueError("position_value must be non-negative, ADV positive and participation_rate in (0, 1]")
    return float(position_value / (average_daily_volume * participation_rate))


def liquidity_adjusted_var(var: float, horizon_days: float, base_horizon_days: float = 1.0) -> float:
    """Square-root-of-time liquidity adjustment to a base VaR estimate."""
    if var < 0 or horizon_days <= 0 or base_horizon_days <= 0:
        raise ValueError("VaR must be non-negative and horizons must be positive")
    return float(var * np.sqrt(horizon_days / base_horizon_days))


def stressed_bid_ask_cost(
    positions: pd.Series,
    bid_ask_spread_bps: pd.Series,
    stress_multiplier: float = 2.0,
) -> float:
    """One-way stressed liquidation cost using half-spread convention."""
    p = pd.Series(positions, dtype=float)
    s = pd.Series(bid_ask_spread_bps, dtype=float).reindex(p.index)
    if p.isna().any() or s.isna().any() or (s < 0).any() or stress_multiplier < 0:
        raise ValueError("positions/spreads must align; spreads and stress multiplier must be non-negative")
    half_spread = s / 20_000.0
    return float(np.sum(np.abs(p) * half_spread * stress_multiplier))


def liquidity_profile(
    positions: pd.Series,
    average_daily_volume: pd.Series,
    participation_rate: float = 0.10,
) -> pd.DataFrame:
    """Position-level liquidation horizons and portfolio liquidity buckets."""
    p = pd.Series(positions, dtype=float)
    adv = pd.Series(average_daily_volume, dtype=float).reindex(p.index)
    if adv.isna().any() or (adv <= 0).any() or not 0 < participation_rate <= 1:
        raise ValueError("ADV must align, be positive, and participation_rate must be in (0, 1]")
    horizon = np.abs(p) / (adv * participation_rate)
    bucket = pd.cut(
        horizon,
        bins=[-np.inf, 1, 5, 20, np.inf],
        labels=["<=1 day", "2-5 days", "6-20 days", ">20 days"],
    )
    return pd.DataFrame({
        "position": p,
        "adv": adv,
        "liquidation_days": horizon,
        "liquidity_bucket": bucket,
    })
