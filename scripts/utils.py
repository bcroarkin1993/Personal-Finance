import pandas as pd
import streamlit as st
from typing import Dict, Any

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