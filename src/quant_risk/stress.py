"""Historical and hypothetical portfolio stress testing."""

from __future__ import annotations

import numpy as np
import pandas as pd


def historical_stress(returns: pd.DataFrame, positions: np.ndarray, worst_days: int = 10) -> pd.Series:
    """Return the worst observed daily portfolio P&L outcomes."""
    pnl = pd.DataFrame(returns).dropna().mul(np.asarray(positions), axis=1).sum(axis=1)
    return pnl.nsmallest(worst_days)


def apply_factor_shocks(
    exposures: dict[str, float], shocks: dict[str, float]
) -> dict[str, float]:
    """Apply linear shocks to named monetary factor exposures."""
    missing = set(shocks) - set(exposures)
    if missing:
        raise ValueError(f"missing exposures for: {sorted(missing)}")
    contributions = {factor: exposures[factor] * shock for factor, shock in shocks.items()}
    contributions["total"] = sum(contributions.values())
    return contributions
