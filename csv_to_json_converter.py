import pandas as pd
import re

def format_column_name(column_name):
    # Remove undesirable characters
    column_name = re.sub(r"[^a-zA-Z0-9\s]", "", column_name)
    
    # Replace spaces with underscores and convert to lowercase
    return column_name.replace(" ", "_").lower()

def csv_to_json(csv_file_path, json_file_path):
    # Read the CSV data into a pandas DataFrame
    df = pd.read_csv(csv_file_path)

    # Format the column names
    df.columns = [format_column_name(col) for col in df.columns]

    # Convert the DataFrame to JSON format
    json_data = df.to_json(orient='records', lines=True)

    # Write the JSON data to a file
    with open(json_file_path, 'w') as json_file:
        json_file.write(json_data)

# Example Usage
csv_file_path = 'mothersheet_current.csv'
json_file_path = 'mothersheet_current.json'
csv_to_json(csv_file_path, json_file_path)
