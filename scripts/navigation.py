import streamlit as st
from time import sleep

# Define the page directory to be used globally
PAGES = {
    "Home": "main.py",
    "Budget Overview": "pages/Budget_Overview.py",
    "Income Analysis": "pages/Income.py",
    "Expense Breakdown": "pages/Expenses.py",
    "Portfolio Overview": "pages/Portfolio_Overview.py",
    "Industry & Sector Breakdown": "pages/Industry_&_Sector_Breakdown.py",
    "Company Deep-Dive": "pages/Company_Deep-Dive.py",
    "Buying Opportunities": "pages/Buying_Opportunities.py",
    "Stock Peer Analysis": "pages/Stock_Peer_Analysis.py",
    "Holdings Leaderboard": "pages/Holdings_Leaderboard.py"
}


def make_sidebar(current_page_id):
    """
    Renders the custom sidebar and handles navigation.

    Args:
        current_page_id (str): The name of the page currently being rendered
                               (e.g., "Budget Overview").
    """

    # 1. HIDE DEFAULT STREAMLIT SIDEBAR
    st.html(
        """
        <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
        </style>
        """
    )

    # 2. INITIALIZE SESSION STATE
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = current_page_id

    # 3. DEFINE CALLBACK WITH SENDER
    def navigate(sender):
        """
        Updates the current page based on which widget was clicked (sender).
        Crucially, it sets the OTHER widgets to None to prevent 'Double Selection'
        and state conflicts.
        """
        if sender == "nav_home":
            st.session_state["current_page"] = "Home"
            st.session_state["nav_budget"] = None
            st.session_state["nav_invest"] = None

        elif sender == "nav_budget":
            st.session_state["current_page"] = st.session_state["nav_budget"]
            # Deselect the others
            st.session_state["nav_home"] = None
            st.session_state["nav_invest"] = None

        elif sender == "nav_invest":
            st.session_state["current_page"] = st.session_state["nav_invest"]
            # Deselect the others
            st.session_state["nav_home"] = None
            st.session_state["nav_budget"] = None

    # 4. RENDER SIDEBAR UI
    st.sidebar.title("Navigation")

    # Determine indices for radio buttons
    # We use index=None if the category is not active

    # Home
    home_index = 0 if st.session_state["current_page"] == "Home" else None

    # Budget
    budget_opts = ["Budget Overview", "Income Analysis", "Expense Breakdown"]
    try:
        b_index = budget_opts.index(st.session_state["current_page"])
    except ValueError:
        b_index = None

    # Invest
    invest_opts = [
        "Portfolio Overview", "Industry & Sector Breakdown", "Company Deep-Dive",
        "Buying Opportunities", "Peer Analysis", "Holdings Leaderboard"
    ]
    try:
        i_index = invest_opts.index(st.session_state["current_page"])
    except ValueError:
        i_index = None

    st.sidebar.subheader("🏠 Home")
    st.sidebar.radio(
        "Home Nav",
        options=["Home"],
        key="nav_home",
        label_visibility="collapsed",
        index=home_index,
        on_change=navigate,
        args=("nav_home",),  # Pass the sender key
    )

    st.sidebar.subheader("📊 Budget Pages")
    st.sidebar.radio(
        "Budget Nav",
        options=budget_opts,
        key="nav_budget",
        index=b_index,
        label_visibility="collapsed",
        on_change=navigate,
        args=("nav_budget",),
    )

    st.sidebar.subheader("📈 Investment Pages")
    st.sidebar.radio(
        "Invest Nav",
        options=invest_opts,
        key="nav_invest",
        index=i_index,
        label_visibility="collapsed",
        on_change=navigate,
        args=("nav_invest",),
    )

    # 5. HANDLE NAVIGATION REDIRECT
    if st.session_state["current_page"] != current_page_id:
        page_path = PAGES.get(st.session_state["current_page"])
        if page_path:
            st.switch_page(page_path)