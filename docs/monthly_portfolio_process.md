# Monthly Portfolio Risk and Active Management Process

This demonstrator turns a static risk calculation into a controlled monthly workflow. It is an
independent educational design and does not reproduce UKEF's PRISM process or internal controls.

## Control sequence

1. Validate required fields, ranges and unique deal identifiers.
2. Reconcile opening and closing expected loss exactly.
3. Attribute movement to new business, exits, exposure run-off, cover, PD and LGD.
4. Project surviving exposure, premium, claims and delayed recoveries over 15 years.
5. Recalculate country-limit utilisation and portfolio tail risk.
6. Rank candidate reinsurance transactions by estimated tail-risk reduction per pound spent.
7. Test Monte Carlo convergence against a larger benchmark run.
8. Export a controlled management-information workbook and committee narrative.

## Movement attribution

Expected loss is decomposed sequentially from

`EAD × guarantee share × PD × LGD`.

The sequential method ensures that the sum of the drivers equals the exact change between opening
and closing expected loss. The dashboard reports any reconciliation difference as a control.

## Projection assumptions

The public demonstrator assumes straight-line contractual run-off, constant annual conditional PD,
premium on surviving opening exposure and recoveries paid after a configurable lag. These are
transparent scenario assumptions, not forecasts of UKEF claims or recoveries.

## Active Portfolio Management

The allocator ranks illustrative quota-share transactions using tail-risk reduction per unit of
reinsurance cost and respects a user-selected budget. A production optimisation would also include
counterparty credit quality, legal eligibility, capacity constraints, pricing uncertainty,
diversification effects and approval policy.

## Validation

The convergence view reruns the loss model at increasing sample sizes with a fixed seed. It compares
VaR and Expected Shortfall with the largest run and assigns an indicative control status. Production
validation would additionally require independent implementation, realised-outcome monitoring,
parameter validation, change control and formal approval.
