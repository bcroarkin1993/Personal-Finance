# Personal Finance Tracker

## Overview
The Personal Finance Tracker is a Streamlit app designed to help users track, monitor, and advise on their personal finances. The app is divided into two main sections:

### 1. Budgeting
- Tracks income and expenses using an uploaded Excel spreadsheet.
- Visualizes spending habits and income sources.
- Provides budgeting recommendations and alerts for exceeding budget thresholds.

### 2. Investing
- Focuses on individual Robinhood transactions from a JSON file.
- Tracks portfolio performance and provides insights on diversification and market trends.
- Includes data from other investment sources like 401K, Roth IRA, and brokerage accounts.

## Project Structure


## Features
### Budgeting Section
- Upload and analyze an Excel file containing income and expense data.
- View metrics such as Total Income, Total Expenses, and Savings.
- Visualize spending habits through bar charts.

### Investing Section
- Upload and analyze a JSON file of Robinhood transactions.
- View total investment value and detailed transaction data.
- Gain insights into portfolio diversification.

## Usage
1. Clone the repository:
   ```bash
   git clone https://github.com/<USERNAME>/<REPO_NAME>.git
   cd personal_finance
   ```
   
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:
   ```bash
   streamlit run app/main.py
   ```
   
## Future Enhancements
- Advanced visualizations for investment trends and income-expense ratios.
- Integration with secure user authentication for historical data storage.
- Real-time investment advice and savings goal tracking.
- Leverage ChatGPT (or another LLM) to add additional analysis (https://finimize.com/content/how-use-chatgpt-analyze-stock?)
  - Identify key risks for a company from their earnings calls
  - Summarize earnings call
  - Perform a SWOT analysis
  - Give a high-level analysis of what a company does
  - Generate code to create buy/sell signals (RSI - relative strength index)