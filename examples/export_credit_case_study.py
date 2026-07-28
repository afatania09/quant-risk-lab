"""Generate an end-to-end export-credit portfolio analysis."""

from pathlib import Path

import pandas as pd

from quant_risk.export_credit import (
    concentration_report,
    country_limit_report,
    reverse_stress_lgd_multiplier,
    simulate_export_credit_losses,
)
from quant_risk.export_credit_finance import premium_adequacy, scenario_weighted_ecl
from quant_risk.reporting import executive_risk_report

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    portfolio = pd.read_csv(ROOT / "data" / "synthetic_export_credit_portfolio.csv")
    scenarios = pd.read_csv(ROOT / "data" / "ifrs9_scenarios.csv")
    simulation = simulate_export_credit_losses(portfolio, simulations=50_000)

    print(executive_risk_report(portfolio, simulation))
    print("\nTop country concentrations")
    print(concentration_report(portfolio, "country").head(8).to_string(index=False))
    print("\nCountry limit watch list")
    limits = country_limit_report(portfolio)
    print(limits.loc[limits["status"] != "Green"].to_string(index=False))
    print("\nIFRS 9 scenario-weighted ECL by stage")
    ecl = scenario_weighted_ecl(portfolio, scenarios)
    print(ecl.groupby("ifrs9_stage")["scenario_weighted_ecl_gbp_m"].sum().to_string())
    print("\nPremium adequacy")
    pricing = premium_adequacy(portfolio)
    print(pricing.head(8).to_string(index=False))
    print("\nReverse stress")
    print(reverse_stress_lgd_multiplier(portfolio, loss_capacity_gbp_m=650))


if __name__ == "__main__":
    main()