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
- **`scripts/data_processing.py`** — Central data layer. `load_and_preprocess_data()` (cached) reads all CSVs, merges stocks with fundamentals, computes daily equity, sector aggregates, and buying opportunity scores. All pages call this function.
- **`scripts/process_investment_data.py`** — Standalone script. Replays transaction history from `stock_dictionary.json` to compute current holdings, fetches yfinance for prices and fundamentals, and saves to CSV.
- **`scripts/process_budget_data.py`** — Standalone script. Parses the Budget Excel workbook (sheets named `Monthly Budget *` and `Budget v Actual`) and saves to CSV.
- **`scripts/navigation.py`** — Custom sidebar navigation with three radio groups (Home, Budget, Investments). Every page must call `make_sidebar("<PageId>")` as its first UI step.
- **`scripts/utils.py`** — Financial calculation helpers (YTD totals, monthly averages, portfolio snapshot).
- **`scripts/config.py`** — Reads `config/config.ini` to expose `RUN_MODE` (`testing` or `production`), which controls debug logging in `data_processing.py`.
- **`pages/`** — One file per Streamlit page; each loads `load_and_preprocess_data()` and calls `make_sidebar()`.

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

### 1. Bug Fixes & Data Accuracy

**These are the highest priority** — some numbers displayed in the app are likely wrong.

- [ ] **Fix `invested` / cost-basis mismatch.** `Portfolio_Overview.py` computes "Amount Invested" as `quantity × avg_cost` from `stocks.csv`, but `avg_cost` is the weighted average at the *current* moment, not a true cost basis. The real cost basis per ticker (accounting for all buys and sells) is the `equity` column in `daily_stocks.csv`. Align Portfolio Overview metrics to use the replayed cost basis from `daily_stocks` so ROE and Return % are accurate.

- [ ] **Fix `stocks_complete.get("avg_cost", 0)` in `data_processing.py`.** Pandas DataFrames do not have a dict-style `.get()` that returns a scalar default. Line 277 (`stocks_complete.get("avg_cost", 0)`) will return `None` rather than `0` if the column is missing, causing a silent NaN multiply. Replace with `stocks_complete["avg_cost"] if "avg_cost" in stocks_complete.columns else 0`.

- [ ] **Fix `Holdings_Leaderboard.py` missing page setup.** The page is missing both `st.set_page_config(...)` and `make_sidebar("Holdings Leaderboard")` calls that every other page has. Add them at the top of the file so navigation and page title work correctly.

- [ ] **Fix `todays_stocks_complete` alias in `data_processing.py`.** Line 338 sets `"todays_stocks_complete": todays_stocks` (same object as `todays_stocks`), which means any page that merges in stock_info via `todays_stocks_complete` is silently getting the unmerged version. This key should contain the version that is joined with `stocks_complete`.

- [ ] **Deduplicate `clean_amount_column`.** An identical helper function is copy-pasted into `Budget_Overview.py`, `Expenses.py`, and `Income.py`. Move it to `scripts/utils.py` (it essentially duplicates the private `_coerce_amount_numeric` already there) and import it in all three pages. This also ensures any future fix is applied everywhere at once.

---

### 2. Multi-Person Budget Tracking

The current schema has no concept of owner, card, or account on individual transactions.

- [ ] **Add `person` and `card` columns to the budget Excel parsing.** Update `process_budget_data.py` to extract or infer a `person` (e.g. "Brandon", "Wife") and `card` (e.g. "Chase Sapphire", "New Card") field from the Excel sheet structure or column headers. Save these to `expenses.csv` and `income.csv`.

- [ ] **Add `person` / `card` filters to Expenses and Budget Overview pages.** Once the columns exist in the CSVs, add multiselect filters in `Expenses.py` and `Budget_Overview.py` so you can view combined or split-by-person views.

- [ ] **Validate the new card's transactions are being captured.** After adding the card to the Excel tracking sheet, do a full refresh and verify the transaction count and totals against your card statement to confirm no rows are dropped by the `skiprows=13/14` parsing logic.

---

### 3. Buying Opportunities Enhancement

The scoring engine works but several inputs are missing or hardcoded.

- [ ] **Surface individual score components in the UI.** The bar chart and table in `Buying_Opportunities.py` only show the final `buy_score`. Add columns for `score_52wk`, `score_target`, `score_diversity`, `score_risk`, and the live `market_sentiment_score` so you can see *why* a stock ranked where it did.

- [ ] **Make score weights and `portfolio_cash` user-configurable.** The weights (0.25, 0.20, 0.20, 0.15, 0.15, 0.05) and `portfolio_cash=5000` are hardcoded in `data_processing.py`. Expose them as `st.slider` widgets on the Buying Opportunities page (or as sidebar inputs) so you can tune the model interactively.

- [ ] **Fix the New Opportunities (Watchlist) tab.** It is permanently empty because `stock_info.csv` does not contain a `price` column for non-owned tickers. `process_investment_data.py` needs to also fetch and store the current price in `stock_info.csv` (e.g., add a `Price` column using `yf.Ticker.fast_info['last_price']`), or the watchlist scoring logic needs to pull price from a different source.

- [ ] **Add RSI as a scoring signal.** The README already calls this out. Use `yfinance` historical data to compute a 14-day RSI during `process_investment_data.py` and store it in `stock_info.csv`. Add `score_rsi` (high score when RSI < 40, i.e. oversold) as an optional component in `calculate_buying_opportunity_scores`.

- [ ] **Cache VIX/S&P 500 fetch separately.** `calculate_buying_opportunity_scores` fetches live VIX and S&P data every time the Streamlit cache is warm-reloaded. Move the market sentiment fetch into `process_investment_data.py` so it is stored in a small `market_context.json` and read from disk — this keeps the scoring function pure and fast.

---

### 4. Testing Framework

There are currently zero automated tests.

- [ ] **Add pytest tests for `scripts/utils.py`.** The financial helpers (`calculate_average_monthly_total`, `calculate_yearly_total`, `get_portfolio_snapshot`) are pure functions with no Streamlit dependency and are the highest-value starting point for tests. Create `tests/test_utils.py` with small synthetic DataFrames covering normal cases, empty inputs, and malformed amount strings (e.g., `"$1,234.56"`, `"(500.00)"`).

- [ ] **Add pytest tests for `scripts/data_processing.py` (non-Streamlit parts).** `preprocess_data`, `calculate_buying_opportunity_scores`, and `safe_read_csv` can all be tested without a running Streamlit server. Create `tests/test_data_processing.py` with fixture DataFrames that exercise the merge logic, the empty-state early-return path, and the buying score computation.

- [ ] **Add a data integrity smoke test.** Create `tests/test_data_integrity.py` that loads the real CSVs from `data/` and asserts basic sanity: no negative quantities in `stocks.csv`, no future dates, `market_value` equals `close × shares_held` within a small tolerance in `daily_stocks.csv`, and income/expense amounts are all positive.

---

### 5. UI / Theme Consistency

- [ ] **Create a shared theme module.** Extract a `scripts/theme.py` (or `scripts/styles.py`) that defines the color palette (greens/reds already used: `#2ecc71`, `#e74c3c`, `#3498db`), reusable CSS strings, and a `apply_page_style()` function. Call it from every page instead of repeating inline CSS or leaving pages unstyled.

- [ ] **Standardize chart library per use case.** The app mixes Altair (trend lines) and Plotly (bar/pie) across pages with no consistent rule. Choose one for each chart type and apply it uniformly — or document the rule in this file so future additions are consistent.

- [ ] **Apply hero-section styling to all pages.** `main.py` has a polished hero gradient header with pill labels. Budget and investment pages just use `st.title(...)`. Wrap the `make_sidebar` call in a shared helper that also injects the hero header markup so all pages have a consistent header look.

- [ ] **Add `st.set_page_config` to `Holdings_Leaderboard.py`.** (Overlaps with the bug fix above — resolve together.)

---

### 6. Documentation & Deployment (README.md)

The current README is a stub that references placeholder URLs and omits most setup details.

- [ ] **Write a complete local setup guide.** Cover cloning the repo, creating the virtual environment, installing dependencies from `requirements.txt`, and configuring `config/config.ini` (run mode). Note that the Budget Excel file must live at `~/Documents/Personal-Finance/Budget/Budget.xlsx` and explain what the expected sheet structure is (`Monthly Budget <Month Year>` and `Budget v Actual`).

- [ ] **Document `stock_dictionary.json` setup.** Explain the schema (ticker key, `stock_name`, `purchase_history` array with `date`, `buy_sell`, `quantity`, `share_price`, `platform`, `account_type`) and walk through adding a new position and a sell transaction. This is the one manual data-entry step and the most likely point of confusion for a new user.

- [ ] **Document the data refresh workflow.** Explain when to run `process_budget_data.py` vs `process_investment_data.py`, what `--full` does vs incremental, and how the Refresh buttons in the UI trigger the same scripts. Include a note on how often each should be run (e.g. budget monthly after reconciling the Excel file, investments whenever you want updated prices).

- [ ] **Add a page-by-page user guide.** A short paragraph per page describing what it shows and how to use it — especially the Buying Opportunities scoring engine (what the score means, how to tune the weights) and the Holdings Leaderboard (how to add logos to `downloaded_logos/`).

- [ ] **Document the three-scope budget model.** Once multi-person tracking is implemented (Section 2 above), document how Brandon personal / shared household / wife personal scopes map to the Excel sheet structure and how to filter between them in the app.
