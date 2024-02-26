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
    # Initialize a list to hold the processed custom fields for all tasks
    custom_fields_data = []
    
    # Iterate through each task in the DataFrame
    for _, task in tasks_df.iterrows():
        # Each task's custom fields are stored in a dictionary {field_name: value}
        task_custom_fields = {}
        # Extract the task ID to associate custom fields with the correct task
        task_custom_fields['id'] = task['id']
        
        # Iterate through each custom field in the task
        for field in task['custom_fields']:
            field_name = field['name']
            # Ensure the field value is a list before iteration
            field_values = field.get('value', [])
            if not isinstance(field_values, list):  # Check if the value is not already a list
                field_values = [field_values]  # Make it a list for uniform processing
            
            # Process the custom field values
            selected_options = []
            if 'type_config' in field and 'options' in field['type_config']:
                # Convert selected option IDs into their corresponding labels
                for option in field['type_config']['options']:
                    if option['id'] in field_values:  # Now field_values is always a list, so this check is safe
                        selected_options.append(option['label'])
                field_value = ', '.join(selected_options)
            else:
                # If there are no predefined options, use the value directly (assumes single value, not list)
                field_value = field.get('value')
            
            task_custom_fields[field_name] = field_value
        
        # Add the processed custom fields for this task to the list
        custom_fields_data.append(task_custom_fields)
    
    # Convert the list of dictionaries into a DataFrame
    custom_fields_df = pd.DataFrame(custom_fields_data)
    
    # Merge the original tasks DataFrame with the new custom fields DataFrame
    # This will add each custom field as a separate column
    return tasks_df.merge(custom_fields_df, on='id')


# Define the scope
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Load credentials
auth_clickup = os.getenv('CLICKUP_API_KEY') or json.load(open('../credentials.json'))['clickup']['api_key']
list_id = '54932029'  # Replace with your list ID
service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT') or json.load(open('../credentials.json'))['google']['service_account']



# List of columns to keep
columns_to_keep = [
    "id", "name", "Reviews", "Article", "Listing price from", 
    "Payment frequency", "Example Reviews", "Example Articles", 
    "Example Listing", "Update", "Media Kit", "Comments Media"
]

# Apply the function to tasks DataFrame
tasks_df = get_all_tasks_from_list(list_id, auth_clickup)

# Filter tasks by status
approval_tasks_df = tasks_df[tasks_df['status.status'] == 'approval']

# Process tasks filtered by status
processed_tasks_df = process_custom_fields(approval_tasks_df)

# This avoids KeyErrors if some custom fields are missing for some tasks
final_df = processed_tasks_df.reindex(columns=columns_to_keep)

# Convert DataFrame to a list of lists, including the header
values_to_update = [final_df.columns.tolist()] + final_df.values.tolist()

# Writing the data into a Google Sheets file
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
websites_tab = "Websites"
sheet = client.open('Popular media by forex/CFD and Crypto').worksheet(websites_tab)

# Update Google Sheet starting from cell A2; use named arguments for clarity and future-proofing
sheet.update(values=values_to_update, range_name='A1')
