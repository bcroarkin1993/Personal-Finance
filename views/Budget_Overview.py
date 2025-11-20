import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Budget Overview")

# Example: Load budget data
budget_data = pd.read_csv("app/data/budget_data.csv")

# Key metrics
total_income = budget_data['Income'].sum()
total_expenses = budget_data['Expenses'].sum()
savings_rate = (total_income - total_expenses) / total_income * 100

st.metric("Total Income", f"${total_income:,.2f}")
st.metric("Total Expenses", f"${total_expenses:,.2f}")
st.metric("Savings Rate", f"{savings_rate:.2f}%")

# Pie chart for expenses
fig = px.pie(budget_data, values="Expenses", names="Category", title="Expense Breakdown")
st.plotly_chart(fig)
