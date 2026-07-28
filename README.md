# Quant Risk Lab

[![Tests](https://github.com/afatania09/quant-risk-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/afatania09/quant-risk-lab/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-70e1c1)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-438ca3)](LICENSE)

**A decision oriented portfolio risk simulator built to demonstrate technical
work in export credit and operational research.**

![Export Credit Risk Lab dashboard](assets/export_credit_dashboard_preview.png)

The centrepiece is an interactive dashboard for a fictional £3.8bn export-credit
portfolio. It converts deal-level assumptions into country-limit monitoring,
correlated claims, tail risk, IFRS 9 ECL, pricing adequacy, reinsurance analysis,
reverse stress testing and a downloadable committee report.

> This independent educational project is not affiliated with UK Export Finance.
> It does not reproduce UKEF's proprietary PRISM methodology, use UKEF data or
> implement official OECD premium rules.

## Why this is useful

The application is organised around real portfolio-management questions:

- Where are country and sector concentrations building?
- Which deals drive losses in severe simulations?
- Which country limits are green, amber or breached?
- How large are expected, unexpected and tail claims?
- What deterioration in recovery assumptions exhausts risk capacity?
- How does IFRS 9 ECL change across macroeconomic scenarios and stages?
- Does illustrative premium cover expected loss, capital and operating cost?
- Does reinsurance reduce tail loss enough to justify its cost?
- How can results be communicated clearly to a risk committee?

## Interactive dashboard

Install and launch:

```bash
git clone https://github.com/afatania09/quant-risk-lab.git
cd quant-risk-lab
python -m venv .venv
```

Activate the environment, then:

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

The dashboard includes six decision views:

1. **Portfolio overview** — exposure, sector mix and deal-level tail contribution.
2. **Country limits** — utilisation, headroom and traffic-light monitoring.
3. **IFRS 9 ECL** — scenario-weighted 12-month and lifetime expected loss.
4. **Pricing and reinsurance** — premium adequacy and risk-transfer comparison.
5. **Reverse stress** — PD/LGD sensitivity and the threshold that breaches capacity.
6. **Committee report** — concise findings and downloadable management information.

Users may upload a compatible CSV; the [data dictionary](docs/data_dictionary.md)
defines the required fields.

## Export-credit analytics

| Capability | Implementation |
|---|---|
| Portfolio claims | Monte Carlo latent-factor model with global, country, sector and obligor risk |
| Concentration | Country, sector, product and conditional tail-risk attribution |
| Exposure limits | Country utilisation, headroom and red/amber/green monitoring |
| Reverse stress | Binary search for the LGD deterioration that breaches risk capacity |
| IFRS 9 | Stage-sensitive, scenario-weighted 12-month and lifetime ECL |
| Premium analysis | Expected loss + capital cost + operating cost adequacy |
| Risk transfer | Quota-share and excess-of-loss reinsurance structures |
| Reporting | Automated committee-style Markdown and CSV downloads |
| Quality control | Schema validation, deterministic simulations and reconciliation tests |

The included dataset contains 24 entirely fictional deals across aviation,
transport, energy, healthcare, telecommunications, technology and infrastructure.
Real country names make concentration analysis intelligible; deal values and risk
parameters do not describe actual UKEF business.

## Wider quantitative risk library

The repository also retains a broader set of tested analytics:

- Historical, parametric, Monte Carlo and filtered historical VaR
- Expected Shortfall
- Rolling VaR forecasts
- Euler component VaR
- Kupiec coverage and Christoffersen independence tests
- Historical and hypothetical stress testing
- PD × LGD × EAD expected loss
- Merton structural default probability
- Credit migration and Gaussian-copula portfolio losses
- Unilateral and bilateral CVA/DVA with simplified collateral

These modules show general quantitative foundations; the export-credit dashboard
shows how to turn them into a useful business process.

## Run the analysis without the dashboard

```bash
pip install -e ".[dev]"
pytest
python examples/export_credit_case_study.py
```

## Model governance

The project includes:

- [Export-credit model card](docs/export_credit_model_card.md)
- [UKEF role alignment](docs/ukef_role_alignment.md)
- [Data dictionary](docs/data_dictionary.md)
- [General model governance framework](docs/model_governance.md)
- [Risk interview guide](docs/interview_guide.md)

The design makes limitations visible. A Gaussian factor model, fixed PD/LGD
assumptions and simplified reinsurance cannot substitute for approved production
methodology, controlled data, independent validation or expert judgement.

## Repository structure

```text
dashboard/                 interactive decision dashboard
data/                      synthetic portfolio and IFRS 9 scenarios
src/quant_risk/            reusable market, credit and export-risk engine
examples/                  executable case studies
tests/                     numerical, behavioural and reconciliation tests
docs/                      model cards, governance and role alignment
assets/                    generated visual preview
.github/workflows/         automated tests and code-quality checks
```

## Disclaimer

This software is provided for education, research and portfolio demonstration.
It is not financial, investment, accounting, regulatory, underwriting or
professional advice. No liability is accepted for decisions made using it.