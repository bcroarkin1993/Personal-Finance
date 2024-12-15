import streamlit as st
import pandas as pd
import plotly.express as px

st.title("Expenses")

# Load expenses data
expense_data = pd.read_csv("app/data/budget_data.csv")[['Category', 'Expenses']]

# Display a table of expenses
st.table(expense_data)

# Bar chart for expenses by category
fig = px.bar(expense_data, x="Category", y="Expenses", title="Expenses by Category")
st.plotly_chart(fig)
