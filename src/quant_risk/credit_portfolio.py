"""Credit migration and correlated portfolio-loss simulation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def migrate_ratings(
    current_ratings: list[str],
    transition_matrix: pd.DataFrame,
    seed: int = 42,
) -> list[str]:
    """Draw one-period rating migrations from a row-stochastic transition matrix."""
    if not np.allclose(transition_matrix.sum(axis=1), 1.0):
        raise ValueError("each transition-matrix row must sum to one")
    rng = np.random.default_rng(seed)
    states = transition_matrix.columns.to_list()
    return [
        str(rng.choice(states, p=transition_matrix.loc[rating].to_numpy(dtype=float)))
        for rating in current_ratings
    ]


def simulate_credit_losses(
    default_probabilities: np.ndarray,
    lgds: np.ndarray,
    exposures: np.ndarray,
    asset_correlation: float = 0.20,
    simulations: int = 100_000,
    seed: int = 42,
) -> np.ndarray:
    """One-factor Gaussian copula simulation of correlated obligor defaults."""
    pd_vector = np.asarray(default_probabilities, dtype=float)
    lgd_vector = np.asarray(lgds, dtype=float)
    ead_vector = np.asarray(exposures, dtype=float)
    if not (pd_vector.shape == lgd_vector.shape == ead_vector.shape):
        raise ValueError("PD, LGD and exposure vectors must have equal shape")
    if np.any((pd_vector <= 0) | (pd_vector >= 1)):
        raise ValueError("default probabilities must be in (0, 1)")
    if np.any((lgd_vector < 0) | (lgd_vector > 1)) or np.any(ead_vector < 0):
        raise ValueError("LGDs must be in [0, 1] and exposures non-negative")
    if not 0 <= asset_correlation < 1:
        raise ValueError("asset_correlation must be in [0, 1)")
    rng = np.random.default_rng(seed)
    systematic = rng.standard_normal((simulations, 1))
    idiosyncratic = rng.standard_normal((simulations, pd_vector.size))
    latent = (
        np.sqrt(asset_correlation) * systematic
        + np.sqrt(1.0 - asset_correlation) * idiosyncratic
    )
    defaults = latent < norm.ppf(pd_vector)
    return defaults @ (lgd_vector * ead_vector)


def credit_var_es(
    losses: np.ndarray, confidence: float = 0.999
) -> tuple[float, float, float]:
    """Expected loss, unexpected-loss VaR and tail Expected Shortfall."""
    values = np.asarray(losses, dtype=float)
    expected = float(values.mean())
    quantile = float(np.quantile(values, confidence))
    tail = values[values >= quantile]
    return expected, max(0.0, quantile - expected), float(tail.mean())
