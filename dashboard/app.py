"""Interactive Export Credit Portfolio Risk Dashboard."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from quant_risk.country_risk import assess_country, country_briefing, latest_country_values
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
from quant_risk.product_pricing import (
    PRODUCTS,
    price_export_credit,
    product_catalogue,
    shortlist_products,
)
from quant_risk.reporting import executive_risk_report
from quant_risk.underwriting import assess_corporate_obligor, project_finance_pd

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "data" / "synthetic_export_credit_portfolio.csv"
SCENARIO_PATH = ROOT / "data" / "ifrs9_scenarios.csv"
COUNTRY_RISK_PATH = ROOT / "data" / "country_risk_world_bank.csv"
COVER_POLICY_PATH = ROOT / "data" / "ukef_cover_policy_snapshot.csv"

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
def load_default_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_csv(PORTFOLIO_PATH),
        pd.read_csv(SCENARIO_PATH),
        pd.read_csv(COUNTRY_RISK_PATH),
        pd.read_csv(COVER_POLICY_PATH),
    )


default_portfolio, scenarios, country_panel, cover_policy = load_default_data()

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

(
    overview,
    country_tab,
    underwriting_tab,
    pricer_tab,
    limits_tab,
    ifrs_tab,
    pricing_tab,
    stress_tab,
    report_tab,
) = st.tabs(
    [
        "Portfolio overview",
        "Country risk monitor",
        "Credit underwriting",
        "Product pricer",
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

with country_tab:
    st.subheader("Country risk and exposure monitor")
    st.caption(
        "Independent screening score using public World Bank macroeconomic and governance "
        "indicators, combined with fictional portfolio exposure and a dated snapshot of "
        "public UKEF cover indications. This is not an official UKEF or OECD risk score."
    )
    available_countries = sorted(set(clean["country"]) & set(country_panel["country"]))
    portfolio_screen = []
    for country in available_countries:
        country_values, _ = latest_country_values(country_panel, country)
        country_assessment = assess_country(country_values)
        country_limit = limits.loc[limits["country"] == country].iloc[0]
        portfolio_screen.append(
            {
                "country": country,
                "risk_score": country_assessment.score,
                "grade": country_assessment.grade,
                "exposure_gbp_m": country_limit["exposure_gbp_m"],
                "utilisation": country_limit["utilisation"],
                "warnings": len(country_assessment.warnings),
                "data_coverage": country_assessment.coverage,
            }
        )
    screen = pd.DataFrame(portfolio_screen)
    screen_fig = px.scatter(
        screen,
        x="risk_score",
        y="utilisation",
        size="exposure_gbp_m",
        color="warnings",
        hover_name="country",
        hover_data={"grade": True, "data_coverage": ":.0%", "exposure_gbp_m": ":.1f"},
        color_continuous_scale=teal_scale,
        labels={
            "risk_score": "Independent country-risk score",
            "utilisation": "Illustrative country-limit utilisation",
            "warnings": "Warnings",
        },
    )
    screen_fig.add_vline(x=60, line_dash="dash", line_color="#ff788c")
    screen_fig.add_hline(y=0.8, line_dash="dash", line_color="#d8aa45")
    screen_fig.update_yaxes(tickformat=".0%")
    screen_fig.update_layout(template=plot_template, height=430, margin={"t": 25})
    st.plotly_chart(screen_fig, width="stretch")

    selected_country = st.selectbox("Country profile", available_countries)
    values, vintage = latest_country_values(country_panel, selected_country)
    assessment = assess_country(values)
    selected_limit = limits.loc[limits["country"] == selected_country].iloc[0]
    policy = cover_policy.loc[cover_policy["country"] == selected_country].iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Independent risk score", f"{assessment.score:.1f} / 100")
    c2.metric("Screening grade", assessment.grade)
    c3.metric("Covered exposure", f"£{selected_limit['exposure_gbp_m']:,.0f}m")
    c4.metric("Limit utilisation", f"{selected_limit['utilisation']:.1%}")
    c5.metric("UKEF appetite snapshot", policy["market_risk_appetite"])

    left, right = st.columns([1.1, 1])
    with left:
        display_components = assessment.components.assign(
            indicator=lambda frame: frame["indicator"].str.replace("_", " ").str.title()
        ).sort_values("risk_score")
        component_fig = px.bar(
            display_components,
            x="risk_score",
            y="indicator",
            orientation="h",
            color="risk_score",
            color_continuous_scale=["#70e1c1", "#d8aa45", "#ff788c"],
            range_color=[0, 100],
            hover_data={"value": ":.2f", "effective_weight": ":.1%"},
            labels={"risk_score": "Component risk (0–100)", "indicator": ""},
        )
        component_fig.update_layout(template=plot_template, height=430, margin={"t": 20})
        st.plotly_chart(component_fig, width="stretch")
    with right:
        st.markdown("#### Public cover-policy context")
        st.markdown(
            f'<div class="decision-card"><b>Cash / short term:</b> '
            f'{policy["short_term_cover"]}<br><b>Medium / long term:</b> '
            f'{policy["medium_long_term_cover"]}<br><b>Care on location:</b> '
            f'{"Yes" if policy["care_on_location"] else "No"}<br>'
            f'<b>Sustainable lending criteria:</b> '
            f'{"Yes" if policy["sustainable_lending"] else "No"}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Snapshot: {policy['snapshot_date']}. Policy can change at any time.")
        st.link_button("Check current UKEF policy", policy["source_url"], width="stretch")
        st.markdown("#### Early-warning signals")
        if assessment.warnings:
            for warning in assessment.warnings:
                st.warning(warning)
        else:
            st.success("No severe model threshold triggered in the latest available readings.")

    history = country_panel.loc[country_panel["country"] == selected_country].copy()
    history = history.loc[history["indicator"].isin(["gdp_growth", "inflation", "current_account"])]
    history["indicator"] = history["indicator"].str.replace("_", " ").str.title()
    trend_fig = px.line(
        history,
        x="year",
        y="value",
        color="indicator",
        markers=True,
        labels={"value": "Indicator value (%)", "year": "", "indicator": ""},
    )
    trend_fig.update_layout(template=plot_template, height=360, margin={"t": 25})
    st.plotly_chart(trend_fig, width="stretch")

    brief = country_briefing(
        selected_country,
        assessment,
        selected_limit["exposure_gbp_m"],
        selected_limit["utilisation"],
        vintage,
        f"The public UKEF market-risk-appetite snapshot is {policy['market_risk_appetite']}",
    )
    st.download_button(
        "Download country briefing",
        data=brief,
        file_name=f"{selected_country.lower().replace(' ', '_')}_country_brief.md",
        mime="text/markdown",
        width="stretch",
    )

with underwriting_tab:
    st.subheader("Corporate and project credit underwriting")
    st.caption(
        "A transparent financial-ratio scorecard converts obligor fundamentals and the "
        "country overlay into an indicative grade and annual PD. Inputs are illustrative."
    )
    u1, u2, u3, u4 = st.columns(4)
    debt_ebitda = u1.number_input("Debt / EBITDA", 0.0, 15.0, 3.0, 0.25)
    interest_cover = u2.number_input("EBITDA / interest", 0.1, 20.0, 4.0, 0.25)
    dscr = u3.number_input("Debt-service coverage", 0.1, 5.0, 1.4, 0.05)
    current_ratio = u4.number_input("Current ratio", 0.1, 5.0, 1.3, 0.1)
    u5, u6, u7, u8 = st.columns(4)
    operating_margin = u5.number_input("Operating margin", -0.5, 0.6, 0.12, 0.01, format="%.2f")
    revenue_growth = u6.number_input("Revenue growth", -0.5, 0.8, 0.05, 0.01, format="%.2f")
    underwriting_country = u7.selectbox("Country overlay", available_countries, key="uw_country")
    years_trading = u8.number_input("Years trading", 1, 100, 10)
    uw_values, _ = latest_country_values(country_panel, underwriting_country)
    uw_country_score = assess_country(uw_values).score
    credit = assess_corporate_obligor(
        debt_to_ebitda=debt_ebitda,
        interest_coverage=interest_cover,
        debt_service_coverage=dscr,
        current_ratio=current_ratio,
        operating_margin=operating_margin,
        revenue_growth=revenue_growth,
        country_risk_score=uw_country_score,
        years_trading=years_trading,
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Obligor score", f"{credit.score:.1f} / 100")
    m2.metric("Indicative grade", credit.grade)
    m3.metric("Base annual PD", f"{credit.one_year_pd:.2%}")
    m4.metric("Country overlay", f"{uw_country_score:.1f} / 100")

    project_toggle = st.toggle("Apply project-finance overlays")
    pricing_pd = credit.one_year_pd
    if project_toggle:
        p1, p2 = st.columns(2)
        completion = p1.select_slider("Completion risk", ["Low", "Medium", "High"], value="Medium")
        offtake = p2.select_slider("Offtake strength", ["Strong", "Adequate", "Weak"], value="Adequate")
        pricing_pd = project_finance_pd(credit.one_year_pd, dscr, completion, offtake)
        st.metric("PD after project overlays", f"{pricing_pd:.2%}")
    credit_fig = px.bar(
        credit.components.sort_values("contribution"), x="contribution", y="component",
        orientation="h", color="risk_score", color_continuous_scale=teal_scale,
        hover_data={"raw_value": ":.2f", "weight": ":.0%", "risk_score": ":.1f"},
        labels={"contribution": "Weighted score contribution", "component": ""},
    )
    credit_fig.update_layout(template=plot_template, height=420, margin={"t": 20})
    st.plotly_chart(credit_fig, width="stretch")
    if credit.flags:
        st.markdown("#### Underwriting flags")
        for flag in credit.flags:
            st.warning(flag)

with pricer_tab:
    st.subheader("Export-credit product selector and economic pricer")
    st.caption(
        "Prices an amortising covered exposure from expected loss, economic capital and "
        "operating cost. It is an independent demonstration—not UKEF's internal model."
    )
    s1, s2, s3 = st.columns([1.5, 1, 1])
    deal_need = s1.selectbox(
        "What does the transaction need?",
        [
            "Finance an overseas buyer", "Protect exporter from non-payment",
            "Provide exporter working capital", "Support a contract bond",
        ],
    )
    selection_amount = s2.number_input("Selection amount (£m)", 1.0, 2_000.0, 100.0)
    selection_tenor = s3.number_input("Selection term (years)", 0.5, 30.0, 5.0, 0.5)
    shortlist = shortlist_products(deal_need, selection_amount, selection_tenor)
    st.dataframe(
        shortlist.style.format({"fit_score": "{:.0f} / 100"}),
        hide_index=True, width="stretch",
    )
    selected_product = st.selectbox(
        "Product to price", list(PRODUCTS),
        index=list(PRODUCTS).index(shortlist.iloc[0]["product"]), key="pricing_product",
    )
    details = PRODUCTS[selected_product]
    st.markdown(
        f'<div class="decision-card"><b>{selected_product}</b><br>{details["purpose"]}<br>'
        f'<b>Risk entity:</b> {details["risk_entity"]} · <b>Charge:</b> '
        f'{details["pricing_basis"]}</div>', unsafe_allow_html=True,
    )
    d1, d2, d3, d4 = st.columns(4)
    deal_amount = d1.number_input("Facility / contract amount (£m)", 1.0, 2_000.0, 100.0, 5.0)
    deal_pd = d2.number_input("Annual PD", 0.0001, 0.50, 0.02, 0.0025, format="%.4f")
    deal_lgd = d3.number_input("LGD", 0.0, 1.0, 0.50, 0.05)
    cover_share = d4.number_input(
        "Covered share", 0.0, 1.0, float(details["typical_cover"]), 0.05
    )
    d5, d6, d7, d8 = st.columns(4)
    tenor = d5.number_input("Total tenor (years)", 1.0, 30.0, 8.0, 0.5)
    drawdown = d6.number_input("Drawdown period (years)", 0.0, 10.0, 1.0, 0.5)
    profile = d7.selectbox("Repayment profile", ["Equal principal", "Bullet"])
    external_floor = d8.number_input(
        "External MPR floor (upfront)", 0.0, 1.0, 0.0, 0.005, format="%.3f",
        help="Optional user-supplied floor. The app does not calculate the official OECD MPR.",
    )
    priced = price_export_credit(
        product=selected_product, amount_gbp_m=deal_amount, annual_pd=deal_pd,
        lgd=deal_lgd, tenor_years=tenor, guarantee_share=cover_share,
        drawdown_years=drawdown, repayment_profile=profile,
        oecd_mpr_floor_rate=external_floor,
    )
    q1, q2, q3, q4, q5 = st.columns(5)
    q1.metric("Covered exposure", f"£{priced.exposure_gbp_m:,.1f}m")
    q2.metric("Lifetime expected loss", f"£{priced.expected_loss_gbp_m:,.2f}m")
    q3.metric("Economic capital", f"£{priced.economic_capital_gbp_m:,.2f}m")
    q4.metric("Required premium", f"£{priced.required_premium_gbp_m:,.2f}m")
    q5.metric("Quoted upfront rate", f"{priced.quoted_upfront_rate:.2%}")
    st.markdown(
        f'<div class="decision-card"><b>Equivalent annual spread:</b> '
        f'{priced.equivalent_annual_spread_bps:,.0f} bps · <b>Illustrative RAROC:</b> '
        f'{priced.risk_adjusted_return:.1%} · <b>Binding basis:</b> '
        f'{"external floor" if priced.floor_upfront_rate > priced.model_upfront_rate else "economic model"}'
        f'</div>', unsafe_allow_html=True,
    )
    exposure_fig = px.area(
        priced.schedule, x="year", y="opening_exposure_gbp_m",
        labels={"year": "Year", "opening_exposure_gbp_m": "Outstanding exposure (£m)"},
    )
    exposure_fig.update_traces(line_color="#70e1c1", fillcolor="rgba(112,225,193,.22)")
    exposure_fig.update_layout(template=plot_template, height=350, margin={"t": 20})
    st.plotly_chart(exposure_fig, width="stretch")
    st.markdown("#### PD × LGD premium sensitivity")
    sensitivity = []
    for pd_multiplier in [0.5, 1.0, 1.5, 2.0]:
        for lgd_multiplier in [0.75, 1.0, 1.25, 1.5]:
            stressed_price = price_export_credit(
                product=selected_product, amount_gbp_m=deal_amount,
                annual_pd=min(deal_pd * pd_multiplier, 0.999),
                lgd=min(deal_lgd * lgd_multiplier, 1.0), tenor_years=tenor,
                guarantee_share=cover_share, drawdown_years=drawdown,
                repayment_profile=profile, oecd_mpr_floor_rate=external_floor,
            )
            sensitivity.append(
                {"PD multiplier": pd_multiplier, "LGD multiplier": lgd_multiplier,
                 "Required premium rate": stressed_price.model_upfront_rate}
            )
    sensitivity_table = pd.DataFrame(sensitivity).pivot(
        index="LGD multiplier", columns="PD multiplier", values="Required premium rate"
    )
    sensitivity_fig = px.imshow(
        sensitivity_table, text_auto=".1%", color_continuous_scale=teal_scale,
        labels={"x": "PD multiplier", "y": "LGD multiplier", "color": "Model rate"},
    )
    sensitivity_fig.update_layout(template=plot_template, height=380)
    st.plotly_chart(sensitivity_fig, width="stretch")
    with st.expander("Compare supported product structures"):
        st.dataframe(product_catalogue(), hide_index=True, width="stretch")
    st.download_button(
        "Download pricing cash flows", priced.schedule.to_csv(index=False),
        "illustrative_export_credit_price.csv", "text/csv", width="stretch",
    )

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
