import os
import pandas as pd
import streamlit as st
import subprocess
from scripts.data_processing import load_and_preprocess_data

### FORMAT STREAMLIT PAGE ###
st.set_page_config(page_title="Personal Finance Tracker",
                   page_icon="💰",
                   layout="wide")

# Sidebar Navigation
st.sidebar.title("Navigation")

# Define Navigation Options
pages = {
    "Home": "main.py",
    "Budget Overview": "views/Budget_Overview.py",
    "Income Analysis": "views/Income.py",
    "Expense Breakdown": "views/Expenses.py",
    "Portfolio Overview": "views/Portfolio_Overview.py",
    "Industry & Sector Breakdown": "views/Industry_&_Sector_Breakdown.py",
    "Company Deep-Dive": "views/Company_Deep-Dive.py",
    "Investment Opportunities": "views/Buying_Opportunities.py",
}

# Subheader for Home
st.sidebar.subheader("🏠 Home")
home_page = st.sidebar.radio(
    "Go to Home:",
    options=["Home"],
    index=0,
    label_visibility="collapsed"
)

# Subheader for Budget Pages
st.sidebar.subheader("📊 Budget Pages")
budget_page = st.sidebar.radio(
    "Go to Budget Page:",
    options=["Budget Overview", "Income Analysis", "Expense Breakdown"],
    index=0,
    label_visibility="collapsed"
)

# Subheader for Investment Pages
st.sidebar.subheader("📈 Investment Pages")
investment_page = st.sidebar.radio(
    "Go to Investment Page:",
    options=["Portfolio Overview", "Buying Opportunities"],
    index=0,
    label_visibility="collapsed"
)

# Navigation Logic
selected_page = None
if home_page == "Home":
    selected_page = "Home"
elif budget_page in ["Budget Overview", "Income Analysis", "Expense Breakdown"]:
    selected_page = budget_page
elif investment_page in ["Investment Opportunities", "Portfolio Overview"]:
    selected_page = investment_page

# Navigate to Selected Page
if selected_page == "Home":
    st.query_params.clear()
else:
    page_file = pages[selected_page]
    st.query_params.update({"page": page_file})

# Main Content for Home Page
if selected_page == "Home":
    st.title("Welcome to Your Personal Finance Tracker 💼")

    # Introduction
    st.write(
        """
        Manage and analyze your finances effectively. This app is divided into **two main sections**:
        - **Budget**: Track your income and expenses to identify saving opportunities and manage your spending habits.
        - **Investments**: Monitor your portfolio performance, including brokerage accounts and retirement accounts.
        """
    )

    def get_last_refresh_date(file_path, date_column):
        try:
            if os.path.exists(file_path):
                data = pd.read_csv(file_path)
                last_date = pd.to_datetime(data[date_column]).max()
                return last_date.strftime("%Y-%m-%d")
            else:
                return "No data available"
        except Exception as e:
            return f"Error: {e}"

    def calculate_average_monthly_expenses(expenses):
        """
        Function to calculate the average monthly expenses for the year from the expenses DataFrame.

        :param expenses: pd.DataFrame
            DataFrame containing expense data with at least 'Amount' and 'Date' columns.
        :return: float
            Average monthly expense total.
        """
        try:
            # Ensure the 'Date' column is in datetime format
            expenses['Date'] = pd.to_datetime(expenses['Date'])

            # Filter expenses for the current year
            current_year = pd.Timestamp.now().year
            expenses_this_year = expenses[expenses['Date'].dt.year == current_year]

            # Group by month and calculate total expenses per month
            monthly_totals = expenses_this_year.groupby(expenses_this_year['Date'].dt.month)['Amount'].sum()

            # Calculate the average monthly expense
            average_monthly_expenses = monthly_totals.mean()
            return average_monthly_expenses

        except Exception as e:
            st.error(f"Error calculating average monthly expenses: {e}")
            return 0

    def calculate_average_monthly_income(income):
        """
        Function to calculate the average monthly income for the year from the income DataFrame.

        :param income: pd.DataFrame
            DataFrame containing income data with at least 'Amount' and 'Date' columns.
        :return: float
            Average monthly income total.
        """
        try:
            # Ensure the 'Date' column is in datetime format
            income['Date'] = pd.to_datetime(income['Date'])

            # Filter income for the current year
            current_year = pd.Timestamp.now().year
            income_this_year = income[income['Date'].dt.year == current_year]

            # Group by month and calculate total income per month
            monthly_totals = income_this_year.groupby(income_this_year['Date'].dt.month)['Amount'].sum()

            # Calculate the average monthly income
            average_monthly_income = monthly_totals.mean()
            return average_monthly_income

        except Exception as e:
            st.error(f"Error calculating average monthly income: {e}")
            return 0

    ### PULL IN & FORMAT DATA ###

    # Load preprocessed data
    data = load_and_preprocess_data()

    # Access dataframes
    stocks = data["stocks"]
    stock_info = data["stock_info"]
    daily_stocks = data["daily_stocks"]
    income = data["income"]
    expenses = data["expenses"]

    # Load data for metrics
    monthly_income = calculate_average_monthly_income(income)
    monthly_expenses = calculate_average_monthly_expenses(expenses)

    # Fetch last refresh dates
    last_investment_refresh = get_last_refresh_date(daily_stocks, "Date")
    last_expenses_refresh = get_last_refresh_date(expenses, "Date")

    # Divide the layout into two main sections
    col1, col2 = st.columns(2)

    # Section 1: Budget Overview
    with col1:
        st.subheader("📊 Budget Overview")
        st.write(
            """
            The Budget section allows you to:
            - **View income and expenses**: Analyze your cash flow to ensure you're saving efficiently.
            - **Explore insights**: Identify your largest expense categories and potential areas for cost savings.
            """
        )
        # List views in the Budget section
        st.write("### Available Pages:")
        st.markdown("- **[Budget Overview](Budget_Overview.py)**")
        st.markdown("- **[Income Analysis](Income.py)**")
        st.markdown("- **[Expenses Breakdown](Expenses.py)**")

        # Quick Stats
        st.write("### Quick Stats:")
        st.metric("Total Income", f"${annual_income:,.2f}")
        st.metric("Total Expenses", f"${total_expenses:,.2f}")
        st.metric("Savings Rate", f"{savings_rate:.2f}%")

        # List the data refresh date
        st.write(f"**Budget Data Last Refreshed:** {last_expenses_refresh}")

        # Add button to run budget data refresh script
        if st.button("Update Budget Data"):
            try:
                # Run the process_budget_data.py script
                subprocess.run(["python", "scripts/process_budget_data.py"], check=True)
                st.success("Budget data updated successfully!")
            except Exception as e:
                st.error(f"Failed to update budget data: {e}")

    # Section 2: Investments Overview
    with col2:
        st.subheader("📈 Investments Overview")
        st.write(
            """
            The Investments section helps you:
            - **Track your portfolio**: See your holdings, gains/losses, and overall performance.
            - **Analyze retirement accounts**: Dive into your 401K, Roth IRA, and Brokerage Accounts for detailed insights.
            """
        )
        # List views in the Investments section
        st.write("### Available Pages:")
        st.markdown("- **[Portfolio Overview](Portfolio_Overview.py)**")
        st.markdown("- **[Company Deep-Dive](Company_Deep-Dive.py)**")
        st.markdown("- **[Industry & Sector Breakdown](Industry_&_Sector_Breakdown.py)**")
        st.markdown("- **[Buying Opportunities](Buying_Opportunities.py)**")

        # Add a chart as a preview of Investments Overview
        st.write("### Portfolio Snapshot:")
        st.metric("Total Portfolio Value", "$200,000")
        st.metric("Brokerage Accounts", "$120,000")
        st.metric("Retirement Accounts", "$80,000")

        # List the data refresh date
        st.write(f"**Investment Data Last Refreshed:** {last_investment_refresh}")

        # Add button to run investment data refresh scripts
        if st.button("Update Investment Data"):
            try:
                # Run the process_investment_data.py script
                subprocess.run(["python", "scripts/process_investment_data.py"], check=True)
                st.success("Investment data updated successfully!")
            except Exception as e:
                st.error(f"Failed to update investment data: {e}")

    # Add a footer with additional information
    st.markdown("---")
    st.write(
        """
        📌 **Tip**: Navigate to specific views from the sidebar to explore details of your finances.
        """
    )