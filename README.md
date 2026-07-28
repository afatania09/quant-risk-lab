# Quant Risk Lab

A tested Python risk engine demonstrating market, credit and counterparty risk
analytics with a realistic multi-sector equity case study.

## What this project demonstrates

| Risk area | Implementation | Why it matters |
|---|---|---|
| Market risk | Historical, parametric and Monte Carlo VaR | Compares three common loss-estimation assumptions |
| Tail risk | Expected Shortfall | Measures loss severity beyond the VaR threshold |
| Model validation | VaR exception backtesting | Tests whether forecast losses are calibrated |
| Stress testing | Historical worst days and factor shocks | Examines risks that ordinary distribution estimates can miss |
| Credit risk | PD × LGD × EAD expected loss | Connects default likelihood to monetary loss |
| Structural credit | Merton distance to default | Links firm asset value and leverage to default probability |
| Counterparty risk | Discrete unilateral CVA | Prices discounted expected exposure to counterparty default |
| Risk attribution | Euler component VaR | Identifies each holding's contribution to total portfolio risk |
| Dynamic risk | Rolling and EWMA-filtered historical VaR | Adapts risk forecasts to changing volatility |
| Model validation | Kupiec and Christoffersen tests | Tests coverage and clustering of VaR exceptions |
| Portfolio credit | Gaussian-copula default simulation | Estimates expected, unexpected and tail credit loss |
| XVA foundations | Bilateral CVA/DVA and collateral | Demonstrates counterparty and own-credit adjustments |

## Real-company case study

The example portfolio contains **Apple, Microsoft, JPMorgan Chase, ExxonMobil,
Johnson & Johnson and Walmart**. A $10 million allocation spans technology,
banking, energy, healthcare and consumer defensives. Daily adjusted prices are
downloaded at run time, so results use genuine co-movement, volatility and crisis
periods rather than invented returns.

This is a portfolio-risk illustration, not investment advice. Yahoo Finance data
is convenient rather than institution-grade. The credit and CVA examples use
clearly labelled illustrative inputs because proper bank models require bond/CDS,
counterparty, netting, collateral and exposure data that are not fully public.

## Quick start

```bash
git clone https://github.com/afatania09/quant-risk-lab.git
cd quant-risk-lab
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -e ".[dev,market-data]"
pytest
python examples/real_company_portfolio.py
python examples/credit_and_cva.py
python examples/advanced_risk_case_study.py
```

## Core equations

For confidence level \(c\), historical VaR is the negative lower-tail P&L
quantile:

\[
\mathrm{VaR}_c=-Q_{1-c}(P\&L).
\]

Expected Shortfall is the average loss conditional on crossing that threshold:

\[
\mathrm{ES}_c=-E[P\&L\mid P\&L\leq -\mathrm{VaR}_c].
\]

Expected credit loss is:

\[
\mathrm{ECL}=PD\times LGD\times EAD.
\]

Discrete unilateral CVA is:

\[
\mathrm{CVA}=(1-R)\sum_t DF_t\,EE_t\,\Delta PD_t.
\]

## Design choices and limitations

- Every risk figure is returned as a positive monetary loss.
- Parametric and Monte Carlo VaR currently assume normally distributed returns.
- Historical VaR is distribution-free but assumes the observed window represents
  future risk.
- Linear position mapping is suitable for cash equities; options require
  full-revaluation or delta-gamma extensions.
- CVA is unilateral and does not yet model netting, collateral, wrong-way risk,
  first-to-default dependence, wrong-way risk, FVA or MVA. The advanced bilateral
  example adds simplified DVA and collateral mechanics.
- Models are deliberately transparent and independently testable.

## Roadmap

- GARCH and extreme-value-theory tail models
- Full-revaluation options VaR and Greeks-based P&L attribution
- Multi-period credit migration valuation and concentration limits
- Monte Carlo exposure profiles with netting and collateral
- Bilateral CVA/DVA and funding valuation adjustment
- Reproducible charts and an executive risk report

## Repository layout

```text
src/quant_risk/    reusable model code
examples/          executable market and credit case studies
tests/             numerical and behavioural tests
docs/              model governance and interview explanations
.github/workflows  automated quality checks
```
