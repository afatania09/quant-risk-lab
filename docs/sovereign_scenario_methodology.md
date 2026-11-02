# Sovereign Migration and Scenario Methodology

This module demonstrates how sovereign-credit deterioration can feed into an export-credit
portfolio. All transition probabilities and scenario multipliers are transparent educational
assumptions. They are not UKEF, OECD or credit-rating-agency calibrations.

## Country-grade migration

The model uses seven performing country-risk grades and an absorbing default state. Annual
transition probabilities permit upgrades, persistence, downgrades and default. A stressed matrix
increases downgrade and default probabilities and removes the additional probability mass from
the unchanged-grade state, preserving row sums of one.

Monte Carlo paths provide:

- portfolio share in each grade by projection year;
- cumulative defaulted exposure;
- mean cumulative default loss; and
- the 95th percentile of cumulative default loss.

The matrix is deliberately smooth and explainable. Production use would require controlled
calibration to approved historical data, expert overlays, validation and formal governance.

## Named macro-credit scenarios

Five scenarios are evaluated on a common simulation basis:

1. Base;
2. Global recession;
3. Sovereign debt shock;
4. Commodity-price collapse; and
5. Physical-climate event.

Each scenario can change portfolio-wide PD, LGD and dependence as well as selected regional or
sector PDs. The comparison reports expected loss, loss-at-risk, Expected Shortfall and movement
against the base case. The scenarios are analytical narratives, not forecasts.

## Parameter uncertainty

The default simulation treats selected PD and LGD values as fixed. The parameter-uncertainty
module instead draws PD and LGD from beta distributions centred on each deal's point estimate.
It reports the distribution of portfolio expected loss and a 90% uncertainty interval.

This distinguishes:

- **process risk** — whether and when defaults occur; from
- **parameter risk** — whether the estimated PD and LGD values are themselves correct.

The beta-distribution strengths are configurable. They should be calibrated and independently
challenged before any real decision use.
