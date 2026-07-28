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


def bilateral_cva_dva(
    positive_exposure: np.ndarray,
    negative_exposure: np.ndarray,
    counterparty_cumulative_pd: np.ndarray,
    own_cumulative_pd: np.ndarray,
    discount_factors: np.ndarray,
    counterparty_recovery: float = 0.40,
    own_recovery: float = 0.40,
) -> dict[str, float]:
    """Simplified bilateral CVA/DVA without first-to-default dependence."""
    cva = unilateral_cva(
        positive_exposure,
        counterparty_cumulative_pd,
        discount_factors,
        counterparty_recovery,
    )
    dva = unilateral_cva(
        np.abs(negative_exposure),
        own_cumulative_pd,
        discount_factors,
        own_recovery,
    )
    return {"cva": cva, "dva": dva, "bilateral_adjustment": dva - cva}


def collateralised_exposure(
    mark_to_market: np.ndarray,
    threshold: float = 0.0,
    minimum_transfer_amount: float = 0.0,
) -> np.ndarray:
    """Positive exposure remaining after a simplified collateral agreement."""
    mtm = np.asarray(mark_to_market, dtype=float)
    required = np.maximum(mtm - threshold, 0.0)
    collateral = np.where(required >= minimum_transfer_amount, required, 0.0)
    return np.maximum(mtm - collateral, 0.0)
