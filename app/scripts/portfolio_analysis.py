import configparser
from datetime import date, timedelta
from geopy import Nominatim
import json
import numpy as np
import os
import pandas as pd
import pycountry
import robin_stocks.robinhood as r
import yfinance as yf

def load_robinhood_credentials(config_file):
    """
    Load credentials from config.ini file
    :param config_file:
    :return:
    """
    # Load configuration file
    config = configparser.ConfigParser()
    config.read(config_file)
    # Access credentials
    username = config['robinhood_credentials']['username']
    email = config['robinhood_credentials']['email']
    password = config['robinhood_credentials']['password']
    return(username, email, password)

def login_to_robinhood(email, password):
    """
    Login to Robinhood API
    :param email:
    :param password:
    :return:
    """
    try:
        # Need to save the username and password in protected fileds
        r.authentication.login(username=email, password=password, expiresIn=86400,
                               scope='internal', by_sms=True, store_session=True)
    except Exception as e:
        print(f"Failed to log in: {e}")
        raise

def country_flag(df):
    country = pycountry.countries.get(alpha_2=df['Country']).name
    country = country if country else ''
    return country

def load_stock_dictionary(file_path):
    """
    Load stock dictionary from JSON file
    :param file_path:
    :return:
    """
    with open(file_path, 'r') as stock_dictionary:
        stock_dictionary = json.load(stock_dictionary)
    return(stock_dictionary)

def create_daily_stocks_csv(stock_dictionary, daily_stocks_csv_path):
    """
    ## Build out Stock positions over time and save CSV file

    # What information do I want in this table?
    # - Company
    # - Date
    # - Closing Values
    # - Stocks Owned

    :return:
    """
    # Create a list of my current stocks
    stock_list = list(stock_dictionary.keys())

    # Set today's date
    today = date.today()

    # Calculate the number of days from today to the first buy date
    first_buy_date = date(2016, 9, 21)
    days_from_first_buy = (today - first_buy_date).days

    # Create the dataframe structure
    daily_stocks = pd.DataFrame(columns=['Date', 'Close', 'Stock'])

    # Step 1: Iterate over my list of stocks and append to a dataframe
    row_index = 0 # Initialize a row index for .loc[]
    for stock in stock_list:
        # Download data from pandas datareader
        temp = yf.download(stock,
                           start=today - timedelta(days=days_from_first_buy),
                           end=today)['Adj Close']
        # Convert to dataframe
        temp_df = pd.DataFrame(temp)
        # Add column for stock name
        temp_df['Stock'] = stock
        # Add the date as a column
        temp_df.reset_index(inplace = True)
        # Rename columns
        temp_df.columns = ['Date', 'Close', 'Stock']
        # Add rows to the daily_stocks DataFrame using .loc
        for _, row in temp_df.iterrows():
            daily_stocks.loc[row_index] = row
            row_index += 1

    # Step 2: Merge my stock quantities into this table

    # Add the stock quantity column
    daily_stocks['Shares_Held'] = np.nan
    # Add the average cost column
    daily_stocks['Avg_Cost'] = np.nan

    # Loop over the stock purchase history dictionary and add quantity information
    for k, v in stock_dictionary.items():

        # Just need to find the initial purchase date and forward fill if only bought once
        if len(v['purchase_history']) == 1:
            # Find the initial_purchase_date
            initial_purchase_date = v['purchase_history'][0]['date']
            # Find the intial purchase quantity
            initial_purchase_quantity = v['purchase_history'][0]['quantity']
            # Find the initial purchase cost
            initial_purchase_cost = v['purchase_history'][0]['share_price']
            # Modify the Shares_Held value at the initial_purchase_date
            daily_stocks.loc[(daily_stocks.Date == initial_purchase_date) &
                    (daily_stocks.Stock == k), 'Shares_Held'] = initial_purchase_quantity
            # Modify the Avg_Cost value at the initial_purchase_date
            daily_stocks.loc[(daily_stocks.Date == initial_purchase_date) &
                    (daily_stocks.Stock == k), 'Avg_Cost'] = initial_purchase_cost

        # Need to do more modifications if multiple buy/sell events
        else:
            # iterate over the different purchase events
            for num, purchase in enumerate(v['purchase_history']):
                if num == 0:
                    # Find the initial_purchase_date
                    initial_purchase_date = v['purchase_history'][0]['date']
                    # Find the intial purchase quantity
                    initial_purchase_quantity = v['purchase_history'][0]['quantity']
                    # Find the initial purchase cost
                    initial_purchase_cost = v['purchase_history'][0]['share_price']
                    # Find the initial equity
                    initial_equity = initial_purchase_cost * initial_purchase_quantity
                    # Modify the value at the initial_purchase date
                    daily_stocks.loc[(daily_stocks.Date == initial_purchase_date) &
                            (daily_stocks.Stock == k), 'Shares_Held'] = initial_purchase_quantity
                    # Modify the Avg_Cost value at the initial_purchase_date
                    daily_stocks.loc[(daily_stocks.Date == initial_purchase_date) &
                            (daily_stocks.Stock == k), 'Avg_Cost'] = initial_purchase_cost
                elif num == 1:
                    # List the current quantity
                    previous_quantity = initial_purchase_quantity
                    # List the current equity
                    previous_equity = initial_equity
                    # Find the purchase_date
                    purchase_date = purchase['date']
                    # Find the purchase quantity
                    purchase_quantity = purchase['quantity'] if purchase['buy_sell'] == 'buy' else -purchase['quantity']
                    # Find the purchase cost
                    purchase_cost = v['purchase_history'][num]['share_price']
                    # Find the equity of the purchase
                    purchase_equity = purchase_cost * purchase_quantity
                    # Update my quantity
                    updated_quantity = previous_quantity + purchase_quantity
                    # Update my total equity
                    updated_equity = (initial_equity + purchase_equity) if updated_quantity != 0 else 0
                    # Update my Avg_Cost
                    try:
                        updated_avg_cost = updated_equity / updated_quantity
                    except ZeroDivisionError:
                        updated_avg_cost = 0
                    # Modify the Shares_Held value at the purchase date
                    daily_stocks.loc[(daily_stocks.Date == purchase_date) &
                            (daily_stocks.Stock == k), 'Shares_Held'] = updated_quantity
                    # Modify the Avg_Cost value
                    daily_stocks.loc[(daily_stocks.Date == purchase_date) &
                            (daily_stocks.Stock == k), 'Avg_Cost'] = updated_avg_cost
                else:
                    # List the current quantity
                    previous_quantity = updated_quantity
                    # List the current equity
                    previous_equity = updated_equity
                    # Find the purchase_date
                    purchase_date = purchase['date']
                    # Find the purchase quantity
                    purchase_quantity = purchase['quantity'] if purchase['buy_sell'] == 'buy' else -purchase['quantity']
                    # Find the purchase cost
                    purchase_cost = v['purchase_history'][num]['share_price']
                    # Find the equity of the purchase
                    purchase_equity = purchase_cost * purchase_quantity
                    # Update my quantity
                    updated_quantity = previous_quantity + purchase_quantity
                    # Update my total equity
                    updated_equity = (previous_equity + purchase_equity) if updated_quantity != 0 else 0
                    # Update my Avg_Cost
                    try:
                        updated_avg_cost = updated_equity / updated_quantity
                    except ZeroDivisionError:
                        updated_avg_cost = 0
                    # Modify the Shares_Held value at the purchase date
                    daily_stocks.loc[(daily_stocks.Date == purchase_date) &
                            (daily_stocks.Stock == k), 'Shares_Held'] = updated_quantity
                    # Modify the Avg_Cost value
                    daily_stocks.loc[(daily_stocks.Date == purchase_date) &
                            (daily_stocks.Stock == k), 'Avg_Cost'] = updated_avg_cost

    # Step 3: Need to connect my quantities across dates now

    # Iterate over the stock list and forward fill values
    temp_list = []  # Use a list to collect DataFrames
    for stock in stock_list:
        temp = daily_stocks.loc[daily_stocks.Stock == stock].ffill()
        temp_list.append(temp)  # Add each temporary DataFrame to the list

    # Concatenate all the temporary DataFrames into a single DataFrame
    daily_stocks_df = pd.concat(temp_list, ignore_index=True)

    # Convert Shares_Held to an integer
    daily_stocks_df['Shares_Held'] = daily_stocks_df['Shares_Held'].dropna().astype(float)

    # Re-format daily_stocks date column
    daily_stocks_df['Date'] = daily_stocks_df['Date'].dt.strftime('%Y-%m-%d')

    # Replace all np.nan values with 0
    daily_stocks_df.fillna(0, inplace = True)

    # Save the data files
    daily_stocks_df.to_csv(daily_stocks_csv_path)

def create_stocks_csv(stock_dictionary, stocks_csv_path):
    """
    # ## Create a summary table that describes my positions today

    # What information do I want in this table?
    # - Company Name
    # - Stock Ticker
    # - Price
    # - Shares Owned
    # - Average Cost
    # - Total Equity
    # - Profit ($'s)
    # - Profit (%)
    # - Portfolio Diversity
    :return:
    """
    # Create a list of my current stocks
    stock_list = list(stock_dictionary.keys())

    # Get the table of my account holdings from RobinHood
    temp = r.account.build_holdings(with_dividends = False)

    # Convert this table into a dataframe
    stocks_df = pd.DataFrame(temp)

    # Transpose table
    stocks_df = stocks_df.T

    # Subset to only the needed columns
    stocks_df = stocks_df[['price', 'quantity', 'average_buy_price', 'equity',
                       'percent_change', 'equity_change', 'name']]

    # Update Column Names
    stocks_df.columns = ['Price', 'Quantity', 'Avg_Cost', 'Market_Value', 'Percent_Change', 'Equity_Change', 'Company']

    # Round columns and change data types as appropriate
    stocks_df['Price'] = round(stocks_df['Price'].astype(float), 2)
    stocks_df['Quantity'] = stocks_df['Quantity'].astype(float)  # convert to float first to avoid error
    stocks_df['Quantity'] = stocks_df['Quantity'].astype(int)
    stocks_df['Market_Value'] = stocks_df['Market_Value'].astype(float)
    stocks_df['Avg_Cost'] = round(stocks_df['Avg_Cost'].astype(float), 2)
    stocks_df['Equity_Change'] = round(stocks_df['Equity_Change'].astype(float), 2)
    stocks_df['Percent_Change'] = stocks_df['Percent_Change'].astype(float)

    # Create new columns for 52 Week High and Low
    stocks_df['52_Week_High'] = 0.0
    stocks_df['52_Week_Low'] = 0.0

    # Add in column with stock/crypto identifier
    stocks_df['Asset_Type'] = 'Stock'

    # Iterate over stock list and append 52-Week High and Low to dataframe
    for stock in stock_list:
        # Pull the fundamentals table
        fundamentals = r.stocks.get_fundamentals(stock)[0]
        # Access the 52-Week High and Low and make them into variables, if they exist
        try:
            high52 = fundamentals['high_52_weeks']
            low52 = fundamentals['low_52_weeks']
            # modify the value
            stocks_df.loc[stock, '52_Week_High'] = float(high52)
            stocks_df.loc[stock, '52_Week_Low'] = float(low52)
        except TypeError:
            # modify the value
            stocks_df.loc[stock, '52_Week_High'] = np.nan
            stocks_df.loc[stock, '52_Week_Low'] = np.nan

    # Modify the datatypes
    stocks_df['52_Week_High'] = stocks_df['52_Week_High'].astype(float)
    stocks_df['52_Week_Low'] = stocks_df['52_Week_Low'].astype(float)

    # Round
    stocks_df['52_Week_High'] = round(stocks_df['52_Week_High'], 2)
    stocks_df['52_Week_Low'] = round(stocks_df['52_Week_Low'], 2)

    # Reorganize columns
    cols = ['Price', 'Quantity', 'Avg_Cost', 'Market_Value', 'Percent_Change', 'Equity_Change', '52_Week_High',
            '52_Week_Low', 'Asset_Type', 'Company']
    stocks_df = stocks_df[cols]

    # Reset index
    stocks_df.reset_index(inplace = True)
    # Rename column
    stocks_df.rename(columns={'index': 'Stock'}, inplace=True)
    # Replace all np.nan values with 0
    stocks_df.fillna(0, inplace=True)

    # Save the data file
    stocks_df.to_csv(stocks_csv_path)

def create_stock_info_csv(stock_dictionary, stock_info_csv_path):
    """
    ## Create CSV file with information about each company I own stock of
    # - Company
    # - CEO
    # - Current Market Cap
    # - Average Volume
    # - 52 week high
    # - 52 week low
    # - Price-to-earnings (PE) Ratio
    # - Price-to-book (PB) Ratio
    # - Dividend Yield
    # - Beta risk (Yahoo continues to give me HTTP errors, so may need to find alternative route to get this)
    # - Sector
    # - Industry
    # - Buy/Sell/Hold ratings
    # - Description
    :return:
    """
    # Create the final dataframe structure
    stock_info_df = pd.DataFrame(columns = ['Company', 'CEO', 'Country', 'State', 'City', 'Lat', 'Lng',
                                            'Market_Cap (Billions)', 'Avg_Volume (Millions)', 'Shares_Outstanding',
                                            'PE_Ratio', 'PB_Ratio', 'Dividend_Yield', 'Beta', 'Sector', 'Industry',
                                            'Buy_Ratio', 'Hold_Ratio', 'Sell_Ratio', 'Description'])

    # Initiate geocoder
    geolocator = Nominatim(user_agent="brcroarkin@gmail.com")

    # Create a list of my current stocks
    stock_list = list(stock_dictionary.keys())

    # Loop over the companies in the stock list, get the needed information, and append df
    for stock in stock_list:
        print(stock)
        company = stock
        # Get information on company's fundamentals from Robinhood, if they exist
        try:
            fundamentals = r.stocks.get_fundamentals(stock)[0]
            ceo = fundamentals['ceo']
            state = fundamentals['headquarters_state']
            city = fundamentals['headquarters_city']
            full_location = f"{city}, {state}"
            market_cap = fundamentals['market_cap']
            average_volume = fundamentals['average_volume']
            shares_outstanding = fundamentals['shares_outstanding']
            pe_ratio = fundamentals['pe_ratio']
            pb_ratio = fundamentals['pb_ratio']
            dividend_yield = fundamentals['dividend_yield']
            sector = fundamentals['sector']
            industry = fundamentals['industry']
            description = fundamentals['description']
        except TypeError:
            ceo = np.nan
            state = np.nan
            city = np.nan
            market_cap = np.nan
            average_volume = np.nan
            shares_outstanding = np.nan
            pe_ratio = np.nan
            pb_ratio = np.nan
            dividend_yield = np.nan
            sector = np.nan
            industry = np.nan
            description = np.nan
        # Get information on the company's geography (lat/long) from Robinhood and enhance with Geocoding, if exists
        try:
            country = r.stocks.find_instrument_data(stock)[0]['country']
            location = geolocator.geocode(full_location, timeout=20)
            latitude = location.latitude
            longitude = location.longitude
        except:
            location = np.nan
            latitude = np.nan
            longitude = np.nan
        # Get information on the company's beta from Yahoo, if it exists
        try:
            beta = yf.Ticker(stock).info['beta']
        except:
            beta = np.nan
        # Get information from Robinhood on Buy/Hold/Sell ratings, if they exist
        try:
            ratings = r.stocks.get_ratings(stock, info=None)['summary']
            total_ratings = sum(ratings.values()) if ratings != None else np.nan
            buy_ratio = ratings['num_buy_ratings'] / total_ratings if ratings != None else np.nan
            hold_ratio = ratings['num_hold_ratings'] / total_ratings if ratings != None else np.nan
            sell_ratio = ratings['num_sell_ratings'] / total_ratings if ratings != None else np.nan
        except TypeError:
            buy_ratio = np.nan
            hold_ratio = np.nan
            sell_ratio = np.nan
        # Format values as a list/series to be added to the final df
        data_list = [company, ceo, country, state, city, latitude, longitude, market_cap, average_volume,
                     shares_outstanding, pe_ratio, pb_ratio, dividend_yield, beta, sector, industry, buy_ratio,
                     hold_ratio, sell_ratio, description]
        # Add the row directly
        stock_info_df.loc[len(stock_info_df)] = data_list

    # Convert country code to country name
    stock_info_df['Country'] = stock_info_df.apply(country_flag, axis=1)

    # Update data types
    stock_info_df['Market_Cap (Billions)'] = stock_info_df['Market_Cap (Billions)'].astype(float)
    stock_info_df['Avg_Volume (Millions)'] = stock_info_df['Avg_Volume (Millions)'].astype(float)
    stock_info_df['Beta'] = stock_info_df['Beta'].astype(float)
    stock_info_df['PE_Ratio'] = stock_info_df['PE_Ratio'].astype(float)
    stock_info_df['PB_Ratio'] = stock_info_df['PB_Ratio'].astype(float)
    stock_info_df['Buy_Ratio'] = stock_info_df['Buy_Ratio'].astype(float)
    stock_info_df['Hold_Ratio'] = stock_info_df['Hold_Ratio'].astype(float)
    stock_info_df['Sell_Ratio'] = stock_info_df['Sell_Ratio'].astype(float)

    # Update format
    stock_info_df['Market_Cap (Billions)'] = round(stock_info_df['Market_Cap (Billions)'] / 1000000000, 1)
    stock_info_df['Avg_Volume (Millions)'] = round(stock_info_df['Avg_Volume (Millions)'] / 1000000, 1)
    stock_info_df['Beta'] = round(stock_info_df['Beta'],2)
    stock_info_df['Shares_Outstanding'] = round(stock_info_df['Shares_Outstanding'].astype(float),2)
    stock_info_df['PE_Ratio'] = round(stock_info_df['PE_Ratio'], 2)
    stock_info_df['PB_Ratio'] = round(stock_info_df['PB_Ratio'], 2)
    stock_info_df['Buy_Ratio'] = round(stock_info_df['Buy_Ratio'], 2)
    stock_info_df['Hold_Ratio'] = round(stock_info_df['Hold_Ratio'], 2)
    stock_info_df['Sell_Ratio'] = round(stock_info_df['Sell_Ratio'], 2)

    # Rename columns
    stock_info_df.rename(columns={'Market_Cap (Billions)':'Market_Cap',
                                  'Avg_Volume (Millions)': 'Avg_Volume'}, inplace=True)

    # Save the data file
    stock_info_df.to_csv(stock_info_csv_path)

if __name__ == '__main__':
    # Resolve paths relative to the current script's directory
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(scripts_dir)
    config_file = os.path.join(app_dir, 'config', 'config.ini')  # Adjust folder name if needed
    stock_dictionary_file = os.path.join(app_dir, 'data', 'stock_dictionary.json')

    # Output file paths
    stocks_csv_path = os.path.join(app_dir, 'data', 'stocks.csv')
    stock_info_csv_path = os.path.join(app_dir, 'data', 'stock_info.csv')
    daily_stocks_csv_path = os.path.join(app_dir, 'data', 'daily_stocks.csv')

    print("BEGINNING PORTFOLIO ANALYSIS")

    # Step 1: Load credentials
    username, email, password = load_robinhood_credentials(config_file)
    print(f"\nRobinhood credentials have been loaded for username ({username})")

    # Step 2: Login to Robinhood
    login_to_robinhood(username, password)
    print("\nSuccessfully logged into Robinhood.")

    # Step 3: Load stock dictionary
    stock_dictionary = load_stock_dictionary(stock_dictionary_file)
    print("\nPersonal stock dictionary has been loaded\n")

    # Step 4: Call the portfolio analysis functions
    create_stocks_csv(stock_dictionary, stocks_csv_path)
    print("\nStock summary file has been created and saved to data/stocks.csv\n")
    create_stock_info_csv(stock_dictionary, stock_info_csv_path)
    print("\nStock info file has been created and saved to data/stock_info.csv\n")
    create_daily_stocks_csv(stock_dictionary, daily_stocks_csv_path)
    print("\nDaily stock file has been created and saved to data/daily_stocks.csv\n")

    print("PORTFOLIO ANALYSIS COMPLETED")