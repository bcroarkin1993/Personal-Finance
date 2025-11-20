import streamlit as st
import plotly.express as px
from ..scripts.data_processing import load_and_preprocess_data

### FORMAT STREAMLIT PAGE ###
st.set_page_config(layout="wide")
st.title("Buying Opportunities")

### PULL IN & FORMAT DATA ###
# Load preprocessed data
data = load_and_preprocess_data()

# Access dataframes
buying_opportunities = data["buying_opportunities"]
rebuying_opportunities = data["rebuying_opportunities"]

### STREAMLIT LAYOUT ###
st.subheader("Overview")
st.write("""
This page highlights the best opportunities for:
- **New Buys**: Stocks you currently don't own but show strong potential based on various metrics.
- **Re-Buys**: Stocks you already own but present an opportunity for additional investment based on their performance.
""")

# Create two tabs for buying and re-buying opportunities
tab1, tab2 = st.tabs(["🔍 New Buying Opportunities", "🔄 Re-Buying Opportunities"])

### TAB 1: New Buying Opportunities ###
with tab1:
    st.subheader("🔍 New Buying Opportunities")
    st.write("""
    These are stocks you currently don't own but are flagged as potential buying opportunities based on their performance and market data.
    """)
    st.dataframe(buying_opportunities)

    # Example visualization: Daily percent change distribution
    if not buying_opportunities.empty:
        fig = px.bar(
            buying_opportunities.nlargest(10, "Daily_Pct_Change"),
            x="Company",
            y="Daily_Pct_Change",
            title="Top 10 New Buys by Daily Percent Change",
            labels={"Daily_Pct_Change": "Daily % Change"},
            text="Daily_Pct_Change",
        )
        fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No buying opportunities available.")

### TAB 2: Re-Buying Opportunities ###
with tab2:
    st.subheader("🔄 Re-Buying Opportunities")
    st.write("""
    These are stocks you already own but are identified as opportunities for additional investment based on their market trends, sector allocation, and scores.
    """)
    st.dataframe(rebuying_opportunities)

    # Example visualization: Top Re-Buy Scores
    if not rebuying_opportunities.empty:
        fig = px.bar(
            rebuying_opportunities.nlargest(10, "Buy_Score"),
            x="Stock",
            y="Buy_Score",
            title="Top 10 Re-Buy Opportunities by Buy Score",
            labels={"Buy_Score": "Buy Score"},
            text="Buy_Score",
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No re-buying opportunities available.")

### FOOTER ###
st.markdown("---")
st.caption("Data powered by your investment strategy. Charts and tables generated using preprocessed datasets.")
