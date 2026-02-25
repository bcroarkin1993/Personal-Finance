import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from scripts.data_processing import load_and_preprocess_data, clear_all_caches
from scripts.navigation import make_sidebar
from scripts.utils import clean_amount_column, render_freshness_badge, render_refresh_status, run_subprocess_refresh

# ----------------- PAGE CONFIG ----------------- #
st.set_page_config(page_title="Income Analysis", page_icon="💵", layout="wide")

# ----------------- INJECT SIDEBAR ----------------- #
make_sidebar("Income Analysis")

col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("💵 Income Analysis")
with col_refresh:
    st.markdown("<div style='padding-top:12px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        run_subprocess_refresh(
            "scripts/process_budget_data.py",
            clear_all_caches,
            "Processing Budget.xlsx...",
        )

render_refresh_status()

# ----------------- DATA LOADING & CLEANING ----------------- #
data = load_and_preprocess_data()
income_df = data["income"].copy()

# Freshness badge
if not income_df.empty and "date" in income_df.columns:
    render_freshness_badge(pd.to_datetime(income_df["date"], errors="coerce").max(), label="Income data through")

# Rename Source -> Category for consistency
if "source" in income_df.columns:
    income_df = income_df.rename(columns={"source": "category"})


income_df = clean_amount_column(income_df)
income_df["date"] = pd.to_datetime(income_df["date"], errors="coerce")
income_df = income_df.dropna(subset=["date"])

# FIX 1: Handle missing description column by using Category/Source
# In income.csv, 'Source' acts as the description.
income_df["description_clean"] = income_df["category"].fillna("").astype(str).str.strip().str.upper()

# ----------------- FILTERS ----------------- #
with st.container():
    st.subheader("Filters")
    f_col1, f_col2, f_col3 = st.columns(3)

    # Date Limits
    if not income_df.empty:
        min_date = income_df["date"].min().date()
        max_date = income_df["date"].max().date()
    else:
        min_date = date.today()
        max_date = date.today()

    # Default Date Logic (Clamped to avoid errors)
    default_start = date(date.today().year, 1, 1)
    # Ensure default end is not in the future relative to data if data ends early
    default_end = min(date.today(), max_date)
    # Ensure start is valid
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

    # FIX 2: Sort Categories by Amount (Highest First)
    # This prevents the messy list by showing important sources at the top
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
total_income = filtered_df["amount"].sum()
transaction_count = len(filtered_df)
avg_transaction = total_income / transaction_count if transaction_count > 0 else 0.0

st.divider()
col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"${total_income:,.2f}")
col2.metric("Transactions", f"{transaction_count}")
col3.metric("Avg Transaction", f"${avg_transaction:,.2f}")
st.divider()

# ----------------- VISUALIZATION ----------------- #
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("Income by Source")
    if not filtered_df.empty:
        cat_group = filtered_df.groupby("category")["amount"].sum().reset_index()
        fig_cat = px.pie(cat_group, values="amount", names="category", hole=0.4, title="Income Distribution")
        fig_cat.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No data for chart.")

with c2:
    st.subheader("Top Sources (Bar)")
    if not filtered_df.empty:
        # Since Description IS Category for income, this is just a bar chart version of the pie
        desc_group = (
            filtered_df.groupby("category")
                .agg(Total_Amount=("amount", "sum"), Count=("amount", "count"))
                .reset_index().sort_values(by="Total_Amount", ascending=False)
        )

        # Display Top 10
        fig_desc = px.bar(
            desc_group.head(10),
            x="Total_Amount",
            y="category",
            orientation='h',
            text="Total_Amount",
            title="Top Income Sources by Value"
        )
        fig_desc.update_layout(yaxis={'categoryorder': 'total ascending'})
        fig_desc.update_traces(texttemplate="$%{text:,.0f}")
        st.plotly_chart(fig_desc, use_container_width=True)
    else:
        st.info("No data for trends.")

# ----------------- TABLE ----------------- #
st.divider()
st.subheader("Income Log")
# Explicitly show 'category' as 'Source' since that's what the user knows
display_cols = ["date", "category", "amount"]
if "description" in filtered_df.columns and not filtered_df["description"].isna().all():
    display_cols.append("description")

display_df = filtered_df[display_cols].rename(columns={"category": "Source"}).sort_values("date", ascending=False)
st.dataframe(display_df.style.format({"amount": "${:,.2f}", "date": "{:%Y-%m-%d}"}), use_container_width=True,
             height=500)