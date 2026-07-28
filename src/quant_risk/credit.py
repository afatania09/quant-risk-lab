"""Credit-risk measures: expected loss and a Merton structural model."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def expected_credit_loss(pd: float, lgd: float, ead: float) -> float:
    """One-period expected credit loss: probability of default × LGD × exposure."""
    if not 0 <= pd <= 1 or not 0 <= lgd <= 1 or ead < 0:
        raise ValueError("pd and lgd must be in [0, 1], and ead must be non-negative")
    return float(pd * lgd * ead)


def merton_default_probability(
    asset_value: float,
    debt_face_value: float,
    asset_volatility: float,
    risk_free_rate: float,
    horizon_years: float = 1.0,
) -> float:
    """Risk-neutral probability that firm asset value falls below debt at horizon."""
    if min(asset_value, debt_face_value, asset_volatility, horizon_years) <= 0:
        raise ValueError("asset value, debt, volatility and horizon must be positive")
    distance = (
        np.log(asset_value / debt_face_value)
        + (risk_free_rate - 0.5 * asset_volatility**2) * horizon_years
    ) / (asset_volatility * np.sqrt(horizon_years))
    return float(norm.cdf(-distance))
