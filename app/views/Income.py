import streamlit as st
import pandas as pd

st.title("Income")

# Load income data
income_data = pd.read_csv("app/data/budget_data.csv")[['Source', 'Income']]
st.table(income_data)
