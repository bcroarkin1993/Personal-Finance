import json
import numpy as np
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import streamlit as st
import yfinance as yf

# ----- Project root & paths -----

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.config import RUN_MODE

DATA_DIR = PROJECT_ROOT / "data"

# ----- SCHEMA DEFINITIONS (For Empty State) -----
# These ensure that if a file is missing, we return a DF with the right columns
# so the app doesn't crash on KeyErrors.
EMPTY_SCHEMAS = {
    "stocks": ["stock", "company", "price", "quantity", "avg_cost", "market_value", "equity_change", "percent_change"],
    "daily_stocks": ["date", "close", "stock", "shares_held", "market_value", "total_profit"],
    "stock_info": ["stock", "company", "sector", "industry", "market_cap", "pe_ratio", "beta"],
    "income": ["date", "category", "amount", "description"],
    "expenses": ["date", "category", "amount", "description"],
    "monthly_budget": ["date", "category", "budget_amount"]
}


def safe_read_csv(file_path: Path, schema_key: str) -> pd.DataFrame:
    """
    Reads a CSV safely. Returns an empty DataFrame with expected columns
    if file is missing or empty.
    """
    expected_cols = EMPTY_SCHEMAS.get(schema_key, [])

    if not file_path.exists():
        return pd.DataFrame(columns=expected_cols)

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return pd.DataFrame(columns=expected_cols)
        return df
    except Exception as e:
        print(f"Error reading {file_path.name}: {e}")
        return pd.DataFrame(columns=expected_cols)


# ----- Helpers -----

def normalize_basic_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
    return df


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


def normalize_stock_info_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    unnamed_cols = [c for c in df.columns if c.startswith("Unnamed")]
    if unnamed_cols:
        df = df.drop(columns=unnamed_cols)
    rename_map = {raw: clean for raw, clean in STOCK_INFO_COLUMN_MAP.items() if raw in df.columns}
    df = df.rename(columns=rename_map)
    return df


# ----- Data loading function -----

@st.cache_data(ttl=1800, show_spinner=False)
def load_main_data() -> Dict[str, Any]:
    if RUN_MODE == "testing":
        print(f"Project Root Dir: {PROJECT_ROOT}")
        print(f"Data Dir: {DATA_DIR}")

    # USE SAFE READ
    stocks = safe_read_csv(DATA_DIR / "stocks.csv", "stocks")
    stocks = normalize_basic_columns(stocks)

    daily_stocks = safe_read_csv(DATA_DIR / "daily_stocks.csv", "daily_stocks")
    daily_stocks = normalize_basic_columns(daily_stocks)

    expenses = safe_read_csv(DATA_DIR / "expenses.csv", "expenses")
    expenses = normalize_basic_columns(expenses)

    income = safe_read_csv(DATA_DIR / "income.csv", "income")
    income = normalize_basic_columns(income)

    monthly_budget = safe_read_csv(DATA_DIR / "monthly_budget.csv", "monthly_budget")
    monthly_budget = normalize_basic_columns(monthly_budget)

    stock_info_raw = safe_read_csv(DATA_DIR / "stock_info.csv", "stock_info")
    stock_info = normalize_stock_info_columns(stock_info_raw)

    stock_dictionary = {}
    if (DATA_DIR / "stock_dictionary.json").exists():
        try:
            with (DATA_DIR / "stock_dictionary.json").open("r") as file:
                stock_dictionary = json.load(file)
        except Exception:
            pass

    return {
        "stocks": stocks,
        "stock_info": stock_info,
        "daily_stocks": daily_stocks,
        "stock_dictionary": stock_dictionary,
        "expenses": expenses,
        "income": income,
        "monthly_budget": monthly_budget
    }


# ----- MARKET CONTEXT -----

@st.cache_data(ttl=3600, show_spinner=False)
def load_market_context() -> Dict[str, float]:
    """
    Fetches VIX and S&P 500 data from yfinance.
    Cached for 1 hour (ttl=3600) so repeated page loads don't hammer the API.
    Returns a dict with vix, sp500_1mo_perf (%), and market_sentiment_score (0-1).
    """
    try:
        vix_data = yf.Ticker("^VIX").history(period="5d")
        vix = float(vix_data["Close"].iloc[-1]) if not vix_data.empty else 20.0
        sp500 = yf.Ticker("^GSPC").history(period="1mo")
        sp500_perf = (
            (sp500["Close"].iloc[-1] - sp500["Close"].iloc[0]) / sp500["Close"].iloc[0]
            if not sp500.empty else 0.0
        )
    except Exception:
        vix = 20.0
        sp500_perf = 0.0

    sentiment = float(np.clip((vix / 40) + (1 - sp500_perf), 0, 1))
    return {
        "vix": round(vix, 2),
        "sp500_1mo_perf_pct": round(float(sp500_perf) * 100, 2),
        "market_sentiment_score": round(sentiment, 4),
    }


# ----- SCORING LOGIC -----

def calculate_buying_opportunity_scores(
    df: pd.DataFrame,
    portfolio_cash: float = 0,
    market_sentiment_score: Optional[float] = None,
    w_52wk: float = 0.25,
    w_diversity: float = 0.20,
    w_target: float = 0.20,
    w_risk: float = 0.15,
    w_sentiment: float = 0.15,
    w_cash: float = 0.05,
) -> pd.DataFrame:
    """
    Scores stocks on a 0-100 composite scale.

    Weights (w_*) must sum to 1.0. Market sentiment is a single shared score
    passed in from load_market_context() to avoid redundant API calls.
    If market_sentiment_score is None, it is fetched from load_market_context().
    """
    if df.empty:
        return df

    df = df.copy()

    required = ["price", "52_week_high", "52_week_low", "target_mean_price"]
    for r in required:
        if r not in df.columns:
            return pd.DataFrame()

    # Fetch market context only if not provided
    if market_sentiment_score is None:
        ctx = load_market_context()
        market_sentiment_score = ctx["market_sentiment_score"]

    # Coerce numerics
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["52_week_high"] = pd.to_numeric(df["52_week_high"], errors="coerce").fillna(df["price"])
    df["52_week_low"] = pd.to_numeric(df["52_week_low"], errors="coerce").fillna(df["price"])
    df["target_mean_price"] = pd.to_numeric(df["target_mean_price"], errors="coerce").fillna(df["price"])

    if "portfolio_diversity" not in df.columns:
        df["portfolio_diversity"] = 0
    df["portfolio_diversity"] = pd.to_numeric(df["portfolio_diversity"], errors="coerce").fillna(0)

    # Individual signal scores (each 0-1)
    df["discount_pct"] = (df["52_week_high"] - df["price"]) / df["52_week_high"].replace(0, 1)
    df["score_52wk"] = (df["discount_pct"] / 0.50).clip(0, 1).fillna(0)

    df["score_diversity"] = 1 - (df["portfolio_diversity"] / 100).clip(0, 1)

    target_upside = (df["target_mean_price"] - df["price"]) / df["price"].replace(0, 1)
    df["score_target"] = target_upside.clip(0, 1)

    risk_cols = ["audit_risk", "board_risk", "compensation_risk", "shareholder_rights_risk"]
    for c in risk_cols:
        if c not in df.columns:
            df[c] = 5
    df["avg_risk"] = df[risk_cols].mean(axis=1)
    df["score_risk"] = (1 - (df["avg_risk"] / 10)).clip(0, 1)

    # Market sentiment is the same for all rows — store for display
    df["score_sentiment"] = float(market_sentiment_score)

    cash_bonus = min(portfolio_cash / 10000, 1.0)
    df["score_cash"] = cash_bonus

    df["buy_score"] = (
        (w_52wk      * df["score_52wk"]) +
        (w_diversity  * df["score_diversity"]) +
        (w_target     * df["score_target"]) +
        (w_risk       * df["score_risk"]) +
        (w_sentiment  * df["score_sentiment"]) +
        (w_cash       * df["score_cash"])
    ) * 100

    return df.sort_values("buy_score", ascending=False)


def preprocess_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    stocks = raw_data["stocks"].copy()
    stock_info = raw_data["stock_info"].copy()
    daily_stocks = raw_data["daily_stocks"].copy()
    expenses = raw_data["expenses"].copy()
    income = raw_data["income"].copy()
    monthly_budget = raw_data.get("monthly_budget", pd.DataFrame()).copy()

    # --- SAFETY CHECKS ---
    # Return early if critical data is missing to avoid crashes
    if stocks.empty and daily_stocks.empty:
        return {
            "stocks": stocks, "daily_stocks": daily_stocks, "stock_info": stock_info,
            "expenses": expenses, "income": income, "monthly_budget": monthly_budget,
            "stock_dictionary": raw_data["stock_dictionary"],
            "stocks_complete": pd.DataFrame(), "daily_equity": pd.DataFrame(),
            "todays_stocks": pd.DataFrame(), "todays_stocks_complete": pd.DataFrame(),
            "daily_gainers": pd.DataFrame(), "daily_losers": pd.DataFrame(),
            "sector_values": pd.DataFrame(), "industry_values": pd.DataFrame(),
            "cap_sizes": pd.DataFrame(), "rebuying_opportunities": pd.DataFrame(),
            "buying_opportunities": pd.DataFrame()
        }

    # ----- Stocks Preprocessing -----
    if not stocks.empty and "quantity" in stocks.columns:
        stocks = stocks[stocks["quantity"] > 0]

    # ----- Merges -----
    stock_names = None
    if not stocks.empty and {"stock", "company"}.issubset(stocks.columns):
        stock_names = stocks[["stock", "company"]].drop_duplicates()

    if not stocks.empty and not stock_info.empty:
        stocks_complete = pd.merge(stocks, stock_info, how="left", on="stock")
    else:
        stocks_complete = stocks.copy()

    # Add invested column if missing
    if "invested" not in stocks_complete.columns and "quantity" in stocks_complete.columns:
        avg_cost_col = stocks_complete["avg_cost"] if "avg_cost" in stocks_complete.columns else 0
        stocks_complete["invested"] = stocks_complete["quantity"] * avg_cost_col

    # ----- Daily Stocks -----
    daily_stocks_complete = daily_stocks.copy()
    if stock_names is not None and not daily_stocks.empty and "stock" in daily_stocks.columns:
        daily_stocks_complete = pd.merge(daily_stocks, stock_names, on="stock", how="left")

    if "date" in daily_stocks_complete.columns:
        daily_stocks_complete["datetime"] = pd.to_datetime(daily_stocks_complete["date"])

    # ----- Daily Equity -----
    daily_equity = pd.DataFrame()
    if not daily_stocks_complete.empty and {"date", "market_value", "equity"}.issubset(daily_stocks_complete.columns):
        daily_equity = daily_stocks_complete.groupby("date")[["market_value", "equity"]].sum().reset_index()
        daily_equity["total_profit"] = daily_equity["market_value"] - daily_equity["equity"]

    # ----- Today's Stocks -----
    todays_stocks = pd.DataFrame()
    todays_stocks_complete = pd.DataFrame()
    if not daily_stocks_complete.empty and "datetime" in daily_stocks_complete.columns:
        max_date = daily_stocks_complete["datetime"].max()
        todays_stocks = daily_stocks_complete[daily_stocks_complete["datetime"] == max_date].copy()
        # Enrich with fundamentals (sector, industry, pe_ratio, etc.) from stocks_complete
        if not todays_stocks.empty and not stocks_complete.empty and "stock" in todays_stocks.columns:
            fund_cols = [c for c in stocks_complete.columns if c not in todays_stocks.columns] + ["stock"]
            todays_stocks_complete = pd.merge(todays_stocks, stocks_complete[fund_cols], on="stock", how="left")
        else:
            todays_stocks_complete = todays_stocks.copy()

    # ----- Market Context (fetched once, cached 1hr, shared with scoring) -----
    market_ctx = load_market_context()
    mss = market_ctx["market_sentiment_score"]

    # ----- Buying Ops -----
    rebuy_df = pd.DataFrame()
    new_buy_df = pd.DataFrame()

    if not stocks_complete.empty and "price" in stocks_complete.columns:
        rebuy_df = calculate_buying_opportunity_scores(
            stocks_complete, portfolio_cash=5000, market_sentiment_score=mss
        )

    # Watchlist logic (requires a 'price' column in stock_info — added by process_investment_data)
    if not stock_info.empty and not stocks.empty:
        owned = stocks["stock"].unique() if "stock" in stocks.columns else []
        watchlist = stock_info[~stock_info["stock"].isin(owned)].copy()
        if "price" in watchlist.columns:
            new_buy_df = calculate_buying_opportunity_scores(
                watchlist, market_sentiment_score=mss
            )

    # ----- Aggregates -----
    sector_values = pd.DataFrame()
    industry_values = pd.DataFrame()
    if not stocks_complete.empty:
        if "sector" in stocks_complete.columns:
            sector_values = stocks_complete.groupby("sector")["market_value"].sum().reset_index()
        if "industry" in stocks_complete.columns:
            industry_values = stocks_complete.groupby("industry")["market_value"].sum().reset_index()

    return {
        "stocks": stocks,
        "daily_stocks": daily_stocks,
        "stock_info": stock_info,
        "expenses": expenses,
        "income": income,
        "monthly_budget": monthly_budget,
        "stock_dictionary": raw_data["stock_dictionary"],
        "stocks_complete": stocks_complete,
        "daily_stocks_complete": daily_stocks_complete,
        "daily_equity": daily_equity,
        "todays_stocks": todays_stocks,
        "todays_stocks_complete": todays_stocks_complete,
        "daily_gainers": pd.DataFrame(),  # Simplified for safe loading
        "daily_losers": pd.DataFrame(),
        "sector_values": sector_values,
        "industry_values": industry_values,
        "cap_sizes": pd.DataFrame(),
        "rebuying_opportunities": rebuy_df,
        "buying_opportunities": new_buy_df,
        "market_context": market_ctx,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def load_and_preprocess_data() -> Dict[str, Any]:
    raw_data = load_main_data()
    return preprocess_data(raw_data)