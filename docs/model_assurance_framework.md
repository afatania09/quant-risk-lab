# Model assurance and controlled release

The model-assurance layer turns an analytical run into reviewable evidence. It is deliberately
separate from model calculation: a numerically valid result is not decision-ready until its data,
configuration, validation evidence and ownership have been checked.

## Automated control suite

Each run evaluates eight deal-level and portfolio-level controls:

| Control | Purpose | Severity |
|---|---|---|
| DQ01 | Required fields are present | Red |
| DQ02 | Required values are complete | Red |
| DQ03 | Deal identifiers are unique | Red |
| DQ04 | Quantitative fields are parseable | Red |
| DQ05 | PD, LGD, cover and premium rates are within zero and one | Red |
| DQ06 | Exposure is non-negative and limits are positive | Red |
| DQ07 | Each country has one internally consistent limit | Amber |
| DQ08 | Covered country exposure is below its limit | Amber |

A Red data failure prevents release. Amber exceptions permit release only after review. The release
gate also uses Monte Carlo convergence and primary-versus-challenger VaR differences. Convergence
above 10% or a challenger gap above 25% prevents release; lower warning thresholds are 5% and 10%.

## Reproducible run manifest

Every run records the model version, UTC timestamp, confidence level, simulation count, random seed,
portfolio dimensions and a SHA-256 fingerprint of canonically ordered input data. The run identifier
is derived from the input fingerprint, version and model settings. Re-running identical inputs and
settings therefore produces the same identifier, regardless of input row order.

The manifest does not replace source-system lineage, access control or retention policies. In a
production implementation it would be stored with the approved input extract, code commit, model
owner sign-off and any expert overlays.

## Governance workflow

1. The first line validates source ownership, cut-off date and input completeness.
2. Automated controls and model validation generate the release gate.
3. The model owner investigates exceptions and documents any overlay.
4. Independent validation challenges Tier 1 models at least annually and after material change.
5. The accountable approver records release, conditional release or rejection.

The included inventory makes criticality, ownership, validation frequency and known limitations
visible. It is an illustrative governance artefact, not evidence of regulatory approval.
