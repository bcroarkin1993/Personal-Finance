import streamlit as st
import pandas as pd


def display_budgeting_section():
    st.header("Budgeting Section")

    # Load Excel Data
    uploaded_file = st.file_uploader("Upload your Expense/Income Excel File", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Data Preview:")
        st.dataframe(df)

        # Summary Metrics
        total_income = df[df['Type'] == 'Income']['Amount'].sum()
        total_expenses = df[df['Type'] == 'Expense']['Amount'].sum()
        savings = total_income - total_expenses

        st.metric("Total Income", f"${total_income:,.2f}")
        st.metric("Total Expenses", f"${total_expenses:,.2f}")
        st.metric("Savings", f"${savings:,.2f}")

        # Expense Visualization
        st.subheader("Expense Breakdown")
        expense_breakdown = df[df['Type'] == 'Expense'].groupby('Category')['Amount'].sum()
        st.bar_chart(expense_breakdown)
