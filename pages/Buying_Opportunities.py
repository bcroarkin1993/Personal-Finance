import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.data_processing import load_and_preprocess_data
# IMPORT NAVIGATION
from scripts.navigation import make_sidebar

st.set_page_config(layout="wide", page_title="Buying Opportunities", page_icon="💰")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Buying Opportunities")

# ----------------- HEADER ----------------- #
st.title("💰 Buying Opportunities")
st.markdown("""
<div style='background-color: #1e2530; padding: 15px; border-radius: 10px; border-left: 5px solid #2ecc71;'>
    This engine scores stocks from <b>0-100</b> based on value (discount to 52w high), 
    analyst targets, risk profile, and market sentiment (VIX).
</div>
""", unsafe_allow_html=True)

# ----------------- LOAD DATA ----------------- #
data = load_and_preprocess_data()
rebuy_df = data.get("rebuying_opportunities", None)
new_buy_df = data.get("buying_opportunities", None)

tab1, tab2 = st.tabs(["🔄 Re-Buy (Current Portfolio)", "🔍 New Opportunities (Watchlist)"])


# ----------------- HELPER: CLEAN COLUMNS ----------------- #
def clean_columns_for_display(df):
    """Renames snake_case columns to Title Case for better presentation."""
    rename_map = {
        "stock": "Ticker",
        "price": "Price",
        "52_week_high": "52 Week High",
        "discount_pct": "Discount %",
        "portfolio_diversity": "Portfolio %",
        "buy_score": "Buy Score",
        "target_mean_price": "Target Price",
        "avg_risk": "Risk Score",
        "company": "Company"
    }
    # Only rename columns that exist
    valid_map = {k: v for k, v in rename_map.items() if k in df.columns}
    return df.rename(columns=valid_map)


# ----------------- TAB 1: RE-BUY ----------------- #
with tab1:
    if rebuy_df is not None and not rebuy_df.empty:

        # Top 3 Cards
        top_picks = rebuy_df.head(3)
        cols = st.columns(3)
        for i, (index, row) in enumerate(top_picks.iterrows()):
            discount = row.get('discount_pct', 0)
            score = row.get('buy_score', 0)
            ticker = row.get('stock', 'N/A')

            with cols[i]:
                st.metric(
                    label=f"🥇 #{i + 1}: {ticker}",
                    value=f"{score:.0f}/100",
                    delta=f"{discount * 100:.1f}% Discount"
                )

        # Visualization
        fig = px.bar(
            rebuy_df.head(10),
            x="stock",
            y="buy_score",
            color="buy_score",
            color_continuous_scale="RdYlGn",
            title="Top 10 Re-Buy Scores",
            labels={"buy_score": "Composite Score", "stock": "Ticker"},
            text_auto='.0f'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed Table
        st.subheader("Detailed Scoring Breakdown")

        # Select specific columns of interest before renaming
        cols_of_interest = ["stock", "price", "52_week_high", "discount_pct", "portfolio_diversity", "buy_score"]
        valid_cols = [c for c in cols_of_interest if c in rebuy_df.columns]

        display_df = rebuy_df[valid_cols].copy()

        # Rename for display
        display_df = clean_columns_for_display(display_df)

        # Apply formatting
        st.dataframe(
            display_df.style.format({
                "Price": "${:,.2f}",
                "52 Week High": "${:,.2f}",
                "Discount %": "{:.1%}",
                "Portfolio %": "{:.1f}%",
                "Buy Score": "{:.0f}"
            }).background_gradient(subset=["Buy Score"], cmap="RdYlGn"),
            use_container_width=True
        )
    else:
        st.info("No re-buying opportunities data available. Check your process_investment_data script.")

# ----------------- TAB 2: NEW BUY ----------------- #
with tab2:
    if new_buy_df is not None and not new_buy_df.empty:
        st.subheader("Watchlist Opportunities")

        # Rename for display
        display_new = clean_columns_for_display(new_buy_df.copy())

        # Identify columns to format if they exist after renaming
        format_dict = {}
        if "Price" in display_new.columns: format_dict["Price"] = "${:,.2f}"
        if "Target Price" in display_new.columns: format_dict["Target Price"] = "${:,.2f}"
        if "Buy Score" in display_new.columns: format_dict["Buy Score"] = "{:.0f}"

        st.dataframe(
            display_new.style.format(format_dict)
                .background_gradient(subset=["Buy Score"],
                                     cmap="RdYlGn") if "Buy Score" in display_new.columns else display_new,
            use_container_width=True
        )
    else:
        st.warning(
            """
            **No New Buy data found.** *To enable this:*
            1. Add non-owned stocks to 'stock_dictionary.json'.
            2. Ensure your 'stock_info.csv' contains live price data for these stocks.
            """
        )