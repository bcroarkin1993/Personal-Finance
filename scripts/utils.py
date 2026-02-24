import sys
import subprocess
import pathlib
import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional

_UTILS_DIR = pathlib.Path(__file__).resolve().parent   # scripts/
_PROJECT_ROOT = _UTILS_DIR.parent                      # project root
_DATA_DIR = _PROJECT_ROOT / "data"


def _latest_csv_mtime() -> float:
    """Return the most recent modification time of any CSV in data/."""
    try:
        return max(
            (f.stat().st_mtime for f in _DATA_DIR.iterdir() if f.suffix == ".csv"),
            default=0.0,
        )
    except Exception:
        return 0.0

def _data_age_days(date_val) -> Optional[float]:
    """Returns how many days ago a date was, or None if unparseable."""
    try:
        ts = pd.to_datetime(date_val)
        return (pd.Timestamp.now() - ts).total_seconds() / 86400
    except Exception:
        return None


def render_freshness_badge(date_val, label: str = "Data last updated") -> None:
    """
    Renders a small color-coded freshness indicator inline.
      Green  — updated within the last 24 hours
      Yellow — 1–7 days old
      Red    — 7+ days old or date unknown
    Call this near the top of any page that displays time-sensitive data.
    """
    age = _data_age_days(date_val)
    try:
        date_str = pd.to_datetime(date_val).strftime("%b %d, %Y")
    except Exception:
        date_str = str(date_val)

    if age is None:
        color, note = "#e74c3c", "unknown — refresh recommended"
    elif age < 1:
        color, note = "#2ecc71", "today ✓"
    elif age < 7:
        color, note = "#f39c12", f"{int(age)}d ago"
    else:
        color, note = "#e74c3c", f"{int(age)}d ago — refresh recommended"

    st.markdown(
        f"<div style='font-size:0.82rem; margin-bottom:6px;'>"
        f"{label}: <span style='color:{color}; font-weight:600;'>{date_str}</span>"
        f" <span style='color:{color}; opacity:0.85;'>({note})</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def run_subprocess_refresh(
    script_path: str,
    clear_cache_fn,
    spinner_msg: str = "Refreshing data...",
    full_refresh: bool = False,
) -> None:
    """
    Runs a data refresh script as a subprocess using the current Python interpreter,
    clears the provided Streamlit cache function, then reruns the page.

    Uses an absolute path derived from the project root so the script is found
    regardless of the working directory Streamlit was launched from.

    full_refresh=True passes --full to the script for a complete historical rebuild.
    """
    abs_script = str(_PROJECT_ROOT / script_path)
    cmd = [sys.executable, abs_script]
    if full_refresh:
        cmd.append("--full")

    mtime_before = _latest_csv_mtime()

    with st.spinner(spinner_msg):
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            st.error(f"Refresh script failed (exit code {e.returncode}).")
            return
        except Exception as e:
            st.error(f"Refresh failed: {e}")
            return

    clear_cache_fn()
    mtime_after = _latest_csv_mtime()

    if mtime_after > mtime_before:
        st.success("Data updated successfully!")
    else:
        st.warning(
            "Refresh ran but no data files changed — "
            "Yahoo Finance may be rate-limiting. Wait a few minutes and try again."
        )
    st.rerun()


def clean_amount_column(df: pd.DataFrame, amount_col: str = "amount") -> pd.DataFrame:
    """
    Coerces an amount column to numeric, handling formatted strings such as
    '$1,234.56', '1,234', and accounting-style negatives like '(500.00)'.
    """
    if amount_col in df.columns:
        s = df[amount_col].astype(str)
        s = s.str.replace(r"[$,]", "", regex=True)
        s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
        df = df.copy()
        df[amount_col] = pd.to_numeric(s, errors="coerce").fillna(0.0)
    return df


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