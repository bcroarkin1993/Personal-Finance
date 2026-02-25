import json
import time
import argparse
import sys
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
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
# 1.5s ≈ 40 req/min, which stays within Yahoo Finance's rate limits.
API_DELAY = 1.5

# Fundamentals (sector, PE, target price, etc.) are stable day-to-day.
# Skip re-fetching any ticker whose stock_info row is younger than this threshold.
FUNDAMENTALS_STALE_HOURS = 23

# Circuit breaker: if this many consecutive tickers fail in one phase, stop
# that phase early and report the issue rather than hanging for minutes.
CIRCUIT_BREAKER_THRESHOLD = 5

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
            sell_qty = min(qty, max(total_quantity, 0.0))
            if total_quantity > 0 and sell_qty > 0:
                avg_cost_at_sale = total_cost / total_quantity
                total_cost -= sell_qty * avg_cost_at_sale
            total_quantity -= sell_qty
    return total_quantity, total_cost


def _check_api_available(test_ticker="MSFT") -> bool:
    """
    Quick pre-flight check: try to fetch 2 days of history for one ticker.
    Returns True if Yahoo Finance is responding, False if rate-limited.
    Exits fast so we don't waste time grinding through 92 tickers when blocked.
    """
    print(f"   Pre-flight: checking Yahoo Finance connectivity ({test_ticker})...")
    try:
        hist = yf.Ticker(test_ticker).history(period="2d")
        if hist.empty:
            print("   Pre-flight FAILED: got empty response — Yahoo Finance may be rate-limiting.")
            return False
        print(f"   Pre-flight OK: {test_ticker} @ ${hist['Close'].iloc[-1]:.2f}")
        return True
    except Exception as e:
        print(f"   Pre-flight FAILED: {e}")
        return False


def _safe_ticker_info(ticker: str, retries: int = 2) -> dict:
    """
    Fetch yf.Ticker(ticker).info with retries on JSONDecodeError and 429 rate limits.
    Uses short backoff (2s / 4s) — enough for transient errors but won't cause
    multi-hour hangs when Yahoo Finance has fully blocked the session.
    Returns {} on total failure so callers can fall back to cached data.
    """
    for attempt in range(retries + 1):
        try:
            return yf.Ticker(ticker).info
        except Exception as e:
            err = str(e).lower()
            is_transient = (
                "429" in err
                or "too many" in err
                or "json" in err
                or isinstance(e, (ValueError, json.JSONDecodeError))
            )
            if is_transient and attempt < retries:
                wait = 2.0 * (2 ** attempt)   # 2s → 4s
                print(f"     [{ticker}] rate limited — waiting {wait:.0f}s "
                      f"(attempt {attempt + 1}/{retries})...")
                time.sleep(wait)
            else:
                print(f"     [{ticker}] info fetch failed: {e}")
                return {}
    return {}


# ----------------- CORE LOGIC ----------------- #

def create_daily_stock_table(stock_dictionary, csv_path, full_refresh=False):
    """
    Fetches price history for every ticker and replays transactions to produce
    per-day holdings, cost basis, market value, and profit rows.

    This is the primary data-fetching phase. Prices for stocks.csv are derived
    from the latest rows here rather than making a separate round of API calls.

    Incremental mode resumes from the last date already on disk; full refresh
    starts from 2016-01-01. A circuit breaker stops the fetch early if Yahoo
    Finance appears to be rate-limiting the entire session.
    """
    print(f"   > Updating Historical Daily Data (Mode: {'FULL' if full_refresh else 'INCREMENTAL'})...")

    existing_df = pd.DataFrame()
    start_date = "2016-01-01"

    if not full_refresh and csv_path.exists():
        try:
            existing_df = pd.read_csv(csv_path)
            if not existing_df.empty and "Date" in existing_df.columns:
                existing_df["Date"] = pd.to_datetime(existing_df["Date"])
                if "Shares_Held" in existing_df.columns:
                    existing_df = existing_df[existing_df["Shares_Held"] > 0]
                last_date = existing_df["Date"].max()
                start_date = last_date.strftime("%Y-%m-%d")
                print(f"     Existing data found. Fetching from {start_date} onward...")
        except Exception as e:
            print(f"     Error reading existing history ({e}). Falling back to full refresh.")
            existing_df = pd.DataFrame()

    new_rows = []
    succeeded = 0
    failed_tickers = []
    consecutive_failures = 0

    for ticker, details in stock_dictionary.items():
        if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            remaining = list(stock_dictionary.keys())
            idx = remaining.index(ticker) if ticker in remaining else 0
            skipped = remaining[idx:]
            print(f"     Circuit breaker: {CIRCUIT_BREAKER_THRESHOLD} consecutive failures. "
                  f"Stopping history fetch early. Skipped: {skipped}")
            break

        try:
            time.sleep(API_DELAY)
            hist = yf.Ticker(ticker).history(start=start_date)

            if hist.empty:
                print(f"     [{ticker}] no price history returned")
                failed_tickers.append(ticker)
                consecutive_failures += 1
                continue

            consecutive_failures = 0  # reset on success

            hist.reset_index(inplace=True)
            hist["Date"] = hist["Date"].dt.tz_localize(None)

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
                        sell_qty = min(t['qty'], max(current_qty, 0.0))
                        if current_qty > 0 and sell_qty > 0:
                            avg = current_cost_basis / current_qty
                            current_cost_basis -= (sell_qty * avg)
                        current_qty -= sell_qty
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
            succeeded += 1

        except Exception as e:
            print(f"     [{ticker}] history fetch error: {e}")
            failed_tickers.append(ticker)
            consecutive_failures += 1

    total = len(stock_dictionary)
    print(f"     History: {succeeded}/{total} tickers OK"
          + (f" | Failed: {failed_tickers}" if failed_tickers else ""))

    new_df = pd.DataFrame(new_rows)

    if not existing_df.empty:
        if new_df.empty:
            print("     No new rows — returning existing data unchanged.")
            return existing_df
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Date", "Stock"], keep="last")
        combined = combined[combined["Shares_Held"] > 0]
        combined = combined.sort_values(by=["Stock", "Date"])
    else:
        if new_df.empty:
            return new_df
        combined = new_df.sort_values(by=["Stock", "Date"])

    # Forward-fill any active tickers that are missing the latest market date.
    # This happens when Yahoo Finance hasn't published a ticker's close yet —
    # without this, the portfolio total for "today" is understated by the
    # missing tickers' entire market value.
    latest_date = combined["Date"].max()
    tickers_on_latest = set(combined[combined["Date"] == latest_date]["Stock"])
    all_tickers = set(combined["Stock"].unique())
    missing_latest = all_tickers - tickers_on_latest
    if missing_latest:
        fill_rows = []
        for ticker in missing_latest:
            last_row = combined[combined["Stock"] == ticker].iloc[-1].copy()
            last_row["Date"] = latest_date
            last_row["Daily_Profit"] = 0.0
            last_row["Daily_Pct_Profit"] = 0.0
            fill_rows.append(last_row)
        fill_df = pd.DataFrame(fill_rows)
        combined = pd.concat([combined, fill_df], ignore_index=True)
        combined = combined.sort_values(by=["Stock", "Date"])
        print(f"     Forward-filled {len(missing_latest)} ticker(s) to {latest_date.date()}: "
              f"{sorted(missing_latest)}")

    combined["Daily_Profit"] = combined.groupby("Stock")["Total_Profit"].diff().fillna(0)
    combined["Daily_Pct_Profit"] = combined.groupby("Stock")["Close"].pct_change().fillna(0) * 100
    return combined


def _fetch_ticker_metadata(ticker: str, pos: dict, latest_prices: dict) -> dict:
    """
    Fetches 52-week range, company name, and pct_change for a single ticker.
    Designed to run inside a ThreadPoolExecutor worker — sleeps API_DELAY before
    making any network calls to keep per-thread request rate inside Yahoo's limits.
    Returns a flat dict of all columns needed for stocks.csv.
    Raises on unrecoverable failure so the caller can append a fallback row.
    """
    total_quantity = pos["total_quantity"]
    total_cost = pos["total_cost"]
    company_name = pos["company_name"]
    current_price = float(latest_prices.get(ticker, 0))

    high_52 = 0.0
    low_52 = 0.0
    pct_change = 0.0

    time.sleep(API_DELAY)
    stock = yf.Ticker(ticker)

    # 52wk range via fast_info (lightweight call)
    try:
        fi = stock.fast_info
        high_52 = getattr(fi, "year_high", None) or 0.0
        low_52 = getattr(fi, "year_low", None) or 0.0
        # Use fast_info price only if daily history gave us nothing
        if current_price == 0:
            current_price = float(
                getattr(fi, "last_price", None) or
                getattr(fi, "previous_close", None) or 0
            )
    except Exception:
        pass

    # Company name and 52-week change from full info
    try:
        info = _safe_ticker_info(ticker)
        company_name = info.get("longName", company_name)
        pct_change = (info.get("52WeekChange", 0) or 0) * 100
    except Exception:
        pass

    avg_cost = total_cost / total_quantity if total_quantity > 0 else 0
    market_value = total_quantity * current_price
    equity_change = market_value - total_cost

    return {
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "total_quantity": total_quantity,
        "avg_cost": avg_cost,
        "market_value": market_value,
        "pct_change": pct_change,
        "equity_change": equity_change,
        "high_52": high_52,
        "low_52": low_52,
    }


def build_summary_dataframe(stock_dictionary, daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the current-holdings snapshot (stocks.csv) by:
      1. Replaying transactions to find active positions (no API calls).
      2. Reading the most recent price from daily_df (the just-updated history)
         rather than making a separate round of price API calls.
      3. Fetching 52-week range and pct_change from fast_info / _safe_ticker_info
         with a circuit breaker.

    Deriving prices from daily_df eliminates the separate batch-download phase
    that previously caused session-level rate limit failures.
    """
    print("   > Building Current Holdings Snapshot...")

    # Phase 1: transaction replay
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
    print(f"     Active positions: {len(active_tickers)} tickers "
          f"({len(stock_dictionary) - len(active_tickers)} sold/inactive skipped)")

    # Phase 2: derive latest price from daily_df (zero extra API calls)
    latest_prices = {}
    if not daily_df.empty and "Stock" in daily_df.columns and "Close" in daily_df.columns:
        daily_df_copy = daily_df.copy()
        daily_df_copy["Date"] = pd.to_datetime(daily_df_copy["Date"])
        latest = (
            daily_df_copy.sort_values("Date")
            .groupby("Stock")
            .last()
            .reset_index()[["Stock", "Close"]]
        )
        latest_prices = dict(zip(latest["Stock"], latest["Close"]))
        found = sum(1 for t in active_tickers if latest_prices.get(t, 0) > 0)
        print(f"     Prices sourced from history: {found}/{len(active_tickers)}")

    # Phase 3: per-ticker metadata (52wk range, pct_change) — parallel fetch
    # 3 workers × API_DELAY sleep per worker ≈ 3× throughput vs sequential.
    # Submissions are staggered 0.5s apart so the first batch of workers doesn't
    # burst all three API calls at the same instant.
    print(f"     Fetching metadata for {len(active_tickers)} tickers "
          f"(parallel, max_workers=3)...")
    stock_data = []
    total_failures = 0

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for ticker in active_tickers:
            time.sleep(0.5)  # stagger submissions to prevent initial burst
            fut = executor.submit(
                _fetch_ticker_metadata, ticker, active_positions[ticker], latest_prices
            )
            futures[fut] = ticker

        for fut in as_completed(futures):
            ticker = futures[fut]
            try:
                r = fut.result()
                stock_data.append([
                    r["ticker"], r["company_name"], r["current_price"],
                    r["total_quantity"], r["avg_cost"], r["market_value"],
                    r["pct_change"], r["equity_change"], r["high_52"], r["low_52"],
                    "Stock"
                ])
            except Exception as e:
                print(f"     [{ticker}] metadata fetch failed: {e}")
                total_failures += 1
                # Zero-filled fallback so the ticker still appears in stocks.csv
                pos = active_positions[ticker]
                tq = pos["total_quantity"]
                tc = pos["total_cost"]
                cp = float(latest_prices.get(ticker, 0))
                stock_data.append([
                    ticker, pos["company_name"], cp, tq,
                    tc / tq if tq > 0 else 0,
                    tq * cp, 0.0, tq * cp - tc, 0.0, 0.0, "Stock"
                ])

    if total_failures >= CIRCUIT_BREAKER_THRESHOLD:
        print(f"     Warning: {total_failures} tickers failed metadata fetch — "
              f"Yahoo Finance may be rate-limiting. Prices from daily history "
              f"are still accurate; metadata (52W range, pct_change) may be stale.")

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


def create_stock_info_table(stock_dict, csv_path, full_refresh=False):
    """
    Fetches fundamentals (sector, PE, target price, etc.) for all tickers.

    Incremental mode skips any ticker whose Last Updated is within
    FUNDAMENTALS_STALE_HOURS — fundamentals don't change daily, so re-fetching
    them on every run is the primary driver of 429 rate limits.
    Falls back to existing data for any ticker whose fetch fails.
    A circuit breaker stops early if the entire session appears rate-limited.
    """
    print("   > Updating Fundamentals...")

    existing_df = pd.DataFrame()
    if not full_refresh and csv_path.exists():
        try:
            existing_df = pd.read_csv(csv_path)
        except Exception:
            pass

    tickers_to_fetch = list(stock_dict.keys())
    fresh_tickers = set()

    # Schema-migration guard: if new columns are missing, re-fetch everything
    # regardless of freshness so the new data gets written on the next incremental run.
    REQUIRED_COLS = {"52 Week High", "52 Week Low"}
    schema_outdated = not existing_df.empty and not REQUIRED_COLS.issubset(set(existing_df.columns))
    if schema_outdated:
        print(f"     stock_info.csv is missing new columns "
              f"({REQUIRED_COLS - set(existing_df.columns)}) — re-fetching all tickers.")

    # Skip tickers with fresh fundamentals in incremental mode
    if not full_refresh and not schema_outdated and not existing_df.empty and "Last Updated" in existing_df.columns:
        try:
            now = pd.Timestamp.now()
            ages_h = (
                (now - pd.to_datetime(existing_df["Last Updated"], errors="coerce"))
                .dt.total_seconds() / 3600
            )
            fresh_tickers = set(existing_df.loc[ages_h < FUNDAMENTALS_STALE_HOURS, "Stock"].tolist())
            tickers_to_fetch = [t for t in tickers_to_fetch if t not in fresh_tickers]
            if fresh_tickers:
                print(f"     Skipping {len(fresh_tickers)} tickers with fresh fundamentals "
                      f"(<{FUNDAMENTALS_STALE_HOURS}h old). Fetching {len(tickers_to_fetch)} stale...")
        except Exception as e:
            print(f"     Staleness check failed ({e}); fetching all tickers.")

    if not tickers_to_fetch:
        print("     All fundamentals are up to date — nothing to fetch.")
        return existing_df

    data_list = []
    succeeded = 0
    failed_tickers = []
    consecutive_failures = 0

    for ticker in tickers_to_fetch:
        if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            remaining = tickers_to_fetch[tickers_to_fetch.index(ticker):]
            print(f"     Circuit breaker: stopping fundamentals fetch after "
                  f"{CIRCUIT_BREAKER_THRESHOLD} consecutive failures. "
                  f"Preserving existing data for {len(remaining)} remaining tickers.")
            # Preserve existing rows for skipped tickers
            if not existing_df.empty and "Stock" in existing_df.columns:
                for t in remaining:
                    match = existing_df[existing_df["Stock"] == t]
                    if not match.empty:
                        data_list.append(match.iloc[0].to_dict())
            break

        try:
            time.sleep(API_DELAY)
            info = _safe_ticker_info(ticker)
            if not info:
                raise ValueError(f"Empty info for {ticker}")

            def get(key, default=0):
                return info.get(key, default)

            # Current price + 52W range from fast_info
            price = 0
            week_high_52 = 0
            week_low_52 = 0
            try:
                fi = yf.Ticker(ticker).fast_info
                price = float(
                    getattr(fi, "last_price", None) or
                    getattr(fi, "previous_close", None) or
                    get("currentPrice", 0)
                )
                week_high_52 = getattr(fi, "year_high", None) or 0
                week_low_52 = getattr(fi, "year_low", None) or 0
            except Exception:
                price = float(get("currentPrice", 0))

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
                "Price": price,
                "52 Week High": week_high_52,
                "52 Week Low":  week_low_52,
            }

            data_list.append(row)
            succeeded += 1
            consecutive_failures = 0

        except Exception as e:
            print(f"     [{ticker}] fundamentals fetch failed: {e}")
            failed_tickers.append(ticker)
            consecutive_failures += 1
            # Preserve existing row
            if not existing_df.empty and "Stock" in existing_df.columns:
                match = existing_df[existing_df["Stock"] == ticker]
                if not match.empty:
                    data_list.append(match.iloc[0].to_dict())

    print(f"     Fundamentals: {succeeded}/{len(tickers_to_fetch)} fetched"
          + (f" | Failed: {failed_tickers}" if failed_tickers else "")
          + (f" | {len(fresh_tickers)} skipped (fresh)" if fresh_tickers else ""))

    new_df = pd.DataFrame(data_list)
    if not existing_df.empty and fresh_tickers:
        fresh_rows = existing_df[existing_df["Stock"].isin(fresh_tickers)]
        new_df = pd.concat([new_df, fresh_rows], ignore_index=True)
        new_df = new_df.drop_duplicates(subset=["Stock"], keep="first")

    return new_df


# ----------------- MAIN ----------------- #

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help="Force full refresh of all data")
    args = parser.parse_args()

    print("--- INVESTMENT DATA UPDATE STARTED ---")

    if not STOCK_DICT_PATH.exists():
        print("CRITICAL: stock_dictionary.json missing.")
        sys.exit(1)

    stock_dict = load_stock_dictionary(STOCK_DICT_PATH)
    print(f"   Loaded {len(stock_dict)} tickers from stock_dictionary.json")

    # Pre-flight: verify Yahoo Finance is accessible before grinding through 92 tickers
    if not _check_api_available():
        print("\nYahoo Finance is rate-limiting this session.")
        print("Wait 15–30 minutes and try again. Existing CSV data has been preserved.")
        sys.exit(1)

    # 1. Daily history — primary data fetch; prices for snapshot are derived from this
    daily_df = create_daily_stock_table(stock_dict, DAILY_STOCKS_CSV_PATH, args.full)
    if not daily_df.empty:
        daily_df.to_csv(DAILY_STOCKS_CSV_PATH, index=False)
        print(f"   > Saved daily_stocks.csv ({len(daily_df)} rows)")
    else:
        print("   > Warning: daily_stocks.csv result empty. Skipping save.")

    # 2. Holdings snapshot — prices come from daily_df, no extra API round
    stocks_df = build_summary_dataframe(stock_dict, daily_df)
    if not stocks_df.empty:
        stocks_df.to_csv(STOCKS_CSV_PATH, index=False)
        print(f"   > Saved stocks.csv ({len(stocks_df)} rows)")
    else:
        print("   > Warning: stocks.csv result empty. Skipping save.")

    # 3. Fundamentals — skips fresh tickers; circuit-breaker stops early if rate-limited
    info_df = create_stock_info_table(stock_dict, STOCK_INFO_CSV_PATH, args.full)
    if not info_df.empty:
        info_df.to_csv(STOCK_INFO_CSV_PATH, index=False)
        print(f"   > Saved stock_info.csv ({len(info_df)} rows)")

    print("--- UPDATE COMPLETE ---")
