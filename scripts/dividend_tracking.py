import pandas as pd
from datetime import datetime, timedelta


def calculate_dividends(holdings, dividends_data):
    """
    Calculate projected and paid dividends based on holdings and dividend data.

    Parameters:
        holdings (list of dict): List of stocks with holdings details.
        dividends_data (pd.DataFrame): Dividend tracker with frequency and yield.

    Returns:
        pd.DataFrame: Updated dividends data.
    """
    updated_data = []

    for stock in holdings:
        ticker = stock["ticker"]
        shares = stock["shares"]
        dividend_info = dividends_data[dividends_data["Ticker"] == ticker]

        if not dividend_info.empty:
            yield_percent = dividend_info["Dividend Yield (%)"].values[0]
            frequency = dividend_info["Frequency"].values[0]
            last_payment = dividend_info["Last Payment Date"].values[0]

            # Calculate projected dividends
            yearly_dividend = shares * (yield_percent / 100)
            projected = yearly_dividend / (12 if frequency == "Monthly" else 4 if frequency == "Quarterly" else 1)

            updated_data.append({
                "Ticker": ticker,
                "Dividend Yield (%)": yield_percent,
                "Frequency": frequency,
                "Last Payment Date": last_payment,
                "Amount Paid": stock.get("amount_paid", 0),
                "Projected Dividends": round(projected, 2)
            })

    return pd.DataFrame(updated_data)


# Example usage
holdings = [
    {"ticker": "AAPL", "shares": 50},
    {"ticker": "O", "shares": 200},
    {"ticker": "JNJ", "shares": 100}
]

dividends_tracker = pd.DataFrame({
    "Ticker": ["AAPL", "O", "JNJ"],
    "Dividend Yield (%)": [0.55, 5.25, 2.8],
    "Frequency": ["Quarterly", "Monthly", "Quarterly"],
    "Last Payment Date": ["2024-12-01", "2024-12-01", "2024-11-15"],
    "Amount Paid": [2.30, 1.00, 10.00],
    "Projected Dividends": [0, 0, 0]
})

updated_tracker = calculate_dividends(holdings, dividends_tracker)
print(updated_tracker)