"""Advanced market, credit and counterparty risk demonstrations."""

import numpy as np
import pandas as pd

from quant_risk.credit_portfolio import credit_var_es, simulate_credit_losses
from quant_risk.cva import bilateral_cva_dva, collateralised_exposure
from quant_risk.data import download_returns
from quant_risk.market import (
    component_parametric_var,
    filtered_historical_var_es,
    rolling_historical_var,
)
from quant_risk.validation import christoffersen_independence_test, kupiec_test


def market_risk_case() -> None:
    returns = download_returns(start="2018-01-01")
    positions = np.array([2_000_000, 2_000_000, 1_500_000, 1_500_000, 1_500_000, 1_500_000])
    var, es = filtered_historical_var_es(returns, positions)
    components = component_parametric_var(returns, positions)
    forecasts = rolling_historical_var(returns, positions).dropna()
    pnl = returns.mul(positions, axis=1).sum(axis=1).reindex(forecasts.index)
    breaches = (pnl < -forecasts).to_numpy()
    print(f"Filtered historical 99% VaR: ${var:,.0f}; ES: ${es:,.0f}")
    print("\nComponent parametric VaR:")
    print(components.sort_values(ascending=False).map("${:,.0f}".format).to_string())
    print("\nKupiec coverage:", kupiec_test(breaches))
    print("Christoffersen independence:", christoffersen_independence_test(breaches))


def credit_case() -> None:
    pd_vector = np.array([0.004, 0.006, 0.012, 0.020, 0.035, 0.060])
    lgds = np.array([0.40, 0.45, 0.45, 0.50, 0.55, 0.60])
    exposures = np.array([8, 7, 6, 5, 4, 3]) * 1_000_000
    losses = simulate_credit_losses(pd_vector, lgds, exposures, asset_correlation=0.25)
    expected, unexpected, tail = credit_var_es(losses)
    print(f"\nExpected credit loss: ${expected:,.0f}")
    print(f"99.9% unexpected-loss VaR: ${unexpected:,.0f}")
    print(f"99.9% tail loss: ${tail:,.0f}")


def counterparty_case() -> None:
    mtm_paths = np.array([0, 400_000, 900_000, 1_400_000, 1_000_000])
    collateralised = collateralised_exposure(
        mtm_paths, threshold=250_000, minimum_transfer_amount=100_000
    )
    result = bilateral_cva_dva(
        positive_exposure=collateralised,
        negative_exposure=np.array([0, -100_000, -250_000, -300_000, -200_000]),
        counterparty_cumulative_pd=np.array([0.005, 0.012, 0.021, 0.032, 0.045]),
        own_cumulative_pd=np.array([0.004, 0.010, 0.018, 0.028, 0.040]),
        discount_factors=np.array([0.99, 0.97, 0.95, 0.93, 0.91]),
    )
    print("\nBilateral valuation adjustments:")
    print(pd.Series(result).map("${:,.0f}".format).to_string())


if __name__ == "__main__":
    market_risk_case()
    credit_case()
    counterparty_case()