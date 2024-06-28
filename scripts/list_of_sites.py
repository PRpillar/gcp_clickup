import os
import requests
import pandas as pd
import json

from oauth2client.service_account import ServiceAccountCredentials
import gspread

def get_all_tasks_from_list(list_id, auth_clickup):
    all_tasks = []  # List to store all tasks across pages
    page = 0  # Start from first page
    while True:  # Keep looping until break is called
        # Include subtasks and closed tasks in the request
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task?archived=false&subtasks=true&include_closed=true&page={page}"
        response = requests.get(url, headers={"Authorization": auth_clickup})
        tasks = response.json().get('tasks', [])
        if not tasks:  # Break the loop if no more tasks are returned
            break
        all_tasks.extend(tasks)  # Add the tasks from the current page to the list
        page += 1  # Move to the next page
    return pd.json_normalize(all_tasks)  # Convert all tasks into a DataFrame


def process_custom_fields(tasks_df):
    custom_fields_data = []

    for _, task in tasks_df.iterrows():
        task_custom_fields = {'id': task['id']}

        for field in task['custom_fields']:
            field_name = field['name']
            if field['type'] == 'drop_down' and 'options' in field['type_config']:
                # Map the drop_down value (orderindex) to the corresponding name
                selected_option_index = field.get('value', None)
                options = field['type_config']['options']
                # Find the option name by matching the orderindex since 'value' appears to correspond to orderindex
                selected_option = next((opt['name'] for opt in options if str(opt['orderindex']) == str(selected_option_index)), None)
                task_custom_fields[field_name] = selected_option
            elif 'value' in field:
                # Process other types of fields as before
                task_custom_fields[field_name] = field['value']
            else:
                # Handle fields with no value or different configurations
                task_custom_fields[field_name] = None

        custom_fields_data.append(task_custom_fields)

    custom_fields_df = pd.DataFrame(custom_fields_data)
    return tasks_df.merge(custom_fields_df, on='id')

# Define the scope
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Load credentials
auth_clickup = os.getenv('CLICKUP_API_KEY_2') or json.load(open('../credentials.json'))['clickup']['api_key_2']
list_id = '54932029'  # Replace with your list ID
service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT') or json.load(open('../credentials.json'))['google']['service_account']
google_sheet_url = 'https://docs.google.com/spreadsheets/d/1o4w3ppIcA8iF-4vx6LCRiHFpVI1fHC7dwe7IiQoOb08/edit?gid=0#gid=0'
sheet_websites = 'List of Sites'

# Check if the environment variable is a string and parse it as JSON
if service_account_info and isinstance(service_account_info, str):
    service_account_info = json.loads(service_account_info)

# List of columns to keep
columns_to_keep = [
    "id", "name", "Reviews", "Article", "Listing price from", 
    "Payment frequency", "Example Reviews", "Example Articles", 
    "Example Listing", "Update", "Media Kit", "Comments Media", "Publishing features",
    "For Task Generation", "Создание аккаунтов",
]

# Apply the function to tasks DataFrame
tasks_df = get_all_tasks_from_list(list_id, auth_clickup)

# Process tasks filtered by status
processed_tasks_df = process_custom_fields(tasks_df)

# Convert specific columns to numeric values. Errors='coerce' will turn non-convertible values to NaN, which Google Sheets interprets as empty cells.
processed_tasks_df['Reviews'] = pd.to_numeric(processed_tasks_df['Reviews'], errors='coerce')
processed_tasks_df['Article'] = pd.to_numeric(processed_tasks_df['Article'], errors='coerce')
processed_tasks_df['Listing price from'] = pd.to_numeric(processed_tasks_df['Listing price from'], errors='coerce')

# This avoids KeyErrors if some custom fields are missing for some tasks
final_df = processed_tasks_df.reindex(columns=columns_to_keep).fillna('')

# Convert DataFrame to a list of lists, including the header, for Google Sheets update
values_to_update = [final_df.columns.tolist()] + final_df.values.tolist()

# Writing the data into a Google Sheets file
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(google_sheet_url).worksheet(sheet_websites)

# Clear existing contents of the sheet before updating with new data
sheet.clear()

# Update Google Sheet starting from cell A1; use named arguments for clarity and future-proofing
sheet.update(values=values_to_update, range_name='A1')
