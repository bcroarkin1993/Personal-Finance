import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

### FORMAT STREAMLIT PAGE ###
st.set_page_config(layout="wide")
# Title
st.title("Investment Dashboard - Industry")
# Today's Date
today = datetime.date.today()
st.subheader(f"Today's Date is {today}")

### PULL IN AND FORMAT DATA ###

# Pull in tables from session_state
todays_stocks_complete = st.session_state['todays_stocks_complete']
industry_values = st.session_state['industry_values']
sector_values = st.session_state['sector_values']

### CREATE DISPLAY INFORMATION

### PLOT CHARTS ###

## Pie Charts

col1, col2 = st.columns(2)

with col1:

    # Create and Sector Pie plot
    fig1 = px.pie(sector_values, values='Market_Value', names='Sector', title="Sector Breakdown")
    fig1.update_traces(textposition='inside', textinfo='percent',
                      hovertemplate='<b>Company</b> = %{label}<br><b>Market Value</b> = %{value:$.0f}')

    # Display Chart
    st.plotly_chart(fig1, use_container_width=True)

with col2:

    # Create and Industry Pie plot
    fig2 = px.pie(industry_values, values='Market_Value', names='Industry', title="Industry Breakdown")
    fig2.update_traces(textposition='inside', textinfo='percent',
                      hovertemplate='<b>Company</b> = %{label}<br><b>Market Value</b> = %{value:$.0f}')

    # Display Chart
    st.plotly_chart(fig2, use_container_width=True)

### Treemap

# Create display choice options
choice = st.radio("Pick one", ["Sector", "Industry"])

# Create and Display Sector/Industry Treemap plot
if choice == "Industry":
    fig3 = px.treemap(todays_stocks_complete, path=['Industry', 'Stock'], values='Market_Value')
    fig3.update_traces(
        hovertemplate='<b>Company</b> = %{label}<br><b>Parent</b> = %{parent}' +
                      '<br><b>Market Value</b> = %{value:$.0f}<br><b>Percent of Parent</b> = %{percentParent:.2%}')
    st.plotly_chart(fig3, use_container_width=True)
else:
    fig4 = px.treemap(todays_stocks_complete, path=['Sector', 'Stock'], values='Market_Value')
    fig4.update_traces(
        hovertemplate='<b>Company</b> = %{label}<br><b>Parent</b> = %{parent}' +
                      '<br><b>Market Value</b> = %{value:$.0f}<br><b>Percent of Parent</b> = %{percentParent:.2%}')
    st.plotly_chart(fig4, use_container_width=True)

