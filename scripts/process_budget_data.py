import os
import pandas as pd

def process_budget_excel(budget_file, income_csv_path, expenses_csv_path):
    """
    Parses the Budget Excel file to generate CSVs for expenses and income.

    Parameters:
    - budget_file: str
        Path to the Budget Excel file.
    - income_csv_path: str
        Path to save the output income CSV file.
    - expenses_csv_path: str
        Path to save the output expenses CSV file.

    Returns:
    - None
    """

    # Initialize master DataFrames
    expenses_df = pd.DataFrame(columns=['Amount', 'Date', 'Expense_Category', 'Description'])
    income_df = pd.DataFrame(columns=['Source', 'Amount', 'Date'])

    print("Reading the Budget Excel file...")
    try:
        # Load all sheets from the Excel file
        budget_xlsx = pd.read_excel(budget_file, engine='openpyxl', sheet_name=None)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Iterate over sheets and process relevant ones
    for sheet_name, sheet_data in budget_xlsx.items():
        if 'Monthly Budget' in sheet_name:
            print(f"Processing sheet: {sheet_name}")

            # Process Expenses
            try:
                expenses = pd.read_excel(
                    budget_file,
                    engine='openpyxl',
                    sheet_name=sheet_name,
                    skiprows=13,
                    usecols=['Amount', 'Date', 'Expense Category', 'Description']
                )
                expenses = expenses.rename(columns={'Expense Category': 'Expense_Category'})
            except:
                # Handle sheets with slightly different formats
                expenses = pd.read_excel(
                    budget_file,
                    engine='openpyxl',
                    sheet_name=sheet_name,
                    skiprows=14,
                    usecols=['Amount', 'Date', 'Expense Category', 'Description']
                )
                expenses = expenses.rename(columns={'Expense Category': 'Expense_Category'})

            # Drop rows with missing values
            expenses = expenses.dropna(how='any')

            # Append to master DataFrame
            expenses_df = pd.concat([expenses_df, expenses], ignore_index=True)

            # Process Income
            try:
                income = pd.read_excel(
                    budget_file,
                    engine='openpyxl',
                    sheet_name=sheet_name,
                    skiprows=13,
                    usecols=['Source', 'Amount.1', 'Date Received']
                )
                income = income.rename(columns={'Amount.1': 'Amount', 'Date Received': 'Date'})
            except:
                # Handle sheets with slightly different formats
                income = pd.read_excel(
                    budget_file,
                    engine='openpyxl',
                    sheet_name=sheet_name,
                    skiprows=14,
                    usecols=['Source', 'Amount.1', 'Date Received']
                )
                income = income.rename(columns={'Amount.1': 'Amount', 'Date Received': 'Date'})

            # Drop rows with missing values
            income = income.dropna(how='any')

            # Append to master DataFrame
            income_df = pd.concat([income_df, income], ignore_index=True)

    # Save the DataFrames to CSV files
    print("Saving expenses to CSV...")
    expenses_df.to_csv(expenses_csv_path, index=False)
    print(f"Expenses saved to: {expenses_csv_path}")

    print("Saving income to CSV...")
    income_df.to_csv(income_csv_path, index=False)
    print(f"Income saved to: {income_csv_path}")


if __name__ == '__main__':
    # Resolve paths dynamically
    home_dir = os.path.expanduser("~")
    budget_file = os.path.join(home_dir, "Documents", "Personal-Finance", "Budget", "Budget.xlsx")
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(scripts_dir)
    income_csv_path = os.path.join(app_dir, 'data', 'income.csv')
    expenses_csv_path = os.path.join(app_dir, 'data', 'expenses.csv')

    print("BEGINNING BUDGET ANALYSIS\n")

    # Run the budget processing function
    process_budget_excel(budget_file, income_csv_path, expenses_csv_path)
