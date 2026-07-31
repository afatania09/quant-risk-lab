"""Refresh the versioned World Bank country-risk data snapshot."""

from pathlib import Path

from quant_risk.country_risk import fetch_world_bank_panel

COUNTRIES = {
    "India": "IND", "Taiwan": "TWN", "Egypt, Arab Rep.": "EGY", "Indonesia": "IDN",
    "South Africa": "ZAF", "Kenya": "KEN", "Morocco": "MAR", "Brazil": "BRA",
    "Viet Nam": "VNM", "Saudi Arabia": "SAU", "Mexico": "MEX", "Turkiye": "TUR",
    "Jordan": "JOR", "Ghana": "GHA", "Malaysia": "MYS", "Chile": "CHL",
    "Iraq": "IRQ", "Kazakhstan": "KAZ", "Philippines": "PHL", "Poland": "POL",
    "Rwanda": "RWA", "Bangladesh": "BGD", "Czechia": "CZE", "Colombia": "COL",
}

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "country_risk_world_bank.csv"

if __name__ == "__main__":
    panel = fetch_world_bank_panel(list(COUNTRIES.values()))
    reverse_names = {iso3: name for name, iso3 in COUNTRIES.items()}
    panel["country"] = panel["iso3"].map(reverse_names)
    panel.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(panel):,} observations to {OUTPUT}")
