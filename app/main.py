import streamlit as st
import numpy as np
import pandas as pd
import datetime
import plotly.express as px

### FORMAT STREAMLIT PAGE ###
st.set_page_config(page_title="Investment Dashboard",
                   page_icon=":bar_chart:",
                   layout="wide")
# Title
st.title("Investment Dashboard - Summary")

### HELPER FUNCTIONS ###
def capSize(x):
    if x < 2:
        return('Small-Cap')
    elif x < 10:
        return('Mid-Cap')
    else:
        return('Large-Cap')

### IMPORT AND FORMAT DATA ###

## Import data
stocks = pd.read_csv('Data/stocks.csv')
stock_info = pd.read_csv('Data/stock_info.csv')
daily_stocks = pd.read_csv('Data/daily_stocks.csv')

## Format stocks
# Add in a column for portfolio diversity to stocks
stocks['Portfolio_Diversity'] = round(stocks['Market_Value'] * 100/ sum(stocks['Market_Value']),2)
# Add in column for the direction of the stock movement
stocks['Direction'] = np.where(stocks['Percent_Change'] > 0, 'Up', 'Down')

## Format stock_info
# Add in cap_size to stock_info (<$2B is small-cap, <$10B is mid-cap, >$10B is large-cap)
stock_info['CapSize'] = stock_info['Market_Cap'].apply(capSize)

## Format daily_stocks
# Add in Equity column
daily_stocks['Equity'] = daily_stocks['Shares_Held'] * daily_stocks['Avg_Cost']
# Add a Market Value column
daily_stocks['Market_Value'] = daily_stocks['Close'] * daily_stocks['Shares_Held']
# Add in Total Profit column
daily_stocks['Total_Profit'] = daily_stocks['Market_Value'] - daily_stocks['Equity']
# Add in Daily Profit column
daily_stocks['Daily_Profit'] = daily_stocks.groupby('Stock')['Total_Profit'].diff()
# Add a Per Share Profit column
daily_stocks['Per_Share_Profit'] = daily_stocks['Close'] - daily_stocks['Avg_Cost']
# Add in Daily Pct Profit column
daily_stocks['Daily_Pct_Profit'] = daily_stocks.groupby('Stock')['Close'].pct_change(1)
daily_stocks['Daily_Pct_Profit'] = round(daily_stocks['Daily_Pct_Profit'] * 100,2)
# Add Datetime column
daily_stocks['Datetime'] = pd.to_datetime(daily_stocks['Date'])
# Remove unnamed columns
daily_stocks = daily_stocks.loc[:, ~daily_stocks.columns.str.contains('^Unnamed')]

## Create a lookup table for Stock Tickers to Company Names
stock_names = stocks[['Stock', 'Company']]

## Merge stocks and stocks_info
stocks_complete = pd.merge(stocks, stock_info, how = 'left', left_on = 'Stock', right_on = 'Company')
# Create a column for invested amount
stocks_complete['Invested'] = stocks_complete['Quantity'] * stocks_complete['Avg_Cost']
# Remove unnamed columns
stocks_complete = stocks_complete.loc[:, ~stocks_complete.columns.str.contains('^Unnamed')]

## Merge daily_stocks and stock_names
daily_stocks_complete = pd.merge(daily_stocks, stock_names)

## Create a dataframe with daily total equity
daily_equity = daily_stocks_complete.groupby(by=["Date"])[["Market_Value", "Equity", "Total_Profit"]].sum()
daily_equity = daily_equity.reset_index()
# Set Date column as datetime
daily_equity['Date'] = pd.to_datetime(daily_equity['Date'])
# Create Daily_Profit column
daily_equity['Daily_Profit'] = daily_equity['Total_Profit'].diff()
# Format Daily_Profit columns
daily_equity['Daily_Profit'] = round(daily_equity['Daily_Profit'], 2)
# Remove unnamed columns
daily_equity = daily_equity.loc[:, ~daily_equity.columns.str.contains('^Unnamed')]

## Create Daily Gainers / Losers dataframes
most_recent_date = daily_stocks_complete['Datetime'].max()
todays_stocks = daily_stocks_complete[(daily_stocks_complete['Datetime'] == most_recent_date) &
                                      (daily_stocks_complete['Shares_Held'] != 0) &
                                      (daily_stocks_complete['Company'] != "0")].copy()
daily_gainers = todays_stocks[['Company', 'Daily_Profit', 'Daily_Pct_Profit']].reset_index(drop=True).sort_values("Daily_Profit", axis = 0, ascending = False).head(5)
daily_losers = todays_stocks[['Company', 'Daily_Profit', 'Daily_Pct_Profit']].reset_index(drop=True).sort_values("Daily_Profit", axis = 0, ascending = True).head(5)
# Remove any negatives from gainers and positives from losers
daily_gainers = daily_gainers[daily_gainers['Daily_Profit'] > 0]
daily_losers = daily_losers[daily_losers['Daily_Profit'] < 0]

## Create a lookup table for Stock Tickers to Sector/Industry
stock_sector_industry = stocks_complete[['Stock', 'Sector', 'Industry']]
# Merge industry/sector data into todays_stocks
todays_stocks_complete = pd.merge(todays_stocks, stock_sector_industry)

# Create a lookup table for Stock Tickers to Company Names
stock_caps = stock_info[['Company', 'CapSize']]
# Merge in cap size to todays_stocks
cap_sizes = pd.merge(todays_stocks, stock_caps, how = 'inner', left_on = 'Stock', right_on = 'Company')
# Format table
cap_sizes = cap_sizes[['Stock', 'Market_Value', 'CapSize']]

## Format dataframe values
daily_stocks_complete['Daily_Profit'] = daily_stocks_complete['Daily_Profit'].apply(lambda x: "${:,.2f}".format(x))
daily_stocks_complete['Daily_Pct_Profit'] = daily_stocks_complete['Daily_Pct_Profit'].apply(lambda x: "{:.2f}%".format(x))
daily_stocks_complete['Market_Value'] = daily_stocks_complete['Market_Value'].apply(lambda x: "${:,.2f}".format(x))
daily_stocks_complete['Total_Profit'] = daily_stocks_complete['Total_Profit'].apply(lambda x: "${:,.2f}".format(x))
daily_stocks_complete['Avg_Cost'] = daily_stocks_complete['Avg_Cost'].apply(lambda x: "${:,.2f}".format(x))
daily_stocks_complete['Equity'] = daily_stocks_complete['Equity'].apply(lambda x: "${:,.2f}".format(x))
daily_stocks_complete['Per_Share_Profit'] = daily_stocks_complete['Per_Share_Profit'].apply(lambda x: "${:,.2f}".format(x))
daily_gainers['Daily_Profit'] = daily_gainers['Daily_Profit'].apply(lambda x: "${:,.2f}".format(x))
daily_gainers['Daily_Pct_Profit'] = daily_gainers['Daily_Pct_Profit'].apply(lambda x: "{:.2f}%".format(x))
daily_losers['Daily_Profit'] = daily_losers['Daily_Profit'].apply(lambda x: "${:,.2f}".format(x))
daily_losers['Daily_Pct_Profit'] = daily_losers['Daily_Pct_Profit'].apply(lambda x: "{:.2f}%".format(x))

# Groupby Sector and sum values
sector_values = pd.DataFrame(todays_stocks_complete.groupby(['Sector'])['Market_Value'].sum())
# Add a column for percent of total
sector_values['Pct_of_Total'] = sector_values['Market_Value'] / sector_values['Market_Value'].sum()
# Add a column for desired percent of total (even split)
sector_values['Desired_Pct'] = 1 / len(sector_values)
# Add a column for deviation from total
sector_values['Pct_Deviation'] = sector_values['Desired_Pct'] - sector_values['Pct_of_Total']
# Reset the index to set Sector as a column
sector_values.reset_index(inplace=True)
# Sort values by Pct_Deviation
sector_values = sector_values.sort_values(by='Pct_Deviation')

# Groupby Industry and sum values
industry_values = pd.DataFrame(todays_stocks_complete.groupby(['Industry'])['Market_Value'].sum())
# Add a column for percent of total
industry_values['Pct_of_Total'] = industry_values['Market_Value'] / industry_values['Market_Value'].sum()
# Add a column for desired percent of total (even split)
industry_values['Desired_Pct'] = 1 / len(industry_values)
# Add a column for deviation from total
industry_values['Pct_Deviation'] = industry_values['Desired_Pct'] - industry_values['Pct_of_Total']
# Reset the index to set Sector as a column
industry_values.reset_index(inplace=True)
# Sort values by Pct_Deviation
industry_values = industry_values.sort_values(by='Pct_Deviation')

## Format dataframe appearance
properties = {"border": "0px", "color": "green", "background-color": "white", "font-size": "14px"}
daily_gainers = daily_gainers.style.set_properties(**properties).set_table_styles([
    {'selector': '', 'props': [('border-width', '0px')]},
    {'selector': 'th', 'props': [('border-width', '0px'), ('display', 'none')]},
]).hide_index()
# Format table data
properties = {"border": "0px", "color": "red", "background-color": "white", "font-size": "14px"}
daily_losers = daily_losers.style.set_properties(**properties).set_table_styles([
    {'selector': '', 'props': [('border-width', '0px')]},
    {'selector': 'th', 'props': [('border-width', '0px'), ('display', 'none')]},
]).hide_index()

## Save the dataframes for multipage use
st.session_state['stocks'] = stocks
st.session_state['stocks_complete'] = stocks_complete
st.session_state['daily_equity'] = daily_equity
st.session_state['stock_info'] = stock_info
st.session_state['todays_stocks'] = todays_stocks
st.session_state['daily_stocks_complete'] = daily_stocks_complete
st.session_state['todays_stocks_complete'] = todays_stocks_complete
st.session_state['cap_sizes'] = cap_sizes
st.session_state['industry_values'] = industry_values
st.session_state['sector_values'] = sector_values

### CALCULATE KEY VALUES / STATS ###

# Number of companies
companies = len(stocks_complete[stocks_complete["Quantity"] > 0])
# Portfolio Value
total_portfolio = round(sum(stocks_complete["Market_Value"]), 0)
total_portfolio_str = "$" + "{:,}".format(total_portfolio)
# Total Gain / Loss
total_change = round(sum(stocks_complete["Equity_Change"]), 0)
total_change_str = "$" + "{:,}".format(total_change)
# Total Invested Value
total_invested = round(sum(stocks_complete["Invested"]), 0)
total_invested_str = "$" + "{:,}".format(total_invested)
# Percentage Gain / Loss
pct_change = round(total_change / total_invested, 2) * 100
pct_change_str = str(pct_change) + "%"

### DISPLAY KEY STATISTICS ###

# Today's Date
today = datetime.date.today()
st.subheader(f"Today's Date: {today.strftime('%A, %B the %dth, %Y')}")
# Most Recent Data Point
st.text(f"Most Recent Data Point: {most_recent_date.strftime('%m/%d/%Y')}")

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Portfolio Value
    st.metric("Portfolio Value", total_portfolio_str)

with col2:
    # Total Invested Value
    st.metric("Invested Value", total_invested_str)

with col3:
    # Total Gain / Loss
    st.metric("Gain / Loss", total_change_str)

with col4:
    # Percentage Gain / Loss
    st.metric("Return on Equity %", pct_change_str)
    

### CREATE CHARTS ###

col1, col2 = st.columns([3,1])

with col1:

    # Give option on date frame to look at
    date_range = st.selectbox(
        'Date range:',
        ('All', '1Y', '3M', '1M', '1W'))

    if date_range == 'All':
        # Display Plotly
        customdata = np.array(daily_equity['Total_Profit'])
        fig = px.line(daily_equity, x='Date', y='Market_Value', title="Portfolio Total Performance")
        fig = fig.update_layout(yaxis_title="Market Value", title_x=0.5)
        fig.update_traces(line_color='#189557', customdata=customdata,
                          hovertemplate='<b>Date</b> = %{x|%Y-%m-%d}<br><b>Market Value</b> = %{y:$.0f}' +
                                        '<br><b>Total Profit</b> = %{customdata:$.0f}')
        # Plot!
        st.plotly_chart(fig, use_container_width=True)

    elif date_range == '1Y':
        # Filter to last year
        year = daily_equity[daily_equity.Date > datetime.datetime.now() - pd.to_timedelta("365days")]
        # Display 1Y Portfolio Performance
        customdata = np.array(year['Total_Profit'])
        fig = px.line(year, x='Date', y='Market_Value', title="Portfolio Annual Performance")
        fig = fig.update_layout(yaxis_title="Market Value", title_x=0.5)
        fig.update_traces(line_color='#189557', customdata=customdata,
                          hovertemplate='<b>Date</b> = %{x|%Y-%m-%d}<br><b>Market Value</b> = %{y:$.0f}' +
                                        '<br><b>Total Profit</b> = %{customdata:$.0f}')
        # Plot!
        st.plotly_chart(fig, use_container_width=True)

    elif date_range == '3M':
        # Filter to last 3 months
        three_month = daily_equity[daily_equity.Date > datetime.datetime.now() - pd.to_timedelta("90days")]
        # Display 3M Portfolio Performance
        customdata = np.array(three_month['Total_Profit'])
        fig = px.line(three_month, x='Date', y='Market_Value', title="Portfolio 3 Month Performance")
        fig = fig.update_layout(yaxis_title="Market Value", title_x=0.5)
        fig.update_traces(line_color='#189557', customdata=customdata,
                          hovertemplate='<b>Date</b> = %{x|%Y-%m-%d}<br><b>Market Value</b> = %{y:$.0f}' +
                                        '<br><b>Total Profit</b> = %{customdata:$.0f}')
        # Plot!
        st.plotly_chart(fig, use_container_width=True)

    elif date_range == '1M':
        # Filter to last month
        month = daily_equity[daily_equity.Date > datetime.datetime.now() - pd.to_timedelta("30days")]
        # Display 1M Portfolio Performance
        customdata = np.array(month['Total_Profit'])
        fig = px.line(month, x='Date', y='Market_Value', title="Portfolio Monthly Performance")
        fig = fig.update_layout(yaxis_title="Market Value", title_x=0.5)
        fig.update_traces(line_color='#189557', customdata=customdata,
                          hovertemplate='<b>Date</b> = %{x|%Y-%m-%d}<br><b>Market Value</b> = %{y:$.0f}' +
                                        '<br><b>Total Profit</b> = %{customdata:$.0f}')
        # Plot!
        st.plotly_chart(fig, use_container_width=True)

    else:
        # Filter to last week
        week = daily_equity[daily_equity.Date > datetime.datetime.now() - pd.to_timedelta("7days")]
        # Display 1M Portfolio Performance
        customdata = np.array(week['Total_Profit'])
        fig = px.line(week, x='Date', y='Market_Value', title="Portfolio Weekly Performance")
        fig = fig.update_layout(yaxis_title="Market Value", title_x=0.5)
        fig.update_traces(line_color='#189557', customdata=customdata,
                          hovertemplate='<b>Date</b> = %{x|%Y-%m-%d}<br><b>Market Value</b> = %{y:$.0f}' +
                                        '<br><b>Total Profit</b> = %{customdata:$.0f}')
        # Plot!
        st.plotly_chart(fig, use_container_width=True)

with col2:

    # Show table data
    st.caption("Top Daily Gainers")
    st.table(daily_gainers)

    # Show table data
    st.caption("Top Daily Losers")
    st.table(daily_losers)

# Create Plotly for Invested Capital
customdata = np.array(daily_equity['Total_Profit'])
fig = px.line(daily_equity, x='Date', y='Equity', title = "Invested Capital")
fig = fig.update_layout(yaxis_title = "Market Value", title_x = 0.5)
fig.update_traces(line_color='#189557', customdata=customdata,
                  hovertemplate='<b>Date</b> = %{x|%Y-%m-%d}<br><b>Equity</b> = %{y:$.0f}')
# Display Plotly
st.plotly_chart(fig, use_container_width=True)
