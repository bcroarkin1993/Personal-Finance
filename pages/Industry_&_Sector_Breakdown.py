import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Industry & Sector Breakdown", page_icon="🧭", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Industry & Sector Breakdown")

# ----------------- HEADER ----------------- #
st.title("🧭 Industry & Sector Breakdown")
st.caption(f"Data as of {date.today().strftime('%B %d, %Y')}")

# ----------------- DATA LOADING ----------------- #
data = load_and_preprocess_data()

# Extract DataFrames
# Note: These come from data_processing.py which converts columns to snake_case
todays_stocks_complete = data.get("todays_stocks_complete", pd.DataFrame()).copy()
sector_values = data.get("sector_values", pd.DataFrame()).copy()
industry_values = data.get("industry_values", pd.DataFrame()).copy()

# Ensure numeric types for plotting
if not todays_stocks_complete.empty:
    todays_stocks_complete["market_value"] = pd.to_numeric(todays_stocks_complete["market_value"],
                                                           errors="coerce").fillna(0)

if not sector_values.empty:
    sector_values["market_value"] = pd.to_numeric(sector_values["market_value"], errors="coerce").fillna(0)

if not industry_values.empty:
    industry_values["market_value"] = pd.to_numeric(industry_values["market_value"], errors="coerce").fillna(0)

# ----------------- VISUALIZATION SECTION ----------------- #

if not todays_stocks_complete.empty:

    # --- ROW 1: PIE CHARTS ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sector Allocation")
        if not sector_values.empty:
            fig1 = px.pie(
                sector_values,
                values='market_value',
                names='sector',
                hole=0.4
            )
            fig1.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Market Value: $%{value:,.0f}'
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No sector data available.")

    with col2:
        st.subheader("Industry Allocation")
        if not industry_values.empty:
            # Group smaller industries into "Other" for cleaner pie chart if too many
            if len(industry_values) > 15:
                disp_industry = industry_values.head(14).copy()
                other_val = industry_values.iloc[14:]["market_value"].sum()
                # Create a DataFrame for "Other"
                other_row = pd.DataFrame([{"industry": "Other", "market_value": other_val}])
                disp_industry = pd.concat([disp_industry, other_row], ignore_index=True)
            else:
                disp_industry = industry_values

            fig2 = px.pie(
                disp_industry,
                values='market_value',
                names='industry',
                hole=0.4
            )
            fig2.update_traces(
                textposition='inside',
                textinfo='percent',  # Label often too long for industry
                hovertemplate='<b>%{label}</b><br>Market Value: $%{value:,.0f}'
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No industry data available.")

    st.markdown("---")

    # --- ROW 2: TREEMAP ---
    st.subheader("Interactive Hierarchy")

    # Toggle
    view_mode = st.radio("Group By:", ["Sector -> Stock", "Industry -> Stock"], horizontal=True)

    if view_mode == "Industry -> Stock":
        path = ['industry', 'stock']
        title = "Portfolio by Industry"
    else:
        path = ['sector', 'stock']
        title = "Portfolio by Sector"

    # Treemap
    # Note: Treemaps handle NaNs poorly in path, fill them
    todays_stocks_complete["sector"] = todays_stocks_complete["sector"].fillna("Unknown")
    todays_stocks_complete["industry"] = todays_stocks_complete["industry"].fillna("Unknown")
    todays_stocks_complete["stock"] = todays_stocks_complete["stock"].fillna("Unknown")

    fig_tree = px.treemap(
        todays_stocks_complete,
        path=path,
        values='market_value',
        color='market_value',  # Optional: color by value or another metric like % change
        color_continuous_scale='Blues'
    )

    fig_tree.update_traces(
        hovertemplate='<b>%{label}</b><br>Market Value: $%{value:,.0f}<br>Share: %{percentParent:.1%}'
    )
    fig_tree.update_layout(margin=dict(t=20, l=0, r=0, b=0))

    st.plotly_chart(fig_tree, use_container_width=True)

else:
    st.warning("No stock data found. Please run the investment data processor.")