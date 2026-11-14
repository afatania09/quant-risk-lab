"""Operational controls and reproducibility evidence for export-credit models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import pandas as pd

from .export_credit import REQUIRED_COLUMNS


def _control(
    control_id: str,
    control: str,
    severity: str,
    exceptions: int,
    detail: str,
) -> dict[str, str | int]:
    return {
        "control_id": control_id,
        "control": control,
        "severity": severity,
        "status": "Pass" if exceptions == 0 else "Fail",
        "exceptions": int(exceptions),
        "detail": detail,
    }


def data_quality_report(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Run non-destructive completeness, validity and consistency controls."""
    missing = sorted(REQUIRED_COLUMNS - set(portfolio.columns))
    rows = [
        _control(
            "DQ01",
            "Required fields present",
            "Red",
            len(missing),
            "All required fields are present" if not missing else f"Missing: {', '.join(missing)}",
        )
    ]
    if missing:
        return pd.DataFrame(rows)

    required = sorted(REQUIRED_COLUMNS)
    rows.append(
        _control(
            "DQ02",
            "Required values complete",
            "Red",
            int(portfolio[required].isna().sum().sum()),
            "Null cells across required fields",
        )
    )
    rows.append(
        _control(
            "DQ03",
            "Deal identifiers unique",
            "Red",
            int(portfolio["deal_id"].duplicated(keep=False).sum()),
            "Rows with a duplicated deal identifier",
        )
    )

    numeric_columns = [
        "ead_gbp_m",
        "pd",
        "lgd",
        "guarantee_share",
        "premium_rate",
        "country_limit_gbp_m",
    ]
    numeric = portfolio[numeric_columns].apply(pd.to_numeric, errors="coerce")
    rows.append(
        _control(
            "DQ04",
            "Numeric fields parseable",
            "Red",
            int(numeric.isna().sum().sum()),
            "Non-numeric or missing cells across quantitative fields",
        )
    )
    probability_columns = ["pd", "lgd", "guarantee_share", "premium_rate"]
    range_exceptions = ((numeric[probability_columns] < 0) | (numeric[probability_columns] > 1))
    rows.append(
        _control(
            "DQ05",
            "Rates within zero and one",
            "Red",
            int(range_exceptions.sum().sum()),
            "Out-of-range PD, LGD, cover or premium-rate cells",
        )
    )
    exposure_exceptions = (numeric["ead_gbp_m"] < 0) | (numeric["country_limit_gbp_m"] <= 0)
    rows.append(
        _control(
            "DQ06",
            "Exposure and limits valid",
            "Red",
            int(exposure_exceptions.sum()),
            "Rows with negative exposure or non-positive country limit",
        )
    )
    limit_counts = portfolio.assign(_limit=numeric["country_limit_gbp_m"]).groupby("country")[
        "_limit"
    ].nunique(dropna=False)
    rows.append(
        _control(
            "DQ07",
            "Country limits internally consistent",
            "Amber",
            int((limit_counts > 1).sum()),
            "Countries assigned more than one limit",
        )
    )

    if numeric.isna().any().any() or range_exceptions.any().any() or exposure_exceptions.any():
        limit_breaches = 0
        limit_detail = "Not evaluated until critical validity controls pass"
    else:
        covered = numeric["ead_gbp_m"] * numeric["guarantee_share"]
        country_exposure = covered.groupby(portfolio["country"]).sum()
        country_limits = numeric["country_limit_gbp_m"].groupby(portfolio["country"]).min()
        limit_breaches = int((country_exposure >= country_limits).sum())
        limit_detail = "Countries at or above approved exposure limit"
    rows.append(
        _control("DQ08", "Country exposure within limit", "Amber", limit_breaches, limit_detail)
    )
    return pd.DataFrame(rows)


def model_inventory() -> pd.DataFrame:
    """Return the governed inventory of decision-support models in the workflow."""
    records = [
        ("EC-01", "Correlated export-credit loss", "Tier 1", "Portfolio Risk", "Annual", "Validated", "Gaussian latent factors and fixed LGD"),
        ("EC-02", "IFRS 9 scenario-weighted ECL", "Tier 1", "Credit Risk", "Annual", "Validated", "Illustrative stage and scenario assumptions"),
        ("EC-03", "Country risk screening", "Tier 2", "Country Risk", "Annual", "In use", "Public indicators are screening signals"),
        ("EC-04", "Product pricing and RAROC", "Tier 1", "Underwriting", "Annual", "In use", "Simplified capital and funding treatment"),
        ("EC-05", "Sovereign migration projection", "Tier 1", "Portfolio Risk", "Annual", "Challenger required", "Illustrative transition calibration"),
        ("EC-06", "Risk-transfer optimiser", "Tier 2", "Portfolio Management", "Annual", "In use", "Binary whole-deal allocation"),
        ("EC-07", "New-business planning optimiser", "Tier 1", "Portfolio Management", "Annual", "In use", "Additive incremental risk approximation"),
    ]
    return pd.DataFrame(
        records,
        columns=[
            "model_id",
            "model",
            "criticality",
            "owner",
            "validation_frequency",
            "status",
            "key_limitation",
        ],
    )


def build_run_manifest(
    portfolio: pd.DataFrame,
    *,
    confidence: float,
    simulations: int,
    seed: int = 42,
    model_version: str = "0.2.0",
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Create deterministic input fingerprints and a reviewable run manifest."""
    if not 0 < confidence < 1 or simulations <= 0:
        raise ValueError("confidence must be in (0, 1) and simulations positive")
    ordered = portfolio.sort_values(list(portfolio.columns)).reset_index(drop=True)
    canonical = ordered.to_csv(index=False, lineterminator="\n", float_format="%.12g")
    fingerprint = sha256(canonical.encode("utf-8")).hexdigest()
    parameters = {
        "confidence": float(confidence),
        "simulations": int(simulations),
        "seed": int(seed),
    }
    run_payload = json.dumps(
        {"data_sha256": fingerprint, "model_version": model_version, **parameters},
        sort_keys=True,
    )
    run_id = sha256(run_payload.encode("utf-8")).hexdigest()[:16]
    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return {
        "run_id": run_id,
        "generated_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "model_version": model_version,
        "data_sha256": fingerprint,
        "portfolio_rows": len(portfolio),
        "portfolio_countries": int(portfolio["country"].nunique()) if "country" in portfolio else None,
        "parameters": parameters,
    }


def assurance_gate(
    quality_report: pd.DataFrame,
    *,
    convergence_gap_pct: float,
    challenger_var_gap_pct: float,
) -> dict[str, Any]:
    """Apply explicit release thresholds to data and model-validation evidence."""
    failed = quality_report.loc[quality_report["status"].eq("Fail")]
    critical_failures = int(failed["severity"].eq("Red").sum())
    warnings = int(failed["severity"].eq("Amber").sum())
    reasons: list[str] = []
    if critical_failures:
        reasons.append(f"{critical_failures} critical data control(s) failed")
    if warnings:
        reasons.append(f"{warnings} data warning(s) require review")
    if abs(convergence_gap_pct) > 10:
        reasons.append("Monte Carlo convergence gap exceeds 10%")
    elif abs(convergence_gap_pct) > 5:
        reasons.append("Monte Carlo convergence gap exceeds 5%")
    if abs(challenger_var_gap_pct) > 25:
        reasons.append("challenger VaR gap exceeds 25%")
    elif abs(challenger_var_gap_pct) > 10:
        reasons.append("challenger VaR gap exceeds 10%")

    red = critical_failures > 0 or abs(convergence_gap_pct) > 10 or abs(challenger_var_gap_pct) > 25
    amber = warnings > 0 or abs(convergence_gap_pct) > 5 or abs(challenger_var_gap_pct) > 10
    rating = "Red" if red else "Amber" if amber else "Green"
    decision = "Do not release" if red else "Release with review" if amber else "Release"
    return {
        "rating": rating,
        "decision": decision,
        "can_release": not red,
        "critical_failures": critical_failures,
        "warnings": warnings,
        "reasons": reasons or ["All automated release thresholds passed"],
    }


def assurance_report(
    gate: dict[str, Any], manifest: dict[str, Any], quality_report: pd.DataFrame
) -> str:
    """Render an audit-ready Markdown summary of a controlled model run."""
    failed = quality_report.loc[quality_report["status"].eq("Fail")]
    exceptions = (
        "\n".join(
            f"- {row.control_id}: {row.control} — {row.exceptions} exception(s)"
            for row in failed.itertuples()
        )
        if not failed.empty
        else "- None"
    )
    reasons = "\n".join(f"- {reason}" for reason in gate["reasons"])
    return f"""# Model assurance report

**Run ID:** `{manifest['run_id']}`  
**Generated:** {manifest['generated_at_utc']}  
**Model version:** {manifest['model_version']}  
**Data SHA-256:** `{manifest['data_sha256']}`

## Release decision

**{gate['rating']} — {gate['decision']}**

{reasons}

## Data-quality exceptions

{exceptions}

## Reproducibility settings

- Portfolio rows: {manifest['portfolio_rows']}
- Countries: {manifest['portfolio_countries']}
- Confidence: {manifest['parameters']['confidence']:.3%}
- Simulations: {manifest['parameters']['simulations']:,}
- Random seed: {manifest['parameters']['seed']}

## Required review

Confirm input ownership, investigate every failed control, record any expert overlay, and obtain
the accountable model owner's approval before using results in a decision.
"""
