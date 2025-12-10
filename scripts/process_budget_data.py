import pandas as pd
import os
import argparse
import sys
from datetime import datetime, date
from pathlib import Path

# ----------------- CONFIGURATION ----------------- #

# Resolve paths relative to this script
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
DATA_DIR = PROJECT_ROOT / 'data'

# Input File Path
HOME_DIR = Path.home()
BUDGET_FILE = HOME_DIR / "Documents" / "Personal-Finance" / "Budget" / "Budget.xlsx"

# Output File Paths
INCOME_CSV = DATA_DIR / 'income.csv'
EXPENSES_CSV = DATA_DIR / 'expenses.csv'
MONTHLY_BUDGET_CSV = DATA_DIR / 'monthly_budget.csv'


# ----------------- HELPER FUNCTIONS ----------------- #

def get_cutoff_date(csv_path):
    """
    Finds the max date in the CSV and returns the 1st of that month.
    This ensures we re-process the current active month to capture edits.
    """
    if not csv_path.exists():
        return None

    try:
        df = pd.read_csv(csv_path)
        if df.empty or 'Date' not in df.columns:
            return None

        # Parse dates with coercion to handle garbage rows
        dates = pd.to_datetime(df['Date'], errors='coerce').dropna()
        if dates.empty:
            return None

        max_date = dates.max()
        # Return the 1st day of the max_date's month
        return max_date.replace(day=1)
    except Exception as e:
        print(f"Warning reading {csv_path}: {e}")
        return None


def process_budget_excel(budget_file, income_csv_path, expenses_csv_path, monthly_budget_csv_path, full_refresh=False):
    """
    Parses the Budget Excel file incrementally or fully.
    Now also scrapes the 'Budget v Actual' sheet for budget targets.
    """
    print(f"Processing Budget Data (Mode: {'FULL' if full_refresh else 'INCREMENTAL'})...")

    # 1. Determine Cutoff Date
    cutoff_date = None
    if not full_refresh:
        inc_cutoff = get_cutoff_date(income_csv_path)
        exp_cutoff = get_cutoff_date(expenses_csv_path)

        # Take the earlier of the two dates to be safe
        if inc_cutoff and exp_cutoff:
            cutoff_date = min(inc_cutoff, exp_cutoff)
        elif inc_cutoff:
            cutoff_date = inc_cutoff
        elif exp_cutoff:
            cutoff_date = exp_cutoff

        if cutoff_date:
            print(f"   > Cutoff Date: {cutoff_date.strftime('%Y-%m-%d')} (Re-processing from here)")
        else:
            print("   > No valid history found. Defaulting to FULL refresh.")

    # 2. Load Existing History (Pre-Cutoff)
    history_expenses = pd.DataFrame(columns=['Amount', 'Date', 'Expense_Category', 'Description'])
    history_income = pd.DataFrame(columns=['Source', 'Amount', 'Date'])

    if cutoff_date:
        try:
            if expenses_csv_path.exists():
                hist_exp = pd.read_csv(expenses_csv_path)
                hist_exp['Date'] = pd.to_datetime(hist_exp['Date'], errors='coerce')
                history_expenses = hist_exp[hist_exp['Date'] < cutoff_date].copy()

            if income_csv_path.exists():
                hist_inc = pd.read_csv(income_csv_path)
                hist_inc['Date'] = pd.to_datetime(hist_inc['Date'], errors='coerce')
                history_income = hist_inc[hist_inc['Date'] < cutoff_date].copy()

            print(
                f"   > Retained {len(history_income)} income and {len(history_expenses)} expense records from history.")
        except Exception as e:
            print(f"   > Error loading history: {e}. Switching to FULL refresh.")
            cutoff_date = None
            history_expenses = history_expenses.iloc[0:0]  # clear
            history_income = history_income.iloc[0:0]  # clear

    # 3. Parse Excel (New Data)
    print(f"   > Reading Excel file: {budget_file}")
    if not budget_file.exists():
        print(f"CRITICAL ERROR: File not found at {budget_file}")
        return

    try:
        # Load all sheets
        budget_xlsx = pd.read_excel(budget_file, engine='openpyxl', sheet_name=None)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # --- PART A: TRANSACTION LOGS ---
    new_expenses_list = []
    new_income_list = []

    for sheet_name, _ in budget_xlsx.items():
        # Only process sheets containing "Monthly Budget"
        if 'Monthly Budget' in sheet_name:

            # --- PROCESS EXPENSES ---
            try:
                # Try standard format (skiprows=13)
                expenses = pd.read_excel(
                    budget_file, engine='openpyxl', sheet_name=sheet_name,
                    skiprows=13, usecols=['Amount', 'Date', 'Expense Category', 'Description']
                )
            except ValueError:
                try:
                    # Fallback for slight format shift (skiprows=14)
                    expenses = pd.read_excel(
                        budget_file, engine='openpyxl', sheet_name=sheet_name,
                        skiprows=14, usecols=['Amount', 'Date', 'Expense Category', 'Description']
                    )
                except Exception:
                    expenses = pd.DataFrame()

            if not expenses.empty:
                expenses = expenses.rename(columns={'Expense Category': 'Expense_Category'})
                expenses = expenses.dropna(how='any')
                expenses['Date'] = pd.to_datetime(expenses['Date'], errors='coerce')
                expenses = expenses.dropna(subset=['Date'])

                # INCREMENTAL FILTER
                if cutoff_date:
                    expenses = expenses[expenses['Date'] >= cutoff_date]

                if not expenses.empty:
                    new_expenses_list.append(expenses)

            # --- PROCESS INCOME ---
            try:
                income = pd.read_excel(
                    budget_file, engine='openpyxl', sheet_name=sheet_name,
                    skiprows=13, usecols=['Source', 'Amount.1', 'Date Received']
                )
            except ValueError:
                try:
                    income = pd.read_excel(
                        budget_file, engine='openpyxl', sheet_name=sheet_name,
                        skiprows=14, usecols=['Source', 'Amount.1', 'Date Received']
                    )
                except Exception:
                    income = pd.DataFrame()

            if not income.empty:
                income = income.rename(columns={'Amount.1': 'Amount', 'Date Received': 'Date'})
                income = income.dropna(how='any')
                income['Date'] = pd.to_datetime(income['Date'], errors='coerce')
                income = income.dropna(subset=['Date'])

                # INCREMENTAL FILTER
                if cutoff_date:
                    income = income[income['Date'] >= cutoff_date]

                if not income.empty:
                    new_income_list.append(income)

    # --- PART B: BUDGET TARGETS (Budget v Actual) ---
    print("   > Processing Budget Targets (Budget v Actual)...")
    if 'Budget v Actual' in budget_xlsx:
        try:
            # Read Columns A:K (Date, Rent... Disposable)
            # Header is in row 2 (index 1), so skiprows=1
            budget_targets = pd.read_excel(
                budget_file,
                engine='openpyxl',
                sheet_name='Budget v Actual',
                header=1,  # Row 2 is header
                usecols="A:K"
            )

            # Rename for consistency
            budget_targets.rename(columns=lambda x: x.strip() if isinstance(x, str) else x, inplace=True)

            # Ensure Date is parsed
            if 'Date' in budget_targets.columns:
                budget_targets['Date'] = pd.to_datetime(budget_targets['Date'], errors='coerce')
                budget_targets = budget_targets.dropna(subset=['Date'])

                # Melt into Long Format: [Date, Category, Budget_Amount]
                # This makes plotting easier (Category as color)
                budget_long = budget_targets.melt(
                    id_vars=['Date'],
                    var_name='Category',
                    value_name='Budget_Amount'
                )

                # Save
                budget_long.to_csv(monthly_budget_csv_path, index=False)
                print(f"   > Saved {len(budget_long)} budget target records to {monthly_budget_csv_path}")
            else:
                print("   > Warning: 'Date' column not found in 'Budget v Actual' sheet.")
        except Exception as e:
            print(f"   > Error processing Budget v Actual sheet: {e}")
    else:
        print("   > Warning: 'Budget v Actual' sheet not found.")

    # 4. Merge & Deduplicate Transactions
    new_expenses_df = pd.concat(new_expenses_list, ignore_index=True) if new_expenses_list else pd.DataFrame()
    new_income_df = pd.concat(new_income_list, ignore_index=True) if new_income_list else pd.DataFrame()

    print(f"   > Parsed {len(new_income_df)} new income rows and {len(new_expenses_df)} new expense rows.")

    final_expenses = pd.concat([history_expenses, new_expenses_df], ignore_index=True)
    final_income = pd.concat([history_income, new_income_df], ignore_index=True)

    # Clean up
    final_expenses.drop_duplicates(inplace=True)
    final_income.drop_duplicates(inplace=True)

    final_expenses.sort_values('Date', ascending=False, inplace=True)
    final_income.sort_values('Date', ascending=False, inplace=True)

    # 5. Save Output
    final_expenses.to_csv(expenses_csv_path, index=False)
    final_income.to_csv(income_csv_path, index=False)

    print(f"Done. Saved transaction data to {expenses_csv_path} and {income_csv_path}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process Budget Excel File")
    parser.add_argument('--full', action='store_true', help="Force a full refresh of all data")
    args = parser.parse_args()

    print("BEGINNING BUDGET DATA PROCESSING")
    process_budget_excel(BUDGET_FILE, INCOME_CSV, EXPENSES_CSV, MONTHLY_BUDGET_CSV, full_refresh=args.full)