# Alignment with a Principal Quantitative Analyst role

This project was developed to demonstrate the technical and decision-support
capabilities described publicly for a Principal Quantitative Analyst working in
portfolio risk and operational research at UK Export Finance.

It is an independent portfolio project. It is not affiliated with UKEF and does
not reproduce PRISM, confidential deal data, internal policy or proprietary
pricing methodologies.

## Requirement mapping

| Role capability | Evidence in this repository |
|---|---|
| Portfolio risk simulation | Correlated global, country, sector and obligor claim simulation |
| Value at Risk | Market VaR plus export-credit portfolio loss-at-risk |
| Monte Carlo methods | Seeded and testable correlated market and credit simulations |
| Scenario and stress testing | PD/LGD scenario grid and reverse stress against risk capacity |
| Claims analysis | Simulated guarantee claims net of coverage and recovery assumptions |
| Country exposure limits | Headroom, utilisation and red/amber/green limit monitoring |
| Risk concentrations | Country, sector, product and deal-level tail-risk contributions |
| Active portfolio management | Quota-share and excess-of-loss reinsurance comparison |
| IFRS 9 | Stage-sensitive, scenario-weighted 12-month and lifetime ECL |
| Premium pricing | Transparent adequacy comparison against loss, capital and operating costs |
| Model development | Modular Python package with validation, deterministic seeds and tests |
| Quality assurance | Input validation, reconciliation tests, model limitations and CI |
| Committee communication | Downloadable executive risk report and decision-oriented dashboard |
| Country risk analysis | Public macro/governance indicator monitor, early-warning thresholds, exposure interaction and downloadable country brief |
| Reproducible research | Versioned World Bank and UKEF public-policy snapshots with refresh scripts and source dates |
| Automation | One command runs the analysis; uploaded portfolios can replace example data |
| Data science | Simulation, decomposition, sensitivity analysis and interactive visualisation |

## What the project intentionally does not claim

- It does not reproduce the design or outputs of UKEF's Portfolio Risk Simulation
  Model (PRISM).
- It does not implement OECD Arrangement minimum premium benchmarks.
- It does not use confidential UKEF portfolio, claims, pricing or country-limit data.
- It does not represent an IFRS 9 or IFRS 17 accounting opinion.
- It is not an underwriting, investment or policy recommendation.

## How this would transfer into the role

The important transferable workflow is:

1. structure and validate portfolio data;
2. encode assumptions transparently;
3. simulate correlated claims;
4. reconcile model results to deterministic expected loss;
5. identify concentration and limit pressures;
6. stress the portfolio and identify failure thresholds;
7. assess pricing or reinsurance decisions;
8. present conclusions, limitations and actions to senior decision-makers.

The dashboard is therefore designed around questions a risk committee might ask,
not around displaying every available model output.
