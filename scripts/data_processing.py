import json
import numpy as np
import sys
from pathlib import Path
from typing import Dict, Any
import pandas as pd
import streamlit as st
import yfinance as yf

# ----- Project root & paths -----

PROJECT_ROOT = Path(__file__).resolve().parent.parent  # personal_finance
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.config import RUN_MODE  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data"


# ----- Helpers -----

def normalize_basic_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to snake_case style by:
    - stripping whitespace
    - replacing spaces with underscores
    - lowercasing

    This is applied to generic CSVs (stocks, daily_stocks, etc.)
    where we don't need a very strict mapping.
    """
    df = df.copy()
    df.columns = [
        col.strip().replace(" ", "_").lower()
        for col in df.columns
    ]
    return df


# ----- Column mappings for stock_info.csv -----

# Raw CSV column name -> internal snake_case name
STOCK_INFO_COLUMN_MAP = {
    "Stock": "stock",
    "Company": "company",
    "CEO": "ceo",
    "Country": "country",
    "State": "state",
    "City": "city",
    "Market Cap (B)": "market_cap",
    "Enterprise Value (B)": "enterprise_value",
    "EBITDA (B)": "ebitda",
    "Revenue (B)": "revenue",
    "Profit Margins": "profit_margins",
    "Operating Margins": "operating_margins",
    "Return On Assets": "return_on_assets",
    "Return On Equity": "return_on_equity",
    "Debt To Equity": "debt_to_equity",
    "Free Cashflow (B)": "free_cashflow",
    "Avg Volume (M)": "avg_volume",
    "Shares Outstanding (B)": "shares_outstanding",
    "Short Interest": "short_interest",
    "Institutional Holdings": "institutional_holdings",
    "PE Ratio": "pe_ratio",
    "PB Ratio": "pb_ratio",
    "Dividend Yield": "dividend_yield",
    "Payout Ratio": "payout_ratio",
    "Dividend Ex Date": "dividend_ex_date",
    "Beta": "beta",
    "Sector": "sector",
    "Industry": "industry",
    "Audit Risk": "audit_risk",
    "Board Risk": "board_risk",
    "Compensation Risk": "compensation_risk",
    "Shareholder Rights Risk": "shareholder_rights_risk",
    "Overall Risk": "overall_risk",
    "Target High Price": "target_high_price",
    "Target Low Price": "target_low_price",
    "Target Mean Price": "target_mean_price",
    "Target Median Price": "target_median_price",
    "Recommendation Mean": "recommendation_mean",
    "Recommendation Key": "recommendation_key",
    "No Analysts": "no_analysts",
    "Description": "description",
    "Last Updated": "last_updated",
    "Is Owned": "is_owned",
    "Market_Cap_Category": "market_cap_category",
}

# Internal snake_case name -> pretty label for charts / tables
STOCK_INFO_DISPLAY_LABELS = {
    "stock": "Stock",
    "company": "Company",
    "ceo": "CEO",
    "country": "Country",
    "state": "State",
    "city": "City",
    "market_cap": "Market Cap (B)",
    "enterprise_value": "Enterprise Value (B)",
    "ebitda": "EBITDA (B)",
    "revenue": "Revenue (B)",
    "profit_margins": "Profit Margins",
    "operating_margins": "Operating Margins",
    "return_on_assets": "Return On Assets",
    "return_on_equity": "Return On Equity",
    "debt_to_equity": "Debt To Equity",
    "free_cashflow": "Free Cashflow (B)",
    "avg_volume": "Avg Volume (M)",
    "shares_outstanding": "Shares Outstanding (B)",
    "short_interest": "Short Interest",
    "institutional_holdings": "Institutional Holdings",
    "pe_ratio": "PE Ratio",
    "pb_ratio": "PB Ratio",
    "dividend_yield": "Dividend Yield",
    "payout_ratio": "Payout Ratio",
    "dividend_ex_date": "Dividend Ex Date",
    "beta": "Beta",
    "sector": "Sector",
    "industry": "Industry",
    "audit_risk": "Audit Risk",
    "board_risk": "Board Risk",
    "compensation_risk": "Compensation Risk",
    "shareholder_rights_risk": "Shareholder Rights Risk",
    "overall_risk": "Overall Risk",
    "target_high_price": "Target High Price",
    "target_low_price": "Target Low Price",
    "target_mean_price": "Target Mean Price",
    "target_median_price": "Target Median Price",
    "recommendation_mean": "Recommendation Mean",
    "recommendation_key": "Recommendation Key",
    "no_analysts": "No Analysts",
    "description": "Description",
    "last_updated": "Last Updated",
    "is_owned": "Is Owned",
    "market_cap_category": "Market Cap Category",
}


def normalize_stock_info_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename raw stock_info columns from the CSV to cleaner snake_case names
    for internal use, and drop unnamed index columns.
    """
    df = df.copy()

    # Drop any unnamed index-like columns that often come from CSVs
    unnamed_cols = [c for c in df.columns if c.startswith("Unnamed")]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)

    # Only rename columns that actually exist, to avoid KeyErrors
    rename_map = {
        raw: clean
        for raw, clean in STOCK_INFO_COLUMN_MAP.items()
        if raw in df.columns
    }

    df = df.rename(columns=rename_map)

    return df


# ----- Data loading function -----

@st.cache_data(show_spinner=False)
def load_main_data() -> Dict[str, Any]:
    """
    Loads the main data files into memory.

    Returns:
        dict: A dictionary containing the raw dataframes and JSON config.
    """
    if RUN_MODE == "testing":
        print(f"Project Root Dir: {PROJECT_ROOT}")
        print(f"Data Dir: {DATA_DIR}")

    # Basic CSVs: normalize to snake_case columns
    stocks = pd.read_csv(DATA_DIR / "stocks.csv")
    stocks = normalize_basic_columns(stocks)

    daily_stocks = pd.read_csv(DATA_DIR / "daily_stocks.csv")
    daily_stocks = normalize_basic_columns(daily_stocks)

    expenses = pd.read_csv(DATA_DIR / "expenses.csv")
    expenses = normalize_basic_columns(expenses)

    income = pd.read_csv(DATA_DIR / "income.csv")
    income = normalize_basic_columns(income)

    # Stock info: use specific mapping
    stock_info_raw = pd.read_csv(DATA_DIR / "stock_info.csv")
    stock_info = normalize_stock_info_columns(stock_info_raw)

    with (DATA_DIR / "stock_dictionary.json").open("r") as file:
        stock_dictionary = json.load(file)

    return {
        "stocks": stocks,
        "stock_info": stock_info,
        "daily_stocks": daily_stocks,
        "stock_dictionary": stock_dictionary,
        "expenses": expenses,
        "income": income,
    }


# ----- SCORING LOGIC -----

def calculate_buying_opportunity_scores(df: pd.DataFrame, portfolio_cash: float = 0) -> pd.DataFrame:
    """
    Applies the proprietary scoring algorithm to a dataframe of stocks.
    Expects columns: 'price', '52_week_high', 'portfolio_diversity', 'target_mean_price', risk cols.
    """
    if df.empty:
        return df

    df = df.copy()

    # 1. Fetch Market Context (VIX + SP500)
    # Note: In production, you might want to cache this specifically to avoid 2s delay
    try:
        vix_data = yf.Ticker("^VIX").history(period="5d")
        vix = vix_data["Close"].iloc[-1] if not vix_data.empty else 20

        sp500 = yf.Ticker("^GSPC").history(period="1mo")
        if not sp500.empty:
            sp500_perf = (sp500["Close"].iloc[-1] - sp500["Close"].iloc[0]) / sp500["Close"].iloc[0]
        else:
            sp500_perf = 0
    except Exception:
        vix = 20
        sp500_perf = 0

    # Market Sentiment Score (Higher VIX + Lower Market Perf = Higher Score)
    market_sentiment_score = (vix / 40) + (1 - sp500_perf)
    market_sentiment_score = np.clip(market_sentiment_score, 0, 1)

    # 2. Normalize Helper
    def normalize(series):
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val: return 0
        return (series - min_val) / (max_val - min_val)

    # 3. Component Scores

    # A: 52-Week Discount (New Logic: % off the high)
    # If High is 100 and Price is 80, val is 0.2. We cap max score at 50% discount.
    df["discount_pct"] = (df["52_week_high"] - df["price"]) / df["52_week_high"]
    df["score_52wk"] = (df["discount_pct"] / 0.50).clip(0, 1)
    # Handle NaNs or negative discounts (breakouts)
    df["score_52wk"] = df["score_52wk"].fillna(0)

    # B: Portfolio Diversity (Lower is better for buying more)
    # If it's 0 (new buy), score is 1. If it's high % (overweight), score is low.
    df["portfolio_diversity"] = pd.to_numeric(df["portfolio_diversity"], errors='coerce').fillna(0)
    df["score_diversity"] = 1 - (df["portfolio_diversity"] / 100).clip(0, 1)

    # C: Analyst Target Discount
    df["target_mean_price"] = pd.to_numeric(df["target_mean_price"], errors='coerce').fillna(df["price"])
    target_upside = (df["target_mean_price"] - df["price"]) / df["price"]
    df["score_target"] = target_upside.clip(0, 1)  # Cap at 100% upside

    # D: Risk Score (Inverted: High risk = Low score)
    # Assuming risk columns are 1 (Low) to 10 (High) or similar.
    # If columns missing, assume neutral.
    risk_cols = ["audit_risk", "board_risk", "compensation_risk", "shareholder_rights_risk"]
    for c in risk_cols:
        if c not in df.columns: df[c] = 5

    df["avg_risk"] = df[risk_cols].mean(axis=1)
    df["score_risk"] = 1 - (df["avg_risk"] / 10)  # Assuming 10 is max risk
    df["score_risk"] = df["score_risk"].clip(0, 1)

    # E: Cash Weight
    cash_bonus = min(portfolio_cash / 10000, 1.0)

    # 4. Final Weighted Calculation
    # Weights: 52wk(25%), Diversity(20%), Target(20%), Risk(15%), Sentiment(15%), Cash(5%)
    df["buy_score"] = (
                              (0.25 * df["score_52wk"]) +
                              (0.20 * df["score_diversity"]) +
                              (0.20 * df["score_target"]) +
                              (0.15 * df["score_risk"]) +
                              (0.15 * market_sentiment_score) +
                              (0.05 * cash_bonus)
                      ) * 100

    return df.sort_values("buy_score", ascending=False)

def preprocess_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preprocesses the raw dataframes.

    Args:
        raw_data (dict): A dictionary containing raw dataframes.

    Returns:
        dict: A dictionary containing processed dataframes.
    """
    stocks = raw_data["stocks"].copy()
    stock_info = raw_data["stock_info"].copy()
    daily_stocks = raw_data["daily_stocks"].copy()
    expenses = raw_data["expenses"].copy()
    income = raw_data["income"].copy()

    # ----- Stocks -----

    # Remove stocks that have been sold
    if "quantity" in stocks.columns:
        stocks = stocks[stocks["quantity"] > 0]

    # Add a Portfolio Diversity field to track how much a stock is of my total portfolio value
    if {"market_value", "quantity"}.issubset(stocks.columns):
        total_mv = stocks["market_value"].sum()
        if total_mv != 0:
            stocks["portfolio_diversity"] = (
                stocks["market_value"] * 100 / total_mv
            ).round(2)

    # Add a column to show whether this stock has been a winner or loser
    if "percent_change" in stocks.columns:
        stocks["direction"] = stocks["percent_change"].apply(
            lambda x: "Up" if x > 0 else "Down"
        )

    # ----- Stock info -----

    # Add a column to categorize companies by market cap (in billions)
    if "market_cap" in stock_info.columns:
        stock_info["cap_size"] = stock_info["market_cap"].apply(
            lambda x: "Small-Cap" if x < 2 else ("Mid-Cap" if x < 10 else "Large-Cap")
        )

    # ----- Daily stocks -----

    # Expect columns: stock, shares_held, avg_cost, close, date, etc.
    if {"shares_held", "avg_cost"}.issubset(daily_stocks.columns):
        daily_stocks["equity"] = daily_stocks["shares_held"] * daily_stocks["avg_cost"]

    if {"close", "shares_held"}.issubset(daily_stocks.columns):
        daily_stocks["market_value"] = daily_stocks["close"] * daily_stocks["shares_held"]

    if {"market_value", "equity"}.issubset(daily_stocks.columns):
        daily_stocks["total_profit"] = daily_stocks["market_value"] - daily_stocks["equity"]

    if RUN_MODE == "testing":
        print(f"Stocks DF: {stocks.head()}")
        print(f"Stock Info DF: {stock_info.head()}")

    # ----- Merges & lookup tables -----

    # Lookup: ticker -> company
    stock_names = None
    if {"stock", "company"}.issubset(stocks.columns):
        stock_names = stocks[["stock", "company"]].drop_duplicates()

    # Merge stocks with stock_info on ticker
    if "stock" in stocks.columns and "stock" in stock_info.columns:
        stocks_complete = pd.merge(stocks, stock_info, how="left", on="stock")
    else:
        # Fallback: if no 'stock' in stock_info, try company name
        stocks_complete = pd.merge(
            stocks,
            stock_info,
            how="left",
            on="company" if "company" in stock_info.columns else None,
        )

    # Invested amount = quantity * avg_cost
    if {"quantity", "avg_cost"}.issubset(stocks_complete.columns):
        stocks_complete["invested"] = stocks_complete["quantity"] * stocks_complete["avg_cost"]

    # Remove unnamed columns
    stocks_complete = stocks_complete.loc[
        :, ~stocks_complete.columns.str.contains(r"^unnamed", case=False)
    ]

    if RUN_MODE == "testing":
        print("STOCKS COMPLETE: \n", stocks_complete.head())
        print("STOCKS COMPLETE COLUMNS: \n", stocks_complete.columns)

    # Merge daily_stocks with company names
    if stock_names is not None and "stock" in daily_stocks.columns:
        daily_stocks_complete = pd.merge(daily_stocks, stock_names, on="stock", how="left")
    else:
        daily_stocks_complete = daily_stocks.copy()

    # Create datetime column
    if "date" in daily_stocks_complete.columns:
        daily_stocks_complete["datetime"] = pd.to_datetime(daily_stocks_complete["date"])

    if RUN_MODE == "testing":
        print("DAILY STOCKS COMPLETE: \n", daily_stocks_complete.head())

    # ----- Daily equity time series -----

    if {"date", "market_value", "equity", "total_profit"}.issubset(daily_stocks_complete.columns):
        daily_equity = (
            daily_stocks_complete.groupby(by=["date"])[
                ["market_value", "equity", "total_profit"]
            ]
            .sum()
            .reset_index()
        )

        daily_equity["date"] = pd.to_datetime(daily_equity["date"])
        daily_equity["daily_profit"] = daily_equity["total_profit"].diff().round(2)
        daily_equity = daily_equity.loc[
            :, ~daily_equity.columns.str.contains(r"^unnamed", case=False)
        ]
    else:
        daily_equity = pd.DataFrame()

    # ----- Today's stocks (most recent date) -----

    todays_stocks = pd.DataFrame()
    if "datetime" in daily_stocks_complete.columns:
        most_recent_date = daily_stocks_complete["datetime"].max()
        mask = daily_stocks_complete["datetime"] == most_recent_date

        if "shares_held" in daily_stocks_complete.columns:
            mask &= daily_stocks_complete["shares_held"] != 0

        if "company" in daily_stocks_complete.columns:
            mask &= daily_stocks_complete["company"].notna()
            mask &= daily_stocks_complete["company"] != "0"

        todays_stocks = daily_stocks_complete[mask].copy()

    if RUN_MODE == "testing":
        print("TODAY'S STOCKS: \n", todays_stocks.head())

    # ----- Daily gainers / losers -----

    daily_gainers = pd.DataFrame()
    daily_losers = pd.DataFrame()
    if {"company", "daily_profit", "daily_pct_profit"}.issubset(todays_stocks.columns):
        base = todays_stocks[["company", "daily_profit", "daily_pct_profit"]].reset_index(
            drop=True
        )

        daily_gainers = (
            base.sort_values("daily_profit", ascending=False).head(5)
        )
        daily_losers = (
            base.sort_values("daily_profit", ascending=True).head(5)
        )

        # Remove any negatives from gainers and positives from losers
        daily_gainers = daily_gainers[daily_gainers["daily_profit"] > 0]
        daily_losers = daily_losers[daily_losers["daily_profit"] < 0]

    if RUN_MODE == "testing":
        print("DAILY GAINERS: \n", daily_gainers.head())
        print("DAILY LOSERS: \n", daily_losers.head())

    # ----- BUYING OPPORTUNITIES LOGIC -----

    # 1. Re-Buying Opportunities (Stocks you already own)
    # We use stocks_complete because it has current price, 52w high, etc.
    rebuy_df = calculate_buying_opportunity_scores(stocks_complete,
                                                   portfolio_cash=5000)  # Replace 5000 with real cash var if available

    # 2. New Buying Opportunities (Watchlist)
    # Since you don't have a 'watchlist.csv' yet, we will just use
    # any stock in 'stock_info' that is NOT in 'stocks'
    owned_tickers = stocks["stock"].unique()
    watchlist_df = stock_info[~stock_info["stock"].isin(owned_tickers)].copy()

    # We need 'price' for the score. stock_info usually is static metadata.
    # For now, we return empty unless stock_info has live price data.
    # Assuming we might not have live price for watchlist yet:
    new_buy_df = pd.DataFrame()
    if "price" in watchlist_df.columns:
        # If you add a script to update watchlist prices, this works:
        new_buy_df = calculate_buying_opportunity_scores(watchlist_df)

    # ----- Sector / industry lookups -----

    stock_sector_industry = pd.DataFrame()
    if {"stock", "sector", "industry"}.issubset(stocks_complete.columns):
        stock_sector_industry = stocks_complete[["stock", "sector", "industry"]].drop_duplicates()

    if RUN_MODE == "testing":
        print("STOCK sector industry: \n", stock_sector_industry)

    # Merge industry/sector into today's stocks
    if not todays_stocks.empty and not stock_sector_industry.empty and "stock" in todays_stocks.columns:
        todays_stocks_complete = pd.merge(
            todays_stocks, stock_sector_industry, on="stock", how="left"
        )
    else:
        todays_stocks_complete = todays_stocks.copy()

    if RUN_MODE == "testing":
        print("TODAY STOCKS COMPLETE: \n", todays_stocks_complete)

    # ----- Market cap sizes -----

    cap_sizes = pd.DataFrame()
    if not todays_stocks.empty and {"company", "cap_size", "market_value"}.issubset(
        pd.concat([stock_info, todays_stocks], axis=1, join="inner").columns
    ):
        stock_caps = stock_info[["company", "cap_size"]]
        cap_sizes = pd.merge(
            todays_stocks,
            stock_caps,
            how="inner",
            on="company",
        )[["stock", "market_value", "cap_size"]]

    # ----- Formatting for display -----
    # NOTE: This converts numeric columns to strings – ideal for tables,
    # but not for further numeric calculations. Use the unformatted copies
    # (daily_stocks, daily_gainers, etc.) for plots.

    currency_cols = ["daily_profit", "market_value", "total_profit", "avg_cost", "equity"]
    pct_cols = ["daily_pct_profit"]

    for col in currency_cols:
        if col in daily_stocks_complete.columns:
            daily_stocks_complete[col] = daily_stocks_complete[col].apply(
                lambda x: "${:,.2f}".format(x)
            )

    for col in pct_cols:
        if col in daily_stocks_complete.columns:
            daily_stocks_complete[col] = daily_stocks_complete[col].apply(
                lambda x: "{:.2f}%".format(x)
            )

    for col in ["daily_profit"]:
        if col in daily_gainers.columns:
            daily_gainers[col] = daily_gainers[col].apply(
                lambda x: "${:,.2f}".format(x)
            )
        if col in daily_losers.columns:
            daily_losers[col] = daily_losers[col].apply(
                lambda x: "${:,.2f}".format(x)
            )

    for col in ["daily_pct_profit"]:
        if col in daily_gainers.columns:
            daily_gainers[col] = daily_gainers[col].apply(
                lambda x: "{:.2f}%".format(x)
            )
        if col in daily_losers.columns:
            daily_losers[col] = daily_losers[col].apply(
                lambda x: "{:.2f}%".format(x)
            )

    # ----- Sector & industry allocation -----

    sector_values = pd.DataFrame()
    if not todays_stocks_complete.empty and {"sector", "market_value"}.issubset(
        todays_stocks_complete.columns
    ):
        sector_values = (
            todays_stocks_complete.groupby(["sector"])[["market_value"]]
            .sum()
            .reset_index()
        )
        total = sector_values["market_value"].sum()
        if total != 0:
            sector_values["pct_of_total"] = sector_values["market_value"] / total
            sector_values["desired_pct"] = 1 / len(sector_values)
            sector_values["pct_deviation"] = (
                sector_values["desired_pct"] - sector_values["pct_of_total"]
            )
            sector_values = sector_values.sort_values(by="pct_deviation")

    if RUN_MODE == "testing":
        print("SECTOR VALUES: \n", sector_values)

    industry_values = pd.DataFrame()
    if not todays_stocks_complete.empty and {"industry", "market_value"}.issubset(
        todays_stocks_complete.columns
    ):
        industry_values = (
            todays_stocks_complete.groupby(["industry"])[["market_value"]]
            .sum()
            .reset_index()
        )
        total_ind = industry_values["market_value"].sum()
        if total_ind != 0:
            industry_values["pct_of_total"] = industry_values["market_value"] / total_ind
            industry_values["desired_pct"] = 1 / len(industry_values)
            industry_values["pct_deviation"] = (
                industry_values["desired_pct"] - industry_values["pct_of_total"]
            )
            industry_values = industry_values.sort_values(by="pct_deviation")

    if RUN_MODE == "testing":
        print("INDUSTRY VALUES: \n", industry_values)

    # ----- Return everything you might want in the app -----

    return {
        "stocks": stocks,
        "stock_info": stock_info,
        "stocks_complete": stocks_complete,
        "rebuying_opportunities": rebuy_df,
        "buying_opportunities": new_buy_df,
        "daily_stocks": daily_stocks,
        "daily_stocks_complete": daily_stocks_complete,
        "daily_equity": daily_equity,
        "todays_stocks": todays_stocks,
        "todays_stocks_complete": todays_stocks_complete,
        "daily_gainers": daily_gainers,
        "daily_losers": daily_losers,
        "sector_values": sector_values,
        "industry_values": industry_values,
        "cap_sizes": cap_sizes,
        "expenses": expenses,
        "income": income,
    }

# Cached loader to be used in Streamlit
@st.cache_data(show_spinner=False)
def load_and_preprocess_data() -> Dict[str, Any]:
    """
    Combines loading and preprocessing logic with caching.

    Returns:
        dict: A dictionary of processed dataframes.
    """
    raw_data = load_main_data()
    return preprocess_data(raw_data)

