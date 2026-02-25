import streamlit as st
import pandas as pd
import plotly.express as px
import random
from datetime import datetime, timedelta
from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar
from scripts.theme import BLUE, GREEN_VIVID, page_header, section_header, grad_divider
from scripts.utils import render_freshness_badge, render_refresh_status

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Company Deep Dive", page_icon="🏢", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Company Deep-Dive")

page_header("Company Deep-Dive", icon="🏢",
            subtitle="Detailed financials and analyst data for individual stocks")

render_refresh_status()

# ----------------- DATA LOADING ----------------- #
data = load_and_preprocess_data()
stock_info   = data["stock_info"].copy()
daily_stocks = data["daily_stocks"].copy()

if not stock_info.empty and "last_updated" in stock_info.columns:
    render_freshness_badge(pd.to_datetime(stock_info["last_updated"]).max(), label="Fundamentals last updated")

stock_info["display_name"] = stock_info["company"] + " (" + stock_info["stock"] + ")"
company_map = dict(zip(stock_info["display_name"], stock_info["stock"]))

# ----------------- SELECTOR ----------------- #
options = sorted(company_map.keys())

if options:
    default_index = random.randint(0, len(options) - 1)
else:
    default_index = 0

selected_display = st.selectbox("Select a Company:", options=options, index=default_index)

if selected_display:
    selected_ticker = company_map[selected_display]

    if not stock_info[stock_info["stock"] == selected_ticker].empty:
        company_data = stock_info[stock_info["stock"] == selected_ticker].iloc[0]
        history_data = daily_stocks[daily_stocks["stock"] == selected_ticker].copy()
    else:
        st.error("Data for this company is missing.")
        st.stop()
else:
    st.stop()


# ----------------- HELPER: SECTOR CONTEXT ----------------- #
def get_comparative_metric(df, sector, metric_col, current_val, inverse=False):
    if current_val == 0 or pd.isna(current_val):
        return "N/A", "off"

    peers = df[df["sector"] == sector]

    if len(peers) < 3:
        peers = df
        comparison_label = "vs Market Median"
    else:
        comparison_label = "vs Sector Median"

    median_val = peers[metric_col].median()

    if median_val == 0 or pd.isna(median_val):
        return "N/A", "off"

    diff = current_val - median_val

    if inverse:
        delta_color = "normal" if diff < 0 else "inverse"
    else:
        delta_color = "normal" if diff > 0 else "inverse"

    return f"{comparison_label}: {median_val:,.2f}", delta_color


# ----------------- SECTION 1: PROFILE & CHART ----------------- #
st.html(grad_divider())
col_profile, col_chart = st.columns([1, 2])

with col_profile:
    st.html(section_header("Company Profile", icon="🏢"))

    # Ticker header inside a styled card div
    sector   = str(company_data.get("sector", "N/A"))
    industry = str(company_data.get("industry", "N/A"))
    st.html(f"""
    <div style='background:#0d1f12;border:1px solid #1b5e20;border-radius:10px;padding:14px 18px;margin-bottom:8px;'>
      <div style='color:#fff;font-size:1.6rem;font-weight:700;'>{selected_ticker}</div>
      <div style='color:#a5d6a7;font-size:0.85rem;margin-top:2px;'>{sector} | {industry}</div>
    </div>
    """)

    st.markdown(f"**CEO:** {company_data.get('ceo', 'N/A')}")
    st.markdown(
        f"**HQ:** {company_data.get('city', '')}, {company_data.get('state', '')}, {company_data.get('country', '')}")
    st.markdown(f"**Employees:** {company_data.get('full_time_employees', 'N/A')}")
    st.markdown("**Description:**")
    st.markdown(f"*{str(company_data.get('description', 'No description available.'))[:400]}...*")

    with st.expander("Read Full Description"):
        st.write(company_data.get('description', ''))

with col_chart:
    st.html(section_header("Price History (1 Year)", icon="📉"))

    if not history_data.empty:
        history_data["date"] = pd.to_datetime(history_data["date"])
        one_year_ago = datetime.now() - timedelta(days=365)
        chart_df = history_data[history_data["date"] >= one_year_ago].sort_values("date")

        fig = px.line(chart_df, x="date", y="close", title=f"{selected_ticker} Stock Price")
        fig.update_traces(fill='tozeroy', line_color=GREEN_VIVID)
        fig.update_layout(xaxis_title=None, yaxis_title="Price ($)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical price data available.")

# ----------------- SECTION 2: FUNDAMENTAL SCORECARD ----------------- #
st.html(grad_divider())
st.html(section_header("Fundamental Scorecard", icon="📊",
                        subtitle="Metrics compared against the median of other companies in the same sector."))

metrics_config = [
    ("P/E Ratio",         "pe_ratio",          True),
    ("P/B Ratio",         "pb_ratio",          True),
    ("Beta (Volatility)", "beta",              True),
    ("Dividend Yield",    "dividend_yield",    False),
    ("Profit Margins",    "profit_margins",    False),
    ("Market Cap (B)",    "market_cap",        False),
]

m_cols  = st.columns(len(metrics_config))
sector  = company_data.get("sector", "")

for i, (label, col_name, is_inverse) in enumerate(metrics_config):
    with m_cols[i]:
        val = company_data.get(col_name, 0)

        if col_name in stock_info.columns:
            comp_text, color_mode = get_comparative_metric(stock_info, sector, col_name, val, is_inverse)

            if col_name in ["dividend_yield", "profit_margins"]:
                fmt_val = f"{val * 100:.2f}%" if pd.notnull(val) else "N/A"
            else:
                fmt_val = f"{val:.2f}" if pd.notnull(val) else "N/A"

            peers = stock_info[stock_info["sector"] == sector]
            if len(peers) < 3:
                peers = stock_info

            if pd.notnull(val) and not peers[col_name].isnull().all():
                median       = peers[col_name].median()
                numeric_delta = (val - median)
            else:
                numeric_delta = None

            st.metric(
                label=label,
                value=fmt_val,
                delta=numeric_delta if color_mode != "off" else None,
                delta_color=color_mode
            )
            st.caption(comp_text)
        else:
            st.metric(label, "N/A")

# ----------------- SECTION 3: RISK & ANALYST RATINGS ----------------- #
st.html(grad_divider())
r1, r2 = st.columns(2)

with r1:
    st.html(section_header("Risk Profile", icon="⚠️"))
    risk_cols    = ["audit_risk", "board_risk", "compensation_risk", "shareholder_rights_risk"]
    current_risks = {k: company_data.get(k, 0) for k in risk_cols}

    risk_df = pd.DataFrame(dict(
        r=list(current_risks.values()),
        theta=[k.replace("_", " ").title() for k in current_risks.keys()]
    ))

    if risk_df['r'].sum() > 0:
        fig_risk = px.line_polar(risk_df, r='r', theta='theta', line_close=True, range_r=[0, 10])
        fig_risk.update_traces(fill='toself')
        fig_risk.update_layout(title="Governance Risk Scores (Lower is Better)")
        st.plotly_chart(fig_risk, use_container_width=True)
    else:
        st.info("No detailed risk data available.")

with r2:
    st.html(section_header("Analyst Consensus", icon="🎯"))
    target_mean   = company_data.get("target_mean_price", 0)
    current_price = history_data.iloc[-1]["close"] if not history_data.empty else 0

    if target_mean > 0 and current_price > 0:
        upside = ((target_mean - current_price) / current_price) * 100
        st.metric("Mean Target Price", f"${target_mean:,.2f}", f"{upside:.2f}% Upside")

        fig_gauge = px.bar(
            x=[current_price, target_mean],
            y=["Current", "Target"],
            orientation='h',
            title="Current vs Target Price"
        )
        st.plotly_chart(fig_gauge, use_container_width=True)
    else:
        st.info("No analyst target data available.")
