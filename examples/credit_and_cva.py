"""Illustrative corporate expected-loss, Merton PD and CVA calculations."""

import numpy as np

from quant_risk.credit import expected_credit_loss, merton_default_probability
from quant_risk.cva import unilateral_cva


def main() -> None:
    ecl = expected_credit_loss(pd=0.018, lgd=0.55, ead=5_000_000)
    merton_pd = merton_default_probability(
        asset_value=150_000_000,
        debt_face_value=100_000_000,
        asset_volatility=0.30,
        risk_free_rate=0.04,
    )
    cva = unilateral_cva(
        expected_exposure=np.array([1_200_000, 1_000_000, 750_000, 400_000]),
        cumulative_default_probability=np.array([0.010, 0.022, 0.036, 0.052]),
        discount_factors=np.array([0.96, 0.92, 0.88, 0.84]),
    )
    print(f"Expected credit loss: ${ecl:,.0f}")
    print(f"Merton one-year default probability: {merton_pd:.2%}")
    print(f"Unilateral CVA: ${cva:,.0f}")


if __name__ == "__main__":
    main()