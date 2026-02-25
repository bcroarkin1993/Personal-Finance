# pages/Peer_Analysis.py

import sys
import subprocess
import pandas as pd
import altair as alt
import streamlit as st

from scripts.data_processing import load_and_preprocess_data, clear_all_caches
from scripts.navigation import make_sidebar
from scripts.utils import render_freshness_badge, render_refresh_status, run_subprocess_refresh

st.set_page_config(page_title="Stock Peer Analysis", page_icon="📊", layout="wide")
make_sidebar("Stock Peer Analysis")

# ---------- PAGE HEADER ---------- #

col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("📊 Stock Peer Analysis")
with col_refresh:
    st.markdown("<div style='padding-top:12px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        run_subprocess_refresh(
            "scripts/process_investment_data.py",
            clear_all_caches,
            "Fetching latest prices...",
        )

render_refresh_status()

st.write(
    "Compare your holdings against each other over different time horizons. "
    "Prices are normalized so they all start at 1, making relative performance easy to see."
)

# ---------- LOAD DATA ---------- #

data = load_and_preprocess_data()
daily_stocks: pd.DataFrame = data["daily_stocks"]
stocks_df: pd.DataFrame = data["stocks"]

# Freshness badge — based on most recent date in daily price history
if not daily_stocks.empty and "date" in daily_stocks.columns:
    max_price_date = pd.to_datetime(daily_stocks["date"], errors="coerce").max()
    render_freshness_badge(max_price_date, label="Price history through")

st.divider()

# Ensure types
if "date" not in daily_stocks.columns or "stock" not in daily_stocks.columns:
    st.error("`daily_stocks` is missing required columns (`date`, `stock`).")
    st.stop()

daily_stocks = daily_stocks.copy()
daily_stocks["date"] = pd.to_datetime(daily_stocks["date"], errors="coerce")

# ---------- UNIVERSE & DEFAULTS ---------- #

# All tickers that appear in your daily price history
universe_tickers = sorted(daily_stocks["stock"].dropna().astype(str).unique().tolist())

# Default: top 7 holdings by market value (if available)
default_tickers = []
if {"stock", "market_value"}.issubset(stocks_df.columns):
    default_tickers = (
        stocks_df.sort_values("market_value", ascending=False)["stock"]
        .dropna()
        .astype(str)
        .head(7)
        .tolist()
    )

if not default_tickers:
    # Fallback: first few tickers in universe
    default_tickers = universe_tickers[:7]

# ---------- LAYOUT: CONTROLS + MAIN CHART ---------- #

cols = st.columns([1, 3])
left_col = cols[0]
right_col = cols[1]

with left_col:
    st.subheader("Controls")

    # Ticker selection
    selected_tickers = st.multiselect(
        "Stock tickers (from your portfolio history)",
        options=universe_tickers,
        default=default_tickers,
        placeholder="Choose stocks to compare",
    )

    # Time horizon selector (in months)
    horizon_map = {
        "1 Month": 1,
        "3 Months": 3,
        "6 Months": 6,
        "1 Year": 12,
        "5 Years": 60,
    }
    horizon_label = st.radio(
        "Time horizon",
        options=list(horizon_map.keys()),
        index=2,  # default to "6 Months"
    )

# If nothing selected, stop early
if not selected_tickers:
    left_col.info("Pick some stocks from your portfolio to compare.", icon="ℹ️")
    st.stop()

# ---------- FILTER & PIVOT PRICE DATA ---------- #

horizon_months = horizon_map[horizon_label]
max_date = daily_stocks["date"].max()
if pd.isna(max_date):
    st.error("No valid dates found in `daily_stocks`.")
    st.stop()

start_date = max_date - pd.DateOffset(months=horizon_months)

# Filter by horizon and selected tickers
mask = (daily_stocks["date"] >= start_date) & daily_stocks["stock"].isin(selected_tickers)
filtered = daily_stocks.loc[mask, ["date", "stock", "close"]].copy()

if filtered.empty:
    st.warning("No price data available for the selected tickers and time horizon.")
    st.stop()

# Pivot to wide: index=date, columns=stock, values=close
price_matrix = (
    filtered.pivot_table(index="date", columns="stock", values="close")
    .sort_index()
)

# Drop tickers with no data at all
price_matrix = price_matrix.dropna(axis=1, how="all")

if price_matrix.empty:
    st.error("No usable price data after filtering. Check your inputs.")
    st.stop()

# Keep only selected tickers that have data
tickers = [t for t in selected_tickers if t in price_matrix.columns]

if not tickers:
    st.error("Selected tickers do not have price data in the chosen horizon.")
    st.stop()

price_matrix = price_matrix[tickers]

# ---------- NORMALIZE PRICES ---------- #

# Normalize each series so first valid price = 1
normalized = pd.DataFrame(index=price_matrix.index)

for t in tickers:
    s = price_matrix[t].dropna()
    if s.empty:
        normalized[t] = pd.Series(index=price_matrix.index, data=pd.NA)
    else:
        norm_series = s / s.iloc[0]
        normalized[t] = norm_series.reindex(price_matrix.index)

# Remove columns that are completely NA after normalization
normalized = normalized.dropna(axis=1, how="all")
tickers = [t for t in tickers if t in normalized.columns]

if not tickers:
    st.error("No normalized series available for the selected tickers.")
    st.stop()

# ---------- BEST / WORST METRICS ---------- #

latest_norm_values = {t: normalized[t].dropna().iat[-1] for t in tickers if not normalized[t].dropna().empty}

if not latest_norm_values:
    st.error("Could not compute latest normalized values.")
    st.stop()

best_ticker = max(latest_norm_values, key=latest_norm_values.get)
worst_ticker = min(latest_norm_values, key=latest_norm_values.get)

best_value = latest_norm_values[best_ticker]
worst_value = latest_norm_values[worst_ticker]

with left_col:
    st.subheader("Peer Highlights")
    m1, m2 = st.columns(2)
    with m1:
        st.metric(
            "Best stock",
            best_ticker,
            delta=f"{(best_value - 1) * 100:,.0f}%",
        )
    with m2:
        st.metric(
            "Worst stock",
            worst_ticker,
            delta=f"{(worst_value - 1) * 100:,.0f}%",
        )

# ---------- MAIN NORMALIZED PRICE CHART ---------- #

with right_col:
    st.subheader("Normalized Price Performance")

    norm_long = (
        normalized.reset_index()
        .rename(columns={"date": "Date"})
        .melt(id_vars=["Date"], var_name="Stock", value_name="NormalizedPrice")
    )

    base_chart = (
        alt.Chart(norm_long)
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(format="%b %y", title="Date")),
            y=alt.Y("NormalizedPrice:Q", title="Normalized Price").scale(zero=False),
            color=alt.Color("Stock:N", legend=alt.Legend(title="Stock")),
            tooltip=[
                alt.Tooltip("Date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("Stock:N", title="Stock"),
                alt.Tooltip("NormalizedPrice:Q", title="Normalized Price", format=".2f"),
            ],
        )
        .properties(height=400)
    )

    st.altair_chart(base_chart, use_container_width=True)

st.markdown("---")

# ---------- INDIVIDUAL STOCK VS PEER AVERAGE ---------- #

st.subheader("Individual Stocks vs Peer Average")

if len(tickers) <= 1:
    st.info("Pick 2 or more tickers above to see peer comparisons.", icon="ℹ️")
    st.stop()

NUM_COLS = 4
grid_cols = st.columns(NUM_COLS)

for i, ticker in enumerate(tickers):
    # Calculate peer average (excluding current stock)
    peers = normalized.drop(columns=[ticker])
    peer_avg = peers.mean(axis=1)

    # Data for normalized vs peer average chart
    plot_data = pd.DataFrame(
        {
            "Date": normalized.index,
            ticker: normalized[ticker],
            "Peer average": peer_avg,
        }
    ).melt(id_vars=["Date"], var_name="Series", value_name="Price")

    line_chart = (
        alt.Chart(plot_data)
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(format="%b %y", title="Date")),
            y=alt.Y("Price:Q", title="Normalized Price").scale(zero=False),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(domain=[ticker, "Peer average"], range=["red", "gray"]),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("Series:N", title="Series"),
                alt.Tooltip("Price:Q", title="Normalized Price", format=".2f"),
            ],
        )
        .properties(title=f"{ticker} vs peer average", height=260)
    )

    cell = grid_cols[(i * 2) % NUM_COLS].container(border=True)
    cell.altair_chart(line_chart, use_container_width=True)

    # Delta chart: stock - peer average
    delta_data = pd.DataFrame(
        {
            "Date": normalized.index,
            "Delta": normalized[ticker] - peer_avg,
        }
    )

    delta_chart = (
        alt.Chart(delta_data)
        .mark_area(opacity=0.6)
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(format="%b %y", title="Date")),
            y=alt.Y("Delta:Q", title="Δ vs Peer Avg").scale(zero=False),
            tooltip=[
                alt.Tooltip("Date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("Delta:Q", title="Delta", format=".2f"),
            ],
        )
        .properties(title=f"{ticker} minus peer average", height=260)
    )

    cell_delta = grid_cols[(i * 2 + 1) % NUM_COLS].container(border=True)
    cell_delta.altair_chart(delta_chart, use_container_width=True)

st.markdown("---")
st.caption("Prices are based on your stored daily close data and normalized to start at 1 for the selected period.")
