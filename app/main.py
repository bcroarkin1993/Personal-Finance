import streamlit as st
from scripts.budgeting import display_budgeting_section
from scripts.investing import display_investing_section

# App Title
st.set_page_config(page_title="Personal Finance Tracker", layout="wide")
st.title("Personal Finance Tracker")

# Sidebar Navigation
st.sidebar.title("Navigation")
options = ["Budgeting", "Investing"]
choice = st.sidebar.radio("Go to:", options)

# Section Handling
if choice == "Budgeting":
    display_budgeting_section()
elif choice == "Investing":
    display_investing_section()
