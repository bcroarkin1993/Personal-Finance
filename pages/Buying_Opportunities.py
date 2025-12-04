import streamlit as st
import plotly.express as px
from scripts.data_processing import load_and_preprocess_data

st.set_page_config(layout="wide")

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

# ----------------- TAB 1: RE-BUY ----------------- #
with tab1:
    if rebuy_df is not None and not rebuy_df.empty:

        # Top 3 Cards
        top_picks = rebuy_df.head(3)
        cols = st.columns(3)
        for i, (index, row) in enumerate(top_picks.iterrows()):
            with cols[i]:
                st.metric(
                    label=f"🥇 #{i + 1}: {row['stock']}",
                    value=f"{row['buy_score']:.0f}/100",
                    delta=f"{row['discount_pct'] * 100:.1f}% Discount"
                )

        # Visualization
        fig = px.bar(
            rebuy_df.head(10),
            x="stock",
            y="buy_score",
            color="buy_score",
            color_continuous_scale="RdYlGn",
            title="Top 10 Re-Buy Scores",
            labels={"buy_score": "Composite Score"},
            text_auto='.0f'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed Table
        st.subheader("Detailed Scoring Breakdown")
        display_cols = ["stock", "price", "52_week_high", "discount_pct", "portfolio_diversity", "buy_score"]
        # Filter for cols that actually exist
        valid_cols = [c for c in display_cols if c in rebuy_df.columns]

        st.dataframe(
            rebuy_df[valid_cols].style.background_gradient(subset=["buy_score"], cmap="RdYlGn"),
            use_container_width=True
        )
    else:
        st.info("No re-buying opportunities data available. Check your process_investment_data script.")

# ----------------- TAB 2: NEW BUY ----------------- #
with tab2:
    if new_buy_df is not None and not new_buy_df.empty:
        st.dataframe(new_buy_df)
    else:
        st.warning(
            """
            **No New Buy data found.** *To enable this:*
            1. Create a 'watchlist.csv' or add non-owned stocks to 'stock_dictionary.json'.
            2. Ensure your 'stock_info.csv' contains live price data for these stocks.
            """
        )