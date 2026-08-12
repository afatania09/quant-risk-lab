"""Explainable obligor credit assessment for export-credit underwriting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CreditAssessment:
    """Transparent obligor assessment with an indicative one-year PD."""

    score: float
    grade: str
    one_year_pd: float
    components: pd.DataFrame
    flags: tuple[str, ...]


def _risk(value: float, strong: float, weak: float) -> float:
    return float(np.clip((value - strong) / (weak - strong) * 100, 0, 100))


def assess_corporate_obligor(
    *,
    debt_to_ebitda: float,
    interest_coverage: float,
    debt_service_coverage: float,
    current_ratio: float,
    operating_margin: float,
    revenue_growth: float,
    country_risk_score: float,
    years_trading: int,
) -> CreditAssessment:
    """Map financial and country indicators to an explainable corporate risk grade.

    Ratios are screening inputs, not a substitute for audited accounts or judgement.
    Margins and growth are decimals (for example, 0.12 means 12%).
    """
    inputs = {
        "Leverage": (_risk(debt_to_ebitda, 1.0, 7.0), 0.20, debt_to_ebitda),
        "Interest coverage": (_risk(interest_coverage, 8.0, 1.0), 0.15, interest_coverage),
        "Debt service coverage": (
            _risk(debt_service_coverage, 2.0, 0.8), 0.18, debt_service_coverage
        ),
        "Liquidity": (_risk(current_ratio, 2.0, 0.6), 0.10, current_ratio),
        "Operating margin": (_risk(operating_margin, 0.25, -0.05), 0.10, operating_margin),
        "Revenue growth": (_risk(revenue_growth, 0.15, -0.20), 0.07, revenue_growth),
        "Country risk": (float(np.clip(country_risk_score, 0, 100)), 0.15, country_risk_score),
        "Trading history": (_risk(float(years_trading), 15.0, 1.0), 0.05, years_trading),
    }
    score = sum(risk * weight for risk, weight, _ in inputs.values())
    cutoffs = [15, 25, 35, 45, 55, 65, 75, 101]
    grades = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2"]
    pds = [0.001, 0.0025, 0.006, 0.012, 0.025, 0.05, 0.10, 0.20]
    bucket = int(np.searchsorted(cutoffs, score, side="right"))
    rows = [
        {
            "component": name,
            "raw_value": raw,
            "risk_score": risk,
            "weight": weight,
            "contribution": risk * weight,
        }
        for name, (risk, weight, raw) in inputs.items()
    ]
    components = pd.DataFrame(rows).sort_values("contribution", ascending=False)
    flags = []
    if debt_service_coverage < 1.1:
        flags.append("Debt-service coverage has limited headroom")
    if interest_coverage < 2:
        flags.append("Weak interest coverage")
    if debt_to_ebitda > 5:
        flags.append("High leverage")
    if current_ratio < 1:
        flags.append("Potential short-term liquidity pressure")
    if operating_margin < 0:
        flags.append("Negative operating margin")
    if country_risk_score >= 60:
        flags.append("Elevated country-risk overlay")
    return CreditAssessment(
        score=score,
        grade=grades[bucket],
        one_year_pd=pds[bucket],
        components=components,
        flags=tuple(flags),
    )


def project_finance_pd(
    base_pd: float,
    debt_service_coverage: float,
    completion_risk: str,
    offtake_strength: str,
) -> float:
    """Apply transparent project-finance overlays to a base annual PD."""
    completion = {"Low": 0.85, "Medium": 1.0, "High": 1.35}
    offtake = {"Strong": 0.80, "Adequate": 1.0, "Weak": 1.30}
    if completion_risk not in completion or offtake_strength not in offtake:
        raise ValueError("invalid project-finance overlay")
    dscr_factor = float(np.clip(1.4 / debt_service_coverage, 0.70, 1.75))
    return float(min(base_pd * completion[completion_risk] * offtake[offtake_strength] * dscr_factor, 0.5))
