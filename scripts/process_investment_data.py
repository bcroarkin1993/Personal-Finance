import json
import time
import argparse
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, date, timedelta
from pathlib import Path

# ----------------- CONFIGURATION ----------------- #

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / 'data'

STOCK_DICT_PATH = DATA_DIR / 'stock_dictionary.json'
STOCKS_CSV_PATH = DATA_DIR / 'stocks.csv'
DAILY_STOCKS_CSV_PATH = DATA_DIR / 'daily_stocks.csv'
STOCK_INFO_CSV_PATH = DATA_DIR / 'stock_info.csv'

# Delay between individual yfinance API calls (seconds).
# Yahoo Finance rate-limits aggressively; 0.5s gives ~120 req/min which is safe.
API_DELAY = 0.5

# ----------------- HELPER FUNCTIONS ----------------- #

def load_stock_dictionary(file_path):
    if not file_path.exists():
        raise FileNotFoundError(f"Stock dictionary not found at {file_path}")
    with open(file_path, 'r') as f:
        return json.load(f)


def categorize_market_cap(market_cap_b):
    if pd.isna(market_cap_b) or market_cap_b <= 0: return "Unknown"
    if market_cap_b >= 200: return "Mega"
    elif 10 <= market_cap_b < 200: return "Large"
    elif 2 <= market_cap_b < 10: return "Medium"
    elif 0.3 <= market_cap_b < 2: return "Small"
    elif 0.05 <= market_cap_b < 0.3: return "Micro"
    else: return "Nano"


def _replay_transactions(details):
    """
    Pure Python: replay buy/sell history to get (total_quantity, total_cost).
    No API calls. Returns (quantity, cost).
    """
    total_quantity = 0.0
    total_cost = 0.0
    for txn in details.get("purchase_history", []):
        qty = float(txn["quantity"])
        price = float(txn["share_price"])
        if txn["buy_sell"] == "buy":
            total_cost += qty * price
            total_quantity += qty
        elif txn["buy_sell"] == "sell":
            if total_quantity > 0:
                avg_cost_at_sale = total_cost / total_quantity
                total_cost -= qty * avg_cost_at_sale
            total_quantity -= qty
    return total_quantity, total_cost


def _batch_fetch_prices(tickers):
    """
    Fetch latest close prices for a list of tickers in a single yf.download() call.
    Returns a dict: {ticker: price}.  Missing tickers default to 0.
    """
    prices = {t: 0.0 for t in tickers}
    if not tickers:
        return prices
    try:
        raw = yf.download(tickers, period="5d", progress=False, auto_adjust=True)
        if raw.empty:
            return prices
        close = raw["Close"] if "Close" in raw.columns else pd.DataFrame()
        if isinstance(close, pd.Series):
            # Single ticker came back as a Series
            val = close.dropna()
            if not val.empty and len(tickers) == 1:
                prices[tickers[0]] = float(val.iloc[-1])
        elif isinstance(close, pd.DataFrame):
            for ticker in tickers:
                if ticker in close.columns:
                    series = close[ticker].dropna()
                    if not series.empty:
                        prices[ticker] = float(series.iloc[-1])
    except Exception as e:
        print(f"     Batch price fetch failed ({e}). Individual fallbacks will be used.")
    return prices


# ----------------- CORE LOGIC ----------------- #

def build_summary_dataframe(stock_dictionary):
    """
    Phase 1 (no API): Replay all transactions to identify active positions.
    Phase 2 (single batch call): Fetch live prices for active tickers only.
    Phase 3 (rate-limited loop): Fetch lightweight metadata (52wk, pct_change).
    """
    print("   > Building Current Holdings Snapshot...")

    # --- Phase 1: Transaction replay (zero API calls) ---
    active_positions = {}
    for ticker, details in stock_dictionary.items():
        total_quantity, total_cost = _replay_transactions(details)
        if total_quantity > 0.001:
            active_positions[ticker] = {
                "total_quantity": total_quantity,
                "total_cost": total_cost,
                "company_name": details.get("stock_name", ticker),
            }

    if not active_positions:
        print("     No active positions found.")
        return pd.DataFrame()

    active_tickers = list(active_positions.keys())
    print(f"     Active positions found: {len(active_tickers)} tickers "
          f"({len(stock_dictionary) - len(active_tickers)} sold/inactive skipped)")

    # --- Phase 2: Batch live price fetch (one API call for all active tickers) ---
    print("     Fetching live prices (batch)...")
    live_prices = _batch_fetch_prices(active_tickers)

    # --- Phase 3: Per-ticker metadata with rate-limit-safe delays ---
    stock_data = []
    for ticker in active_tickers:
        pos = active_positions[ticker]
        total_quantity = pos["total_quantity"]
        total_cost = pos["total_cost"]
        company_name = pos["company_name"]
        current_price = live_prices.get(ticker, 0)

        high_52 = 0.0
        low_52 = 0.0
        pct_change = 0.0

        try:
            time.sleep(API_DELAY)
            stock = yf.Ticker(ticker)

            # If batch price failed for this ticker, get it individually
            if current_price == 0:
                try:
                    current_price = stock.fast_info.get("last_price", 0) or 0
                except Exception:
                    current_price = stock.info.get("currentPrice", 0) or 0

            # Use fast_info for 52wk data (lightweight, avoids quoteSummary endpoint)
            try:
                fi = stock.fast_info
                high_52 = getattr(fi, "year_high", None) or 0
                low_52 = getattr(fi, "year_low", None) or 0
            except Exception:
                pass

            # pct_change needs full info — grab only what's needed
            try:
                full_info = stock.info
                company_name = full_info.get("longName", company_name)
                pct_change = (full_info.get("52WeekChange", 0) or 0) * 100
            except Exception:
                pass

        except Exception as e:
            print(f"     Metadata fetch failed for {ticker}: {e}")

        avg_cost = total_cost / total_quantity if total_quantity > 0 else 0
        market_value = total_quantity * current_price
        equity_change = market_value - total_cost

        stock_data.append([
            ticker, company_name, current_price, total_quantity, avg_cost,
            market_value, pct_change, equity_change, high_52, low_52, "Stock"
        ])

    cols = ["Stock", "Company", "Price", "Quantity", "Avg_Cost", "Market_Value",
            "Percent_Change", "Equity_Change", "52_Week_High", "52_Week_Low", "Asset_Type"]

    df = pd.DataFrame(stock_data, columns=cols)

    if not df.empty:
        total_mv = df["Market_Value"].sum()
        df["Portfolio_Diversity"] = round(df["Market_Value"] * 100 / total_mv, 2) if total_mv > 0 else 0
        df["Direction"] = np.where(df["Percent_Change"] > 0, 'Up', 'Down')
        for c in ["Price", "Quantity", "Avg_Cost", "Market_Value", "Equity_Change", "52_Week_High", "52_Week_Low"]:
            df[c] = df[c].round(2)
        return df.sort_values(by="Market_Value", ascending=False)

    return pd.DataFrame(columns=cols)


def create_daily_stock_table(stock_dictionary, csv_path, full_refresh=False):
    """
    Updates historical timeline incrementally.
    """
    print(f"   > Updating Historical Daily Data (Mode: {'FULL' if full_refresh else 'INCREMENTAL'})...")

    existing_df = pd.DataFrame()
    start_date = "2016-01-01"  # Default start for full refresh

    # 1. Load Existing Data
    if not full_refresh and csv_path.exists():
        try:
            existing_df = pd.read_csv(csv_path)
            if not existing_df.empty and "Date" in existing_df.columns:
                existing_df["Date"] = pd.to_datetime(existing_df["Date"])
                last_date = existing_df["Date"].max()
                start_date = last_date.strftime("%Y-%m-%d")
                print(f"     Found existing data. Fetching new data from {start_date}...")
        except Exception as e:
            print(f"     Error reading existing history ({e}). Switching to full refresh.")
            existing_df = pd.DataFrame()

    new_rows = []

    for ticker, details in stock_dictionary.items():
        try:
            time.sleep(API_DELAY)
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date)

            if hist.empty:
                continue

            hist.reset_index(inplace=True)
            hist["Date"] = hist["Date"].dt.tz_localize(None)

            # Transaction Replay Logic
            txns = []
            for t in details["purchase_history"]:
                d_str = t["date"]
                try:
                    d = pd.to_datetime(d_str).tz_localize(None)
                except Exception:
                    d = pd.to_datetime(d_str, format="%m/%d/%Y").tz_localize(None)
                txns.append({
                    'date': d,
                    'qty': float(t['quantity']),
                    'price': float(t['share_price']),
                    'type': t['buy_sell']
                })
            txns.sort(key=lambda x: x['date'])

            current_qty = 0.0
            current_cost_basis = 0.0
            txn_idx = 0
            stock_rows = []

            for _, row in hist.iterrows():
                market_date = row["Date"]
                close_price = row["Close"]

                while txn_idx < len(txns) and txns[txn_idx]['date'] <= market_date:
                    t = txns[txn_idx]
                    if t['type'] == 'buy':
                        current_cost_basis += (t['qty'] * t['price'])
                        current_qty += t['qty']
                    elif t['type'] == 'sell':
                        if current_qty > 0:
                            avg = current_cost_basis / current_qty
                            current_cost_basis -= (t['qty'] * avg)
                        current_qty -= t['qty']
                    txn_idx += 1

                if current_qty > 0.001:
                    avg_cost = current_cost_basis / current_qty
                    market_val = current_qty * close_price
                    stock_rows.append({
                        "Date": market_date,
                        "Close": close_price,
                        "Stock": ticker,
                        "Shares_Held": current_qty,
                        "Avg_Cost": avg_cost,
                        "Equity": current_cost_basis,
                        "Market_Value": market_val,
                        "Total_Profit": market_val - current_cost_basis
                    })

            new_rows.extend(stock_rows)

        except Exception as e:
            print(f"Error processing history for {ticker}: {e}")

    new_df = pd.DataFrame(new_rows)

    if not existing_df.empty:
        if new_df.empty:
            return existing_df

        combined = pd.concat([existing_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Date", "Stock"], keep="last")
        combined = combined.sort_values(by=["Stock", "Date"])
        combined["Daily_Profit"] = combined.groupby("Stock")["Total_Profit"].diff().fillna(0)
        combined["Daily_Pct_Profit"] = combined.groupby("Stock")["Close"].pct_change().fillna(0) * 100
        return combined
    else:
        if not new_df.empty:
            new_df = new_df.sort_values(by=["Stock", "Date"])
            new_df["Daily_Profit"] = new_df.groupby("Stock")["Total_Profit"].diff().fillna(0)
            new_df["Daily_Pct_Profit"] = new_df.groupby("Stock")["Close"].pct_change().fillna(0) * 100
        return new_df


def create_stock_info_table(stock_dict, csv_path, full_refresh=False):
    """
    Updates fundamentals. Fetches data for all tickers (owned + watchlist).
    Preserves existing data for any ticker whose fetch fails.
    """
    print("   > Updating Fundamentals...")

    existing_df = pd.DataFrame()
    if not full_refresh and csv_path.exists():
        try:
            existing_df = pd.read_csv(csv_path)
        except Exception:
            pass

    tickers_to_fetch = list(stock_dict.keys())
    data_list = []

    for ticker in tickers_to_fetch:
        try:
            time.sleep(API_DELAY)
            stock = yf.Ticker(ticker)
            info = stock.info

            def get(key, default=0):
                return info.get(key, default)

            row = {
                "Stock": ticker,
                "Company": get("longName", ticker),
                "CEO": (get("companyOfficers", [{}])[0].get("name", "N/A")
                        if get("companyOfficers") else "N/A"),
                "Country": get("country", "N/A"),
                "State": get("state", "N/A"),
                "City": get("city", "N/A"),
                "Sector": get("sector", "N/A"),
                "Industry": get("industry", "N/A"),
                "Market Cap (B)": (get("marketCap", 0) or 0) / 1e9,
                "PE Ratio": get("trailingPE", 0),
                "PB Ratio": get("priceToBook", 0),
                "Beta": get("beta", 0),
                "Dividend Yield": get("dividendYield", 0),
                "Target Mean Price": get("targetMeanPrice", 0),
                "Description": get("longBusinessSummary", "N/A"),
                "Last Updated": date.today(),
                "Audit Risk": get("auditRisk", 5),
                "Board Risk": get("boardRisk", 5),
                "Compensation Risk": get("compensationRisk", 5),
                "Shareholder Rights Risk": get("shareHolderRightsRisk", 5),
                "Overall Risk": get("overallRisk", 5),
            }

            # Also store the current price so Buying Opportunities page can use it
            try:
                row["Price"] = stock.fast_info.get("last_price", 0) or get("currentPrice", 0)
            except Exception:
                row["Price"] = get("currentPrice", 0)

            data_list.append(row)

        except Exception as e:
            print(f"Failed to fetch info for {ticker}: {e}")
            # Fall back to existing data so we don't lose it
            if not existing_df.empty and ticker in existing_df.get("Stock", pd.Series()).values:
                old_row = existing_df[existing_df["Stock"] == ticker].iloc[0].to_dict()
                data_list.append(old_row)

    return pd.DataFrame(data_list)


# ----------------- MAIN ----------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help="Force full refresh")
    args = parser.parse_args()

    print("--- INVESTMENT DATA UPDATE STARTED ---")

    if not STOCK_DICT_PATH.exists():
        print("CRITICAL: stock_dictionary.json missing.")
        sys.exit(1)

    stock_dict = load_stock_dictionary(STOCK_DICT_PATH)

    # 1. Stocks (Snapshot — only active positions)
    stocks_df = build_summary_dataframe(stock_dict)
    if not stocks_df.empty:
        stocks_df.to_csv(STOCKS_CSV_PATH, index=False)
        print(f"   > Saved stocks.csv ({len(stocks_df)} rows)")
    else:
        print("   > Warning: stocks.csv empty. Skipping save to preserve data.")

    # 2. Daily History (Incremental)
    daily_df = create_daily_stock_table(stock_dict, DAILY_STOCKS_CSV_PATH, args.full)
    if not daily_df.empty:
        daily_df.to_csv(DAILY_STOCKS_CSV_PATH, index=False)
        print(f"   > Saved daily_stocks.csv ({len(daily_df)} rows)")
    else:
        print("   > Warning: daily_stocks.csv result empty. Skipping save.")

    # 3. Info (Fundamentals)
    info_df = create_stock_info_table(stock_dict, STOCK_INFO_CSV_PATH, args.full)
    if not info_df.empty:
        info_df.to_csv(STOCK_INFO_CSV_PATH, index=False)
        print(f"   > Saved stock_info.csv ({len(info_df)} rows)")

    print("--- UPDATE COMPLETE ---")
