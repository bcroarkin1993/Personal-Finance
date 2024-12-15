import os
import json


def update_stock_dictionary():
    # Path to the data folder and the stock dictionary file
    data_folder = os.path.join(os.path.dirname(__file__), "data")
    file_path = os.path.join(data_folder, "stock_dictionary.json")

    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: The file {file_path} does not exist.")

        # Print all files in the data folder
        if os.path.exists(data_folder):
            print("\nFiles in the data folder:")
            for file_name in os.listdir(data_folder):
                print(f"- {file_name}")
        else:
            print("\nThe data folder does not exist or is empty.")
        return

    # Load the existing stock dictionary
    with open(file_path, 'r') as f:
        stock_data = json.load(f)

    # Update each stock entry with platform and account_type
    for ticker, details in stock_data.items():
        for transaction in details.get("purchase_history", []):
            transaction["platform"] = "Robinhood"
            transaction["account_type"] = "Taxable"

    # Save the updated dictionary back to the JSON file
    with open(file_path, 'w') as f:
        json.dump(stock_data, f, indent=4)
    print(f"Updated {file_path} with platform and account_type fields.")


# Run the function
update_stock_dictionary()
