import json
import os
import pandas as pd
import robin_stocks.robinhood as r
import streamlit as st
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from streamlit_app.scripts.config import RUN_MODE

# Define reusable functions for loading and preprocessing data
def load_main_data():
    """
    Loads the main data files into memory.

    Returns:
        dict: A dictionary containing the raw dataframes.
    """
    # Get absolute path to the current script (main.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Go up one level to reach the project root
    project_root = os.path.abspath(os.path.join(base_dir, "../.."))

    # Set the path to the data directory
    data_dir = os.path.join(project_root, "data")

    if RUN_MODE == "testing":
        print(f"Base Dir: {base_dir}")
        print(f"Project Root Dir: {project_root}")
        print(f"Data Dir: {data_dir}")

    # Load data
    stocks = pd.read_csv(os.path.join(data_dir, "stocks.csv"))
    stock_info = pd.read_csv(os.path.join(data_dir, "stock_info.csv"))
    daily_stocks = pd.read_csv(os.path.join(data_dir, "daily_stocks.csv"))
    expenses = pd.read_csv(os.path.join(data_dir, "expenses.csv"))
    income = pd.read_csv(os.path.join(data_dir, "income.csv"))
    with open(os.path.join(data_dir, "stock_dictionary.json"), "r") as file:
        stock_dictionary = json.load(file)

    return {
        "stocks": stocks,
        "stock_info": stock_info,
        "daily_stocks": daily_stocks,
        "stock_dictionary": stock_dictionary,
        "expenses": expenses,
        "income": income
    }

def preprocess_data(raw_data):
    """
    Preprocesses the raw dataframes.

    Args:
        raw_data (dict): A dictionary containing raw dataframes.

    Returns:
        dict: A dictionary containing processed dataframes.
    """
    stock_dictionary = raw_data["stock_dictionary"]
    stocks = raw_data["stocks"].copy()
    stock_info = raw_data["stock_info"]
    daily_stocks = raw_data["daily_stocks"]
    expenses = raw_data["expenses"]
    income = raw_data["income"]

    # Remove stocks that have been sold
    stocks = stocks[stocks["Quantity"] > 0]
    # Add a Portfolio Diversity field to track how much a stock is of my total portfolio value
    stocks.loc[:, "Portfolio_Diversity"] = round(stocks["Market_Value"] * 100 / stocks["Market_Value"].sum(), 2)
    # Add a column to show whether this stock has been a winner or loser for me
    stocks.loc[:, "Direction"] = stocks["Percent_Change"].apply(lambda x: "Up" if x > 0 else "Down")

    # Add a column to the stock_info df to categorize the companies by market size
    stock_info["CapSize"] = stock_info["Market_Cap"].apply(
        lambda x: "Small-Cap" if x < 2 else ("Mid-Cap" if x < 10 else "Large-Cap")
    )

    # Process daily_stocks
    daily_stocks["Equity"] = daily_stocks["Shares_Held"] * daily_stocks["Avg_Cost"]
    daily_stocks["Market_Value"] = daily_stocks["Close"] * daily_stocks["Shares_Held"]
    daily_stocks["Total_Profit"] = daily_stocks["Market_Value"] - daily_stocks["Equity"]

    if RUN_MODE == "testing":
        print(f"Stocks DF: {stocks.head()}")
        print(f"Stock Info DF: {stock_info.head()}")

    # Merge processed data
    stocks_complete = pd.merge(stocks, stock_info, how="left", left_on="Stock", right_on="Company")
    stocks_complete["Invested"] = stocks_complete["Quantity"] * stocks_complete["Avg_Cost"]

    ## Create a lookup table for Stock Tickers to Company Names
    stock_names = stocks[['Stock', 'Company']]

    ## Merge stocks and stocks_info
    stocks_complete = pd.merge(stocks, stock_info, how='left', left_on='Stock', right_on='Company')
    # Create a column for invested amount
    stocks_complete['Invested'] = stocks_complete['Quantity'] * stocks_complete['Avg_Cost']
    # Remove unnamed columns
    stocks_complete = stocks_complete.loc[:, ~stocks_complete.columns.str.contains('^Unnamed')]

    ## Merge daily_stocks and stock_names
    daily_stocks_complete = pd.merge(daily_stocks, stock_names)
    print("DAILY STOCKS COMPLETE: \n", daily_stocks_complete)

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

    # Create a DF to just capture stock info as it is today (or for the most recent date available)
    most_recent_date = daily_stocks_complete['Datetime'].max()
    todays_stocks = daily_stocks_complete[(daily_stocks_complete['Datetime'] == most_recent_date) &
                                          (daily_stocks_complete['Shares_Held'] != 0) &
                                          (daily_stocks_complete['Company'] != "0")].copy()
    print("TODAY'S STOCKS: \n", todays_stocks)

    ## Create Daily Gainers / Losers dataframes
    daily_gainers = todays_stocks[['Company', 'Daily_Profit', 'Daily_Pct_Profit']].reset_index(drop=True).sort_values(
        "Daily_Profit", axis=0, ascending=False).head(5)
    daily_losers = todays_stocks[['Company', 'Daily_Profit', 'Daily_Pct_Profit']].reset_index(drop=True).sort_values(
        "Daily_Profit", axis=0, ascending=True).head(5)
    # Remove any negatives from gainers and positives from losers
    daily_gainers = daily_gainers[daily_gainers['Daily_Profit'] > 0]
    daily_losers = daily_losers[daily_losers['Daily_Profit'] < 0]

    ## Create a lookup table for Stock Tickers to Sector/Industry
    stock_sector_industry = stocks_complete[['Stock', 'Sector', 'Industry']]
    print("STOCK SECTOR INDUSTRY: \n", stock_sector_industry)
    # Merge industry/sector data into todays_stocks
    todays_stocks_complete = pd.merge(todays_stocks, stock_sector_industry)
    print("TODAY STOCKS COMPLETE: \n", todays_stocks_complete)

    # Create a lookup table for Stock Tickers to Company Names
    stock_caps = stock_info[['Company', 'CapSize']]
    # Merge in cap size to todays_stocks
    cap_sizes = pd.merge(todays_stocks, stock_caps, how='inner', left_on='Stock', right_on='Company')
    # Format table
    cap_sizes = cap_sizes[['Stock', 'Market_Value', 'CapSize']]

    ## Format dataframe values
    daily_stocks_complete['Daily_Profit'] = daily_stocks_complete['Daily_Profit'].apply(lambda x: "${:,.2f}".format(x))
    daily_stocks_complete['Daily_Pct_Profit'] = daily_stocks_complete['Daily_Pct_Profit'].apply(
        lambda x: "{:.2f}%".format(x))
    daily_stocks_complete['Market_Value'] = daily_stocks_complete['Market_Value'].apply(lambda x: "${:,.2f}".format(x))
    daily_stocks_complete['Total_Profit'] = daily_stocks_complete['Total_Profit'].apply(lambda x: "${:,.2f}".format(x))
    daily_stocks_complete['Avg_Cost'] = daily_stocks_complete['Avg_Cost'].apply(lambda x: "${:,.2f}".format(x))
    daily_stocks_complete['Equity'] = daily_stocks_complete['Equity'].apply(lambda x: "${:,.2f}".format(x))
    daily_stocks_complete['Per_Share_Profit'] = daily_stocks_complete['Per_Share_Profit'].apply(
        lambda x: "${:,.2f}".format(x))
    daily_gainers['Daily_Profit'] = daily_gainers['Daily_Profit'].apply(lambda x: "${:,.2f}".format(x))
    daily_gainers['Daily_Pct_Profit'] = daily_gainers['Daily_Pct_Profit'].apply(lambda x: "{:.2f}%".format(x))
    daily_losers['Daily_Profit'] = daily_losers['Daily_Profit'].apply(lambda x: "${:,.2f}".format(x))
    daily_losers['Daily_Pct_Profit'] = daily_losers['Daily_Pct_Profit'].apply(lambda x: "{:.2f}%".format(x))

    # Groupby Sector and sum values
    sector_values = pd.DataFrame(todays_stocks_complete.groupby(['Sector'])['Market_Value'].sum())
    print("SECTOR VALUES: \n", sector_values)
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

    ## BUYING OPPORTUNITIES

    # Pull the information for the top 100 stocks on Robinhood
    top_100 = r.get_top_100()

    # Create an empty dataframe to append information to
    buying_opportunities = pd.DataFrame(columns=['Symbol', 'Company', 'Description', 'Year_Founded', 'Industry', 'Sector',
                                              'Price', 'Daily_Pct_Change', 'Low_52_Weeks', 'High_52_Weeks', 'PB_Ratio',
                                              'PE_Ratio', 'Buy_Rating', 'Hold_Rating', 'Sell_Rating'])

    # Loop over each stock
    for stock in top_100:
        symbol = stock['symbol']
        # Filter out stocks that I already have
        if symbol in stock_dictionary.keys():
            continue
        else:
            company = r.find_instrument_data(symbol)[0]['simple_name']
            fundamentals = r.get_fundamentals(symbol)[0]
            year_founded = fundamentals['year_founded']
            sector = fundamentals['sector']
            industry = fundamentals['industry']
            description = fundamentals['description']
            low_52_weeks = fundamentals['low_52_weeks']
            high_52_weeks = fundamentals['high_52_weeks']
            pb_ratio = fundamentals['pb_ratio']
            pe_ratio = fundamentals['pe_ratio']
            open = float(stock['previous_close'])
            current_price = float(stock['last_trade_price'])
            daily_pct_change = (current_price - open) / open * 100
            ratings = r.stocks.get_ratings(symbol, info=None)['summary']
            total_ratings = sum(ratings.values()) if ratings != None else np.nan
            buy_ratio = ratings['num_buy_ratings'] / total_ratings if ratings != None else np.nan
            hold_ratio = ratings['num_hold_ratings'] / total_ratings if ratings != None else np.nan
            sell_ratio = ratings['num_sell_ratings'] / total_ratings if ratings != None else np.nan
            stock_series = pd.Series([symbol, company, description, year_founded, industry, sector, current_price,
                                      daily_pct_change, low_52_weeks, high_52_weeks, pb_ratio, pe_ratio,
                                      buy_ratio, hold_ratio, sell_ratio], index=buy_opportunities.columns)
            buying_opportunities = buying_opportunities.append(stock_series, ignore_index=True)

    ## REBUYING OPPORTUNITIES

    # Start with the stocks table for the Price, Market Value, and 52 Week High/Low
    rebuying_opportunities = stocks[['Stock', 'Price', 'Market_Value', '52_Week_High', '52_Week_Low']]
    # Merge in the Industry and the Buy/Hold/Sell ratios from stock_info
    rebuying_opportunities = pd.merge(rebuying_opportunities,
                                      stock_info[['Company', 'Sector', 'Buy_Ratio', 'Hold_Ratio',
                                                  'Sell_Ratio']],
                                      how='inner', left_on='Stock', right_on='Company')
    # Merge in the Sector Values
    rebuying_opportunities = pd.merge(rebuying_opportunities, sector_values[['Sector', 'Sector_Value']],
                                      how='inner', on='Sector')
    # Add a rank for Market_Value
    rebuying_opportunities['Market_Rank'] = rebuying_opportunities['Market_Value'].rank(ascending=False)
    # Create a Market Score
    rebuying_opportunities['Market_Score'] = rebuying_opportunities['Market_Rank'] * 20 \
                                             / rebuying_opportunities['Market_Rank'].max()
    # Add a rank for Sector_Value
    rebuying_opportunities['Sector_Rank'] = rebuying_opportunities['Sector_Value'].rank(method='dense', ascending=False)
    # Create an Sector Score
    rebuying_opportunities['Sector_Score'] = rebuying_opportunities['Sector_Rank'] * 20 \
                                             / rebuying_opportunities['Sector_Rank'].max()

    # Create 52 Week High/Low Score
    rebuying_opportunities['HighLow_Score'] = (rebuying_opportunities['Price'] - rebuying_opportunities['52_Week_Low']) \
                                              / (rebuying_opportunities['52_Week_High'] - rebuying_opportunities[
        '52_Week_Low'])
    rebuying_opportunities['HighLow_Score'] = abs(1 - rebuying_opportunities['HighLow_Score']) * 30

    # Create Buy/Hold/Sell Score
    rebuying_opportunities['BuyHoldSell_Score'] = (rebuying_opportunities['Buy_Ratio'] - rebuying_opportunities[
        'Sell_Ratio']) * 30

    # Format dataframe
    rebuying_opportunities = rebuying_opportunities.drop(columns=['Company', 'Market_Value', 'Sector_Value', 'Price',
                                                                  '52_Week_High', '52_Week_Low', 'Sector',
                                                                  'Market_Rank',
                                                                  'Sector_Rank', 'Buy_Ratio', 'Hold_Ratio',
                                                                  'Sell_Ratio'])
    rebuying_opportunities['Market_Score'] = rebuying_opportunities['Market_Score'].round(2)
    rebuying_opportunities['Sector_Score'] = rebuying_opportunities['Sector_Score'].round(2)
    rebuying_opportunities['HighLow_Score'] = rebuying_opportunities['HighLow_Score'].round(2)
    rebuying_opportunities['BuyHoldSell_Score'] = rebuying_opportunities['BuyHoldSell_Score'].round(2)
    rebuying_opportunities.fillna(0, inplace=True)

    # Create Final Score
    rebuying_opportunities['Buy_Score'] = rebuying_opportunities['Market_Score'] + rebuying_opportunities[
        'Sector_Score'] + rebuying_opportunities['HighLow_Score'] + rebuying_opportunities['BuyHoldSell_Score']
    rebuying_opportunities = rebuying_opportunities.sort_values(by='Buy_Score', ascending=False)

    return {
        "stocks": stocks,
        "stock_info": stock_info,
        "daily_stocks_complete": daily_stocks_complete,
        "stocks_complete": stocks_complete,
        "industry_values": industry_values,
        "sector_values": sector_values,
        "daily_equity": daily_equity,
        "buying_opportunities": buying_opportunities,
        "rebuying_opportunities": rebuying_opportunities,
        "expenses": expenses,
        "income": income
    }

# Cached loader to be used in Streamlit
@st.cache_data
def load_and_preprocess_data():
    """
    Combines loading and preprocessing logic with caching.

    Returns:
        dict: A dictionary of processed dataframes.
    """
    raw_data = load_main_data()
    return preprocess_data(raw_data)



