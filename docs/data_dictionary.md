# Export Credit Portfolio Data Dictionary

| Field | Type | Meaning |
|---|---|---|
| `deal_id` | Text | Unique deal identifier |
| `project` | Text | Fictional project description |
| `country` | Text | Country of risk |
| `region` | Text | Geographic region |
| `sector` | Text | Economic sector |
| `product` | Text | Guarantee, lending or insurance product |
| `ead_gbp_m` | Number | Gross exposure at default in GBP millions |
| `pd` | Decimal | Annual probability of default |
| `lgd` | Decimal | Loss given default after expected recoveries |
| `guarantee_share` | Decimal | Share of gross exposure covered |
| `premium_rate` | Decimal | Illustrative annual premium as a proportion of covered EAD |
| `country_limit_gbp_m` | Number | Illustrative country exposure limit in GBP millions |
| `maturity_years` | Integer | Remaining contractual maturity |
| `ifrs9_stage` | Integer | Illustrative IFRS 9 stage: 1, 2 or 3 |
| `country_risk_grade` | Integer | Illustrative ordinal country-risk grade |

All included deals and input values are fictional. The schema is deliberately
simple so that a reviewer can upload a replacement CSV and understand why each
field affects the results.