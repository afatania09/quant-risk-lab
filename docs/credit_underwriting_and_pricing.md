# Credit underwriting and product pricing methodology

## Decision process

The new workflow demonstrates how an export-credit analyst can move from evidence to a
decision:

1. assess the obligor's leverage, coverage, liquidity, profitability and trading history;
2. apply a country-risk overlay and, where relevant, project completion and offtake risks;
3. map the score to an indicative annual probability of default (PD);
4. select a product based on the transaction purpose and risk entity;
5. construct the drawdown and repayment schedule;
6. calculate marginal default probabilities and discounted lifetime expected loss;
7. estimate unexpected loss/economic capital and its cost;
8. add operating cost and compare the economic price with a supplied premium floor;
9. report price, equivalent spread, RAROC, sensitivities and limitations.

## Corporate scorecard

| Component | Weight | Example evidence |
|---|---:|---|
| Debt / EBITDA | 20% | Audited debt and EBITDA reconciliation |
| Debt-service coverage | 18% | Forecast cash flow and debt schedule |
| Interest coverage | 15% | EBITDA or EBIT relative to interest |
| Country risk | 15% | Independent public-data screening score |
| Liquidity | 10% | Current assets and liabilities |
| Operating margin | 10% | Sustainable operating performance |
| Revenue growth | 7% | Historic and forecast revenue |
| Trading history | 5% | Operating track record |

The thresholds, grades and PD mapping are illustrative and version controlled in
`src/quant_risk/underwriting.py`. They are intentionally simple enough to challenge. A
production model would require development data, calibration, discrimination and
calibration testing, overrides governance, independent validation and ongoing monitoring.

## Product structures represented

The Python pricer models six broad structures:

- Buyer Credit Facility
- Direct Lending Facility
- Export Insurance Policy
- General Export Facility
- Export Working Capital Scheme
- Bond Support Scheme

The catalogue explains the purpose, risk entity, indicative covered share and form of
charge. Product eligibility and terms must always be checked against current UKEF guidance.

## Economic pricing

For each repayment period, expected loss is:

`covered average exposure × marginal default probability × LGD × discount factor`

Economic capital uses an illustrative one-factor conditional default probability at the
selected confidence. Required premium is the sum of discounted expected loss, the cost of
economic capital over average life, and operating cost. The dashboard converts that amount
to an upfront rate and an equivalent annual spread and calculates an illustrative RAROC.

## OECD and UKEF boundary

OECD Arrangement minimum premium rates depend on matters including country classification,
time at risk, buyer risk and the political/commercial risk covered. The repository does not
reverse engineer or label its output as an official Minimum Premium Rate. Instead, a user
may enter a verified external MPR as a pricing floor. The displayed quote is then the higher
of the independent economic model price and that supplied floor.

UKEF's published premium indication service itself states that it produces an OECD minimum
premium indication. Final UKEF pricing and approved methodologies remain outside this
portfolio demonstration.

## Key limitations and validation agenda

- The score-to-PD mapping is judgemental, not empirically calibrated.
- Financial ratios can be distorted by accounting policy, cyclicality and forecasts.
- The exposure schedule assumes a fully drawn facility and simplified repayment profiles.
- LGD does not separately model security, guarantees, restructuring costs or recovery lag.
- Economic capital is a simplified single-name approximation, not PRISM.
- Interest-rate, currency, prepayment, fee timing and tax effects are excluded.
- Model outputs should be sensitivity tested and independently reviewed before use.

Useful validation extensions would include Gini/AUC, calibration curves, Brier score,
rating-migration analysis, realised-versus-expected default rates and override monitoring.

## Public sources

- [UKEF product collection](https://www.gov.uk/government/collections/our-products)
- [UKEF Buyer Credit Facility](https://www.gov.uk/guidance/buyer-credit-facility)
- [UKEF corporate premium indication](https://www.gov.uk/government/publications/get-a-corporate-premium-indication)
- [OECD financing terms and conditions](https://www.oecd.org/en/topics/financing-terms-and-conditions.html)
