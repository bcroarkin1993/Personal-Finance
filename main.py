from typing import Dict, Any

import pandas as pd
import streamlit as st
import altair as alt

from scripts.data_processing import load_and_preprocess_data, clear_all_caches
from scripts.navigation import make_sidebar
from scripts.theme import (
    GREEN, RED,
    page_header, section_header, stat_card_grid, grad_divider,
)
from scripts.utils import (
    calculate_average_monthly_total,
    calculate_yearly_total,
    get_last_refresh_date_from_df,
    get_portfolio_snapshot,
    run_subprocess_refresh,
    render_refresh_status,
)

# ----------------- PAGE CONFIG ----------------- #

st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide",
)

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Home")

# (shared CSS injected by page_header below)

# ----------------- HOME PAGE LOGIC ----------------- #

# Show any pending refresh result from the previous run
render_refresh_status()

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
page_header(
    "Personal Finance Command Center",
    subtitle="High-level snapshot of your budget and investments in one place.",
    pills=["Dashboard Overview"],
)

# ----------------- HIGH-LEVEL SNAPSHOT ----------------- #
st.html(section_header("Today at a Glance"))

st.html(stat_card_grid([
    {
        "label": "Total Income (YTD)",
        "value": f"${annual_income:,.2f}",
        "icon": "💵",
        "subtitle": "From all tracked sources",
    },
    {
        "label": "Total Expenses (YTD)",
        "value": f"${annual_expenses:,.2f}",
        "icon": "🧾",
        "subtitle": "Across all categories",
    },
    {
        "label": "Savings Rate",
        "value": f"{savings_rate:.1f}%",
        "icon": "📊",
        "delta": f"{savings_rate:.1f}%",
        "positive": savings_rate >= 0,
        "subtitle": "Income left after expenses",
    },
    {
        "label": "Portfolio Value",
        "value": f"${total_portfolio_value:,.2f}",
        "icon": "💼",
        "subtitle": "Latest market value",
    },
], cols=4))

# ----------------- BUDGET & INVESTMENT OVERVIEW SIDE-BY-SIDE ----------------- #
st.html(grad_divider())
left, right = st.columns(2)

# ----- Budget Overview Column ----- #
with left:
    st.html(section_header("Budget Overview", icon="💸"))
    st.html("""
    <div style='color:#a5d6a7;font-size:0.88rem;line-height:1.7;margin-bottom:8px;'>
      Get a quick read on your cashflow:
      <ul style='margin:4px 0;padding-left:18px;'>
        <li>How much you're bringing in vs. spending</li>
        <li>What your average month looks like</li>
        <li>Whether your savings rate is trending in the right direction</li>
      </ul>
    </div>
    """)

    st.html(stat_card_grid([
        {"label": "Avg Monthly Income",   "value": f"${avg_monthly_income:,.2f}",   "icon": "📥"},
        {"label": "Avg Monthly Expenses", "value": f"${avg_monthly_expenses:,.2f}", "icon": "📤",
         "positive": avg_monthly_income >= avg_monthly_expenses},
    ], cols=2))

    st.html(f"<span class='muted-label'>Budget data last refreshed: {last_expenses_refresh}</span>")

    if st.button("🔄 Refresh Budget Data"):
        run_subprocess_refresh(
            "scripts/process_budget_data.py",
            clear_all_caches,
            "Processing Budget.xlsx...",
        )

# ----- Investments Overview Column ----- #
with right:
    st.html(section_header("Investments Overview", icon="📈"))
    st.html("""
    <div style='color:#a5d6a7;font-size:0.88rem;line-height:1.7;margin-bottom:8px;'>
      See how your investments are performing overall:
      <ul style='margin:4px 0;padding-left:18px;'>
        <li>Current portfolio value vs. amount invested</li>
        <li>Total profit or loss across accounts</li>
      </ul>
    </div>
    """)

    st.html(stat_card_grid([
        {"label": "Portfolio Value",       "value": f"${total_portfolio_value:,.2f}", "icon": "💼"},
        {"label": "Total Equity (Invested)", "value": f"${total_equity:,.2f}",        "icon": "💰"},
        {
            "label": "Total Profit / Loss",
            "value": f"${total_profit:,.2f}",
            "icon": "📊",
            "delta": f"${total_profit:,.2f}",
            "positive": total_profit >= 0,
        },
    ], cols=3))

    st.html(f"<span class='muted-label'>Investment data last refreshed: {last_investment_refresh}</span>")

    b_incr, b_full = st.columns(2)
    with b_incr:
        if st.button("🔄 Refresh Investment Data", use_container_width=True):
            run_subprocess_refresh(
                "scripts/process_investment_data.py",
                clear_all_caches,
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
                clear_all_caches,
                "Full rebuild in progress (this takes ~5 min)...",
                full_refresh=True,
            )
    st.caption("Incremental: updates prices for today. Full Rebuild: re-fetches all history (fixes corrupt data).")

# ----------------- PORTFOLIO TREND (BOTTOM, FULL WIDTH) ----------------- #
st.html(grad_divider())
st.html(section_header("Portfolio Trend Over Time", icon="📉"))

if not daily_equity_df.empty and {"date", "market_value", "total_profit"}.issubset(daily_equity_df.columns):
    chart_df = daily_equity_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.dropna(subset=["date"]).sort_values("date")

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
                alt.value(GREEN),
                alt.value(RED),
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
    st.html("<span class='muted-label'>Color reflects profit (green) or loss (red) at each point in time.</span>")
else:
    st.info("No portfolio history available yet. Once you have daily data, a trend chart will appear here.")

# ----------------- FOOTER ----------------- #
st.html(grad_divider())
st.write(
    "🔍 **Next step:** Use the sidebar to dive into Budget or Investments and start exploring the details."
)
