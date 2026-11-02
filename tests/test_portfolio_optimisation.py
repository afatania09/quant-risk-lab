from pathlib import Path

import pandas as pd
import pytest

from quant_risk.portfolio_optimisation import (
    challenger_model_comparison,
    optimise_risk_transfer,
    risk_transfer_concentration,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def portfolio():
    return pd.read_csv(ROOT / "data" / "synthetic_export_credit_portfolio.csv")


def test_constrained_optimiser_respects_budget_and_concentration(portfolio):
    budget = 12.0
    result = optimise_risk_transfer(
        portfolio,
        budget_gbp_m=budget,
        max_country_budget_share=0.30,
        max_sector_budget_share=0.35,
        simulations=4_000,
    )
    selected = result[result["recommended"]]
    assert selected["cost_gbp_m"].sum() <= budget + 1e-8
    assert selected.groupby("country")["cost_gbp_m"].sum().max() <= budget * 0.30 + 1e-8
    assert selected.groupby("sector")["cost_gbp_m"].sum().max() <= budget * 0.35 + 1e-8
    assert selected["tail_risk_reduction_gbp_m"].sum() > 0


def test_invalid_concentration_limit_is_rejected(portfolio):
    with pytest.raises(ValueError):
        optimise_risk_transfer(portfolio, max_country_budget_share=1.2)


def test_transfer_concentration_reconciles(portfolio):
    result = optimise_risk_transfer(portfolio, simulations=3_000)
    concentration = risk_transfer_concentration(result)
    for dimension in ["Country", "Sector"]:
        subset = concentration[concentration["dimension"] == dimension]
        assert subset["cost_share"].sum() == pytest.approx(1.0)


def test_challenger_comparison_is_reproducible_and_complete(portfolio):
    first = challenger_model_comparison(portfolio, simulations=8_000, seed=8)
    second = challenger_model_comparison(portfolio, simulations=8_000, seed=8)
    pd.testing.assert_frame_equal(first, second)
    assert set(first["model"]) == {"Multi-factor primary", "One-factor challenger"}
    assert (first["expected_shortfall_gbp_m"] >= first["loss_var_gbp_m"]).all()
