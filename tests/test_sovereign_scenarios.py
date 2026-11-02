from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_risk.sovereign_scenarios import (
    illustrative_transition_matrix,
    macro_scenario_comparison,
    migration_projection,
    parameter_uncertainty,
    stressed_transition_matrix,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def portfolio():
    return pd.read_csv(ROOT / "data" / "synthetic_export_credit_portfolio.csv")


def test_transition_matrices_are_stochastic_and_stress_increases_default():
    base = illustrative_transition_matrix()
    stressed = stressed_transition_matrix(base)
    assert np.allclose(base.sum(axis=1), 1.0)
    assert np.allclose(stressed.sum(axis=1), 1.0)
    assert (stressed.loc[range(1, 8), "D"] >= base.loc[range(1, 8), "D"]).all()
    assert stressed.loc["D", "D"] == pytest.approx(1.0)


def test_migration_projection_is_reproducible_and_stress_is_worse(portfolio):
    base_distribution, base_losses = migration_projection(
        portfolio, years=4, simulations=4_000, seed=7
    )
    repeated_distribution, repeated_losses = migration_projection(
        portfolio, years=4, simulations=4_000, seed=7
    )
    _, stressed_losses = migration_projection(
        portfolio, years=4, simulations=4_000, stressed=True, seed=7
    )
    pd.testing.assert_frame_equal(base_distribution, repeated_distribution)
    pd.testing.assert_frame_equal(base_losses, repeated_losses)
    assert stressed_losses.iloc[-1]["mean_cumulative_default_loss_gbp_m"] > base_losses.iloc[-1][
        "mean_cumulative_default_loss_gbp_m"
    ]
    annual_totals = base_distribution.groupby("year")["portfolio_share"].sum()
    assert np.allclose(annual_totals, 1.0)


def test_parameter_uncertainty_brackets_point_estimate(portfolio):
    result = parameter_uncertainty(portfolio, draws=8_000, seed=5)
    assert result["p05_gbp_m"] < result["point_estimate_gbp_m"] < result["p95_gbp_m"]
    assert len(result["draws"]) == 8_000


def test_macro_scenarios_include_base_and_raise_tail_risk(portfolio):
    result = macro_scenario_comparison(portfolio, simulations=6_000)
    base = result.loc[result["scenario"] == "Base"].iloc[0]
    assert len(result) == 5
    assert base["change_in_var_gbp_m"] == pytest.approx(0.0)
    assert result["loss_var_gbp_m"].max() > base["loss_var_gbp_m"]
    assert (result["expected_shortfall_gbp_m"] >= result["loss_var_gbp_m"]).all()
