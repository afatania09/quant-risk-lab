# Quant Risk Lab

[![Tests](https://github.com/afatania09/quant-risk-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/afatania09/quant-risk-lab/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-70e1c1)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-438ca3)](LICENSE)

**A portfolio-grade quantitative risk analytics laboratory spanning market, credit, liquidity, counterparty, concentration, stress-testing and export-credit risk.**

![Export Credit Risk Lab dashboard](assets/export_credit_dashboard_preview.png)

Quant Risk Lab is designed as a reusable Python risk engine rather than a collection of disconnected notebooks. It combines transparent statistical models, portfolio diagnostics, model validation, stress testing and decision-oriented reporting with an interactive export-credit case study.

> This independent educational project is not affiliated with UK Export Finance.
> It does not reproduce UKEF's proprietary PRISM methodology, use UKEF data or
> implement official OECD premium rules.

## Core quantitative capabilities

| Risk domain | Capability |
|---|---|
| **Market risk** | Historical, delta-normal, Monte Carlo and filtered historical VaR/ES |
| **Risk attribution** | Euler component VaR and volatility risk contributions |
| **Portfolio construction** | Annualised volatility, diversification ratio and effective number of risk bets |
| **Concentration risk** | HHI, effective positions and top-1/top-5 exposure concentration |
| **Drawdown risk** | Maximum drawdown, peak-to-trough duration and recovery diagnostics |
| **Model validation** | Kupiec coverage, Christoffersen independence and conditional-coverage testing |
| **VaR governance** | Indicative Basel 250-day green/yellow/red exception classification |
| **Liquidity risk** | Liquidation horizon, liquidity-adjusted VaR and stressed bid-ask liquidation cost |
| **Credit risk** | PD × LGD × EAD expected loss and structural Merton default probability |
| **Credit portfolio risk** | Rating migration, correlated credit losses and credit VaR/ES |
| **Counterparty risk** | Unilateral CVA, bilateral CVA/DVA and simplified collateral treatment |
| **Stress testing** | Historical and hypothetical factor shocks plus reverse stress testing |
| **IFRS 9** | Stage-sensitive, scenario-weighted 12-month and lifetime ECL |
| **Export credit** | Country limits, underwriting, pricing adequacy, reinsurance and tail-loss analysis |

## Why this repo is useful

The project is built around questions a risk analyst, portfolio manager or model reviewer might actually need to answer:

- What are the portfolio's 95% and 99% VaR and Expected Shortfall under competing methodologies?
- Do VaR exceptions occur at the expected rate, and do they cluster?
- Which positions contribute most to volatility and tail risk?
- Is apparent diversification genuine, or is risk concentrated in a few effective bets?
- How concentrated is exposure by name, country, sector or product?
- How severe have historical drawdowns been and how long did recovery take?
- How many days would positions take to liquidate under participation constraints?
- How much does stressed market liquidity add to measured risk?
- What happens to credit losses under correlated defaults and rating migration?
- How large is counterparty valuation adjustment under changing default assumptions?
- Which stresses exhaust risk capacity?
- How do credit, country and product assumptions translate into export-credit pricing and capital decisions?

## Interactive export-credit dashboard

The repository includes a Streamlit application built around a fictional multi-country export-credit portfolio. It converts deal-level assumptions into country-limit monitoring, correlated claims, tail-risk attribution, country-risk screening, IFRS 9 ECL, underwriting, product pricing, reinsurance analysis, reverse stress testing and committee-style reporting.

Install and launch:

```bash
git clone https://github.com/afatania09/quant-risk-lab.git
cd quant-risk-lab
python -m venv .venv
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

The dashboard includes nine decision views:

1. **Portfolio overview** — exposure, sector mix and deal-level tail contribution.
2. **Country risk monitor** — public macro/governance indicators and early warnings.
3. **Credit underwriting** — corporate scorecard, project-finance overlays, grade and PD.
4. **Product pricer** — amortising exposure, expected loss, capital, premium and RAROC.
5. **Country limits** — utilisation, headroom and traffic-light monitoring.
6. **IFRS 9 ECL** — scenario-weighted 12-month and lifetime expected loss.
7. **Pricing and reinsurance** — portfolio premium adequacy and risk-transfer comparison.
8. **Reverse stress** — PD/LGD sensitivity and capacity breach thresholds.
9. **Committee report** — concise management information and downloadable outputs.

Users may upload a compatible CSV; the [data dictionary](docs/data_dictionary.md) defines the required fields.

## Example Python API

```python
import numpy as np
import pandas as pd

from quant_risk import (
    historical_var_es,
    marginal_risk_contribution,
    diversification_ratio,
    concentration_metrics,
    liquidity_adjusted_var,
)

returns = pd.DataFrame(...)
positions = np.array([4_000_000, 3_000_000, 2_000_000])

var_99, es_99 = historical_var_es(returns, positions, confidence=0.99)
contrib = marginal_risk_contribution(returns, positions / positions.sum())
div_ratio = diversification_ratio(returns, positions / positions.sum())
concentration = concentration_metrics(pd.Series(np.abs(positions)))
liquidity_var = liquidity_adjusted_var(var_99, horizon_days=5)
```

## Model governance and validation

The repository intentionally separates model calculation from model governance. Validation tooling now includes unconditional coverage, independence and joint conditional-coverage testing for VaR exceptions, while model documentation records assumptions, use limitations and required controls.

Included documentation:

- [Export-credit model card](docs/export_credit_model_card.md)
- [Country-risk methodology](docs/country_risk_methodology.md)
- [Credit underwriting and pricing methodology](docs/credit_underwriting_and_pricing.md)
- [UKEF role alignment](docs/ukef_role_alignment.md)
- [Data dictionary](docs/data_dictionary.md)
- [General model governance framework](docs/model_governance.md)
- [Risk interview guide](docs/interview_guide.md)

## Testing

```bash
pip install -e ".[dev]"
pytest
```

Tests cover numerical behaviour, risk decomposition reconciliation, concentration metrics, liquidity calculations, backtesting statistics, export-credit simulations, underwriting and pricing logic.

## Repository structure

```text
src/quant_risk/
  market.py               VaR, ES, filtered historical simulation and component VaR
  portfolio.py            volatility, diversification, drawdown and concentration analytics
  liquidity.py            liquidation horizon and liquidity-adjusted risk
  validation.py           Kupiec and Christoffersen backtesting diagnostics
  credit.py               expected loss and structural default modelling
  credit_portfolio.py     migration and correlated portfolio credit losses
  cva.py                  counterparty valuation adjustment
  stress.py               historical and hypothetical stress testing
  export_credit*.py       export-credit simulation, ECL, pricing and reinsurance

dashboard/                interactive decision dashboard
data/                      synthetic and public-context datasets
examples/                  executable case studies
tests/                     numerical and behavioural test suite
docs/                      methodology, governance and model documentation
assets/                    generated visual preview
.github/workflows/         CI tests
```

## Roadmap

Planned extensions include EVT tail modelling, GARCH volatility forecasting, liquidity-adjusted Expected Shortfall, factor-based scenario generation, FRTB-style sensitivities, credit concentration capital and richer backtesting diagnostics.

## Disclaimer

This software is provided for education, research and portfolio demonstration. It is not financial, investment, accounting, regulatory, underwriting or professional advice. No liability is accepted for decisions made using it.
