"""Statistical validation tests for VaR forecasts."""

from __future__ import annotations

import numpy as np
from scipy.stats import chi2


def kupiec_test(breaches: np.ndarray, expected_rate: float = 0.01) -> dict[str, float]:
    """Kupiec likelihood-ratio test of unconditional VaR coverage."""
    hits = np.asarray(breaches, dtype=bool)
    n, x = hits.size, int(hits.sum())
    if n == 0 or not 0 < expected_rate < 1:
        raise ValueError("breaches cannot be empty and expected_rate must be in (0, 1)")
    observed = np.clip(x / n, 1e-12, 1 - 1e-12)
    null_ll = (n - x) * np.log(1 - expected_rate) + x * np.log(expected_rate)
    alt_ll = (n - x) * np.log(1 - observed) + x * np.log(observed)
    statistic = float(-2 * (null_ll - alt_ll))
    return {
        "statistic": statistic,
        "p_value": float(chi2.sf(statistic, df=1)),
        "breaches": x,
        "observations": n,
        "breach_rate": float(x / n),
        "expected_rate": float(expected_rate),
    }


def christoffersen_independence_test(breaches: np.ndarray) -> dict[str, float]:
    """Christoffersen test for independence (non-clustering) of VaR breaches."""
    hits = np.asarray(breaches, dtype=int)
    if hits.size < 2 or np.any((hits != 0) & (hits != 1)):
        raise ValueError("provide at least two binary breach observations")
    previous, current = hits[:-1], hits[1:]
    n00 = int(((previous == 0) & (current == 0)).sum())
    n01 = int(((previous == 0) & (current == 1)).sum())
    n10 = int(((previous == 1) & (current == 0)).sum())
    n11 = int(((previous == 1) & (current == 1)).sum())

    def ratio(successes: int, total: int) -> float:
        return float(np.clip(successes / total if total else 0.0, 1e-12, 1 - 1e-12))

    pi0, pi1 = ratio(n01, n00 + n01), ratio(n11, n10 + n11)
    pi = ratio(n01 + n11, n00 + n01 + n10 + n11)
    independent_ll = (n00 + n10) * np.log(1 - pi) + (n01 + n11) * np.log(pi)
    markov_ll = (
        n00 * np.log(1 - pi0)
        + n01 * np.log(pi0)
        + n10 * np.log(1 - pi1)
        + n11 * np.log(pi1)
    )
    statistic = float(-2 * (independent_ll - markov_ll))
    return {
        "statistic": statistic,
        "p_value": float(chi2.sf(statistic, df=1)),
        "n00": n00,
        "n01": n01,
        "n10": n10,
        "n11": n11,
    }


def christoffersen_conditional_coverage_test(
    breaches: np.ndarray, expected_rate: float = 0.01
) -> dict[str, float]:
    """Joint likelihood-ratio test of correct coverage and breach independence."""
    uc = kupiec_test(breaches, expected_rate=expected_rate)
    ind = christoffersen_independence_test(breaches)
    statistic = float(uc["statistic"] + ind["statistic"])
    return {
        "statistic": statistic,
        "p_value": float(chi2.sf(statistic, df=2)),
        "coverage_statistic": float(uc["statistic"]),
        "independence_statistic": float(ind["statistic"]),
    }


def basel_traffic_light(breaches: int, observations: int = 250) -> str:
    """Indicative Basel-style traffic-light classification for 99% daily VaR.

    The canonical 250-observation thresholds are green for 0-4 breaches,
    yellow for 5-9, and red for 10 or more. For other sample sizes, this helper
    intentionally refuses to extrapolate regulatory thresholds.
    """
    if observations != 250:
        raise ValueError("Basel traffic-light thresholds are defined here only for 250 observations")
    if breaches < 0 or breaches > observations:
        raise ValueError("breaches must lie between 0 and observations")
    if breaches <= 4:
        return "green"
    if breaches <= 9:
        return "yellow"
    return "red"
