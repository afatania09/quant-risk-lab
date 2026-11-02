from pathlib import Path

import pandas as pd
import pytest

from quant_risk.export_credit import validate_export_portfolio
from quant_risk.portfolio_planning import (
    build_approved_portfolio,
    evaluate_new_business_pipeline,
    optimise_new_business_plan,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def portfolio():
    return pd.read_csv(ROOT / "data" / "synthetic_export_credit_portfolio.csv")


@pytest.fixture
def pipeline():
    return pd.read_csv(ROOT / "data" / "synthetic_new_business_pipeline.csv")


def test_pipeline_evaluation_is_reproducible(portfolio, pipeline):
    first = evaluate_new_business_pipeline(portfolio, pipeline, simulations=3_000, seed=8)
    second = evaluate_new_business_pipeline(portfolio, pipeline, simulations=3_000, seed=8)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == len(pipeline)
    assert (first["incremental_var_gbp_m"] >= 0).all()


def test_plan_respects_commitment_risk_and_country_limits(portfolio, pipeline):
    evaluation = evaluate_new_business_pipeline(portfolio, pipeline, simulations=3_000)
    decisions = optimise_new_business_plan(
        portfolio,
        evaluation,
        commitment_budget_gbp_m=500.0,
        var_headroom_gbp_m=150.0,
    )
    approved = decisions[decisions["approved"]]
    assert approved["covered_ead_gbp_m"].sum() <= 500.0 + 1e-8
    assert approved["incremental_var_gbp_m"].sum() <= 150.0 + 1e-8
    combined = validate_export_portfolio(build_approved_portfolio(portfolio, pipeline, decisions))
    for country, group in combined.groupby("country"):
        assert group["covered_ead_gbp_m"].sum() <= group["country_limit_gbp_m"].iloc[0] + 1e-8


def test_zero_capacity_approves_nothing(portfolio, pipeline):
    evaluation = evaluate_new_business_pipeline(portfolio, pipeline, simulations=2_000)
    decisions = optimise_new_business_plan(
        portfolio,
        evaluation,
        commitment_budget_gbp_m=0.0,
        var_headroom_gbp_m=0.0,
    )
    assert not decisions["approved"].any()


def test_pipeline_requires_strategic_score(portfolio, pipeline):
    with pytest.raises(ValueError):
        evaluate_new_business_pipeline(portfolio, pipeline.drop(columns="strategic_score"))
