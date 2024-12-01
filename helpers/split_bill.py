from collections import defaultdict, Counter
import os
import pandas as pd

def split_bill(file_name, tax, tip):
    # Define the input folder and full file path
    input_folder = 'input'
    file_path = os.path.join(input_folder, file_name)

    # Check if the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File '{file_name}' not found in the 'input' folder.")

    # Read the CSV file
    df = pd.read_csv(file_path)

    # Ensure the necessary columns are present
    required_columns = ['Item', 'Cost', 'Quantity', 'Total', 'Owner']
    if not all(col in df.columns for col in required_columns):
        print("Current Columns: ", df.columns)
        raise ValueError(f"CSV file must contain these columns: {required_columns}")

    # Split 'Owner' column into lists and normalize names to title case
    df['Owner'] = df['Owner'].str.split(' & ').apply(lambda owners: [owner.strip().title() for owner in owners])

    # Initialize dictionaries for subtotals and items
    subtotals = defaultdict(float)
    person_items = defaultdict(list)

    # Calculate individual subtotals and track items for each person
    for _, row in df.iterrows():
        item, cost, quantity, total_cost, owners = row['Item'], row['Cost'], row['Quantity'], row['Total'], row['Owner']
        num_owners = len(owners)

        # Calculate each person's proportional share of the total quantity and cost
        portion_quantity = quantity / num_owners  # Quantity per owner
        portion_cost = cost * portion_quantity  # Proportional cost per owner

        for owner in owners:
            subtotals[owner] += portion_cost
            # Track each person's share with the correct format
            person_items[owner].append(
                f"{item} (${cost}) x {portion_quantity:.2f} portion = ${portion_cost:.2f}"
            )

    # Aggregate all items for the summary section
    item_counter = Counter()
    for _, row in df.iterrows():
        item_counter[row['Item']] += row['Quantity']

    # Calculate the total amount of all items
    total_items_cost = sum(subtotals.values())

    # Calculate proportional share of tax and tip for each person
    total_tax_and_tip = tax + tip
    shares = {}
    for person, subtotal in subtotals.items():
        person_tax = (subtotal / total_items_cost) * tax
        person_tip = (subtotal / total_items_cost) * tip
        grand_total = subtotal + person_tax + person_tip
        shares[person] = (subtotal, person_tax, person_tip, grand_total)

    # Print the final bill breakdown for each person
    print("\nFinal Bill Breakdown:")
    for person, (subtotal, person_tax, person_tip, grand_total) in shares.items():
        print(f"\n{person}")
        print("Items:")
        for item in person_items[person]:
            print(f"  - {item}")
        print(f"[Tax] = ${person_tax:.2f}")
        print(f"[Tip] = ${person_tip:.2f}")
        print(f"[GRAND TOTAL] = ${grand_total:.2f}")

    # Print overall summary of all items, aggregated by item name
    print("\nSummary of All Items:")
    for item, quantity in item_counter.items():
        print(f"{item} (x{quantity})")

    # Check summary: Total, Tax, and Tip breakdown
    total_with_tax = total_items_cost + tax
    tip_percentage = (tip / total_with_tax) * 100

    print("\nCheck Summary:")
    print(f"Subtotal (Items) = ${total_items_cost:.2f}")
    print(f"Tax = ${tax:.2f}")
    print(f"Total (Items + Tax) = ${total_with_tax:.2f}")
    print(f"Tip = ${tip:.2f} ({tip_percentage:.2f}%)")
    print(f"Grand Total (All-In) = ${total_with_tax + tip:.2f}")

    return shares

# Example usage:
file_path = '101824_palette_22.csv'  # Replace with your CSV file path
tax = 30.1  # Example tax amount
tip = 60.2  # Example tip amount

split_bill(file_path, tax, tip)



