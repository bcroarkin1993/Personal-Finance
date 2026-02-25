# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose & Goals

This app is a personal financial management tool built for a household of two. The north star is to give both users a single place to understand their complete financial picture — not just a dashboard, but an actionable tool they return to regularly.

**Budget & Spending**
- Track income and expenses across three scopes: Brandon's personal finances, shared household finances, and (view-only) my wife's personal finances
- Set monthly budget targets by category and measure actual spend against them
- Identify spending patterns, highlight categories trending over budget, and surface opportunities to save

**Financial Goals**
- Define and track savings goals of varying sizes and timelines — e.g. buying a house, saving for a child's college fund, or a near-term purchase like a couch
- Each goal should have a target amount, target date, and an assigned funding source (personal, shared, or joint)
- The app should show progress toward each goal and how current savings rates project against them

**Investments**
- Maintain a full transaction history across all accounts (taxable brokerage, Roth IRA, 401K) and replay it to produce an accurate, real-time view of holdings and cost basis
- Track portfolio performance over time (total value, return on equity, gainers/losers)
- Provide a data-driven buying opportunity engine that scores owned and watchlist stocks on value, analyst targets, risk, and market conditions
- Understand portfolio diversification across sectors, industries, and market caps

**Guiding principles for new features**
- Accuracy over aesthetics — financial numbers must be correct before the UI is polished
- The three-scope model (Brandon personal / shared household / wife personal) should be respected in all budget and expense views
- The app should be self-contained and runnable locally without external services beyond yfinance

---

## Development Workflow

All work must follow this branching model:

1. **Create a feature branch** before making any changes:
   ```bash
   git checkout main && git pull
   git checkout -b feature/<short-description>   # e.g. feature/bug-fixes, feature/buying-opportunities
   ```

2. **Commit work incrementally** on the feature branch. Never commit directly to `main`.

3. **Before merging into `main`, always stop and prompt the user to test the app:**
   > "The changes are ready on branch `feature/<name>`. Please run `streamlit run main.py` and verify the affected pages look and behave correctly before I merge into `main`. Let me know when you're happy to proceed."

4. **Only merge after the user confirms** the app is working:
   ```bash
   git checkout main
   git merge --no-ff feature/<short-description>
   ```

5. **Delete the feature branch** after a successful merge:
   ```bash
   git branch -d feature/<short-description>
   ```

---

## Running the App

```bash
streamlit run main.py
```

## Data Refresh Scripts

These scripts fetch/process data and write CSVs to `data/`. They are also triggered from the Streamlit UI via subprocess calls.

```bash
# Incremental refresh (default) — only processes new data since last run
python scripts/process_budget_data.py
python scripts/process_investment_data.py

# Full refresh — reprocesses all historical data
python scripts/process_budget_data.py --full
python scripts/process_investment_data.py --full
```

## Architecture

### Data Flow

```
Budget.xlsx (~/Documents/Personal-Finance/Budget/Budget.xlsx)
    └─> scripts/process_budget_data.py
            └─> data/income.csv, data/expenses.csv, data/monthly_budget.csv

data/stock_dictionary.json  (manually maintained transaction log)
    └─> scripts/process_investment_data.py  (fetches live data via yfinance)
            └─> data/stocks.csv, data/daily_stocks.csv, data/stock_info.csv

data/*.csv  (all CSVs)
    └─> scripts/data_processing.py  (@st.cache_data)
            └─> Streamlit pages
```

### Key Modules

- **`main.py`** — Home page / dashboard. Loads preprocessed data and renders summary metrics and portfolio trend chart.
- **`scripts/data_processing.py`** — Central data layer. `load_and_preprocess_data()` (cached) reads all CSVs, merges stocks with fundamentals, computes daily equity, sector aggregates, and 14-day RSI (from `daily_stocks.csv` — no API). All pages call this function. Buying opportunity scoring is **not** run here — it's deferred to `Buying_Opportunities.py`.
- **`scripts/process_investment_data.py`** — Standalone script. Replays transaction history from `stock_dictionary.json` to compute current holdings, fetches yfinance for prices and fundamentals (parallelised via `ThreadPoolExecutor(max_workers=3)`), and saves to CSV.
- **`scripts/process_budget_data.py`** — Standalone script. Parses the Budget Excel workbook (sheets named `Monthly Budget *` and `Budget v Actual`) and saves to CSV.
- **`scripts/navigation.py`** — Custom sidebar navigation with three radio groups (Home, Budget, Investments). Every page must call `make_sidebar("<PageId>")` as its first UI step.
- **`scripts/theme.py`** — Shared UI theme module. Exports color constants (`GREEN`, `RED`, `BLUE`, `YELLOW`, `DARK_BG`, `CARD_BORDER`, `BANNER_BG`) and `page_header(title, icon, subtitle, pills)`. Every page calls `page_header()` instead of `st.title()`.
- **`scripts/utils.py`** — Financial calculation helpers (YTD totals, monthly averages, portfolio snapshot).
- **`scripts/config.py`** — Reads `config/config.ini` to expose `RUN_MODE` (`testing` or `production`), which controls debug logging in `data_processing.py`.
- **`pages/`** — One file per Streamlit page; each loads `load_and_preprocess_data()` and calls `make_sidebar()`.

### Chart Library Convention

- **Altair** — time-series line charts (portfolio trend, normalized price performance, peer comparison lines)
- **Plotly** — all other chart types (bar, pie, treemap, scatter, polar/radar)

Use color constants from `scripts/theme.py` rather than hex literals in chart encoding.

### `stock_dictionary.json` Schema

The investment pipeline's source of truth. Each key is a ticker; each value has a `purchase_history` array with `date`, `buy_sell`, `quantity`, `share_price`, `platform`, and `account_type`. The processing script replays this history to compute average cost basis and shares held at each point in time.

### Caching

`load_and_preprocess_data()` uses `@st.cache_data`. After running either refresh script, the cache must be cleared by calling `load_and_preprocess_data.clear()` before `st.rerun()`. This is already handled in the Refresh buttons in `main.py`.

### Empty-State Safety

`data_processing.py` defines `EMPTY_SCHEMAS` for all CSVs. `safe_read_csv()` returns an empty DataFrame with the correct columns if a file is missing, preventing KeyErrors in pages when data hasn't been fetched yet.

## Environment

- Python 3.9 (local `venv/`)
- Runtime mode is set in `config/config.ini` under `[ENVIRONMENT] run_mode`
- Budget source file is hardcoded to `~/Documents/Personal-Finance/Budget/Budget.xlsx`

---

## Task List

Prioritized backlog of improvements. Work top-to-bottom within each section.

---

### 1. Bug Fixes & Data Accuracy ✅ *Completed — merged to main*

- [x] **Fix `invested` / cost-basis mismatch.** Portfolio Overview now pulls `equity` from `daily_stocks` (replayed transaction history) as the true cost basis, with a `quantity × avg_cost` fallback if daily history is unavailable.
- [x] **Fix `stocks_complete.get("avg_cost", 0)` in `data_processing.py`.** Replaced with a proper column existence check.
- [x] **Fix `Holdings_Leaderboard.py` missing page setup.** Added `set_page_config` and `make_sidebar`.
- [x] **Fix `todays_stocks_complete` alias in `data_processing.py`.** Now correctly merges today's snapshot with `stocks_complete` fundamentals.
- [x] **Deduplicate `clean_amount_column`.** Moved to `scripts/utils.py`; imported in `Budget_Overview.py`, `Expenses.py`, and `Income.py`.

---

### 2. Multi-Person Budget Tracking

The current schema has no concept of owner, card, or account on individual transactions.

- [ ] **Add `person` and `card` columns to the budget Excel parsing.** Update `process_budget_data.py` to extract or infer a `person` (e.g. "Brandon", "Wife") and `card` (e.g. "Chase Sapphire", "New Card") field from the Excel sheet structure or column headers. Save these to `expenses.csv` and `income.csv`.

- [ ] **Add `person` / `card` filters to Expenses and Budget Overview pages.** Once the columns exist in the CSVs, add multiselect filters in `Expenses.py` and `Budget_Overview.py` so you can view combined or split-by-person views.

- [ ] **Validate the new card's transactions are being captured.** After adding the card to the Excel tracking sheet, do a full refresh and verify the transaction count and totals against your card statement to confirm no rows are dropped by the `skiprows=13/14` parsing logic.

---

### 3. Buying Opportunities Enhancement ✅ *Completed — merged to main*

- [x] **Surface individual score components in the UI.** Breakdown table now shows `score_52wk`, `score_target`, `score_diversity`, `score_risk`, `score_sentiment` alongside the final `buy_score`.
- [x] **Make score weights user-configurable.** `calculate_buying_opportunity_scores` now accepts `w_*` weight parameters. The page exposes sliders that re-score live without any extra API calls.
- [x] **Cache VIX/S&P 500 fetch separately.** Extracted into `load_market_context()` with `@st.cache_data(ttl=3600)`. Scoring function accepts `market_sentiment_score` as a parameter; the page passes the cached value when re-scoring with custom weights.
- [x] **Add data freshness banner and Refresh button to Buying Opportunities page.** Shows `Last Updated` from `stock_info.csv` with a color indicator (green/yellow/red). Refresh button triggers `process_investment_data.py` and clears both data caches.
- [x] **Add market context strip.** Page displays current VIX, S&P 1-month return, and composite sentiment score at the top.
- [x] **Fix the New Opportunities (Watchlist) tab.** `process_investment_data.py` now writes `52 Week High` and `52 Week Low` to `stock_info.csv`. Schema-migration guard in `create_stock_info_table` detects missing columns and forces a re-fetch on the next incremental run. Watchlist scoring guard updated to require `52_week_high`.
- [x] **Add RSI as a scoring signal.** 14-day RSI computed in `data_processing.py` directly from `daily_stocks.csv` price history — no API calls. Owned stocks get real RSI; watchlist stocks default to 50 (neutral). `score_rsi` added as a user-configurable weight (default 15%).
- [x] **Scoring overhaul (8-signal engine).** `calculate_buying_opportunity_scores` expanded to 8 signals: 52-Week Discount (20%), Analyst Target Upside (15%), RSI Oversold (15%), Industry-Relative PE (15%), Governance Risk (15%), Market Sentiment (10%), Portfolio Diversity (5%), Cash Bonus (5%). New default weights sum to 100%. Cash cap raised from $10k to $50k. Portfolio Diversity neutral default changed from 0→50 for watchlist stocks (was artificially inflating their scores). Industry-relative PE scores each stock vs. its sector median; negative/missing PE defaults to 0.5 (neutral — fair to growth stocks).
- [x] **Fix merge collision between `stocks` and `stock_info`.** Added `Price`, `52 Week High`, `52 Week Low` to `STOCK_INFO_COLUMN_MAP`. To prevent pandas `_x`/`_y` column suffixes when both DataFrames share column names, overlapping columns are now dropped from `stock_info` before the left join. Owned stocks keep authoritative values from `stocks.csv`; the merge brings in fundamentals only.

---

### 4. App-Wide Data Freshness ✅ *Completed — merged to main*

- [x] **Refresh buttons on every page.** All 9 pages now have a Refresh button via `run_subprocess_refresh()`. Investment pages trigger `process_investment_data.py`; budget pages trigger `process_budget_data.py`.
- [x] **Persistent refresh status messages.** `render_refresh_status()` in `scripts/utils.py` uses `st.session_state` to survive `st.rerun()`. Every page calls it so success/warning/error is always visible.
- [x] **Absolute script paths.** `run_subprocess_refresh()` resolves paths via `_PROJECT_ROOT` so it works regardless of the directory Streamlit was launched from.
- [x] **Full Rebuild button on Home page.** Passes `--full` to `process_investment_data.py` to reprocess all historical data from 2016.
- [x] **Two-layer cache fix.** `clear_all_caches()` clears `load_main_data`, `load_and_preprocess_data`, and `load_market_context` in one call. All Refresh buttons use it.
- [x] **yfinance upgraded to 1.2.0.** Fixes crumb-poisoning rate limit bug in 0.2.50; uses `curl-cffi` for a more reliable auth flow.
- [x] **Pre-flight API check.** Script tests one ticker before processing; exits in ~3s with a clear message if Yahoo Finance is rate-limiting.
- [x] **Circuit breakers + staleness gate.** Each fetch phase stops after 5 consecutive failures. Fundamentals skip tickers updated within the last 23 hours.
- [x] **Forward-fill missing tickers.** If a ticker has no data for the latest date (Yahoo Finance lag), its last known close is carried forward so the portfolio trend chart isn't artificially depressed.

---

### 5. Testing Framework (was §4) ✅ *Completed — merged to main*

- [x] **Add pytest tests for `scripts/utils.py`.** 32 tests in `tests/test_utils.py` covering `clean_amount_column` (dollar signs, commas, accounting parens), `calculate_average_monthly_total` (empty input, prior-year exclusion, multi-month averaging), `calculate_yearly_total`, and `get_portfolio_snapshot` (latest-row selection, out-of-order dates).
- [x] **Add pytest tests for `scripts/data_processing.py` (non-Streamlit parts).** 30 tests in `tests/test_data_processing.py` covering `safe_read_csv` (missing/empty/normal files, all schema keys), `calculate_buying_opportunity_scores` (all 8 signals, weight customisation, edge cases), and `preprocess_data` (merge logic, RSI computation, zero-qty filter). Streamlit stubbed via `tests/conftest.py` so tests run without a server.
- [x] **Add a data integrity smoke test.** 19 tests in `tests/test_data_integrity.py` against real CSVs. Uses 1% relative tolerance for floating-point checks. Caught a real data issue: `income.csv` has a typo date `2108-12-21` — fix in `Budget.xlsx` and re-run `process_budget_data.py`.

Run with: `venv/bin/python -m pytest tests/ -v`

---

### 6. UI / Theme Consistency (was §5) ✅ *Completed — merged to main*

- [x] **Create a shared theme module.** `scripts/theme.py` exports color constants (`GREEN`, `RED`, `BLUE`, `YELLOW`, `DARK_BG`, `CARD_BORDER`, `BANNER_BG`) and `page_header(title, icon, subtitle, pills)` which injects shared CSS + renders the gradient hero header.
- [x] **Standardize chart library per use case.** Convention documented above: Altair for time-series, Plotly for all other chart types. Color literals replaced with theme constants across all pages.
- [x] **Apply hero-section styling to all pages.** All 9 pages (`main.py`, `Budget_Overview.py`, `Expenses.py`, `Income.py`, `Portfolio_Overview.py`, `Industry_&_Sector_Breakdown.py`, `Company_Deep-Dive.py`, `Buying_Opportunities.py`, `Stock_Peer_Analysis.py`, `Holdings_Leaderboard.py`) now call `page_header()` in place of `st.title()`.

---

### 7. Performance — Data Loading & Refresh Speed

The two biggest pain points are the initial page load time and how long a full investment refresh takes. Both should be improved before the app is used regularly by two people.

- [ ] **Profile the cold-start load time.** `load_and_preprocess_data()` reads 6 CSVs, runs two merges, computes daily equity aggregates, and runs buying opportunity scoring (including a VIX call). Instrument with `time.perf_counter` to identify the slowest steps before optimizing.

- [x] **Parallelize yfinance fetches in `process_investment_data.py`.** `_fetch_ticker_metadata()` extracted as a worker function; `build_summary_dataframe()` Phase 3 replaced with `ThreadPoolExecutor(max_workers=3)` + 0.5s submission stagger + `as_completed()` collection. Reduces metadata phase from ~90s to ~30s.

- [x] **Skip unchanged tickers in `create_stock_info_table`.** `FUNDAMENTALS_STALE_HOURS = 23` threshold skips tickers whose `Last Updated` is less than 23 hours old in incremental mode.

- [x] **Defer buying opportunity scoring out of `load_and_preprocess_data`.** Scoring block (market context fetch + both `calculate_buying_opportunity_scores` calls) removed from `preprocess_data()`. `Buying_Opportunities.py` calls `load_market_context()` directly. Eliminates 2 yfinance API calls from cold-start for all 8 non-scoring pages.

- [x] **Add a `ttl` to `load_main_data` cache.** Both `load_main_data` and `load_and_preprocess_data` now have `ttl=1800`.

---

### 8. Documentation & Deployment (README.md) (was §6)

The current README is a stub that references placeholder URLs and omits most setup details.

- [ ] **Write a complete local setup guide.** Cover cloning the repo, creating the virtual environment, installing dependencies from `requirements.txt`, and configuring `config/config.ini` (run mode). Note that the Budget Excel file must live at `~/Documents/Personal-Finance/Budget/Budget.xlsx` and explain what the expected sheet structure is (`Monthly Budget <Month Year>` and `Budget v Actual`).

- [ ] **Document `stock_dictionary.json` setup.** Explain the schema (ticker key, `stock_name`, `purchase_history` array with `date`, `buy_sell`, `quantity`, `share_price`, `platform`, `account_type`) and walk through adding a new position and a sell transaction. This is the one manual data-entry step and the most likely point of confusion for a new user.

- [ ] **Document the data refresh workflow.** Explain when to run `process_budget_data.py` vs `process_investment_data.py`, what `--full` does vs incremental, and how the Refresh buttons in the UI trigger the same scripts. Include a note on how often each should be run (e.g. budget monthly after reconciling the Excel file, investments whenever you want updated prices).

- [ ] **Add a page-by-page user guide.** A short paragraph per page describing what it shows and how to use it — especially the Buying Opportunities scoring engine (what the score means, how to tune the weights) and the Holdings Leaderboard (how to add logos to `downloaded_logos/`).

- [ ] **Document the three-scope budget model.** Once multi-person tracking is implemented (Section 2 above), document how Brandon personal / shared household / wife personal scopes map to the Excel sheet structure and how to filter between them in the app.
