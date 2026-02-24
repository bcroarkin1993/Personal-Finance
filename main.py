from typing import Dict, Any

import pandas as pd
import streamlit as st
import altair as alt

from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar
from scripts.utils import (
    calculate_average_monthly_total,
    calculate_yearly_total,
    get_last_refresh_date_from_df,
    get_portfolio_snapshot,
    run_subprocess_refresh,
)

# ----------------- PAGE CONFIG ----------------- #

st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide",
)

# ----------------- INJECT SIDEBAR ----------------- #
# This renders the centralized navigation
make_sidebar("Home")

# ----------------- CUSTOM STYLING ----------------- #
st.markdown(
    """
    <style>
    /* Hero gradient background */
    .hero-container {
        padding: 1.5rem 1.75rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 40%, #3b8d99 100%);
        color: white;
        margin-bottom: 0.75rem;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .hero-subtitle {
        font-size: 1rem;
        opacity: 0.9;
        margin-top: 0.25rem;
    }
    .hero-pill {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 999px;
        background-color: rgba(255,255,255,0.12);
        font-size: 0.8rem;
        margin-bottom: 0.5rem;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background-color: #0b1621;
        padding: 10px 14px;
        border-radius: 14px;
        border: 1px solid #243447;
    }
    div[data-testid="metric-container"] > label > div {
        font-size: 0.75rem;
        font-weight: 500;
    }
    div[data-testid="metric-container"] > div {
        font-size: 0.95rem;
        font-weight: 600;
        overflow-wrap: anywhere;
    }

    /* Section titles */
    .section-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-top: 0.75rem;
        margin-bottom: 0.25rem;
    }

    /* Small label text */
    .muted-label {
        font-size: 0.8rem;
        opacity: 0.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------- HOME PAGE LOGIC ----------------- #

# Load data safely (returns empty DFs if files missing)
data: Dict[str, Any] = load_and_preprocess_data()

income_df: pd.DataFrame = data.get("income", pd.DataFrame())
expenses_df: pd.DataFrame = data.get("expenses", pd.DataFrame())
daily_stocks_df: pd.DataFrame = data.get("daily_stocks", pd.DataFrame())
daily_equity_df: pd.DataFrame = data.get("daily_equity", pd.DataFrame())

# Check for empty state to guide the user
if income_df.empty and expenses_df.empty and daily_stocks_df.empty:
    st.warning(
        """
        ⚠️ **No data found.**

        It looks like your data files are missing or empty. 
        Please ensure your `Budget.xlsx` and `stock_dictionary.json` are in the `data/` folder, 
        then click the **Refresh** buttons below to process them.
        """
    )

# Calculate Budget Metrics
avg_monthly_income = calculate_average_monthly_total(income_df)
avg_monthly_expenses = calculate_average_monthly_total(expenses_df)
annual_income = calculate_yearly_total(income_df)
annual_expenses = calculate_yearly_total(expenses_df)

if annual_income > 0:
    savings_rate = (annual_income - annual_expenses) / annual_income * 100
else:
    savings_rate = 0.0

last_expenses_refresh = get_last_refresh_date_from_df(expenses_df, "date")

# Calculate Investment Metrics
portfolio_snapshot = get_portfolio_snapshot(data)
total_portfolio_value = portfolio_snapshot["total_portfolio_value"]
total_equity = portfolio_snapshot["total_equity"]
total_profit = portfolio_snapshot["total_profit"]
last_investment_refresh = get_last_refresh_date_from_df(daily_stocks_df, "date")

# ----------------- HERO SECTION ----------------- #
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-pill">Dashboard Overview</div>
        <div class="hero-title">Personal Finance Command Center</div>
        <div class="hero-subtitle">
            High-level snapshot of your budget and investments in one place.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- HIGH-LEVEL SNAPSHOT ----------------- #
st.markdown('<div class="section-title">Today at a Glance</div>', unsafe_allow_html=True)
top_col1, top_col2, top_col3, top_col4 = st.columns(4)

with top_col1:
    st.metric("💵 Total Income (YTD)", f"${annual_income:,.2f}")
    st.markdown('<span class="muted-label">From all tracked sources</span>', unsafe_allow_html=True)

with top_col2:
    st.metric("🧾 Total Expenses (YTD)", f"${annual_expenses:,.2f}")
    st.markdown('<span class="muted-label">Across all categories</span>', unsafe_allow_html=True)

with top_col3:
    # Use delta to color the number green/red
    sr_delta = f"{savings_rate:.1f}%" if savings_rate != 0 else None
    st.metric("📊 Savings Rate", f"{savings_rate:.1f}%", delta=sr_delta)
    st.markdown('<span class="muted-label">Income left after expenses</span>', unsafe_allow_html=True)

with top_col4:
    st.metric("💼 Portfolio Value", f"${total_portfolio_value:,.2f}")
    st.markdown('<span class="muted-label">Latest market value</span>', unsafe_allow_html=True)

st.markdown("")  # spacing

# ----------------- BUDGET & INVESTMENT OVERVIEW SIDE-BY-SIDE ----------------- #
left, right = st.columns(2)

# ----- Budget Overview Column ----- #
with left:
    st.markdown('<div class="section-title">💸 Budget Overview</div>', unsafe_allow_html=True)
    st.write(
        """
        Get a quick read on your cashflow:
        - How much you're bringing in vs. spending
        - What your average month looks like
        - Whether your savings rate is trending in the right direction
        """
    )

    b1, b2 = st.columns(2)
    with b1:
        st.metric("Avg Monthly Income", f"${avg_monthly_income:,.2f}")
    with b2:
        st.metric("Avg Monthly Expenses", f"${avg_monthly_expenses:,.2f}")

    st.markdown(
        f"<span class='muted-label'>Budget data last refreshed: {last_expenses_refresh}</span>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh Budget Data"):
        run_subprocess_refresh(
            "scripts/process_budget_data.py",
            load_and_preprocess_data.clear,
            "Processing Budget.xlsx...",
        )

# ----- Investments Overview Column ----- #
with right:
    st.markdown('<div class="section-title">📈 Investments Overview</div>', unsafe_allow_html=True)
    st.write(
        """
        See how your investments are performing overall:
        - Current portfolio value vs. amount invested
        - Total profit or loss across accounts
        """
    )

    i1, i2, i3 = st.columns(3)
    with i1:
        st.metric("Portfolio Value", f"${total_portfolio_value:,.2f}")
    with i2:
        st.metric("Total Equity (Invested)", f"${total_equity:,.2f}")
    with i3:
        # Use delta to color profit/loss green/red
        pl_delta = f"${total_profit:,.2f}" if total_profit != 0 else None
        st.metric("Total Profit / Loss", f"${total_profit:,.2f}", delta=pl_delta)

    st.markdown(
        f"<span class='muted-label'>Investment data last refreshed: {last_investment_refresh}</span>",
        unsafe_allow_html=True,
    )

    b_incr, b_full = st.columns(2)
    with b_incr:
        if st.button("🔄 Refresh Investment Data", use_container_width=True):
            run_subprocess_refresh(
                "scripts/process_investment_data.py",
                load_and_preprocess_data.clear,
                "Fetching latest prices (incremental)...",
            )
    with b_full:
        if st.button(
            "⚠️ Full Rebuild",
            use_container_width=True,
            help="Re-fetches ALL historical data from 2016. Takes 5–10 minutes.",
        ):
            run_subprocess_refresh(
                "scripts/process_investment_data.py",
                load_and_preprocess_data.clear,
                "Full rebuild in progress (this takes ~5 min)...",
                full_refresh=True,
            )
    st.caption("Incremental: updates prices for today. Full Rebuild: re-fetches all history (fixes corrupt data).")

# ----------------- PORTFOLIO TREND (BOTTOM, FULL WIDTH) ----------------- #
st.markdown('<div class="section-title">📉 Portfolio Trend Over Time</div>', unsafe_allow_html=True)

if not daily_equity_df.empty and {"date", "market_value", "total_profit"}.issubset(daily_equity_df.columns):
    chart_df = daily_equity_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date"]).sort_values("date")

    # Altair chart with month-year x-axis and profit in tooltip, color by profit sign
    chart = (
        alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
            x=alt.X(
                "date:T",
                axis=alt.Axis(format="%b %y", title="Date"),
            ),
            y=alt.Y("market_value:Q", title="Portfolio Value"),
            color=alt.condition(
                "datum.total_profit >= 0",
                alt.value("#2ecc71"),  # green
                alt.value("#e74c3c"),  # red
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("market_value:Q", title="Portfolio Value", format=",.2f"),
                alt.Tooltip("total_profit:Q", title="Total Profit", format=",.2f"),
            ],
        )
            .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)
    st.markdown(
        "<span class='muted-label'>Color reflects profit (green) or loss (red) at each point in time.</span>",
        unsafe_allow_html=True,
    )
else:
    st.info("No portfolio history available yet. Once you have daily data, a trend chart will appear here.")

# ----------------- FOOTER ----------------- #
st.markdown("---")
st.write(
    "🔍 **Next step:** Use the sidebar to dive into Budget or Investments and start exploring the details."
)