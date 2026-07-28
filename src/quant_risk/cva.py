"""A transparent unilateral CVA implementation."""

from __future__ import annotations

import numpy as np


def unilateral_cva(
    expected_exposure: np.ndarray,
    cumulative_default_probability: np.ndarray,
    discount_factors: np.ndarray,
    recovery_rate: float = 0.40,
) -> float:
    """Discrete CVA = LGD × sum(discounted EE × marginal default probability)."""
    ee = np.asarray(expected_exposure, dtype=float)
    cumulative_pd = np.asarray(cumulative_default_probability, dtype=float)
    discount = np.asarray(discount_factors, dtype=float)
    if not (ee.shape == cumulative_pd.shape == discount.shape):
        raise ValueError("all term structures must have equal shape")
    if np.any(np.diff(cumulative_pd) < 0) or np.any((cumulative_pd < 0) | (cumulative_pd > 1)):
        raise ValueError("cumulative default probability must be increasing and in [0, 1]")
    if not 0 <= recovery_rate <= 1:
        raise ValueError("recovery_rate must be in [0, 1]")
    marginal_pd = np.diff(np.r_[0.0, cumulative_pd])
    return float((1.0 - recovery_rate) * np.sum(discount * ee * marginal_pd))
