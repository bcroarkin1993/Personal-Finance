import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np

### FORMAT STREAMLIT PAGE ###
st.set_page_config(layout="wide")
# Title
st.title("Investment Dashboard - Portfolio Analysis")

### PULL IN & FORMAT DATA ###

# Pull in tables from session_state
stocks = st.session_state['stocks']
stocks_complete = st.session_state['stocks_complete']
stock_info = st.session_state['stock_info']
daily_equity = st.session_state['daily_equity']
todays_stocks = st.session_state['todays_stocks']
daily_stocks_complete = st.session_state['daily_stocks_complete']
cap_sizes = st.session_state['cap_sizes']

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