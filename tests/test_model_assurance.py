from datetime import datetime, timezone

import pandas as pd

from quant_risk.model_assurance import (
    assurance_gate,
    assurance_report,
    build_run_manifest,
    data_quality_report,
    model_inventory,
)


def portfolio() -> pd.DataFrame:
    return pd.read_csv("data/synthetic_export_credit_portfolio.csv")


def test_default_portfolio_passes_critical_data_controls():
    report = data_quality_report(portfolio())
    assert len(report) == 8
    assert not ((report["severity"] == "Red") & (report["status"] == "Fail")).any()


def test_quality_report_detects_duplicate_and_inconsistent_limit():
    data = portfolio()
    duplicate = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    duplicate.loc[duplicate.index[-1], "country_limit_gbp_m"] *= 2
    report = data_quality_report(duplicate).set_index("control_id")
    assert report.loc["DQ03", "status"] == "Fail"
    assert report.loc["DQ07", "status"] == "Fail"


def test_manifest_is_reproducible_and_order_independent():
    data = portfolio()
    kwargs = {
        "confidence": 0.995,
        "simulations": 25_000,
        "generated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    first = build_run_manifest(data, **kwargs)
    second = build_run_manifest(data.sample(frac=1, random_state=3), **kwargs)
    assert first == second
    assert len(first["data_sha256"]) == 64


def test_assurance_gate_blocks_critical_failure_and_warns_on_challenge():
    quality = data_quality_report(portfolio())
    green = assurance_gate(quality, convergence_gap_pct=2, challenger_var_gap_pct=4)
    assert green["decision"] == "Release"
    amber = assurance_gate(quality, convergence_gap_pct=7, challenger_var_gap_pct=12)
    assert amber["decision"] == "Release with review"
    quality.loc[0, "status"] = "Fail"
    red = assurance_gate(quality, convergence_gap_pct=2, challenger_var_gap_pct=4)
    assert red["decision"] == "Do not release"
    assert not red["can_release"]


def test_inventory_and_report_are_reviewable():
    data = portfolio()
    quality = data_quality_report(data)
    manifest = build_run_manifest(data, confidence=0.99, simulations=5_000)
    gate = assurance_gate(quality, convergence_gap_pct=3, challenger_var_gap_pct=8)
    report = assurance_report(gate, manifest, quality)
    assert model_inventory()["model_id"].is_unique
    assert "Data SHA-256" in report
    assert manifest["run_id"] in report
