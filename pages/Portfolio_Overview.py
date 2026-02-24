import sys
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
from datetime import date, timedelta
from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar
from scripts.utils import render_freshness_badge, run_subprocess_refresh

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Portfolio Overview", page_icon="📈", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Portfolio Overview")

col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("📈 Portfolio Overview")
with col_refresh:
    st.markdown("<div style='padding-top:12px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        run_subprocess_refresh(
            "scripts/process_investment_data.py",
            load_and_preprocess_data.clear,
            "Fetching latest prices and fundamentals...",
        )

# ----------------- DATA LOADING ----------------- #
data = load_and_preprocess_data()
stocks_complete = data["stocks_complete"].copy()
daily_stocks = data["daily_stocks"].copy()
daily_equity = data.get("daily_equity", pd.DataFrame())
stock_info = data.get("stock_info", pd.DataFrame())

# Freshness badges
if not stock_info.empty and "last_updated" in stock_info.columns:
    render_freshness_badge(pd.to_datetime(stock_info["last_updated"]).max(), label="Fundamentals last updated")
if not daily_stocks.empty and "date" in daily_stocks.columns:
    render_freshness_badge(pd.to_datetime(daily_stocks["date"], errors="coerce").max(), label="Price history through")

# ----------------- DATA CLEANING ----------------- #
# The data loader converts columns to snake_case (e.g., Market_Value -> market_value)

# 1. Market Value
if "market_value" in stocks_complete.columns:
    stocks_complete["market_value"] = pd.to_numeric(stocks_complete["market_value"], errors="coerce").fillna(0)
else:
    stocks_complete["market_value"] = 0.0

# 2. True Cost Basis from daily_stocks (replayed transaction history)
# daily_stocks.equity = total dollars deployed per ticker, adjusted for all buys and partial sells.
# This is more accurate than quantity * avg_cost, which drifts when shares are sold.
if not daily_stocks.empty and {"stock", "equity", "date"}.issubset(daily_stocks.columns):
    daily_stocks["date"] = pd.to_datetime(daily_stocks["date"], errors="coerce")
    latest_date = daily_stocks["date"].max()
    cost_basis = (
        daily_stocks[daily_stocks["date"] == latest_date]
        .groupby("stock")["equity"]
        .sum()
        .reset_index()
        .rename(columns={"equity": "true_cost_basis"})
    )
    stocks_complete = pd.merge(stocks_complete, cost_basis, on="stock", how="left")
    stocks_complete["invested"] = pd.to_numeric(stocks_complete["true_cost_basis"], errors="coerce").fillna(0)
else:
    # Fallback: quantity * avg_cost if daily history is unavailable
    if "quantity" in stocks_complete.columns and "avg_cost" in stocks_complete.columns:
        stocks_complete["invested"] = (
            pd.to_numeric(stocks_complete["quantity"], errors="coerce").fillna(0) *
            pd.to_numeric(stocks_complete["avg_cost"], errors="coerce").fillna(0)
        )
    else:
        stocks_complete["invested"] = 0.0

# 3. Equity Change (Profit/Loss) = current market value minus true cost basis
stocks_complete["equity_change"] = stocks_complete["market_value"] - stocks_complete["invested"]

# ----------------- SECTION 1: SUMMARY METRICS (2x3 GRID) ----------------- #
st.subheader("At a Glance")

# Calculations
total_value = stocks_complete["market_value"].sum()
total_invested = stocks_complete["invested"].sum()
roe_dollar = total_value - total_invested
roe_percent = (roe_dollar / total_invested * 100) if total_invested > 0 else 0.0

# Count active positions (quantity > 0)
if "quantity" in stocks_complete.columns:
    num_companies = len(stocks_complete[stocks_complete["quantity"] > 0])
else:
    num_companies = 0

# Avg Dividend Yield (handle missing data)
if "dividend_yield" in stocks_complete.columns:
    avg_div_yield = stocks_complete["dividend_yield"].mean() * 100  # Convert dec to %
else:
    avg_div_yield = 0.0

# Row 1
r1c1, r1c2, r1c3 = st.columns(3)
r1c1.metric("Total Portfolio Value", f"${total_value:,.2f}")
r1c2.metric("Amount Invested", f"${total_invested:,.2f}")
r1c3.metric("Return on Equity ($)", f"${roe_dollar:,.2f}", delta=f"${roe_dollar:,.2f}")

# Row 2
r2c1, r2c2, r2c3 = st.columns(3)
r2c1.metric("Rate of Return (%)", f"{roe_percent:.2f}%", delta=f"{roe_percent:.2f}%")
r2c2.metric("Number of Companies", f"{num_companies}")
r2c3.metric("Avg Dividend Yield", f"{avg_div_yield:.2f}%")

st.markdown("---")

# ----------------- SECTION 2: PORTFOLIO TREND (ALTAIR) ----------------- #
st.subheader("📉 Portfolio Trend Over Time")

if not daily_equity.empty and {"date", "market_value", "total_profit"}.issubset(daily_equity.columns):
    chart_df = daily_equity.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.sort_values("date")

    # Altair chart
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
            .properties(height=350)
    )

    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No portfolio history available yet.")

st.markdown("---")

# ----------------- SECTION 3: ASSET ALLOCATION (BAR GRAPH) ----------------- #
st.subheader("🏆 Top Assets (Market Value vs. Return)")

if not stocks_complete.empty:
    # Sort by Market Value
    asset_chart_data = stocks_complete.sort_values("market_value", ascending=False).head(20)  # Top 20

    # Calculate Percent Return for color scale
    asset_chart_data["return_pct"] = asset_chart_data.apply(
        lambda x: ((x["market_value"] - x["invested"]) / x["invested"] * 100) if x["invested"] > 0 else 0,
        axis=1
    )

    fig_assets = px.bar(
        asset_chart_data,
        x="stock",
        y="market_value",
        color="return_pct",
        color_continuous_scale="RdYlGn",  # Red to Green
        range_color=[-50, 50],  # Cap color scale at +/- 50% for visibility
        title="Top Holdings by Value (Colored by % Return)",
        labels={"market_value": "Current Value ($)", "return_pct": "Return %", "stock": "Ticker"},
        hover_data={"invested": ":$,.2f", "market_value": ":$,.2f", "return_pct": ":.2f%"}
    )

    fig_assets.update_layout(xaxis_title=None)
    st.plotly_chart(fig_assets, use_container_width=True)

st.markdown("---")

# ----------------- SECTION 4: GAINERS / LOSERS (DYNAMIC TIME) ----------------- #
st.subheader("🔥 Movers & Shakers")

# Date Range Selector
time_frame = st.radio(
    "Calculate Performance Over:",
    ["1 Day", "1 Week", "1 Month", "3 Months", "1 Year", "YTD"],
    horizontal=True
)


# Helper to calculate performance dataframe
def get_performance_df(daily_df, days_lookback=None, is_ytd=False):
    if daily_df.empty:
        return pd.DataFrame()

    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df = daily_df.sort_values("date")

    max_date = daily_df["date"].max()

    if is_ytd:
        start_date = date(max_date.year, 1, 1)
    else:
        start_date = max_date - timedelta(days=days_lookback)

    # Get Prices at End Date
    end_prices = daily_df[daily_df["date"] == max_date][["stock", "close"]].rename(columns={"close": "End_Price"})

    # Get Prices nearest to Start Date (without going future)
    history_subset = daily_df[daily_df["date"] <= pd.Timestamp(start_date)]
    if history_subset.empty:
        history_subset = daily_df.copy()

    latest_dates = history_subset.groupby("stock")["date"].max().reset_index()
    start_prices_raw = pd.merge(daily_df, latest_dates, on=["stock", "date"])
    start_prices = start_prices_raw[["stock", "close"]].rename(columns={"close": "Start_Price"})

    # Merge
    perf_df = pd.merge(end_prices, start_prices, on="stock", how="inner")

    # Calc Change
    perf_df["Abs_Change"] = perf_df["End_Price"] - perf_df["Start_Price"]
    perf_df["Pct_Change"] = (perf_df["Abs_Change"] / perf_df["Start_Price"]) * 100

    return perf_df


# Logic for Lookback
lookback_map = {
    "1 Day": 1,
    "1 Week": 7,
    "1 Month": 30,
    "3 Months": 90,
    "1 Year": 365
}

if "daily_stocks" in data and not daily_stocks.empty:
    if time_frame == "YTD":
        perf_df = get_performance_df(daily_stocks, is_ytd=True)
    else:
        perf_df = get_performance_df(daily_stocks, days_lookback=lookback_map[time_frame])

    if not perf_df.empty:
        col_g, col_l = st.columns(2)

        with col_g:
            st.write(f"**Top Gainers ({time_frame})**")
            gainers = perf_df.sort_values("Pct_Change", ascending=False).head(10)
            st.dataframe(
                gainers[["stock", "Start_Price", "End_Price", "Pct_Change"]]
                    .style.format({
                    "Start_Price": "${:,.2f}",
                    "End_Price": "${:,.2f}",
                    "Pct_Change": "{:+.2f}%"
                })
                    .background_gradient(subset=["Pct_Change"], cmap="Greens"),
                use_container_width=True,
                hide_index=True
            )

        with col_l:
            st.write(f"**Top Losers ({time_frame})**")
            losers = perf_df.sort_values("Pct_Change", ascending=True).head(10)
            st.dataframe(
                losers[["stock", "Start_Price", "End_Price", "Pct_Change"]]
                    .style.format({
                    "Start_Price": "${:,.2f}",
                    "End_Price": "${:,.2f}",
                    "Pct_Change": "{:+.2f}%"
                })
                    .background_gradient(subset=["Pct_Change"], cmap="Reds_r"),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning("Not enough historical data to calculate performance for this period.")
else:
    st.info("No daily stock history available (daily_stocks.csv). Run the investment data processor.")