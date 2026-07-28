"""Decision-useful executive reporting for export-credit portfolios."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd

from .export_credit import (
    PortfolioSimulation,
    concentration_report,
    country_limit_report,
    validate_export_portfolio,
)
from .export_credit_finance import premium_adequacy


def executive_risk_report(
    portfolio: pd.DataFrame,
    simulation: PortfolioSimulation,
    as_of: date | None = None,
) -> str:
    """Generate a concise committee-style Markdown portfolio risk report."""
    clean = validate_export_portfolio(portfolio)
    countries = concentration_report(clean, "country")
    sectors = concentration_report(clean, "sector")
    limits = country_limit_report(clean)
    premiums = premium_adequacy(clean)
    report_date = as_of or datetime.now(UTC).date()
    top_country = countries.iloc[0]
    top_sector = sectors.iloc[0]
    red = limits.loc[limits["status"] == "Red", "country"].tolist()
    amber = limits.loc[limits["status"] == "Amber", "country"].tolist()
    inadequate = int((premiums["adequacy_ratio"] < 1.0).sum())

    limit_comment = (
        f"Red limits: {', '.join(red)}." if red else "No country exposure limit is breached."
    )
    if amber:
        limit_comment += f" Amber watch list: {', '.join(amber)}."

    return f"""# Export Credit Portfolio Risk Report

**As at:** {report_date:%d %B %Y}  
**Basis:** Synthetic educational portfolio; figures in GBP millions

## Executive assessment

The portfolio contains **{len(clean)} deals** across **{clean['country'].nunique()} countries**
with covered exposure of **£{clean['covered_ead_gbp_m'].sum():,.1f}m**. Modelled expected
loss is **£{simulation.expected_loss:,.1f}m**, while the
**{simulation.confidence:.1%} loss-at-risk is £{simulation.loss_var:,.1f}m** and tail
Expected Shortfall is **£{simulation.expected_shortfall:,.1f}m**.

{limit_comment}

## Concentration

- Largest country: **{top_country['country']}**, £{top_country['exposure_gbp_m']:,.1f}m
  ({top_country['portfolio_share']:.1%} of covered exposure).
- Largest sector: **{top_sector['sector']}**, £{top_sector['exposure_gbp_m']:,.1f}m
  ({top_sector['portfolio_share']:.1%}).
- Unexpected loss at the selected confidence: **£{simulation.unexpected_loss:,.1f}m**.

## Pricing and risk actions

- **{inadequate} deals** have illustrative annual premium below the modelled combination
  of expected loss, capital cost and operating cost.
- Review amber/red country limits before approving additional exposure.
- Challenge PD, LGD and dependence assumptions for the largest tail contributors.
- Consider reinsurance where the reduction in tail loss and concentration justifies cost.

## Governance note

Results depend on synthetic exposures and simplified dependence assumptions. This report
does not reproduce UKEF's proprietary PRISM methodology, implement OECD minimum-premium
rules, or constitute financial, regulatory or underwriting advice.
"""