import pandas as pd

def csv_to_json(csv_file_path, json_file_path):
    # Read the CSV data into a pandas DataFrame
    df = pd.read_csv(csv_file_path)

    # Convert the DataFrame to JSON format
    json_data = df.to_json(orient='records', lines=True)

    # Write the JSON data to a file
    with open(json_file_path, 'w') as json_file:
        json_file.write(json_data)

# Example Usage
csv_file_path = 'mothersheet_2023.csv'
json_file_path = 'mothersheet_2023.json'
csv_to_json(csv_file_path, json_file_path)
