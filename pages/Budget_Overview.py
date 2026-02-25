import streamlit as st
import pandas as pd
import altair as alt
from datetime import date
from scripts.data_processing import load_and_preprocess_data, clear_all_caches
from scripts.navigation import make_sidebar
from scripts.theme import (
    BLUE, GREEN, RED,
    page_header, section_header, stat_card_grid, html_table, grad_divider,
)
from scripts.utils import clean_amount_column, render_freshness_badge, render_refresh_status, run_subprocess_refresh

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Budget Overview", page_icon="💸", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Budget Overview")

page_header("Budget Overview", icon="💸",
            subtitle="Monthly budget vs. actual spending across all categories")
_, col_refresh = st.columns([5, 1])
with col_refresh:
    if st.button("🔄 Refresh Data", use_container_width=True):
        run_subprocess_refresh(
            "scripts/process_budget_data.py",
            clear_all_caches,
            "Processing Budget.xlsx...",
        )

render_refresh_status()

# ----------------- DATA LOADING & CLEANING ----------------- #
data = load_and_preprocess_data()
income_df  = data["income"].copy()
expenses_df = data["expenses"].copy()

_budget_max_date = None
if not expenses_df.empty and "date" in expenses_df.columns:
    _budget_max_date = pd.to_datetime(expenses_df["date"], errors="coerce").max()
elif not income_df.empty and "date" in income_df.columns:
    _budget_max_date = pd.to_datetime(income_df["date"], errors="coerce").max()
if _budget_max_date is not None:
    render_freshness_badge(_budget_max_date, label="Budget data through")

if "expense_category" in expenses_df.columns:
    expenses_df = expenses_df.rename(columns={"expense_category": "category"})
if "source" in income_df.columns:
    income_df = income_df.rename(columns={"source": "category"})

income_df   = clean_amount_column(income_df)
expenses_df = clean_amount_column(expenses_df)

income_df["date"]   = pd.to_datetime(income_df["date"],   errors="coerce")
expenses_df["date"] = pd.to_datetime(expenses_df["date"], errors="coerce")
income_df   = income_df.dropna(subset=["date"])
expenses_df = expenses_df.dropna(subset=["date"])

# ----------------- FILTERS (TOP OF PAGE) ----------------- #
with st.container():
    st.html(section_header("Filters", icon="🔍"))
    f_col1, f_col2 = st.columns(2)

    if not income_df.empty and not expenses_df.empty:
        min_date = min(income_df["date"].min(), expenses_df["date"].min()).date()
        max_date = max(income_df["date"].max(), expenses_df["date"].max()).date()
    else:
        min_date = date.today()
        max_date = date.today()

    default_start = max(min_date, date(date.today().year, 1, 1))
    default_end   = min(max_date, date.today())

    with f_col1:
        date_range = st.date_input(
            "Date Range",
            value=(default_start, default_end),
            min_value=min_date,
            max_value=max_date
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = default_start, default_end

    unique_categories = sorted(expenses_df["category"].dropna().astype(str).unique().tolist())

    with f_col2:
        selected_categories = st.multiselect(
            "Expense Categories (Impacts Expenses Line)",
            options=unique_categories,
            default=unique_categories
        )

# ----------------- DATA PROCESSING ----------------- #
mask_income = (income_df["date"].dt.date >= start_date) & (income_df["date"].dt.date <= end_date)
filtered_income = income_df.loc[mask_income]

mask_expenses = (
        (expenses_df["date"].dt.date >= start_date) &
        (expenses_df["date"].dt.date <= end_date) &
        (expenses_df["category"].isin(selected_categories))
)
filtered_expenses = expenses_df.loc[mask_expenses]

income_monthly = (
    filtered_income.set_index("date")
        .resample("MS")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "Income"})
)

expenses_monthly = (
    filtered_expenses.set_index("date")
        .resample("MS")["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "Expenses"})
)

chart_data = pd.merge(income_monthly, expenses_monthly, on="date", how="outer").fillna(0.0)
chart_data["Net_Savings"] = chart_data["Income"] - chart_data["Expenses"]
chart_data["Savings_Rate"] = chart_data.apply(
    lambda x: (x["Net_Savings"] / x["Income"]) if x["Income"] > 0 else 0.0, axis=1
)

# ----------------- MAIN CHART SECTION ----------------- #
st.html(grad_divider())
st.html(section_header("Income vs. Expenses Trend", icon="📈"))

if not chart_data.empty:
    base_chart_data = chart_data.melt(
        id_vars=["date", "Savings_Rate"],
        value_vars=["Income", "Expenses"],
        var_name="Type",
        value_name="Amount"
    )

    hover = alt.selection_point(fields=["date"], nearest=True, on="mouseover", empty="none")

    lines = (
        alt.Chart(base_chart_data)
            .mark_line(point=True)
            .encode(
            x=alt.X("date:T", axis=alt.Axis(format="%b %Y", title="Date")),
            y=alt.Y("Amount:Q", axis=alt.Axis(title="Amount ($)")),
            color=alt.Color("Type:N", scale=alt.Scale(domain=["Income", "Expenses"], range=[GREEN, RED])),
            tooltip=[alt.Tooltip("date:T", format="%b %Y"), alt.Tooltip("Type:N"),
                     alt.Tooltip("Amount:Q", format="$,.2f")]
        )
    )

    savings_area = (
        alt.Chart(chart_data)
            .mark_area(opacity=0.15, interpolate="monotone")
            .encode(
            x="date:T",
            y=alt.Y("Savings_Rate:Q", axis=alt.Axis(title="Savings Rate %", format="%")),
            color=alt.value(BLUE),
            tooltip=[alt.Tooltip("date:T", format="%b %Y"),
                     alt.Tooltip("Savings_Rate:Q", title="Savings Rate", format=".1%")]
        )
    )

    combined_chart = (
        alt.layer(savings_area, lines)
            .resolve_scale(y="independent")
            .properties(height=400)
            .interactive()
    )

    st.altair_chart(combined_chart, use_container_width=True)

    # Snapshot metrics
    st.html(grad_divider())
    st.html(section_header("Snapshot (Selected Period)", icon="📊"))

    total_inc  = chart_data["Income"].sum()
    total_exp  = chart_data["Expenses"].sum()
    net_sav    = total_inc - total_exp
    avg_sav_rate = (net_sav / total_inc * 100) if total_inc > 0 else 0.0

    st.html(stat_card_grid([
        {"label": "Total Income",    "value": f"${total_inc:,.2f}",     "icon": "💵"},
        {"label": "Total Expenses",  "value": f"${total_exp:,.2f}",     "icon": "🧾", "positive": False},
        {
            "label": "Net Savings",
            "value": f"${net_sav:,.2f}",
            "icon": "🏦",
            "delta": f"${net_sav:,.2f}",
            "positive": net_sav >= 0,
        },
        {
            "label": "Avg Savings Rate",
            "value": f"{avg_sav_rate:.1f}%",
            "icon": "📊",
            "delta": f"{avg_sav_rate:.1f}%",
            "positive": avg_sav_rate >= 0,
        },
    ], cols=4))

    st.html(grad_divider())

    with st.expander("View Underlying Data"):
        display_data = chart_data[["date", "Income", "Expenses", "Net_Savings", "Savings_Rate"]].sort_values(
            "date", ascending=False
        ).copy()
        display_data["date"] = display_data["date"].dt.strftime("%b %Y")

        st.html(html_table(
            display_data,
            col_labels={
                "date":         "Month",
                "Income":       "Income",
                "Expenses":     "Expenses",
                "Net_Savings":  "Net Savings",
                "Savings_Rate": "Savings Rate",
            },
            formatters={
                "Income":       "${:,.2f}",
                "Expenses":     "${:,.2f}",
                "Net Savings":  "${:,.2f}",
                "Savings Rate": "{:.1%}",
            },
            pos_cols=["Net_Savings"],
            neg_cols=["Expenses"],
        ))
else:
    st.info("No data available for the selected range.")
