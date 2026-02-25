# Personal Finance Tracker

A local Streamlit app for tracking household budget, spending, and investments. Built for a household of two — one place to see the complete financial picture and make data-driven decisions.

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd personal_finance
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the runtime mode

Edit `config/config.ini` and set `run_mode` to `testing` (verbose logging) or `production` (quiet):

```ini
[ENVIRONMENT]
run_mode = testing
```

> The `[ROBINHOOD]` section in `config.ini` is unused — yfinance is the only data source.

### 3. Set up the Budget Excel file

The budget processor expects the workbook at a fixed path:

```
~/Documents/Personal-Finance/Budget/Budget.xlsx
```

The workbook must contain:
- One or more sheets named `Monthly Budget <Month Year>` (e.g. `Monthly Budget January 2025`) — these supply the monthly budget targets per category.
- A sheet named `Budget v Actual` — this contains the income and expense transactions.

### 4. Set up your investment data

Create `data/stock_dictionary.json` (see [Investment Data](#investment-data) below). This is the only file you edit manually.

### 5. Run the app

```bash
streamlit run main.py
```

---

## Data Refresh

Data is stored as CSVs in `data/` and refreshed by running standalone scripts — either from the terminal or via the **🔄 Refresh Data** button on any page.

| Script | What it does | When to run |
|---|---|---|
| `process_budget_data.py` | Parses `Budget.xlsx` → writes `income.csv`, `expenses.csv`, `monthly_budget.csv` | After reconciling the Excel file (typically monthly) |
| `process_investment_data.py` | Fetches yfinance prices/fundamentals, replays transaction history → writes `stocks.csv`, `daily_stocks.csv`, `stock_info.csv` | Whenever you want updated prices (daily or weekly) |

```bash
# Incremental — only fetches what's new since last run (fast)
python scripts/process_budget_data.py
python scripts/process_investment_data.py

# Full rebuild — reprocesses all historical data from the beginning
python scripts/process_budget_data.py --full
python scripts/process_investment_data.py --full
```

Use **Full Rebuild** when data looks wrong or after adding historical transactions that pre-date your most recent run. The Home page has a dedicated ⚠️ Full Rebuild button for investments.

---

## Investment Data

### `data/stock_dictionary.json`

This is the source of truth for all investment transactions. Each key is a ticker symbol; each value has a `stock_name` and a `purchase_history` array.

```json
{
  "AAPL": {
    "stock_name": "Apple",
    "purchase_history": [
      {
        "date": "3/15/2021",
        "buy_sell": "buy",
        "quantity": 10,
        "share_price": 121.03,
        "platform": "Robinhood",
        "account_type": "Taxable"
      },
      {
        "date": "6/1/2023",
        "buy_sell": "sell",
        "quantity": 3,
        "share_price": 180.57,
        "platform": "Robinhood",
        "account_type": "Taxable"
      }
    ]
  }
}
```

**Field notes:**
- `date` — `M/D/YYYY` format (e.g. `"3/15/2021"`)
- `buy_sell` — `"buy"` or `"sell"`
- `quantity` — number of shares (positive integer or decimal)
- `share_price` — price per share at time of transaction
- `platform` — e.g. `"Robinhood"`, `"Fidelity"`, `"Vanguard"`
- `account_type` — e.g. `"Taxable"`, `"Roth IRA"`, `"401K"`

The processing script replays this history chronologically to compute shares held and cost basis at every point in time.

**Adding a new position:** Add an entry for the ticker with at least one `"buy"` transaction.

**Adding a watchlist ticker** (not owned, used in Buying Opportunities): Add an entry with an empty `purchase_history`:

```json
"NVDA": {
  "stock_name": "NVIDIA",
  "purchase_history": []
}
```

**Recording a sell:** Add a `"sell"` entry to the existing ticker's `purchase_history`. The script will reduce the position accordingly and stop tracking the ticker if quantity reaches zero.

After any changes, run `python scripts/process_investment_data.py` to update the CSVs.

---

## Pages

### Home
High-level snapshot: YTD income, YTD expenses, savings rate, portfolio value, and a portfolio trend chart. Buttons to refresh budget data (incremental) or investment data (incremental or full rebuild).

### Budget — Budget Overview
Monthly budget vs. actual spending by category. Filter by date range and category. Bar charts show budget targets vs. actuals; categories over budget are highlighted. Trend lines show spending over time.

### Budget — Expenses
Full transaction log with filters for date, category, and amount. Useful for finding specific charges or reviewing a category in detail.

### Budget — Income
Income transactions with monthly totals and year-over-year comparison.

### Investments — Portfolio Overview
Total portfolio value, amount invested (true cost basis from replayed transaction history), return on equity ($ and %), and a trend chart. Movers & Shakers section shows top gainers and losers over a selectable time window (1D / 1W / 1M / 3M / 1Y / YTD).

### Investments — Buying Opportunities
Data-driven scoring engine that ranks owned stocks (Re-Buy tab) and watchlist stocks (New Opportunities tab) on a 0–100 scale using 8 signals:

| Signal | Default weight | Notes |
|---|---|---|
| 52-Week Discount | 20% | How far below the 52-week high |
| Analyst Target Upside | 15% | Upside to consensus price target |
| RSI (Oversold) | 15% | 14-day RSI from daily price history |
| Industry-Relative PE | 15% | Stock PE vs. sector median PE |
| Governance Risk | 15% | Lower audit/board/compensation risk = higher score |
| Market Sentiment | 10% | VIX-based fear indicator |
| Portfolio Diversity | 5% | Prefers underweight positions |
| Cash Bonus | 5% | Scales with available cash (cap $50k) |

Weights are fully adjustable via sliders — the engine re-scores live without any API calls. The market context strip (VIX, S&P 1-month return, sentiment score) updates from yfinance with a 1-hour cache.

### Investments — Holdings Leaderboard
Top 25 holdings ranked by portfolio value, with company logos, sector, and market cap. Logos are loaded from `downloaded_logos/<TICKER>.png` — add a PNG file named after the ticker to display a logo.

### Investments — Company Deep-Dive
Select any tracked company for a detailed view: price history chart, fundamental scorecard (P/E, P/B, beta, dividend yield, profit margins, market cap — each compared to sector median), governance risk radar, and analyst consensus target.

### Investments — Stock Peer Analysis
Compare multiple holdings on a normalized price chart (all start at 1.0) over a selectable time horizon. Each stock also gets a side-by-side panel showing its performance vs. the peer average and a delta chart.

### Investments — Industry & Sector Breakdown
Portfolio allocation as pie charts (sector and industry), plus an interactive treemap that drills from sector or industry down to individual ticker.

---

## Running Tests

```bash
venv/bin/python -m pytest tests/ -v
```

- `tests/test_utils.py` — 32 unit tests for financial helpers
- `tests/test_data_processing.py` — 30 tests for the data processing pipeline (no Streamlit server needed)
- `tests/test_data_integrity.py` — 19 smoke tests that load the real CSVs and assert basic sanity
