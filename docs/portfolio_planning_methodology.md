# Portfolio Planning Methodology

This module demonstrates how an export-credit institution could evaluate a pipeline of prospective
transactions against finite risk capacity. All candidate deals, scores and results are fictional.

## Candidate evaluation

Each candidate is added individually to the current portfolio using a common random seed. The model
calculates:

- covered exposure;
- expected loss;
- incremental loss-at-risk;
- annual premium;
- annual economic value after expected loss, capital cost and operating cost;
- strategic score; and
- remaining country-limit capacity.

The incremental risk measure is a stand-alone approximation. A production planning process would
revalue candidate combinations jointly where material diversification or concentration effects exist.

## Approval optimisation

The mixed-integer model chooses whole candidate transactions. Its objective combines annual economic
value with a configurable monetary weight applied to the strategic score. It is subject to:

1. a maximum new covered-exposure budget;
2. maximum aggregate incremental loss-at-risk; and
3. the remaining exposure limit for every affected country.

An approved result is therefore not simply the highest-premium deal. It reflects the opportunity cost
of scarce exposure and risk capacity.

## Forward portfolio view

The approved pipeline is combined with the existing fictional book and passed to the multi-year
cash-flow engine. The dashboard compares surviving exposure under the current portfolio with the
post-approval portfolio over 15 years.

## Limitations

The public model does not include legal eligibility, funding availability, OECD pricing requirements,
reinsurer capacity, transaction interdependencies, deal execution probability, foreign-exchange risk,
or official UKEF strategic priorities. These would be required in a controlled production process.
