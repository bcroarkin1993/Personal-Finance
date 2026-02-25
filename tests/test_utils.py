"""
tests/test_utils.py — unit tests for scripts/utils.py financial helpers.

These functions are pure pandas/Python with no Streamlit server requirement
(st.error calls are silenced by the conftest.py stub).

Coverage:
  - clean_amount_column      — string → float coercion with $, commas, parens
  - calculate_average_monthly_total — current-year monthly average
  - calculate_yearly_total          — current-year YTD sum
  - get_portfolio_snapshot          — latest-row extraction from daily_equity
"""

import pandas as pd
import pytest

from scripts.utils import (
    clean_amount_column,
    calculate_average_monthly_total,
    calculate_yearly_total,
    get_portfolio_snapshot,
)

CURRENT_YEAR = pd.Timestamp.now().year


# ── Helpers ──────────────────────────────────────────────────────────────────

def _expense_df(dates, amounts):
    return pd.DataFrame({"date": dates, "amount": amounts})


def _equity_df(rows):
    return pd.DataFrame(rows, columns=["date", "market_value", "equity", "total_profit"])


# ── clean_amount_column ───────────────────────────────────────────────────────

class TestCleanAmountColumn:

    def test_plain_numeric_strings(self):
        df = pd.DataFrame({"amount": ["100.50", "200.00", "50"]})
        result = clean_amount_column(df)
        assert list(result["amount"]) == pytest.approx([100.50, 200.00, 50.0])

    def test_dollar_sign_and_commas(self):
        df = pd.DataFrame({"amount": ["$1,234.56", "$10,000.00"]})
        result = clean_amount_column(df)
        assert list(result["amount"]) == pytest.approx([1234.56, 10000.00])

    def test_accounting_negatives(self):
        df = pd.DataFrame({"amount": ["(500.00)", "(1,234.56)"]})
        result = clean_amount_column(df)
        assert list(result["amount"]) == pytest.approx([-500.00, -1234.56])

    def test_already_numeric_values(self):
        df = pd.DataFrame({"amount": [1.5, 2.5, 3.0]})
        result = clean_amount_column(df)
        assert list(result["amount"]) == pytest.approx([1.5, 2.5, 3.0])

    def test_unparseable_becomes_zero(self):
        df = pd.DataFrame({"amount": ["N/A", "abc", ""]})
        result = clean_amount_column(df)
        assert list(result["amount"]) == pytest.approx([0.0, 0.0, 0.0])

    def test_original_df_not_mutated(self):
        df = pd.DataFrame({"amount": ["$100.00"]})
        clean_amount_column(df)
        assert df["amount"].iloc[0] == "$100.00"

    def test_missing_column_is_no_op(self):
        df = pd.DataFrame({"other_col": [1, 2]})
        result = clean_amount_column(df)
        assert "amount" not in result.columns
        assert list(result.columns) == ["other_col"]

    def test_mixed_formats_in_one_column(self):
        df = pd.DataFrame({"amount": ["$1,000.00", "(250.50)", "500", "N/A"]})
        result = clean_amount_column(df)
        assert list(result["amount"]) == pytest.approx([1000.00, -250.50, 500.0, 0.0])


# ── calculate_average_monthly_total ──────────────────────────────────────────

class TestCalculateAverageMonthlyTotal:

    def test_empty_df_returns_zero(self):
        df = pd.DataFrame({"date": [], "amount": []})
        assert calculate_average_monthly_total(df) == 0.0

    def test_prior_year_data_excluded(self):
        df = _expense_df(
            [f"{CURRENT_YEAR - 1}-01-15", f"{CURRENT_YEAR - 1}-06-10"],
            [500.0, 300.0],
        )
        assert calculate_average_monthly_total(df) == 0.0

    def test_single_month_equals_that_months_total(self):
        df = _expense_df(
            [f"{CURRENT_YEAR}-03-01", f"{CURRENT_YEAR}-03-15"],
            [200.0, 300.0],
        )
        # One month, total = 500, average = 500
        assert calculate_average_monthly_total(df) == pytest.approx(500.0)

    def test_two_unequal_months_averages_correctly(self):
        df = _expense_df(
            [f"{CURRENT_YEAR}-01-10", f"{CURRENT_YEAR}-02-10"],
            [1000.0, 500.0],
        )
        # Jan = 1000, Feb = 500  →  avg = 750
        assert calculate_average_monthly_total(df) == pytest.approx(750.0)

    def test_multiple_rows_same_month_aggregated_first(self):
        df = _expense_df(
            [f"{CURRENT_YEAR}-04-05", f"{CURRENT_YEAR}-04-20", f"{CURRENT_YEAR}-05-10"],
            [100.0, 150.0, 200.0],
        )
        # Apr = 250, May = 200  →  avg = 225
        assert calculate_average_monthly_total(df) == pytest.approx(225.0)

    def test_formatted_amount_strings_parsed(self):
        df = _expense_df([f"{CURRENT_YEAR}-01-10"], ["$1,500.00"])
        assert calculate_average_monthly_total(df) == pytest.approx(1500.0)

    def test_missing_date_col_returns_zero(self):
        df = pd.DataFrame({"amount": [100.0, 200.0]})
        assert calculate_average_monthly_total(df) == 0.0

    def test_custom_column_names(self):
        df = pd.DataFrame({
            "txn_date": [f"{CURRENT_YEAR}-07-01"],
            "total": [999.0],
        })
        result = calculate_average_monthly_total(df, date_col="txn_date", amount_col="total")
        assert result == pytest.approx(999.0)


# ── calculate_yearly_total ───────────────────────────────────────────────────

class TestCalculateYearlyTotal:

    def test_empty_df_returns_zero(self):
        df = pd.DataFrame({"date": [], "amount": []})
        assert calculate_yearly_total(df) == 0.0

    def test_prior_year_excluded(self):
        df = _expense_df([f"{CURRENT_YEAR - 1}-06-01"], [9999.0])
        assert calculate_yearly_total(df) == 0.0

    def test_sums_current_year_rows(self):
        df = _expense_df(
            [f"{CURRENT_YEAR}-01-01", f"{CURRENT_YEAR}-06-15", f"{CURRENT_YEAR}-12-31"],
            [100.0, 200.0, 300.0],
        )
        assert calculate_yearly_total(df) == pytest.approx(600.0)

    def test_mixed_years_sums_only_current(self):
        df = _expense_df(
            [f"{CURRENT_YEAR}-01-01", f"{CURRENT_YEAR - 1}-01-01"],
            [400.0, 600.0],
        )
        assert calculate_yearly_total(df) == pytest.approx(400.0)

    def test_formatted_amount_strings_parsed(self):
        df = _expense_df([f"{CURRENT_YEAR}-03-01"], ["$2,500.50"])
        assert calculate_yearly_total(df) == pytest.approx(2500.50)

    def test_missing_date_col_returns_zero(self):
        df = pd.DataFrame({"amount": [500.0]})
        assert calculate_yearly_total(df) == 0.0


# ── get_portfolio_snapshot ───────────────────────────────────────────────────

class TestGetPortfolioSnapshot:

    def test_empty_dict_returns_zeros(self):
        result = get_portfolio_snapshot({})
        assert result == {
            "total_portfolio_value": 0.0,
            "total_equity": 0.0,
            "total_profit": 0.0,
        }

    def test_missing_daily_equity_key_returns_zeros(self):
        result = get_portfolio_snapshot({"stocks": pd.DataFrame()})
        assert result["total_portfolio_value"] == 0.0

    def test_empty_daily_equity_df_returns_zeros(self):
        result = get_portfolio_snapshot({"daily_equity": pd.DataFrame()})
        assert result["total_portfolio_value"] == 0.0

    def test_daily_equity_without_date_col_returns_zeros(self):
        df = pd.DataFrame({"market_value": [50000.0], "equity": [30000.0]})
        result = get_portfolio_snapshot({"daily_equity": df})
        assert result["total_portfolio_value"] == 0.0

    def test_single_row_returns_correct_values(self):
        df = _equity_df([["2026-01-15", 50000.0, 30000.0, 20000.0]])
        result = get_portfolio_snapshot({"daily_equity": df})
        assert result["total_portfolio_value"] == pytest.approx(50000.0)
        assert result["total_equity"] == pytest.approx(30000.0)
        assert result["total_profit"] == pytest.approx(20000.0)

    def test_picks_latest_row_by_date(self):
        df = _equity_df([
            ["2026-01-01", 40000.0, 25000.0, 15000.0],
            ["2026-06-01", 60000.0, 35000.0, 25000.0],  # latest
            ["2026-03-01", 50000.0, 30000.0, 20000.0],
        ])
        result = get_portfolio_snapshot({"daily_equity": df})
        assert result["total_portfolio_value"] == pytest.approx(60000.0)
        assert result["total_equity"] == pytest.approx(35000.0)
        assert result["total_profit"] == pytest.approx(25000.0)

    def test_out_of_order_dates_sorted_correctly(self):
        df = _equity_df([
            ["2026-12-31", 99000.0, 50000.0, 49000.0],
            ["2026-01-01", 10000.0, 8000.0, 2000.0],
        ])
        result = get_portfolio_snapshot({"daily_equity": df})
        assert result["total_portfolio_value"] == pytest.approx(99000.0)
