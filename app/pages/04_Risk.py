import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

### FORMAT STREAMLIT PAGE ###
st.set_page_config(layout="wide")
# Title
st.title("Investment Dashboard - Risk")
# Today's Date
today = datetime.date.today()
st.subheader(f"Today's Date is {today}")

# Pull in tables from session_state
stocks_complete = st.session_state['stocks_complete']

# Create display options
companies = st.slider("Choose Number of Companies", 1, 60)

### BETA BAR CHART ###

# Remove null Beta value companies
beta_stocks = stocks_complete.dropna(subset=["Beta"])
# Filter stocks
beta_stocks = beta_stocks.sort_values("Beta", axis=0, ascending=True)
beta_stocks = beta_stocks.tail(companies)

# Create Plotly
fig = px.bar(beta_stocks, x='Beta', y='Stock', title = "Beta Risk by Company", hover_name = 'Stock',
             hover_data = {
                 'Market_Value': ':.2f',
                 'Stock': False
            })

# Plot!
st.plotly_chart(fig, use_container_width=True)

### BUY/HOLD/SELL RATING BAR CHART ###

# Filter stocks
rating_stocks = stocks_complete[['Stock', 'Buy_Ratio', 'Hold_Ratio', 'Sell_Ratio']]
# Remove null Buy ratio companies
rating_stocks = rating_stocks.dropna(subset=["Buy_Ratio"])
# Filter stocks
rating_stocks = rating_stocks.sort_values("Buy_Ratio", axis = 0, ascending = True)
rating_stocks = rating_stocks.tail(companies)

# shape from wide to long with melt function in pandas
rating_stocks = pd.melt(rating_stocks, id_vars=['Stock'], var_name='Rating_Type', value_name='Rating')

# Create Plotly
fig2 = px.bar(rating_stocks, x = 'Stock', y = 'Rating', color = 'Rating_Type')

# Plot!
st.plotly_chart(fig2, use_container_width=True)