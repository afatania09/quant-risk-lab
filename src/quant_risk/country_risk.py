"""Transparent sovereign-risk monitoring using public macroeconomic indicators."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.request import urlopen

import numpy as np
import pandas as pd

INDICATORS = {
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "inflation": "FP.CPI.TOTL.ZG",
    "current_account": "BN.CAB.XOKA.GD.ZS",
    "reserves_months": "FI.RES.TOTL.MO",
    "external_debt_gni": "DT.DOD.DECT.GN.ZS",
    "political_stability": "PV.EST",
    "government_effectiveness": "GE.EST",
    "rule_of_law": "RL.EST",
}

WEIGHTS = {
    "gdp_growth": 0.14,
    "inflation": 0.14,
    "current_account": 0.10,
    "reserves_months": 0.14,
    "external_debt_gni": 0.12,
    "political_stability": 0.14,
    "government_effectiveness": 0.11,
    "rule_of_law": 0.11,
}


@dataclass(frozen=True)
class CountryAssessment:
    """A point-in-time, independently modelled country-risk assessment."""

    score: float
    grade: str
    coverage: float
    components: pd.DataFrame
    warnings: tuple[str, ...]
    top_drivers: tuple[str, ...]


def _linear_risk(value: float, good: float, bad: float) -> float:
    """Map an indicator to 0–100 risk, supporting both threshold directions."""
    if good == bad:
        raise ValueError("good and bad thresholds must differ")
    risk = (value - good) / (bad - good) * 100
    return float(np.clip(risk, 0, 100))


def component_scores(values: dict[str, float]) -> dict[str, float]:
    """Calculate transparent component risk scores from 0 (low) to 100 (high)."""
    rules = {
        "gdp_growth": (6.0, -3.0),
        "inflation": (2.0, 20.0),
        "current_account": (3.0, -10.0),
        "reserves_months": (9.0, 1.0),
        "external_debt_gni": (20.0, 100.0),
        "political_stability": (1.0, -2.0),
        "government_effectiveness": (1.0, -1.5),
        "rule_of_law": (1.0, -1.5),
    }
    return {
        name: _linear_risk(float(values[name]), *thresholds)
        for name, thresholds in rules.items()
        if name in values and pd.notna(values[name])
    }


def early_warnings(values: dict[str, float]) -> tuple[str, ...]:
    """Return plain-language early-warning signals for severe indicator readings."""
    tests = [
        ("gdp_growth", lambda x: x < 0, "Economic contraction"),
        ("inflation", lambda x: x > 15, "Inflation above 15%"),
        ("current_account", lambda x: x < -5, "Current-account deficit below -5% of GDP"),
        ("reserves_months", lambda x: x < 3, "Import cover below three months"),
        ("external_debt_gni", lambda x: x > 70, "External debt above 70% of GNI"),
        ("political_stability", lambda x: x < -1, "Weak political-stability indicator"),
        ("government_effectiveness", lambda x: x < -0.75, "Weak government effectiveness"),
        ("rule_of_law", lambda x: x < -0.75, "Weak rule-of-law indicator"),
    ]
    return tuple(
        label
        for name, test, label in tests
        if name in values and pd.notna(values[name]) and test(float(values[name]))
    )


def assess_country(values: dict[str, float]) -> CountryAssessment:
    """Score available indicators, reweighting missing data rather than treating it as safe."""
    scores = component_scores(values)
    if not scores:
        raise ValueError("at least one recognised indicator is required")
    available_weight = sum(WEIGHTS[name] for name in scores)
    overall = sum(scores[name] * WEIGHTS[name] for name in scores) / available_weight
    grade = pd.cut(
        [overall], bins=[-1, 20, 40, 60, 80, 101],
        labels=["Low", "Moderate", "Elevated", "High", "Very high"],
    )[0]
    rows = [
        {
            "indicator": name,
            "value": float(values[name]),
            "risk_score": score,
            "base_weight": WEIGHTS[name],
            "effective_weight": WEIGHTS[name] / available_weight,
            "weighted_contribution": score * WEIGHTS[name] / available_weight,
        }
        for name, score in scores.items()
    ]
    components = pd.DataFrame(rows).sort_values("weighted_contribution", ascending=False)
    drivers = tuple(components.head(3)["indicator"].str.replace("_", " ").str.title())
    return CountryAssessment(
        score=float(overall), grade=str(grade), coverage=available_weight,
        components=components, warnings=early_warnings(values), top_drivers=drivers,
    )


def fetch_world_bank_panel(
    iso3_codes: list[str], start_year: int = 2019, end_year: int = 2025
) -> pd.DataFrame:
    """Download a tidy indicator panel from the World Bank v2 API."""
    rows: list[dict[str, object]] = []
    country_path = ";".join(iso3_codes)
    for name, code in INDICATORS.items():
        url = (
            f"https://api.worldbank.org/v2/country/{country_path}/indicator/{code}"
            f"?format=json&date={start_year}:{end_year}&per_page=2000"
        )
        with urlopen(url, timeout=30) as response:
            payload = json.load(response)
        if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
            continue
        for item in payload[1]:
            if item.get("value") is not None:
                rows.append(
                    {
                        "country": item["country"]["value"],
                        "iso3": item["countryiso3code"],
                        "year": int(item["date"]),
                        "indicator": name,
                        "value": float(item["value"]),
                    }
                )
    return pd.DataFrame(rows).sort_values(["country", "indicator", "year"])


def latest_country_values(panel: pd.DataFrame, country: str) -> tuple[dict[str, float], int]:
    """Select the latest non-null reading for each indicator and report oldest vintage."""
    selected = panel.loc[panel["country"] == country].sort_values("year")
    if selected.empty:
        raise ValueError(f"country not found in panel: {country}")
    latest = selected.groupby("indicator", as_index=False).tail(1)
    return dict(zip(latest["indicator"], latest["value"])), int(latest["year"].min())


def country_briefing(
    country: str,
    assessment: CountryAssessment,
    exposure_gbp_m: float,
    limit_utilisation: float,
    data_vintage: int,
    cover_context: str = "Refer to current UKEF country cover policy",
) -> str:
    """Create a concise, decision-oriented Markdown country briefing."""
    warnings = "\n".join(f"- {item}" for item in assessment.warnings) or "- No severe threshold triggered."
    drivers = ", ".join(assessment.top_drivers)
    return f"""# {country}: country risk and exposure brief

**Independent model score:** {assessment.score:.1f}/100 ({assessment.grade})  
**Portfolio exposure:** £{exposure_gbp_m:,.1f}m  
**Illustrative limit utilisation:** {limit_utilisation:.1%}  
**Indicator coverage:** {assessment.coverage:.0%} of model weight  
**Oldest latest-observation vintage:** {data_vintage}

## Decision view

The largest modelled risk contributions are **{drivers}**. {cover_context}.

## Early-warning signals

{warnings}

## Interpretation and controls

The score is an independent screening tool built from public World Bank indicators. It is
not a sovereign rating, an OECD classification, UKEF policy or a substitute for expert
country analysis. Review indicator vintages, political events, obligor structure, currency,
security and the current UKEF country cover policy before any decision.
"""
