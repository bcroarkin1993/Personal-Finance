import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar
from scripts.theme import (
    page_header, section_header, stat_card_grid, html_table, badge, grad_divider,
    GREEN_PIE_PALETTE,
)
from scripts.utils import clean_amount_column, render_freshness_badge, render_refresh_status

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Income Analysis", page_icon="💵", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Income Analysis")

page_header("Income Analysis", icon="💵",
            subtitle="Track income by source and month")

render_refresh_status()

# ----------------- DATA LOADING & CLEANING ----------------- #
data = load_and_preprocess_data()
income_df = data["income"].copy()

if not income_df.empty and "date" in income_df.columns:
    render_freshness_badge(pd.to_datetime(income_df["date"], errors="coerce").max(), label="Income data through")

if "source" in income_df.columns:
    income_df = income_df.rename(columns={"source": "category"})

income_df = clean_amount_column(income_df)
income_df["date"] = pd.to_datetime(income_df["date"], errors="coerce")
income_df = income_df.dropna(subset=["date"])

income_df["description_clean"] = income_df["category"].fillna("").astype(str).str.strip().str.upper()


def _cat_color(cat: str) -> str:
    palette = ["teal", "green", "yellow"]
    return palette[abs(hash(cat)) % len(palette)]


# ----------------- FILTERS ----------------- #
with st.container():
    st.html(section_header("Filters", icon="🔍"))
    f_col1, f_col2, f_col3 = st.columns(3)

    if not income_df.empty:
        min_date = income_df["date"].min().date()
        max_date = income_df["date"].max().date()
    else:
        min_date = date.today()
        max_date = date.today()

    default_start = date(date.today().year, 1, 1)
    default_end   = min(date.today(), max_date)
    if default_start > max_date:
        default_start = min_date

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

    if not income_df.empty:
        cat_stats = income_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        sorted_categories = cat_stats.index.tolist()
    else:
        sorted_categories = []

    with f_col2:
        selected_categories = st.multiselect(
            "Source / Category (Sorted by Value)",
            options=sorted_categories,
            default=sorted_categories
        )

    with f_col3:
        search_term = st.text_input("Search Source", "")

# ----------------- FILTERING ----------------- #
mask = (
        (income_df["date"].dt.date >= start_date) &
        (income_df["date"].dt.date <= end_date) &
        (income_df["category"].isin(selected_categories))
)
filtered_df = income_df.loc[mask].copy()

if search_term:
    filtered_df = filtered_df[filtered_df["description_clean"].str.contains(search_term.upper())]

# ----------------- METRICS ----------------- #
total_income      = filtered_df["amount"].sum()
transaction_count = len(filtered_df)
avg_transaction   = total_income / transaction_count if transaction_count > 0 else 0.0

st.html(grad_divider())
st.html(stat_card_grid([
    {"label": "Total Income",    "value": f"${total_income:,.2f}",    "icon": "💵"},
    {"label": "Transactions",    "value": f"{transaction_count}",     "icon": "🔢"},
    {"label": "Avg Transaction", "value": f"${avg_transaction:,.2f}", "icon": "📊"},
], cols=3))
st.html(grad_divider())

# ----------------- VISUALIZATION ----------------- #
c1, c2 = st.columns([1, 1])

with c1:
    st.html(section_header("Income by Source", icon="🥧"))
    if not filtered_df.empty:
        cat_group = filtered_df.groupby("category")["amount"].sum().reset_index()
        fig_cat = px.pie(
            cat_group, values="amount", names="category",
            hole=0.4, title="Income Distribution",
            color_discrete_sequence=GREEN_PIE_PALETTE,
        )
        fig_cat.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No data for chart.")

with c2:
    st.html(section_header("Top Sources (Bar)", icon="📊"))
    if not filtered_df.empty:
        desc_group = (
            filtered_df.groupby("category")
                .agg(Total_Amount=("amount", "sum"), Count=("amount", "count"))
                .reset_index().sort_values(by="Total_Amount", ascending=False)
        )

        fig_desc = px.bar(
            desc_group.head(10),
            x="Total_Amount",
            y="category",
            orientation='h',
            text="Total_Amount",
            title="Top Income Sources by Value",
            color_discrete_sequence=GREEN_PIE_PALETTE,
        )
        fig_desc.update_layout(yaxis={'categoryorder': 'total ascending'})
        fig_desc.update_traces(texttemplate="$%{text:,.0f}")
        st.plotly_chart(fig_desc, use_container_width=True)
    else:
        st.info("No data for trends.")

# ----------------- INCOME LOG TABLE ----------------- #
st.html(grad_divider())
st.html(section_header("Income Log", icon="📋"))

if not filtered_df.empty:
    display_cols = ["date", "category", "amount"]
    if "description" in filtered_df.columns and not filtered_df["description"].isna().all():
        display_cols.append("description")

    display_df = filtered_df[display_cols].sort_values("date", ascending=False).copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    col_map = {"date": "Date", "category": "Source", "amount": "Amount"}
    if "description" in display_df.columns:
        col_map["description"] = "Description"

    st.html(html_table(
        display_df,
        col_labels=col_map,
        formatters={
            "Amount": "${:,.2f}",
            "Source": lambda v: badge(str(v), _cat_color(str(v))),
        },
    ))
else:
    st.info("No income records to display for the selected filters.")
