import streamlit as st
import json
import pandas as pd


def display_investing_section():
    st.header("Investing Section")

    # Load JSON Data
    uploaded_file = st.file_uploader("Upload your Robinhood JSON File", type=["json"])
    if uploaded_file:
        data = json.load(uploaded_file)
        st.write("Data Preview:", data)

        # Convert JSON to DataFrame
        investments = pd.json_normalize(data, 'purchases')
        st.dataframe(investments)

        # Portfolio Summary
        total_investment = investments['purchase_price'].sum()
        st.metric("Total Investment", f"${total_investment:,.2f}")
