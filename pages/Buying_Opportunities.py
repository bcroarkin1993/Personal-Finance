import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from scripts.data_processing import (
    load_and_preprocess_data,
    load_market_context,
    calculate_buying_opportunity_scores,
    clear_all_caches,
)
from scripts.navigation import make_sidebar
from scripts.theme import BANNER_BG, GREEN, RED, YELLOW, page_header
from scripts.utils import render_refresh_status, run_subprocess_refresh

st.set_page_config(layout="wide", page_title="Buying Opportunities", page_icon="💰")
make_sidebar("Buying Opportunities")
render_refresh_status()

# ----------------- LOAD DATA ----------------- #
data = load_and_preprocess_data()
stocks_complete = data.get("stocks_complete", pd.DataFrame())
market_ctx = load_market_context()
stock_info = data.get("stock_info", pd.DataFrame())
stocks = data.get("stocks", pd.DataFrame())

# ----------------- DATA FRESHNESS BANNER ----------------- #
last_updated = "Unknown"
if not stock_info.empty and "last_updated" in stock_info.columns:
    try:
        last_updated = pd.to_datetime(stock_info["last_updated"]).max().strftime("%b %d, %Y")
    except Exception:
        pass

page_header("Buying Opportunities", icon="💰",
            subtitle="Data-driven scoring engine for re-buying and new positions")
_, col_refresh = st.columns([5, 1])
with col_refresh:
    if st.button("🔄 Refresh Data", use_container_width=True):
        run_subprocess_refresh(
            "scripts/process_investment_data.py",
            clear_all_caches,
            "Fetching latest prices and fundamentals...",
        )

freshness_color = RED if last_updated == "Unknown" else (
    YELLOW if pd.to_datetime(last_updated, errors="coerce") < pd.Timestamp.now() - pd.Timedelta(days=7)
    else GREEN
)
st.markdown(
    f"""
    <div style='background-color:{BANNER_BG}; padding:12px 16px; border-radius:10px;
                border-left:5px solid {freshness_color}; margin-bottom:12px;'>
        <b>Fundamentals last refreshed:</b> <span style='color:{freshness_color};'>{last_updated}</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        This engine scores stocks <b>0–100</b> using: discount to 52-week high, analyst target upside,
        portfolio diversity, governance risk, and market sentiment (VIX).
        &nbsp;&nbsp;<span style='opacity:0.6; font-size:0.85em;'>
        Prices stale &gt;7 days turn the indicator yellow; &gt;stale shown in red.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- MARKET CONTEXT STRIP ----------------- #
vix = market_ctx.get("vix", 20.0)
sp_perf = market_ctx.get("sp500_1mo_perf_pct", 0.0)
sentiment = market_ctx.get("market_sentiment_score", 0.5)

vix_color = RED if vix > 30 else (YELLOW if vix > 20 else GREEN)
sp_color = GREEN if sp_perf >= 0 else RED
sentiment_label = "Fearful (Buy Signal)" if sentiment > 0.6 else ("Neutral" if sentiment > 0.4 else "Greedy (Caution)")

mc1, mc2, mc3 = st.columns(3)
mc1.metric("VIX (Volatility)", f"{vix:.1f}", help="VIX > 30 = high fear = potential buying opportunity")
mc2.metric("S&P 500 (1 Month)", f"{sp_perf:+.1f}%", delta=f"{sp_perf:+.1f}%",
           help="S&P 500 return over the past month")
mc3.metric("Market Sentiment Score", f"{sentiment:.2f} / 1.00",
           help=f"Composite: {sentiment_label}. Higher = more fearful market = better buying conditions.")

st.divider()

# ----------------- CASH INPUT + WEIGHT CONTROLS ----------------- #
with st.expander("⚙️ Customize Scoring Weights", expanded=False):
    portfolio_cash = st.number_input(
        "💵 Available Cash to Deploy ($)",
        min_value=0, max_value=100_000, value=5_000, step=1_000,
        help="Higher available cash raises all buy scores — more capital = wider opportunity. Cap is $50,000.",
    )
    st.markdown("Adjust how much each signal contributes to the Buy Score. Weights are normalized automatically.")
    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        w_52wk = st.slider("📉 52-Week Discount", 0, 50, 20, 5,
                           help="How far below the 52-week high the stock is trading") / 100
        w_diversity = st.slider("📊 Portfolio Diversity", 0, 50, 5, 5,
                                help="Preference for stocks with lower current portfolio weight") / 100
    with wc2:
        w_target = st.slider("🎯 Analyst Target Upside", 0, 50, 15, 5,
                             help="Upside to analyst consensus price target") / 100
        w_risk = st.slider("🛡️ Governance Risk", 0, 50, 15, 5,
                           help="Lower governance risk scores rank higher") / 100
        w_pe = st.slider("💲 Industry PE", 0, 50, 15, 5,
                         help="Stocks trading below their industry median PE rank higher. "
                              "Negative/missing PE stocks are scored neutral (0.5).") / 100
    with wc3:
        w_sentiment = st.slider("🌡️ Market Sentiment", 0, 50, 10, 5,
                                help="VIX-based fear indicator — higher fear = better buying conditions") / 100
        w_cash = st.slider("💵 Cash Bonus", 0, 20, 5, 5,
                           help="Bonus for available cash to deploy (cap: $50,000)") / 100
        w_rsi = st.slider("📈 RSI (Oversold)", 0, 50, 15, 5,
                          help="14-day RSI: lower RSI = more oversold = higher score. "
                               "RSI 30 → 0.70, RSI 50 → 0.50, RSI 70 → 0.30.") / 100

    total_weight = w_52wk + w_diversity + w_target + w_risk + w_sentiment + w_cash + w_rsi + w_pe
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"Weights sum to {total_weight:.0%} — they will be normalized to 100% for scoring.")
    else:
        st.success("Weights sum to 100% ✓")

# Normalize weights so they always sum to 1
weight_sum = w_52wk + w_diversity + w_target + w_risk + w_sentiment + w_cash + w_rsi + w_pe
if weight_sum > 0:
    w_52wk, w_diversity, w_target, w_risk, w_sentiment, w_cash, w_rsi, w_pe = (
        w / weight_sum for w in (w_52wk, w_diversity, w_target, w_risk, w_sentiment, w_cash, w_rsi, w_pe)
    )

# ----------------- RE-SCORE WITH USER WEIGHTS ----------------- #
# Re-run scoring live using cached stock data + user-configured weights.
# This is fast (pure pandas) and avoids any extra yfinance calls.
mss = market_ctx.get("market_sentiment_score", 0.5)

rebuy_df = pd.DataFrame()
if not stocks_complete.empty and "price" in stocks_complete.columns:
    rebuy_df = calculate_buying_opportunity_scores(
        stocks_complete,
        portfolio_cash=portfolio_cash,
        market_sentiment_score=mss,
        w_52wk=w_52wk, w_target=w_target, w_rsi=w_rsi, w_pe=w_pe,
        w_risk=w_risk, w_sentiment=w_sentiment, w_diversity=w_diversity, w_cash=w_cash,
    )

new_buy_df = pd.DataFrame()
if (not stock_info.empty and not stocks.empty
        and "price" in stock_info.columns
        and "52_week_high" in stock_info.columns):
    owned = stocks["stock"].unique() if "stock" in stocks.columns else []
    watchlist = stock_info[~stock_info["stock"].isin(owned)].copy()
    if not watchlist.empty:
        new_buy_df = calculate_buying_opportunity_scores(
            watchlist,
            portfolio_cash=portfolio_cash,
            market_sentiment_score=mss,
            w_52wk=w_52wk, w_target=w_target, w_rsi=w_rsi, w_pe=w_pe,
            w_risk=w_risk, w_sentiment=w_sentiment, w_diversity=w_diversity, w_cash=w_cash,
        )

# ----------------- TABS ----------------- #
tab1, tab2 = st.tabs(["🔄 Re-Buy (Current Portfolio)", "🔍 New Opportunities (Watchlist)"])


def render_score_breakdown(df: pd.DataFrame):
    """Renders the detailed scoring breakdown table with all signal components."""
    score_cols = {
        "stock":          "Ticker",
        "company":        "Company",
        "price":          "Price",
        "52_week_high":   "52W High",
        "discount_pct":   "Discount %",
        "rsi_14":         "RSI (14d)",
        "target_mean_price": "Target Price",
        "score_52wk":     "52W Score",
        "score_target":   "Target Score",
        "score_rsi":      "RSI Score",
        "score_pe":       "PE Score",
        "score_diversity": "Diversity Score",
        "score_risk":     "Risk Score",
        "score_sentiment": "Sentiment Score",
        "buy_score":      "Buy Score",
    }
    valid = {k: v for k, v in score_cols.items() if k in df.columns}
    display = df[list(valid.keys())].rename(columns=valid).copy()

    fmt = {}
    if "Price" in display.columns:        fmt["Price"] = "${:,.2f}"
    if "52W High" in display.columns:     fmt["52W High"] = "${:,.2f}"
    if "Target Price" in display.columns: fmt["Target Price"] = "${:,.2f}"
    if "Discount %" in display.columns:   fmt["Discount %"] = "{:.1%}"
    if "RSI (14d)" in display.columns:    fmt["RSI (14d)"] = "{:.1f}"
    for score_col in ["52W Score", "Target Score", "RSI Score", "PE Score",
                      "Diversity Score", "Risk Score", "Sentiment Score"]:
        if score_col in display.columns:  fmt[score_col] = "{:.2f}"
    if "Buy Score" in display.columns:    fmt["Buy Score"] = "{:.1f}"

    styled = display.style.format(fmt)
    if "Buy Score" in display.columns:
        styled = styled.background_gradient(subset=["Buy Score"], cmap="RdYlGn", vmin=0, vmax=100)

    st.dataframe(styled, use_container_width=True, hide_index=True)


# ----------------- TAB 1: RE-BUY ----------------- #
with tab1:
    if rebuy_df is not None and not rebuy_df.empty:

        # Top 3 highlight cards
        top_picks = rebuy_df.head(3)
        card_cols = st.columns(3)
        for i, (_, row) in enumerate(top_picks.iterrows()):
            discount = row.get("discount_pct", 0)
            score = row.get("buy_score", 0)
            ticker = row.get("stock", "N/A")
            company = row.get("company", "")
            price = row.get("price", 0)
            target = row.get("target_mean_price", 0)
            upside_pct = ((target - price) / price * 100) if price > 0 else 0
            with card_cols[i]:
                st.metric(
                    label=f"#{i + 1}: {ticker}" + (f" — {company}" if company else ""),
                    value=f"{score:.0f} / 100",
                    delta=f"{discount * 100:.1f}% off 52W high",
                )
                if upside_pct > 0:
                    st.caption(f"Analyst target: ${target:,.2f} ({upside_pct:+.1f}% upside)")

        st.markdown("---")

        # Bar chart
        fig = px.bar(
            rebuy_df.head(15),
            x="stock", y="buy_score",
            color="buy_score",
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            title="Top 15 Re-Buy Scores (current weights)",
            labels={"buy_score": "Buy Score", "stock": "Ticker"},
            text_auto=".0f",
        )
        fig.update_layout(coloraxis_showscale=False, xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Full Scoring Breakdown")
        render_score_breakdown(rebuy_df)
    else:
        st.info(
            "No re-buying data available. Run a data refresh or check that "
            "`stocks.csv` and `stock_info.csv` both exist in `data/`."
        )

# ----------------- TAB 2: WATCHLIST ----------------- #
with tab2:
    if new_buy_df is not None and not new_buy_df.empty:
        st.subheader("New Opportunities (Watchlist)")
        render_score_breakdown(new_buy_df)
    else:
        st.warning(
            """
            **No watchlist data found.**

            To populate this tab:
            1. Add non-owned tickers to `data/stock_dictionary.json` with an empty `purchase_history`.
            2. Run a data refresh — `process_investment_data.py` will fetch prices for all tickers
               in the dictionary, including non-owned ones, and store them in `stock_info.csv`.
            """
        )
