import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from scripts.data_processing import load_and_preprocess_data
from scripts.navigation import make_sidebar

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Expense Breakdown", page_icon="🧾", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Expense Breakdown")

st.title("🧾 Expense Breakdown")

# ----------------- DATA LOADING & CLEANING ----------------- #
data = load_and_preprocess_data()
expenses_df = data["expenses"].copy()

if "expense_category" in expenses_df.columns:
    expenses_df = expenses_df.rename(columns={"expense_category": "category"})


def clean_amount_column(df):
    if "amount" in df.columns:
        df["amount"] = df["amount"].astype(str).str.replace(r"[$,]", "", regex=True)
        df["amount"] = df["amount"].str.replace(r"^\((.*)\)$", r"-\1", regex=True)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df


expenses_df = clean_amount_column(expenses_df)
expenses_df["date"] = pd.to_datetime(expenses_df["date"], errors="coerce")
expenses_df = expenses_df.dropna(subset=["date"])
expenses_df["description_clean"] = expenses_df["description"].fillna("").astype(str).str.strip().str.upper()

# ----------------- FILTERS ----------------- #
with st.container():
    st.subheader("Filters")
    f_col1, f_col2, f_col3 = st.columns(3)

    # 1. Date Range
    if not expenses_df.empty:
        min_date = expenses_df["date"].min().date()
        max_date = expenses_df["date"].max().date()
    else:
        min_date = date.today()
        max_date = date.today()

    # FIX: Ensure default selection is within bounds [min_date, max_date]
    default_start = date(date.today().year, 1, 1)
    default_end = min(date.today(), max_date)  # Clamp to max data date

    # Handle case where start of year is after max date (e.g. stale data)
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

    # 2. Category Filter
    unique_categories = sorted(expenses_df["category"].dropna().astype(str).unique().tolist())
    with f_col2:
        selected_categories = st.multiselect("Category", options=unique_categories, default=unique_categories)

    # 3. Description Search
    with f_col3:
        search_term = st.text_input("Search Description (e.g., 'Uber')", "")

# ----------------- FILTERING LOGIC ----------------- #
mask = (
        (expenses_df["date"].dt.date >= start_date) &
        (expenses_df["date"].dt.date <= end_date) &
        (expenses_df["category"].isin(selected_categories))
)
filtered_df = expenses_df.loc[mask].copy()

if search_term:
    filtered_df = filtered_df[filtered_df["description_clean"].str.contains(search_term.upper())]

# ----------------- METRICS ----------------- #
total_spend = filtered_df["amount"].sum()
transaction_count = len(filtered_df)
avg_transaction = total_spend / transaction_count if transaction_count > 0 else 0.0

st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("Total Expenses", f"${total_spend:,.2f}")
col2.metric("Transactions", f"{transaction_count}")
col3.metric("Avg Transaction", f"${avg_transaction:,.2f}")
st.divider()

# ----------------- VISUALIZATION ----------------- #
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("Spending by Category")
    if not filtered_df.empty:
        cat_group = filtered_df.groupby("category")["amount"].sum().reset_index()
        fig_cat = px.pie(cat_group, values="amount", names="category", hole=0.4, title="Expense Distribution")
        fig_cat.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No data for chart.")

with c2:
    st.subheader("Description Trends")
    if not filtered_df.empty:
        desc_group = (
            filtered_df.groupby("description_clean")
                .agg(Total_Amount=("amount", "sum"), Count=("amount", "count"), Category=("category", "first"))
                .reset_index().sort_values(by="Count", ascending=False)
        )
        sort_mode = st.radio("Sort Trends By:", ["Frequency (Count)", "Total Spent ($)"], horizontal=True)
        if sort_mode == "Frequency (Count)":
            top_desc = desc_group.sort_values("Count", ascending=False).head(10)
            y_axis = "Count"
        else:
            top_desc = desc_group.sort_values("Total_Amount", ascending=False).head(10)
            y_axis = "Total_Amount"

        fig_desc = px.bar(top_desc, x=y_axis, y="description_clean", orientation='h', text=y_axis, color="Category")
        fig_desc.update_layout(yaxis={'categoryorder': 'total ascending'})
        if sort_mode == "Total Spent ($)":
            fig_desc.update_traces(texttemplate="$%{text:,.0f}")
        st.plotly_chart(fig_desc, use_container_width=True)
    else:
        st.info("No data for trends.")

# ----------------- TABLE ----------------- #
st.divider()
st.subheader("Detailed Transaction Log")
display_df = filtered_df[["date", "category", "description", "amount"]].sort_values("date", ascending=False)
st.dataframe(display_df.style.format({"amount": "${:,.2f}", "date": "{:%Y-%m-%d}"}), use_container_width=True,
             height=500)