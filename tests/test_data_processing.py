"""
tests/test_data_processing.py — unit tests for non-Streamlit parts of
scripts/data_processing.py.

Functions under test:
  - safe_read_csv                      — missing/empty/normal CSV handling
  - calculate_buying_opportunity_scores — 8-signal scoring engine
  - preprocess_data                    — merge pipeline (no API calls)

The Streamlit stub in conftest.py makes @st.cache_data transparent so the
module can be imported outside a running Streamlit server.
"""

import pandas as pd
import pytest

from scripts.data_processing import (
    EMPTY_SCHEMAS,
    calculate_buying_opportunity_scores,
    preprocess_data,
    safe_read_csv,
)


# ── safe_read_csv ─────────────────────────────────────────────────────────────

class TestSafeReadCsv:

    def test_missing_file_returns_empty_df_with_schema_columns(self, tmp_path):
        result = safe_read_csv(tmp_path / "nonexistent.csv", "stocks")
        assert result.empty
        assert set(EMPTY_SCHEMAS["stocks"]).issubset(set(result.columns))

    def test_unknown_schema_key_returns_empty_no_columns(self, tmp_path):
        result = safe_read_csv(tmp_path / "ghost.csv", "does_not_exist")
        assert result.empty
        assert list(result.columns) == []

    def test_reads_normal_csv(self, tmp_path):
        csv = tmp_path / "test.csv"
        csv.write_text("a,b\n1,2\n3,4\n")
        result = safe_read_csv(csv, "stocks")
        assert len(result) == 2
        assert list(result.columns) == ["a", "b"]

    def test_empty_file_returns_schema_columns(self, tmp_path):
        csv = tmp_path / "empty.csv"
        csv.write_text("")
        result = safe_read_csv(csv, "expenses")
        assert result.empty
        assert set(EMPTY_SCHEMAS["expenses"]).issubset(set(result.columns))

    def test_header_only_csv_returns_empty_df(self, tmp_path):
        csv = tmp_path / "header_only.csv"
        csv.write_text("stock,company,price\n")
        result = safe_read_csv(csv, "stocks")
        assert result.empty

    def test_all_known_schema_keys_are_valid(self, tmp_path):
        for key in EMPTY_SCHEMAS:
            result = safe_read_csv(tmp_path / f"{key}_missing.csv", key)
            assert result.empty
            assert set(EMPTY_SCHEMAS[key]).issubset(set(result.columns))


# ── calculate_buying_opportunity_scores ──────────────────────────────────────

def _scoreable_df(**overrides):
    """Builds the smallest DataFrame that passes all scoring validation guards."""
    base = {
        "stock":                    ["AAA", "BBB"],
        "company":                  ["Alpha Inc", "Beta Corp"],
        "price":                    [80.0, 60.0],
        "52_week_high":             [100.0, 100.0],
        "52_week_low":              [50.0, 40.0],
        "target_mean_price":        [100.0, 80.0],
        "sector":                   ["Technology", "Technology"],
        "industry":                 ["Software", "Software"],
        "pe_ratio":                 [20.0, 30.0],
        "beta":                     [1.0, 1.2],
        "audit_risk":               [3, 7],
        "board_risk":               [3, 7],
        "compensation_risk":        [3, 7],
        "shareholder_rights_risk":  [3, 7],
        "rsi_14":                   [45.0, 55.0],
        "portfolio_diversity":      [10.0, 5.0],
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestCalculateBuyingOpportunityScores:

    def test_empty_df_returns_empty(self):
        assert calculate_buying_opportunity_scores(pd.DataFrame()).empty

    def test_missing_required_columns_returns_empty(self):
        df = pd.DataFrame({"stock": ["X"], "price": [50.0]})
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        assert result.empty

    def test_scores_bounded_0_to_100(self):
        df = _scoreable_df()
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        assert not result.empty
        assert result["buy_score"].between(0, 100).all()

    def test_result_sorted_descending_by_buy_score(self):
        df = _scoreable_df()
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        scores = list(result["buy_score"])
        assert scores == sorted(scores, reverse=True)

    def test_all_score_component_columns_present(self):
        df = _scoreable_df()
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        for col in ["score_52wk", "score_target", "score_rsi", "score_pe",
                    "score_risk", "score_sentiment", "score_diversity", "score_cash"]:
            assert col in result.columns, f"Missing column: {col}"

    # ── Signal: 52-Week Discount ─────────────────────────────────────────────

    def test_52wk_discount_at_half_high_scores_one(self):
        # Price = 50% of 52W high → discount_pct = 0.5 → score_52wk = 1.0 (capped)
        df = _scoreable_df(price=[50.0, 100.0], **{"52_week_high": [100.0, 100.0]})
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        scores = result.set_index("stock")["score_52wk"]
        assert scores["AAA"] == pytest.approx(1.0, abs=0.01)

    def test_52wk_at_high_scores_zero(self):
        df = _scoreable_df(price=[100.0, 80.0], **{"52_week_high": [100.0, 100.0]})
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        scores = result.set_index("stock")["score_52wk"]
        assert scores["AAA"] == pytest.approx(0.0, abs=0.01)

    # ── Signal: RSI Oversold ──────────────────────────────────────────────────

    def test_rsi_30_scores_0_70(self):
        df = _scoreable_df(rsi_14=[30.0, 70.0])
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        rsi_scores = result.set_index("stock")["score_rsi"]
        assert rsi_scores["AAA"] == pytest.approx(0.70, abs=0.01)

    def test_rsi_70_scores_0_30(self):
        df = _scoreable_df(rsi_14=[30.0, 70.0])
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        rsi_scores = result.set_index("stock")["score_rsi"]
        assert rsi_scores["BBB"] == pytest.approx(0.30, abs=0.01)

    def test_rsi_50_scores_0_50_neutral(self):
        df = _scoreable_df(rsi_14=[50.0, 50.0])
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        assert result["score_rsi"].tolist() == pytest.approx([0.50, 0.50], abs=0.01)

    def test_missing_rsi_column_defaults_to_neutral(self):
        df = _scoreable_df()
        df = df.drop(columns=["rsi_14"])
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.5)
        assert result["score_rsi"].tolist() == pytest.approx([0.50, 0.50], abs=0.01)

    # ── Signal: Cash Bonus ────────────────────────────────────────────────────

    def test_zero_cash_score_cash_is_zero(self):
        df = _scoreable_df()
        result = calculate_buying_opportunity_scores(df, portfolio_cash=0, market_sentiment_score=0.5)
        assert result["score_cash"].tolist() == pytest.approx([0.0, 0.0])

    def test_max_cash_50k_score_cash_is_one(self):
        df = _scoreable_df()
        result = calculate_buying_opportunity_scores(df, portfolio_cash=50_000, market_sentiment_score=0.5)
        assert result["score_cash"].tolist() == pytest.approx([1.0, 1.0])

    def test_cash_above_cap_clamps_to_one(self):
        df = _scoreable_df()
        result = calculate_buying_opportunity_scores(df, portfolio_cash=100_000, market_sentiment_score=0.5)
        assert result["score_cash"].tolist() == pytest.approx([1.0, 1.0])

    def test_higher_cash_yields_higher_buy_score(self):
        df = _scoreable_df()
        no_cash = calculate_buying_opportunity_scores(df, portfolio_cash=0, market_sentiment_score=0.5)
        max_cash = calculate_buying_opportunity_scores(df, portfolio_cash=50_000, market_sentiment_score=0.5)
        assert (max_cash["buy_score"].values > no_cash["buy_score"].values).all()

    # ── Signal: Market Sentiment ──────────────────────────────────────────────

    def test_sentiment_applied_uniformly_to_all_rows(self):
        df = _scoreable_df()
        result = calculate_buying_opportunity_scores(df, market_sentiment_score=0.75)
        assert result["score_sentiment"].tolist() == pytest.approx([0.75, 0.75])

    def test_higher_sentiment_increases_buy_score(self):
        df = _scoreable_df()
        low = calculate_buying_opportunity_scores(df, market_sentiment_score=0.2)
        high = calculate_buying_opportunity_scores(df, market_sentiment_score=0.8)
        assert (high["buy_score"].values > low["buy_score"].values).all()

    # ── Weight customisation ──────────────────────────────────────────────────

    def test_custom_weights_change_rank_order(self):
        # AAA: bigger discount (80% of high), BBB: bigger analyst upside
        df = _scoreable_df(
            price=[80.0, 90.0],
            **{"52_week_high": [100.0, 100.0]},
            target_mean_price=[100.0, 130.0],
        )
        # Weight all on 52W discount → AAA should rank first
        r_discount = calculate_buying_opportunity_scores(
            df, market_sentiment_score=0.5,
            w_52wk=1.0, w_target=0.0, w_rsi=0.0, w_pe=0.0,
            w_risk=0.0, w_sentiment=0.0, w_diversity=0.0, w_cash=0.0,
        )
        # Weight all on analyst target → BBB should rank first
        r_target = calculate_buying_opportunity_scores(
            df, market_sentiment_score=0.5,
            w_52wk=0.0, w_target=1.0, w_rsi=0.0, w_pe=0.0,
            w_risk=0.0, w_sentiment=0.0, w_diversity=0.0, w_cash=0.0,
        )
        assert r_discount.iloc[0]["stock"] == "AAA"
        assert r_target.iloc[0]["stock"] == "BBB"


# ── preprocess_data ──────────────────────────────────────────────────────────

def _empty_raw():
    """Minimal raw_data dict — all keys present, all DataFrames empty."""
    return {
        "stocks":         pd.DataFrame(columns=EMPTY_SCHEMAS["stocks"]),
        "daily_stocks":   pd.DataFrame(columns=EMPTY_SCHEMAS["daily_stocks"]),
        "stock_info":     pd.DataFrame(columns=EMPTY_SCHEMAS["stock_info"]),
        "expenses":       pd.DataFrame(columns=EMPTY_SCHEMAS["expenses"]),
        "income":         pd.DataFrame(columns=EMPTY_SCHEMAS["income"]),
        "monthly_budget": pd.DataFrame(columns=EMPTY_SCHEMAS["monthly_budget"]),
        "stock_dictionary": {},
    }


def _stocks_row(**overrides):
    base = {
        "stock": "AAA", "company": "Alpha", "price": 50.0,
        "quantity": 5, "avg_cost": 40.0, "market_value": 250.0,
        "equity_change": 50.0, "percent_change": 5.0,
    }
    base.update(overrides)
    return base


class TestPreprocessData:

    def test_empty_input_returns_all_expected_keys(self):
        result = preprocess_data(_empty_raw())
        required = {
            "stocks", "daily_stocks", "stock_info", "expenses", "income",
            "monthly_budget", "stock_dictionary", "stocks_complete",
            "daily_equity", "todays_stocks", "todays_stocks_complete",
            "rebuying_opportunities", "buying_opportunities",
        }
        assert required.issubset(set(result.keys()))

    def test_empty_input_early_return_gives_empty_frames(self):
        result = preprocess_data(_empty_raw())
        assert result["stocks_complete"].empty
        assert result["daily_equity"].empty
        assert result["rebuying_opportunities"].empty
        assert result["buying_opportunities"].empty

    def test_zero_quantity_rows_filtered_out(self):
        raw = _empty_raw()
        raw["stocks"] = pd.DataFrame([
            _stocks_row(stock="AAA", quantity=0),
            _stocks_row(stock="BBB", quantity=10),
        ])
        result = preprocess_data(raw)
        assert "AAA" not in result["stocks"]["stock"].values
        assert "BBB" in result["stocks"]["stock"].values

    def test_fundamentals_merged_into_stocks_complete(self):
        raw = _empty_raw()
        raw["stocks"] = pd.DataFrame([_stocks_row(stock="AAA")])
        raw["stock_info"] = pd.DataFrame({
            "stock": ["AAA"],
            "sector": ["Technology"],
            "industry": ["Software"],
            "pe_ratio": [20.0],
            "beta": [1.1],
            "market_cap": [500.0],
        })
        result = preprocess_data(raw)
        sc = result["stocks_complete"]
        assert "sector" in sc.columns
        assert sc.iloc[0]["sector"] == "Technology"

    def test_rsi_computed_from_daily_history(self):
        """preprocess_data attaches rsi_14 for owned tickers with sufficient price history."""
        raw = _empty_raw()
        raw["stocks"] = pd.DataFrame([_stocks_row(stock="AAA")])
        # 20 days of steadily rising prices → RSI should be well above 50
        dates = pd.date_range("2026-01-01", periods=20).strftime("%Y-%m-%d").tolist()
        closes = [float(10 + i) for i in range(20)]
        raw["daily_stocks"] = pd.DataFrame({
            "date":         dates,
            "close":        closes,
            "stock":        ["AAA"] * 20,
            "shares_held":  [5] * 20,
            "market_value": [c * 5 for c in closes],
            "total_profit": [0.0] * 20,
        })
        result = preprocess_data(raw)
        sc = result["stocks_complete"]
        assert "rsi_14" in sc.columns
        assert sc.iloc[0]["rsi_14"] > 50.0  # strong uptrend → RSI > 50

    def test_rsi_neutral_when_insufficient_history(self):
        """Fewer than 15 price points → RSI defaults to 50.0 (neutral)."""
        raw = _empty_raw()
        raw["stocks"] = pd.DataFrame([_stocks_row(stock="AAA")])
        raw["daily_stocks"] = pd.DataFrame({
            "date":         ["2026-01-01", "2026-01-02"],
            "close":        [50.0, 51.0],
            "stock":        ["AAA", "AAA"],
            "shares_held":  [5, 5],
            "market_value": [250.0, 255.0],
            "total_profit": [0.0, 0.0],
        })
        result = preprocess_data(raw)
        sc = result["stocks_complete"]
        assert sc.iloc[0]["rsi_14"] == pytest.approx(50.0)

    def test_sector_aggregates_computed(self):
        raw = _empty_raw()
        raw["stocks"] = pd.DataFrame([_stocks_row(stock="AAA"), _stocks_row(stock="BBB")])
        raw["stock_info"] = pd.DataFrame({
            "stock":    ["AAA", "BBB"],
            "sector":   ["Technology", "Healthcare"],
            "industry": ["Software", "Biotech"],
        })
        result = preprocess_data(raw)
        assert not result["sector_values"].empty
        assert "sector" in result["sector_values"].columns

    def test_invested_column_added_when_missing(self):
        raw = _empty_raw()
        raw["stocks"] = pd.DataFrame([_stocks_row(stock="AAA", quantity=5, avg_cost=40.0)])
        result = preprocess_data(raw)
        sc = result["stocks_complete"]
        assert "invested" in sc.columns
        assert sc.iloc[0]["invested"] == pytest.approx(200.0)  # 5 × 40
