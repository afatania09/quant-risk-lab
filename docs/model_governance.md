# Model governance and validation

Good risk management is not simply producing a VaR number. A model must have a
defined purpose, an accountable owner, controlled data, independent validation,
limits and an escalation process.

## Model inventory

| Model | Intended use | Principal assumption | Main limitation |
|---|---|---|---|
| Historical VaR/ES | One-day equity portfolio risk | Past empirical distribution remains relevant | Regime changes may be absent |
| Delta-normal VaR/ES | Fast linear risk estimate | Elliptical returns and linear exposures | Weak for options and fat tails |
| Monte Carlo VaR/ES | Correlated scenario generation | Estimated Gaussian joint distribution | Correlation is unstable in crises |
| Filtered historical simulation | Volatility-adjusted tail risk | EWMA scaling captures current volatility | Standardised residual history remains representative |
| Merton PD | Structural corporate default signal | Firm assets follow a diffusion | Asset value and volatility are unobservable |
| Gaussian copula credit loss | Portfolio capital simulation | Single systematic factor and fixed correlation | Tail dependence can be understated |
| CVA/DVA | Counterparty valuation adjustment | Exposure and default are independent | Omits wrong-way and first-to-default risk |

## Validation framework

1. **Conceptual soundness** — document the use case, mathematics and assumptions.
2. **Data controls** — check completeness, stale prices, corporate actions and currency.
3. **Implementation verification** — unit tests, reconciliation identities and seeded simulations.
4. **Outcomes analysis** — VaR exception counts, Kupiec coverage and Christoffersen independence.
5. **Benchmarking** — compare historical, parametric, Monte Carlo and filtered estimates.
6. **Sensitivity analysis** — vary window, confidence, decay, PD, LGD and correlation.
7. **Stress testing** — assess crises and severe hypothetical shocks outside ordinary VaR.
8. **Limitations and overlays** — record weaknesses and apply expert overlays transparently.

## Governance example

An institution might set a daily 99% VaR limit and an Expected Shortfall limit,
but also monitor concentrations and stress losses. A limit breach should trigger
investigation rather than automatic model rejection: the cause could be a real
position change, a market-data problem, volatility escalation or model failure.

Repeated exceptions can indicate under-calibration. Clustered exceptions suggest
the model does not adjust quickly enough to new volatility. The two issues are
separated by the Kupiec and Christoffersen tests implemented in this repository.

## Regulatory context

This repository is educational and does not claim regulatory compliance. A real
FRTB implementation also requires liquidity horizons, modellability assessment,
Expected Shortfall calibration to a stress period, default-risk charge, non-
modellable risk factors, P&L attribution and backtesting at prescribed desk levels.
