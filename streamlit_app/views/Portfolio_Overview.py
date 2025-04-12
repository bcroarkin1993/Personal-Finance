import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
from ..scripts.data_processing import load_and_preprocess_data

### FORMAT STREAMLIT PAGE ###
st.set_page_config(layout="wide")
# Title
st.title("Portfolio Overview")

### PULL IN & FORMAT DATA ###

# Load preprocessed data
data = load_and_preprocess_data()

# Access dataframes
stocks = data["stocks"]
stock_info = data["stock_info"]
daily_stocks = data["daily_stocks"]
stocks_complete = data["stocks_complete"]

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

# Number of companies
companies = len(stocks_complete[stocks_complete["Quantity"] > 0])

# Filter and sort stocks
stocks_complete = stocks_complete.sort_values("Market_Value", axis = 0, ascending = True)
stocks_complete = stocks_complete.tail(companies)

# Total Invested Value
total_invested = round(sum(stocks_complete["Invested"]), 0)
total_invested_str = "$" + str(total_invested)

### CREATE AND DISPLAY VISUALS ###

# Create display options
companies = st.slider("Pick Number of Companies", 1, companies)

col1, col2 = st.columns(2)

with col1:

    st.subheader("Top Companies by Market Value")

    # Filter stocks_complete based on filter option
    stocks_complete = stocks_complete.sort_values("Market_Value", axis=0, ascending=False)
    stocks_complete = stocks_complete.head(companies)

    # Display Plotly
    fig = px.bar(stocks_complete, x='Market_Value', y='Stock', color='Equity_Change',
                 color_continuous_scale='rdylgn', range_color=[-2000, 2000],
                 hover_name='Stock',
                 hover_data={
                     'Market_Value': ':$,.0f',
                     'Equity_Change': ':$,.0f',
                     'Stock': False
                 })
    fig = fig.update_layout(yaxis=dict(autorange="reversed"), yaxis_title=None, xaxis_title=None, autosize=True)
    # Plot!
    st.plotly_chart(fig, use_container_width=True)

with col2:

    st.subheader("52 Week Range")
    st.subheader("")
    st.text("")

    # 52 Week Range
    # Filter to columns of interest
    range52Week = stocks[['Stock', 'Price', '52_Week_High', '52_Week_Low', 'Market_Value']].copy()
    # Add dummy columns for the start and stop position
    range52Week.loc[:, 'Start'] = 0
    range52Week.loc[:, 'Stop'] = 1
    # Scale the current price on a 0-1 scale between the 52 week high and low
    range52Week.loc[:, 'PriceAdjusted'] = (range52Week['Price'] - range52Week['52_Week_Low']) / (
                range52Week['52_Week_High'] - range52Week['52_Week_Low'])
    # Filter to top x companies
    range52Week = range52Week.sort_values(by="Market_Value", ascending=False).head(companies)
    # Reverse Y-axis order (gets twisted going to horizontal for some reason)
    range52Week = range52Week.iloc[::-1].reset_index().drop(columns=['index'])
    # Format dataframe values
    range52Week['52_Week_High'] = range52Week['52_Week_High'].apply(lambda x: "${:,.2f}".format(x))
    range52Week['52_Week_Low'] = range52Week['52_Week_Low'].apply(lambda x: "${:.2f}".format(x))
    range52Week['Price'] = range52Week['Price'].apply(lambda x: "${:,.2f}".format(x))

    # Create bar chart
    fig = plt.figure()
    plt.barh(range52Week['Stock'], range52Week['Stop'], height=.02, color='black')
    # Set figure dimensions
    fig.set_figwidth(4)
    fig.set_figheight(2)
    plt.rc('font', size=5)  # controls default text size
    # Remove x-axis labels and y-axis ticks
    plt.xticks([])
    #plt.yticks([])
    # Remove border line
    for pos in ['right', 'top', 'bottom', 'left']:
        plt.gca().spines[pos].set_visible(False)
    # Add price marker
    y_pos = np.arange(len(range52Week['PriceAdjusted']))
    plt.plot(range52Week['PriceAdjusted'], y_pos, marker="D", linestyle="", alpha=0.8, color="g")
    # Add price marker labels
    for index, row in range52Week.iterrows():
        plt.text(-0.05, index + .1, row['52_Week_Low'])
        plt.text(.95, index + .1, row['52_Week_High'])
        #plt.text(row['PriceAdjusted'] - .1, index + .1, row['Price'])
    # Display bar chart
    st.pyplot(fig)

col1, col2 = st.columns(2)

with col1:

    # Show Cap Size Ratio
    fig = px.pie(cap_sizes, values='Market_Value', hole=0.6,
                 names='CapSize', color='CapSize',
                 title='Company Cap Sizes')
    st.plotly_chart(fig, use_container_width=True)

with col2:

    # Show Stock / Crypto Ratio
    fig = px.pie(todays_stocks, values='Market_Value', hole=0.6,
                 names='Asset_Type', color='Asset_Type',
                 title='Stock to Crypto Ratio')
    st.plotly_chart(fig, use_container_width=True)

# Create display options
companies = st.slider("Choose Number of Companies", 1, 60)

### BETA BAR CHART ###

# Remove null Beta value companies
beta_stocks = stocks_complete.dropna(subset=["Beta"])
# Filter stocks
beta_stocks = beta_stocks.sort_values("Beta", axis=0, ascending=True)
beta_stocks = beta_stocks.tail(companies)

# Create Plotly
fig = px.bar(beta_stocks, x='Beta', y='Stock', title = "Beta Risk by Company", hover_name = 'Stock',
             hover_data = {
                 'Market_Value': ':.2f',
                 'Stock': False
            })

# Plot!
st.plotly_chart(fig, use_container_width=True)

### BUY/HOLD/SELL RATING BAR CHART ###

# Filter stocks
rating_stocks = stocks_complete[['Stock', 'Buy_Ratio', 'Hold_Ratio', 'Sell_Ratio']]
# Remove null Buy ratio companies
rating_stocks = rating_stocks.dropna(subset=["Buy_Ratio"])
# Filter stocks
rating_stocks = rating_stocks.sort_values("Buy_Ratio", axis = 0, ascending = True)
rating_stocks = rating_stocks.tail(companies)

# shape from wide to long with melt function in pandas
rating_stocks = pd.melt(rating_stocks, id_vars=['Stock'], var_name='Rating_Type', value_name='Rating')

# Create Plotly
fig2 = px.bar(rating_stocks, x = 'Stock', y = 'Rating', color = 'Rating_Type')

# Plot!
st.plotly_chart(fig2, use_container_width=True)

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

col1, col2 = st.columns([3, 1])

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

# Create Plotly for Invested Capital
customdata = np.array(daily_equity['Total_Profit'])
fig = px.line(daily_equity, x='Date', y='Equity', title="Invested Capital")
fig = fig.update_layout(yaxis_title="Market Value", title_x=0.5)
fig.update_traces(line_color='#189557', customdata=customdata,
                  hovertemplate='<b>Date</b> = %{x|%Y-%m-%d}<br><b>Equity</b> = %{y:$.0f}')
# Display Plotly
st.plotly_chart(fig, use_container_width=True)

# Format and Show table data
stocks_complete = stocks_complete.rename(columns = {"Company_x": "Company", "Stock": "Ticker", "Avg_Cost": "Avg Cost",
                                                    "Market_Value": "Market Value", "Equity_Change": "Equity Change",
                                                    "Percent_Change": "Percent Change", "52_Week_High": "52 Week High",
                                                    "52_Week_Low": "52 Week Low", "Asset_Type": "Asset Type",
                                                    "Market_Cap": "Market Cap", "Avg_Volume": "Volume", "PE_Ratio":
                                                    "PE Ratio"})
stocks_complete = stocks_complete[['Company', 'Quantity', 'Avg Cost', 'Market Value', 'Equity Change', 'Percent Change',
                                   '52 Week High', '52 Week Low', 'Volume', 'PE Ratio', 'Beta']]
st.dataframe(stocks_complete.style.format({"Quantity": "{:.2f}", "Avg Cost": "${:.2f}", "Market Value": "${:.2f}",
                                           "Equity Change": "${:.2f}", "Percent Change": "{:.0%}",
                                           "52 Week High": "${:.2f}", "52 Week Low": "${:.2f}", "Volume": "${:.2f}",
                                           "PE Ratio": "{:.2f}", "Beta": "{:.2f}"}))