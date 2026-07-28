"""Interactive Export Credit Portfolio Risk Dashboard."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from quant_risk.export_credit import (
    concentration_report,
    country_limit_report,
    reverse_stress_lgd_multiplier,
    risk_contributions,
    simulate_export_credit_losses,
    validate_export_portfolio,
)
from quant_risk.export_credit_finance import (
    apply_reinsurance,
    premium_adequacy,
    scenario_weighted_ecl,
)
from quant_risk.reporting import executive_risk_report

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "data" / "synthetic_export_credit_portfolio.csv"
SCENARIO_PATH = ROOT / "data" / "ifrs9_scenarios.csv"

st.set_page_config(
    page_title="Export Credit Risk Lab",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp {background: #07111f; color: #e8eef6;}
    [data-testid="stSidebar"] {background: #0b1728;}
    .hero {
        padding: 1.35rem 1.5rem; border: 1px solid #203957; border-radius: 18px;
        background: linear-gradient(120deg, #0b1f36 0%, #0b2b31 55%, #17213d 100%);
        margin-bottom: 1rem;
    }
    .eyebrow {color: #70e1c1; font-weight: 700; letter-spacing: .14em; font-size: .75rem;}
    .hero h1 {margin: .25rem 0; color: #f7fbff; font-size: 2.2rem;}
    .hero p {color: #b8c8da; margin: 0; max-width: 850px;}
    [data-testid="stMetric"] {
        background: #0c1a2c; border: 1px solid #1d3551; padding: .8rem;
        border-radius: 14px;
    }
    .decision-card {
        background: #0c1a2c; border-left: 4px solid #70e1c1; padding: 1rem;
        border-radius: 10px; margin: .45rem 0;
    }
    div[data-testid="stDataFrame"] {border: 1px solid #1d3551; border-radius: 12px;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_default_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(PORTFOLIO_PATH), pd.read_csv(SCENARIO_PATH)


default_portfolio, scenarios = load_default_data()

st.sidebar.markdown("## Portfolio controls")
uploaded = st.sidebar.file_uploader("Upload a compatible portfolio CSV", type="csv")
portfolio = pd.read_csv(uploaded) if uploaded else default_portfolio
confidence = st.sidebar.select_slider(
    "Loss confidence",
    options=[0.95, 0.99, 0.995, 0.999],
    value=0.995,
    format_func=lambda value: f"{value:.1%}",
)
simulations = st.sidebar.select_slider(
    "Monte Carlo scenarios",
    options=[5_000, 10_000, 25_000, 50_000, 100_000],
    value=25_000,
    format_func=lambda value: f"{value:,}",
)
loss_capacity = st.sidebar.number_input(
    "Risk capacity (£m)", min_value=50.0, value=650.0, step=25.0
)
st.sidebar.caption("All example deals are fictional. Countries and sectors are illustrative.")

try:
    clean = validate_export_portfolio(portfolio)
except ValueError as error:
    st.error(f"Portfolio validation failed: {error}")
    st.stop()

simulation = simulate_export_credit_losses(
    clean, simulations=simulations, confidence=confidence
)
countries = concentration_report(clean, "country")
sectors = concentration_report(clean, "sector")
limits = country_limit_report(clean)

st.markdown(
    """
<div class="hero">
  <div class="eyebrow">QUANT RISK LAB · EXPORT CREDIT</div>
  <h1>Portfolio risk, made decision-useful</h1>
  <p>Explore concentrations, correlated claims, country limits, IFRS 9 expected
  credit loss, premium adequacy, reinsurance and reverse stress testing in one
  transparent analytical workflow.</p>
</div>
""",
    unsafe_allow_html=True,
)

metric_columns = st.columns(5)
metric_columns[0].metric("Covered exposure", f"£{clean['covered_ead_gbp_m'].sum():,.0f}m")
metric_columns[1].metric("Expected loss", f"£{simulation.expected_loss:,.1f}m")
metric_columns[2].metric(
    f"{confidence:.1%} loss-at-risk", f"£{simulation.loss_var:,.1f}m"
)
metric_columns[3].metric("Tail expected shortfall", f"£{simulation.expected_shortfall:,.1f}m")
metric_columns[4].metric(
    "Limit watch list", f"{(limits['status'] != 'Green').sum()} countries"
)

overview, limits_tab, ifrs_tab, pricing_tab, stress_tab, report_tab = st.tabs(
    [
        "Portfolio overview",
        "Country limits",
        "IFRS 9 ECL",
        "Pricing & reinsurance",
        "Reverse stress",
        "Committee report",
    ]
)

plot_template = "plotly_dark"
teal_scale = ["#16344d", "#1e6371", "#35a78a", "#70e1c1"]

with overview:
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Country exposure")
        country_fig = px.bar(
            countries.head(12),
            x="exposure_gbp_m",
            y="country",
            orientation="h",
            color="expected_loss_gbp_m",
            color_continuous_scale=teal_scale,
            labels={
                "exposure_gbp_m": "Covered exposure (£m)",
                "expected_loss_gbp_m": "Expected loss (£m)",
                "country": "",
            },
        )
        country_fig.update_layout(
            template=plot_template,
            height=470,
            yaxis={"categoryorder": "total ascending"},
            margin={"l": 10, "r": 20, "t": 15, "b": 10},
        )
        st.plotly_chart(country_fig, width="stretch")
    with right:
        st.subheader("Sector mix")
        sector_fig = px.treemap(
            sectors,
            path=["sector"],
            values="exposure_gbp_m",
            color="expected_loss_gbp_m",
            color_continuous_scale=teal_scale,
            hover_data=["deal_count", "portfolio_share"],
        )
        sector_fig.update_layout(
            template=plot_template, height=470, margin={"t": 15, "b": 10}
        )
        st.plotly_chart(sector_fig, width="stretch")

    contributions = risk_contributions(clean, simulations=min(simulations, 30_000))
    st.subheader("Largest tail-risk contributors")
    contribution_fig = px.bar(
        contributions.head(10),
        x="deal_id",
        y="tail_contribution_gbp_m",
        color="country",
        hover_data=["sector", "covered_ead_gbp_m", "tail_share"],
        labels={"tail_contribution_gbp_m": "Tail contribution (£m)", "deal_id": "Deal"},
    )
    contribution_fig.update_layout(
        template=plot_template,
        height=390,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
    )
    st.plotly_chart(contribution_fig, width="stretch")

with limits_tab:
    st.subheader("Country exposure limit monitor")
    status_order = {"Red": 0, "Amber": 1, "Green": 2}
    displayed_limits = limits.assign(
        _status_order=limits["status"].map(status_order)
    ).sort_values(["_status_order", "utilisation"], ascending=[True, False])
    st.dataframe(
        displayed_limits.drop(columns="_status_order").style.format(
            {
                "exposure_gbp_m": "£{:,.1f}m",
                "limit_gbp_m": "£{:,.1f}m",
                "expected_loss_gbp_m": "£{:,.2f}m",
                "utilisation": "{:.1%}",
                "headroom_gbp_m": "£{:,.1f}m",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    gauge_country = st.selectbox("Inspect country", limits["country"].tolist())
    selected = limits.loc[limits["country"] == gauge_country].iloc[0]
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=selected["utilisation"] * 100,
            number={"suffix": "%"},
            title={"text": f"{gauge_country} limit utilisation"},
            gauge={
                "axis": {"range": [0, max(120, selected["utilisation"] * 110)]},
                "bar": {"color": "#70e1c1"},
                "steps": [
                    {"range": [0, 80], "color": "#123249"},
                    {"range": [80, 100], "color": "#6d5a26"},
                    {"range": [100, 120], "color": "#6b2935"},
                ],
                "threshold": {"line": {"color": "#ff788c", "width": 4}, "value": 100},
            },
        )
    )
    gauge.update_layout(
        template=plot_template, height=330, margin={"t": 60, "b": 20}
    )
    st.plotly_chart(gauge, width="stretch")

with ifrs_tab:
    ecl = scenario_weighted_ecl(clean, scenarios)
    total_ecl = ecl["scenario_weighted_ecl_gbp_m"].sum()
    stage_summary = (
        ecl.groupby("ifrs9_stage", as_index=False)["scenario_weighted_ecl_gbp_m"].sum()
    )
    a, b = st.columns(2)
    a.metric("Scenario-weighted ECL", f"£{total_ecl:,.1f}m")
    b.metric("Stage 2/3 share", f"{ecl.loc[ecl['ifrs9_stage'] > 1, 'scenario_weighted_ecl_gbp_m'].sum() / total_ecl:.1%}")
    stage_fig = px.bar(
        stage_summary,
        x="ifrs9_stage",
        y="scenario_weighted_ecl_gbp_m",
        labels={
            "ifrs9_stage": "IFRS 9 stage",
            "scenario_weighted_ecl_gbp_m": "Scenario-weighted ECL (£m)",
        },
        text_auto=".2s",
    )
    stage_fig.update_layout(template=plot_template, height=360)
    st.plotly_chart(stage_fig, width="stretch")
    with st.expander("Macroeconomic scenario assumptions"):
        st.dataframe(
            scenarios.style.format(
                {"weight": "{:.0%}", "pd_multiplier": "{:.2f}×", "lgd_multiplier": "{:.2f}×"}
            ),
            hide_index=True,
            width="stretch",
        )

with pricing_tab:
    pricing = premium_adequacy(clean)
    inadequate = pricing["adequacy_ratio"] < 1
    p1, p2, p3 = st.columns(3)
    p1.metric("Annual premium", f"£{pricing['annual_premium_gbp_m'].sum():,.1f}m")
    p2.metric("Required premium", f"£{pricing['required_premium_gbp_m'].sum():,.1f}m")
    p3.metric("Deals below adequacy", f"{inadequate.sum()} / {len(pricing)}")
    pricing_fig = px.scatter(
        pricing,
        x="required_premium_gbp_m",
        y="annual_premium_gbp_m",
        size="covered_ead_gbp_m",
        color="country",
        hover_name="deal_id",
        labels={
            "required_premium_gbp_m": "Illustrative required premium (£m)",
            "annual_premium_gbp_m": "Annual premium (£m)",
        },
    )
    maximum = max(
        pricing["required_premium_gbp_m"].max(), pricing["annual_premium_gbp_m"].max()
    )
    pricing_fig.add_shape(
        type="line", x0=0, y0=0, x1=maximum, y1=maximum, line={"dash": "dash", "color": "#70e1c1"}
    )
    pricing_fig.update_layout(template=plot_template, height=470)
    st.plotly_chart(pricing_fig, width="stretch")

    structure = st.radio("Reinsurance structure", ["Quota share", "Excess of loss"], horizontal=True)
    reinsured = apply_reinsurance(simulation.losses, structure=structure)
    gross_var = np.quantile(reinsured["gross_loss_gbp_m"], confidence)
    net_var = np.quantile(reinsured["net_loss_gbp_m"], confidence)
    st.markdown(
        f'<div class="decision-card"><b>Tail-risk impact:</b> {structure} reduces '
        f'{confidence:.1%} simulated loss from <b>£{gross_var:,.1f}m</b> to '
        f'<b>£{net_var:,.1f}m</b>, after the illustrative reinsurance premium.</div>',
        unsafe_allow_html=True,
    )

with stress_tab:
    reverse = reverse_stress_lgd_multiplier(
        clean,
        loss_capacity_gbp_m=loss_capacity,
        confidence=confidence,
        simulations=min(simulations, 30_000),
    )
    s1, s2 = st.columns(2)
    s1.metric("Loss capacity", f"£{loss_capacity:,.0f}m")
    s2.metric("LGD multiplier to breach", f"{reverse['lgd_multiplier']:.2f}×")
    st.markdown(
        f'<div class="decision-card">At the selected confidence, portfolio loss reaches '
        f'<b>£{reverse["stressed_var_gbp_m"]:,.1f}m</b> when loss-given-default assumptions '
        f'are multiplied by <b>{reverse["lgd_multiplier"]:.2f}×</b>.</div>',
        unsafe_allow_html=True,
    )
    stress_grid = []
    for pd_multiplier in [1.0, 1.25, 1.5, 2.0]:
        for lgd_multiplier in [1.0, 1.15, 1.3, 1.5]:
            stressed = clean.copy()
            stressed["pd"] = np.minimum(stressed["pd"] * pd_multiplier, 0.999)
            stressed["lgd"] = np.minimum(stressed["lgd"] * lgd_multiplier, 1.0)
            result = simulate_export_credit_losses(
                stressed,
                simulations=min(simulations, 15_000),
                confidence=confidence,
                seed=42,
            )
            stress_grid.append(
                {
                    "PD multiplier": pd_multiplier,
                    "LGD multiplier": lgd_multiplier,
                    "Loss-at-risk (£m)": result.loss_var,
                }
            )
    heatmap_data = pd.DataFrame(stress_grid).pivot(
        index="LGD multiplier", columns="PD multiplier", values="Loss-at-risk (£m)"
    )
    heatmap = px.imshow(
        heatmap_data,
        text_auto=".0f",
        color_continuous_scale=teal_scale,
        labels={"x": "PD multiplier", "y": "LGD multiplier", "color": "Loss-at-risk (£m)"},
    )
    heatmap.update_layout(template=plot_template, height=430)
    st.plotly_chart(heatmap, width="stretch")

with report_tab:
    report = executive_risk_report(clean, simulation)
    st.markdown(report)
    st.download_button(
        "Download committee report",
        data=report,
        file_name="export_credit_portfolio_risk_report.md",
        mime="text/markdown",
        width="stretch",
    )
    st.download_button(
        "Download country limit report",
        data=limits.to_csv(index=False),
        file_name="country_limit_report.csv",
        mime="text/csv",
        width="stretch",
    )

st.caption(
    "Educational model using fictional deals. It does not reproduce UKEF PRISM, "
    "implement OECD premium rules, or provide underwriting or investment advice."
)