"""Snapshot public UKEF cover indications for portfolio countries."""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

URL = "https://www.gov.uk/guidance/country-cover-policy-and-indicators"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "ukef_cover_policy_snapshot.csv"
PORTFOLIO_NAMES = {
    "turkey": "Türkiye",
    "czech-republic": "Czechia",
}


def plain(fragment: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


if __name__ == "__main__":
    with urlopen(URL, timeout=30) as response:
        page = response.read().decode("utf-8")
    rows = []
    headings = list(re.finditer(r'<h3 id="([^"]+)">(.*?)</h3>', page, re.DOTALL))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(page)
        section = page[heading.end():end]
        table = re.search(r"<table>(.*?)</table>", section, re.DOTALL)
        if not table:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", table.group(1), re.DOTALL)
        if len(cells) < 4:
            continue
        country = PORTFOLIO_NAMES.get(heading.group(1), plain(heading.group(2)))
        rows.append(
            {
                "country": country,
                "market_risk_appetite": plain(cells[-3]),
                "short_term_cover": plain(cells[-2]),
                "medium_long_term_cover": plain(cells[-1]),
                "care_on_location": "carelocation" in section.lower(),
                "sustainable_lending": "sustainable" in section.lower(),
                "snapshot_date": datetime.now(UTC).date().isoformat(),
                "source_url": URL,
            }
        )
    portfolio = pd.read_csv(OUTPUT.parents[0] / "synthetic_export_credit_portfolio.csv")
    snapshot = pd.DataFrame(rows)
    snapshot = snapshot.loc[snapshot["country"].isin(portfolio["country"].unique())]
    snapshot.sort_values("country").to_csv(OUTPUT, index=False)
    print(f"Wrote {len(snapshot)} country policies to {OUTPUT}")
