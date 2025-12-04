import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

### FORMAT STREAMLIT PAGE ###
st.set_page_config(layout="wide")
# Title
st.title("Investment Dashboard - Company Analysis")

# Pull in tables from session_state
stocks = st.session_state['stocks']
stocks_complete = st.session_state['stocks_complete']
stock_info = st.session_state['stock_info']
daily_equity = st.session_state['daily_equity']
todays_stocks = st.session_state['todays_stocks']
daily_stocks_complete = st.session_state['daily_stocks_complete']
cap_sizes = st.session_state['cap_sizes']

### CREATE AND DISPLAY VISUALS ###

# Create Company display option
companies = daily_stocks_complete['Company'].unique().tolist()
companies = [x for x in companies if x != '0']
comp = st.selectbox("Pick a Company", companies)

# Filter dataframe to single company for analysis
company_complete = daily_stocks_complete[daily_stocks_complete['Company'] == comp]

## Create company_info table
stock_info.rename(columns={'Company': 'Stock'}, inplace=True)
# Create a lookup table for Stock Tickers to Company Names
stock_names = stocks[['Stock', 'Company']]
# Add company name to stock_info
stock_info = pd.merge(stock_info, stock_names)
# Filter to single company that is being analyzed
company_info = stock_info[stock_info['Company'] == comp]

# Pull additional company info from stock_info dataframe
ticker = company_info['Stock'].values[0]
ceo = company_info['CEO'].values[0]
country = company_info['Country'].values[0]
state = company_info['State'].values[0]
city = company_info['City'].values[0]
market_cap = company_info['Market_Cap'].values[0]
dividend_yield = company_info['Dividend_Yield'].values[0]
shares_outstanding = company_info['Shares_Outstanding'].values[0]
volume = company_info['Avg_Volume'].values[0]
pe_ratio = company_info['PE_Ratio'].values[0]
pb_ratio = company_info['PB_Ratio'].values[0]
beta = company_info['Beta'].values[0]
sector = company_info['Sector'].values[0]
industry = company_info['Industry'].values[0]
description = company_info['Description'].values[0]

col1, col2, col3 = st.columns([1,1,3])

with col1:
    # Display information on the company
    st.header(f" ")
    st.markdown(f"**Ticker Symbol:** {ticker}")
    st.markdown(f"**CEO:** {ceo}")
    st.markdown(f"**Country:** {country}")
    st.markdown(f"**State:** {state}")
    st.markdown(f"**City:** {city}")
    st.markdown(f"**Sector:** {sector}")
    st.markdown(f"**Industry:** {industry}")
    st.markdown(f"**Dividend Yield:** {dividend_yield}")

with col2:
    # Display information on the company
    st.header(f" ")
    st.markdown(f"**Market Capitalization (Billions):** {market_cap}")
    st.markdown(f"**Average Volume (Millions):** {volume}")
    st.markdown(f"**Shares Outstanding:** {shares_outstanding}")
    st.markdown(f"**PE Ratio:** {pe_ratio}")
    st.markdown(f"**PB Ratio:** {pb_ratio}")
    st.markdown(f"**Beta:** {beta}")

with col3:
    # Plot the share price over time
    fig = px.line(company_complete, x='Date', y='Close', hover_name='Date')

    # Plot!
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"**Description:** {description}")




