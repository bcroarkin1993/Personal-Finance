import sys
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
from datetime import date, timedelta
from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar
from scripts.theme import (
    GREEN, RED,
    page_header, section_header, stat_card_grid, html_table, grad_divider,
)
from scripts.utils import render_freshness_badge, render_refresh_status

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Portfolio Overview", page_icon="📈", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Portfolio Overview")

page_header("Portfolio Overview", icon="📈",
            subtitle="Holdings value, cost basis, and performance over time")

render_refresh_status()

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

# 1. Market Value
if "market_value" in stocks_complete.columns:
    stocks_complete["market_value"] = pd.to_numeric(stocks_complete["market_value"], errors="coerce").fillna(0)
else:
    stocks_complete["market_value"] = 0.0

# 2. True Cost Basis from daily_stocks (replayed transaction history)
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
    if "quantity" in stocks_complete.columns and "avg_cost" in stocks_complete.columns:
        stocks_complete["invested"] = (
            pd.to_numeric(stocks_complete["quantity"], errors="coerce").fillna(0) *
            pd.to_numeric(stocks_complete["avg_cost"], errors="coerce").fillna(0)
        )
    else:
        stocks_complete["invested"] = 0.0

# 3. Equity Change (Profit/Loss)
stocks_complete["equity_change"] = stocks_complete["market_value"] - stocks_complete["invested"]

# ----------------- SECTION 1: SUMMARY METRICS (2×3 GRID) ----------------- #
st.html(section_header("At a Glance", icon="📊"))

# Calculations
total_value    = stocks_complete["market_value"].sum()
total_invested = stocks_complete["invested"].sum()
roe_dollar  = total_value - total_invested
roe_percent = (roe_dollar / total_invested * 100) if total_invested > 0 else 0.0

if "quantity" in stocks_complete.columns:
    num_companies = len(stocks_complete[stocks_complete["quantity"] > 0])
else:
    num_companies = 0

if "dividend_yield" in stocks_complete.columns:
    avg_div_yield = stocks_complete["dividend_yield"].mean() * 100
else:
    avg_div_yield = 0.0

st.html(stat_card_grid([
    {"label": "Total Portfolio Value", "value": f"${total_value:,.2f}",    "icon": "💼"},
    {"label": "Amount Invested",       "value": f"${total_invested:,.2f}", "icon": "💰"},
    {
        "label": "Return on Equity ($)",
        "value": f"${roe_dollar:,.2f}",
        "icon": "📈",
        "delta": f"${roe_dollar:,.2f}",
        "positive": roe_dollar >= 0,
    },
    {
        "label": "Rate of Return (%)",
        "value": f"{roe_percent:.2f}%",
        "icon": "📊",
        "delta": f"{roe_percent:.2f}%",
        "positive": roe_percent >= 0,
    },
    {"label": "Number of Companies", "value": f"{num_companies}",      "icon": "🏢"},
    {"label": "Avg Dividend Yield",  "value": f"{avg_div_yield:.2f}%", "icon": "💸"},
], cols=3))

# ----------------- SECTION 2: PORTFOLIO TREND (ALTAIR) ----------------- #
st.html(grad_divider())
st.html(section_header("Portfolio Trend Over Time", icon="📉"))

if not daily_equity.empty and {"date", "market_value", "total_profit"}.issubset(daily_equity.columns):
    chart_df = daily_equity.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.sort_values("date")

    chart = (
        alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
            x=alt.X("date:T", axis=alt.Axis(format="%b %y", title="Date")),
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
            .properties(height=350)
    )

    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No portfolio history available yet.")

# ----------------- SECTION 3: ASSET ALLOCATION (BAR GRAPH) ----------------- #
st.html(grad_divider())
st.html(section_header("Top Assets (Market Value vs. Return)", icon="🏆"))

if not stocks_complete.empty:
    asset_chart_data = stocks_complete.sort_values("market_value", ascending=False).head(20)

    asset_chart_data["return_pct"] = asset_chart_data.apply(
        lambda x: ((x["market_value"] - x["invested"]) / x["invested"] * 100) if x["invested"] > 0 else 0,
        axis=1
    )

    fig_assets = px.bar(
        asset_chart_data,
        x="stock",
        y="market_value",
        color="return_pct",
        color_continuous_scale="RdYlGn",
        range_color=[-50, 50],
        title="Top Holdings by Value (Colored by % Return)",
        labels={"market_value": "Current Value ($)", "return_pct": "Return %", "stock": "Ticker"},
        hover_data={"invested": ":$,.2f", "market_value": ":$,.2f", "return_pct": ":.2f%"}
    )

    fig_assets.update_layout(xaxis_title=None)
    st.plotly_chart(fig_assets, use_container_width=True)

# ----------------- SECTION 4: GAINERS / LOSERS (DYNAMIC TIME) ----------------- #
st.html(grad_divider())
st.html(section_header("Movers & Shakers", icon="🔥"))

time_frame = st.radio(
    "Calculate Performance Over:",
    ["1 Day", "1 Week", "1 Month", "3 Months", "1 Year", "YTD"],
    horizontal=True
)


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

    end_prices = daily_df[daily_df["date"] == max_date][["stock", "close"]].rename(columns={"close": "End_Price"})

    history_subset = daily_df[daily_df["date"] <= pd.Timestamp(start_date)]
    if history_subset.empty:
        history_subset = daily_df.copy()

    latest_dates = history_subset.groupby("stock")["date"].max().reset_index()
    start_prices_raw = pd.merge(daily_df, latest_dates, on=["stock", "date"])
    start_prices = start_prices_raw[["stock", "close"]].rename(columns={"close": "Start_Price"})

    perf_df = pd.merge(end_prices, start_prices, on="stock", how="inner")
    perf_df["Abs_Change"] = perf_df["End_Price"] - perf_df["Start_Price"]
    perf_df["Pct_Change"] = (perf_df["Abs_Change"] / perf_df["Start_Price"]) * 100

    return perf_df


lookback_map = {
    "1 Day": 1,
    "1 Week": 7,
    "1 Month": 30,
    "3 Months": 90,
    "1 Year": 365
}

_MOVER_COLS = {
    "stock":       "Ticker",
    "Start_Price": "Start Price",
    "End_Price":   "End Price",
    "Pct_Change":  "% Change",
}
_MOVER_FMT = {
    "Start Price": "${:,.2f}",
    "End Price":   "${:,.2f}",
    "% Change":    "{:+.2f}%",
}

if "daily_stocks" in data and not daily_stocks.empty:
    if time_frame == "YTD":
        perf_df = get_performance_df(daily_stocks, is_ytd=True)
    else:
        perf_df = get_performance_df(daily_stocks, days_lookback=lookback_map[time_frame])

    if not perf_df.empty:
        col_g, col_l = st.columns(2)

        with col_g:
            st.html(f"<div style='color:#333;font-weight:600;margin-bottom:6px;'>Top Gainers ({time_frame})</div>")
            gainers = perf_df.sort_values("Pct_Change", ascending=False).head(10)
            st.html(html_table(
                gainers,
                col_labels=_MOVER_COLS,
                formatters=_MOVER_FMT,
                pos_cols=["Pct_Change"],
                ticker_col="stock",
            ))

        with col_l:
            st.html(f"<div style='color:#333;font-weight:600;margin-bottom:6px;'>Top Losers ({time_frame})</div>")
            losers = perf_df.sort_values("Pct_Change", ascending=True).head(10)
            st.html(html_table(
                losers,
                col_labels=_MOVER_COLS,
                formatters=_MOVER_FMT,
                neg_cols=["Pct_Change"],
                ticker_col="stock",
            ))
    else:
        st.warning("Not enough historical data to calculate performance for this period.")
else:
    st.info("No daily stock history available (daily_stocks.csv). Run the investment data processor.")
