import subprocess
from typing import Dict, Any

import pandas as pd
import streamlit as st
import altair as alt

from scripts.data_processing import load_and_preprocess_data

# ----------------- PAGE CONFIG ----------------- #

st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide",
)

# ----------------- LIGHT CUSTOM STYLING ----------------- #

st.markdown(
    """
    <style>
    /* Hero gradient background */
    .hero-container {
        padding: 1.5rem 1.75rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 40%, #3b8d99 100%);
        color: white;
        margin-bottom: 0.75rem;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .hero-subtitle {
        font-size: 1rem;
        opacity: 0.9;
        margin-top: 0.25rem;
    }
    .hero-pill {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 999px;
        background-color: rgba(255,255,255,0.12);
        font-size: 0.8rem;
        margin-bottom: 0.5rem;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background-color: #0b1621;
        padding: 10px 14px;
        border-radius: 14px;
        border: 1px solid #243447;
    }
    div[data-testid="metric-container"] > label > div {
        font-size: 0.75rem;
        font-weight: 500;
    }
    div[data-testid="metric-container"] > div {
        font-size: 0.95rem;
        font-weight: 600;
        overflow-wrap: anywhere;
    }

    /* Section titles */
    .section-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-top: 0.75rem;
        margin-bottom: 0.25rem;
    }

    /* Small label text */
    .muted-label {
        font-size: 0.8rem;
        opacity: 0.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------- SIDEBAR NAVIGATION ----------------- #

st.sidebar.title("Navigation")

# NOTE: For st.switch_page, these strings should match your actual app paths.
# Adjust if your multipage structure is different.
pages: Dict[str, str] = {
    "Home": "main.py",
    # Budget pages
    "Budget Overview": "views/Budget_Overview.py",
    "Income Analysis": "views/Income.py",
    "Expense Breakdown": "views/Expenses.py",
    # Investment pages
    "Portfolio Overview": "views/Portfolio_Overview.py",
    "Industry & Sector Breakdown": "views/Industry_&_Sector_Breakdown.py",
    "Company Deep-Dive": "views/Company_Deep-Dive.py",
    "Buying Opportunities": "views/Buying_Opportunities.py",
    "Stock Peer Analysis": "views/Stock_Peer_Analysis.py",
    "Holdings Leaderboard": "views/Holdings_Leaderboard.py"
}

st.sidebar.subheader("🏠 Home")
home_page = st.sidebar.radio(
    "Go to Home:",
    options=["Home"],
    index=0,
    label_visibility="collapsed",
)

st.sidebar.subheader("📊 Budget Pages")
budget_page = st.sidebar.radio(
    "Go to Budget Page:",
    options=["Budget Overview",
             "Income Analysis",
             "Expense Breakdown"],
    index=0,
    label_visibility="collapsed",
)

st.sidebar.subheader("📈 Investment Pages")
investment_page = st.sidebar.radio(
    "Go to Investment Page:",
    options=[
        "Portfolio Overview",
        "Industry & Sector Breakdown",
        "Company Deep-Dive",
        "Buying Opportunities",
        "Peer Analysis",
        "Holdings Leaderboard"
    ],
    index=0,
    label_visibility="collapsed",
)

# Decide which page is selected
if home_page == "Home":
    selected_page = "Home"
elif budget_page:
    selected_page = budget_page
else:
    selected_page = investment_page


def handle_navigation(page_key: str):
    """Use Streamlit's multipage navigation to switch pages."""
    if page_key == "Home":
        return
    page_file = pages.get(page_key)
    if not page_file:
        return
    try:
        st.switch_page(page_file)
    except Exception:
        # If user is on older Streamlit or paths don't match,
        # we fail silently and stay on Home rather than crashing.
        st.warning(
            "Sidebar navigation requires Streamlit's multipage setup. "
            "Check that your page paths in `pages` match your actual files."
        )


# If not on Home, navigate away and stop executing this page
if selected_page != "Home":
    handle_navigation(selected_page)
    st.stop()

# ----------------- HELPER FUNCTIONS ----------------- #

def get_last_refresh_date_from_df(df: pd.DataFrame, date_col: str = "date") -> str:
    """
    Get the most recent date from a dataframe date column.
    Assumes the column is a date-like string or datetime.
    """
    try:
        if date_col not in df.columns:
            return f"Column '{date_col}' not found"
        dates = pd.to_datetime(df[date_col], errors="coerce")
        if dates.isna().all():
            return "No valid dates"
        last_date = dates.max()
        return last_date.strftime("%Y-%m-%d")
    except Exception as e:
        return f"Error: {e}"


def _coerce_amount_numeric(df: pd.DataFrame, amount_col: str = "amount") -> pd.DataFrame:
    """
    Force the amount column to numeric, handling strings like '$2,550.83', '1,234', '(123.45)'.
    """
    if amount_col not in df.columns:
        raise KeyError(f"Required column '{amount_col}' not found")

    df = df.copy()
    s = df[amount_col].astype(str)

    # Remove $ and commas
    s = s.str.replace(r"[,\$]", "", regex=True)
    # Convert '(123.45)' -> '-123.45'
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    df[amount_col] = pd.to_numeric(s, errors="coerce")
    return df


def calculate_average_monthly_total(
    df: pd.DataFrame,
    date_col: str = "date",
    amount_col: str = "amount",
) -> float:
    """
    Generic helper to calculate average monthly total (income/expenses)
    for the current year from a dataframe.
    """
    try:
        if date_col not in df.columns:
            raise KeyError(f"Required column '{date_col}' not found")

        df = _coerce_amount_numeric(df, amount_col=amount_col)
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        current_year = pd.Timestamp.now().year
        df_year = df[df[date_col].dt.year == current_year]

        if df_year.empty:
            return 0.0

        monthly_totals = (
            df_year
            .groupby(df_year[date_col].dt.to_period("M"))[amount_col]
            .sum()
        )

        return float(monthly_totals.mean())
    except Exception as e:
        st.error(f"Error calculating average monthly total: {e}")
        return 0.0


def calculate_yearly_total(
    df: pd.DataFrame,
    date_col: str = "date",
    amount_col: str = "amount",
) -> float:
    """
    Calculate the total for the current year (e.g., annual income or expenses).
    """
    try:
        if date_col not in df.columns:
            raise KeyError(f"Required column '{date_col}' not found")

        df = _coerce_amount_numeric(df, amount_col=amount_col)
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        current_year = pd.Timestamp.now().year
        df_year = df[df[date_col].dt.year == current_year]

        return float(df_year[amount_col].sum())
    except Exception as e:
        st.error(f"Error calculating yearly total: {e}")
        return 0.0


def get_portfolio_snapshot(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Derive investment snapshot metrics from preprocessed data.

    Uses the `daily_equity` table for portfolio-level numbers.
    """
    daily_equity: pd.DataFrame = data.get("daily_equity", pd.DataFrame())

    if daily_equity.empty or "date" not in daily_equity.columns:
        return {
            "total_portfolio_value": 0.0,
            "total_equity": 0.0,
            "total_profit": 0.0,
        }

    df = daily_equity.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date")

    latest = df.iloc[-1]

    total_portfolio_value = float(latest.get("market_value", 0.0))
    total_equity = float(latest.get("equity", 0.0))
    total_profit = float(latest.get("total_profit", 0.0))

    return {
        "total_portfolio_value": total_portfolio_value,
        "total_equity": total_equity,
        "total_profit": total_profit,
    }


# ----------------- HOME PAGE (LANDING) ----------------- #

# Load data once
data: Dict[str, Any] = load_and_preprocess_data()
income_df: pd.DataFrame = data["income"]
expenses_df: pd.DataFrame = data["expenses"]
daily_stocks_df: pd.DataFrame = data["daily_stocks"]
daily_equity_df: pd.DataFrame = data.get("daily_equity", pd.DataFrame())

# Budget metrics
avg_monthly_income = calculate_average_monthly_total(income_df)
avg_monthly_expenses = calculate_average_monthly_total(expenses_df)
annual_income = calculate_yearly_total(income_df)
annual_expenses = calculate_yearly_total(expenses_df)

if annual_income > 0:
    savings_rate = (annual_income - annual_expenses) / annual_income * 100
else:
    savings_rate = 0.0

last_expenses_refresh = get_last_refresh_date_from_df(expenses_df, "date")

# Investment metrics
portfolio_snapshot = get_portfolio_snapshot(data)
total_portfolio_value = portfolio_snapshot["total_portfolio_value"]
total_equity = portfolio_snapshot["total_equity"]
total_profit = portfolio_snapshot["total_profit"]
last_investment_refresh = get_last_refresh_date_from_df(daily_stocks_df, "date")

# ----------------- HERO SECTION (FULL WIDTH) ----------------- #
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-pill">Dashboard Overview</div>
        <div class="hero-title">Personal Finance Command Center</div>
        <div class="hero-subtitle">
            High-level snapshot of your budget and investments in one place.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------- HIGH-LEVEL SNAPSHOT ----------------- #
st.markdown('<div class="section-title">Today at a Glance</div>', unsafe_allow_html=True)
top_col1, top_col2, top_col3, top_col4 = st.columns(4)

with top_col1:
    st.metric("💵 Total Income (YTD)", f"${annual_income:,.2f}")
    st.markdown('<span class="muted-label">From all tracked sources</span>', unsafe_allow_html=True)

with top_col2:
    st.metric("🧾 Total Expenses (YTD)", f"${annual_expenses:,.2f}")
    st.markdown('<span class="muted-label">Across all categories</span>', unsafe_allow_html=True)

with top_col3:
    # Use delta to color the number green/red
    sr_delta = f"{savings_rate:.1f}%" if savings_rate != 0 else None
    st.metric("📊 Savings Rate", f"{savings_rate:.1f}%", delta=sr_delta)
    st.markdown('<span class="muted-label">Income left after expenses</span>', unsafe_allow_html=True)

with top_col4:
    st.metric("💼 Portfolio Value", f"${total_portfolio_value:,.2f}")
    st.markdown('<span class="muted-label">Latest market value</span>', unsafe_allow_html=True)

st.markdown("")  # spacing

# ----------------- BUDGET & INVESTMENT OVERVIEW SIDE-BY-SIDE ----------------- #
left, right = st.columns(2)

# ----- Budget Overview Column ----- #
with left:
    st.markdown('<div class="section-title">💸 Budget Overview</div>', unsafe_allow_html=True)
    st.write(
        """
        Get a quick read on your cashflow:
        - How much you're bringing in vs. spending
        - What your average month looks like
        - Whether your savings rate is trending in the right direction
        """
    )

    b1, b2 = st.columns(2)
    with b1:
        st.metric("Avg Monthly Income", f"${avg_monthly_income:,.2f}")
    with b2:
        st.metric("Avg Monthly Expenses", f"${avg_monthly_expenses:,.2f}")

    st.markdown(
        f"<span class='muted-label'>Budget data last refreshed: {last_expenses_refresh}</span>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh Budget Data"):
        try:
            subprocess.run(
                ["python", "scripts/process_budget_data.py"],
                check=True,
            )
            load_and_preprocess_data.clear()
            st.success("Budget data updated. Reloading with fresh data...")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update budget data: {e}")

# ----- Investments Overview Column ----- #
with right:
    st.markdown('<div class="section-title">📈 Investments Overview</div>', unsafe_allow_html=True)
    st.write(
        """
        See how your investments are performing overall:
        - Current portfolio value vs. amount invested
        - Total profit or loss across accounts
        """
    )

    i1, i2, i3 = st.columns(3)
    with i1:
        st.metric("Portfolio Value", f"${total_portfolio_value:,.2f}")
    with i2:
        st.metric("Total Equity (Invested)", f"${total_equity:,.2f}")
    with i3:
        # Use delta to color profit/loss green/red
        pl_delta = f"${total_profit:,.2f}" if total_profit != 0 else None
        st.metric("Total Profit / Loss", f"${total_profit:,.2f}", delta=pl_delta)
    st.markdown(
        f"<span class='muted-label'>Investment data last refreshed: {last_investment_refresh}</span>",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh Investment Data"):
        try:
            subprocess.run(
                ["python", "scripts/process_investment_data.py"],
                check=True,
            )
            load_and_preprocess_data.clear()
            st.success("Investment data updated. Reloading with fresh data...")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update investment data: {e}")

# ----------------- PORTFOLIO TREND (BOTTOM, FULL WIDTH) ----------------- #
st.markdown('<div class="section-title">📉 Portfolio Trend Over Time</div>', unsafe_allow_html=True)

if not daily_equity_df.empty and {"date", "market_value", "total_profit"}.issubset(daily_equity_df.columns):
    chart_df = daily_equity_df.copy()
    chart_df["date"] = pd.to_datetime(chart_df["date"], errors="coerce")
    chart_df = chart_df.sort_values("date")

    # Altair chart with month-year x-axis and profit in tooltip, color by profit sign
    chart = (
        alt.Chart(chart_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "date:T",
                axis=alt.Axis(format="%b %y", title="Date"),
            ),
            y=alt.Y("market_value:Q", title="Portfolio Value"),
            color=alt.condition(
                "datum.total_profit >= 0",
                alt.value("#2ecc71"),  # green
                alt.value("#e74c3c"),  # red
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("market_value:Q", title="Portfolio Value", format=",.2f"),
                alt.Tooltip("total_profit:Q", title="Total Profit", format=",.2f"),
            ],
        )
        .properties(height=300)
    )

    st.altair_chart(chart, use_container_width=True)
    st.markdown(
        "<span class='muted-label'>Color reflects profit (green) or loss (red) at each point in time.</span>",
        unsafe_allow_html=True,
    )
else:
    st.info("No portfolio history available yet. Once you have daily data, a trend chart will appear here.")

# ----------------- FOOTER ----------------- #
st.markdown("---")
st.write(
    "🔍 **Next step:** Use the sidebar to dive into Budget or Investments and start exploring the details."
)
