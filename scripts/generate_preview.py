"""Generate a static repository preview from the synthetic portfolio."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from quant_risk.export_credit import (
    concentration_report,
    country_limit_report,
    simulate_export_credit_losses,
)
from quant_risk.sovereign_scenarios import macro_scenario_comparison

ROOT = Path(__file__).resolve().parents[1]
portfolio = pd.read_csv(ROOT / "data" / "synthetic_export_credit_portfolio.csv")
simulation = simulate_export_credit_losses(portfolio, simulations=50_000)
countries = concentration_report(portfolio, "country").head(8).sort_values(
    "exposure_gbp_m"
)
limits = country_limit_report(portfolio).head(10)
scenario_results = macro_scenario_comparison(portfolio, simulations=20_000)

plt.style.use("dark_background")
figure = plt.figure(figsize=(16, 9), facecolor="#07111f")
grid = figure.add_gridspec(12, 24)
figure.text(0.05, 0.94, "EXPORT CREDIT RISK LAB", color="#70e1c1", fontsize=11, weight="bold")
figure.text(
    0.05,
    0.89,
    "Portfolio risk, made decision-useful",
    color="#f7fbff",
    fontsize=26,
    weight="bold",
)
figure.text(
    0.05,
    0.855,
    "Fictional 24-deal portfolio · country migration · macro scenarios · pricing · validation",
    color="#9fb2c7",
    fontsize=11,
)

metrics = [
    ("COVERED EXPOSURE", f"£{(portfolio.ead_gbp_m * portfolio.guarantee_share).sum():,.0f}m"),
    ("EXPECTED LOSS", f"£{simulation.expected_loss:,.1f}m"),
    ("99.5% LOSS-AT-RISK", f"£{simulation.loss_var:,.1f}m"),
    ("TAIL SHORTFALL", f"£{simulation.expected_shortfall:,.1f}m"),
]
for index, (label, value) in enumerate(metrics):
    x = 0.05 + index * 0.235
    figure.text(x, 0.79, label, color="#8299b1", fontsize=8, weight="bold")
    figure.text(x, 0.745, value, color="#ffffff", fontsize=18, weight="bold")

country_ax = figure.add_subplot(grid[5:12, :11], facecolor="#0c1a2c")
country_ax.barh(countries["country"], countries["exposure_gbp_m"], color="#35a78a")
country_ax.set_title("Largest country exposures", loc="left", fontsize=13, weight="bold")
country_ax.set_xlabel("Covered exposure (£m)", color="#8fa4bb")
country_ax.grid(axis="x", color="#203957", alpha=0.6)
country_ax.spines[:].set_visible(False)

scenario_ax = figure.add_subplot(grid[5:8, 13:24], facecolor="#0c1a2c")
scenario_plot = scenario_results.sort_values("loss_var_gbp_m")
scenario_ax.barh(scenario_plot["scenario"], scenario_plot["loss_var_gbp_m"], color="#438ca3")
scenario_ax.set_title("Macro-scenario loss-at-risk", loc="left", fontsize=13, weight="bold")
scenario_ax.set_xlabel("99.5% loss-at-risk (£m)", color="#8fa4bb")
scenario_ax.tick_params(axis="y", labelsize=7)
scenario_ax.grid(axis="x", color="#203957", alpha=0.6)
scenario_ax.spines[:].set_visible(False)

limit_ax = figure.add_subplot(grid[9:12, 13:24], facecolor="#0c1a2c")
limit_ax.barh(
    limits["country"],
    limits["utilisation"] * 100,
    color=["#ff788c" if value >= 1 else "#f1bf5b" if value >= 0.8 else "#70e1c1" for value in limits["utilisation"]],
)
limit_ax.axvline(100, color="#ff788c", linewidth=1)
limit_ax.set_title("Country limit utilisation", loc="left", fontsize=11, weight="bold")
limit_ax.set_xlim(0, max(110, limits["utilisation"].max() * 110))
limit_ax.set_xlabel("% of limit", color="#8fa4bb")
limit_ax.spines[:].set_visible(False)
limit_ax.tick_params(axis="y", labelsize=7)

figure.subplots_adjust(left=0.12, right=0.97, top=0.83, bottom=0.07, wspace=0.5, hspace=2.0)
output = ROOT / "assets" / "export_credit_dashboard_preview.png"
output.parent.mkdir(exist_ok=True)
figure.savefig(output, dpi=150, facecolor=figure.get_facecolor())
print(output)
