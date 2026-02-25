"""
tests/test_data_integrity.py — sanity checks against the real CSVs in data/.

These tests load live data files and assert basic financial invariants.
They are intentionally skipped (not failed) when a file is absent, so the
suite still passes on a fresh checkout before the first data refresh.

When a test DOES fail it means there is a real data-quality issue that
should be investigated and fixed in the source data.

Known issues (document here, fix in the data):
  - income.csv contains at least one row with date "2108-12-21" (typo: 2108
    instead of 2026). The test_no_future_dates_in_income test will flag this.
    Fix by correcting the date in Budget.xlsx and re-running process_budget_data.py.
"""

from typing import List, Optional

import pandas as pd
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(filename: str, required_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Read a CSV from data/, normalize column names to snake_case lowercase,
    and skip the test if the file is missing or required columns are absent.
    """
    path = DATA_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found in data/ — run a data refresh first")
    df = pd.read_csv(path)
    df.columns = [c.strip().replace(" ", "_").lower() for c in df.columns]
    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            pytest.skip(f"{filename} missing expected columns: {missing}")
    return df


# ── stocks.csv ────────────────────────────────────────────────────────────────

class TestStocksCsv:

    def test_no_zero_or_negative_quantity(self):
        """process_investment_data filters out sold/inactive positions; all remaining rows
        should have quantity > 0."""
        df = _load("stocks.csv", ["quantity"])
        bad = df[df["quantity"] <= 0]
        assert bad.empty, f"Rows with quantity ≤ 0: {bad['stock'].tolist() if 'stock' in bad else bad.index.tolist()}"

    def test_market_value_equals_price_times_quantity(self):
        """market_value should be price × quantity within 1% relative tolerance.
        Small discrepancies arise from floating-point rounding in the refresh script."""
        df = _load("stocks.csv", ["price", "quantity", "market_value"])
        diff = (df["market_value"] - df["price"] * df["quantity"]).abs()
        # 1% relative tolerance (with $1 floor for near-zero values)
        tol = df["market_value"].abs().clip(lower=1.0) * 0.01
        bad = df[diff > tol]
        assert bad.empty, (
            f"{len(bad)} rows have market_value more than 1% away from price × quantity:\n"
            + bad[["stock", "price", "quantity", "market_value"]].to_string()
        )

    def test_no_negative_market_value(self):
        df = _load("stocks.csv", ["market_value"])
        bad = df[df["market_value"] < 0]
        assert bad.empty, f"Negative market_value rows: {bad.index.tolist()}"

    def test_avg_cost_is_positive(self):
        df = _load("stocks.csv", ["avg_cost"])
        bad = df[df["avg_cost"] <= 0]
        assert bad.empty, f"Rows with avg_cost ≤ 0: {bad.index.tolist()}"

    def test_portfolio_diversity_sums_to_100(self):
        df = _load("stocks.csv", ["portfolio_diversity"])
        total = df["portfolio_diversity"].sum()
        assert total == pytest.approx(100.0, abs=0.5), \
            f"Portfolio diversity sums to {total:.2f}%, expected ~100%"


# ── daily_stocks.csv ──────────────────────────────────────────────────────────

class TestDailyStocksCsv:

    def test_no_negative_shares_held(self):
        df = _load("daily_stocks.csv", ["shares_held"])
        bad = df[df["shares_held"] < 0]
        assert bad.empty, f"{len(bad)} rows with negative shares_held"

    def test_market_value_equals_close_times_shares(self):
        """market_value ≈ close × shares_held within 1% relative tolerance.
        Discrepancies arise from floating-point accumulation in transaction replay."""
        df = _load("daily_stocks.csv", ["close", "shares_held", "market_value"])
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["shares_held"] = pd.to_numeric(df["shares_held"], errors="coerce")
        df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce")
        df = df.dropna(subset=["close", "shares_held", "market_value"])
        diff = (df["market_value"] - df["close"] * df["shares_held"]).abs()
        tol = df["market_value"].abs().clip(lower=1.0) * 0.01
        bad_count = (diff > tol).sum()
        assert bad_count == 0, \
            f"{bad_count} rows where |market_value − close × shares_held| > 1%"

    def test_no_future_dates(self):
        df = _load("daily_stocks.csv", ["date"])
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        future = dates[dates > pd.Timestamp.now()]
        assert future.empty, f"{len(future)} future dates found in daily_stocks.csv"

    def test_dates_are_parseable(self):
        df = _load("daily_stocks.csv", ["date"])
        unparseable = pd.to_datetime(df["date"], errors="coerce").isna().sum()
        assert unparseable == 0, f"{unparseable} unparseable dates in daily_stocks.csv"

    def test_close_price_is_positive(self):
        df = _load("daily_stocks.csv", ["close"])
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        bad = df[df["close"].notna() & (df["close"] <= 0)]
        assert bad.empty, f"{len(bad)} rows with close price ≤ 0"


# ── stock_info.csv ────────────────────────────────────────────────────────────

class TestStockInfoCsv:

    def test_no_duplicate_tickers(self):
        df = _load("stock_info.csv", ["stock"])
        dupes = df[df.duplicated("stock", keep=False)]["stock"].unique()
        assert len(dupes) == 0, f"Duplicate tickers in stock_info.csv: {list(dupes)}"

    def test_last_updated_not_future(self):
        df = _load("stock_info.csv", ["last_updated"])
        dates = pd.to_datetime(df["last_updated"], errors="coerce").dropna()
        future = dates[dates > pd.Timestamp.now()]
        assert future.empty, f"{len(future)} future last_updated timestamps"

    def test_52_week_high_gte_low(self):
        df = _load("stock_info.csv", ["52_week_high", "52_week_low"])
        df["52_week_high"] = pd.to_numeric(df["52_week_high"], errors="coerce")
        df["52_week_low"] = pd.to_numeric(df["52_week_low"], errors="coerce")
        # Only check rows where both values are > 0 (0 means data was unavailable)
        valid = df[(df["52_week_high"] > 0) & (df["52_week_low"] > 0)]
        bad = valid[valid["52_week_high"] < valid["52_week_low"]]
        assert bad.empty, f"Rows where 52W high < 52W low: {bad['stock'].tolist() if 'stock' in bad else []}"


# ── expenses.csv ──────────────────────────────────────────────────────────────

class TestExpensesCsv:

    def test_amounts_are_parseable_numeric(self):
        """All amount values should coerce to a finite number (catches #N/A, blank cells, etc.)."""
        df = _load("expenses.csv", ["amount"])
        unparseable = pd.to_numeric(df["amount"], errors="coerce").isna().sum()
        assert unparseable == 0, f"{unparseable} non-numeric amount values in expenses.csv"

    def test_amounts_within_plausible_range(self):
        """Amounts should be within a plausible range.
        Negatives are valid (refunds/credits). Catches wild data-entry errors."""
        df = _load("expenses.csv", ["amount"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        too_large = df[df["amount"].abs() > 50_000]
        assert too_large.empty, f"{len(too_large)} expense rows with |amount| > $50,000"

    def test_no_future_dates(self):
        df = _load("expenses.csv", ["date"])
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        future = dates[dates > pd.Timestamp.now()]
        assert future.empty, f"{len(future)} future dates in expenses.csv"

    def test_dates_are_parseable(self):
        df = _load("expenses.csv", ["date"])
        unparseable = pd.to_datetime(df["date"], errors="coerce").isna().sum()
        assert unparseable == 0, f"{unparseable} unparseable dates in expenses.csv"


# ── income.csv ────────────────────────────────────────────────────────────────

class TestIncomeCsv:

    def test_amounts_are_parseable_numeric(self):
        """All amount values should coerce to a finite number."""
        df = _load("income.csv", ["amount"])
        unparseable = pd.to_numeric(df["amount"], errors="coerce").isna().sum()
        assert unparseable == 0, f"{unparseable} non-numeric amount values in income.csv"

    def test_amounts_within_plausible_range(self):
        """Amounts should be within a plausible range.
        Negatives are valid (fantasy/betting losses tracked in income table).
        Catches wild data-entry errors."""
        df = _load("income.csv", ["amount"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        too_large = df[df["amount"].abs() > 100_000]
        assert too_large.empty, f"{len(too_large)} income rows with |amount| > $100,000"

    def test_no_future_dates(self):
        """Flags rows with clearly erroneous dates (e.g. year typos like 2108).
        See module docstring for the known offending row in income.csv."""
        df = _load("income.csv", ["date"])
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        future = dates[dates > pd.Timestamp.now()]
        # Surface the bad rows for easy diagnosis
        if not future.empty:
            bad_rows = df[pd.to_datetime(df["date"], errors="coerce") > pd.Timestamp.now()]
            pytest.fail(
                f"{len(future)} future date(s) in income.csv:\n"
                + bad_rows.to_string()
                + "\nFix the date in Budget.xlsx and re-run process_budget_data.py."
            )
