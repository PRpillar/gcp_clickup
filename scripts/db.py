import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Get team members from ClickUp
def get_team_members(auth_clickup, team_id):
    try:
        url = f"https://api.clickup.com/api/v2/team/{team_id}"
        response = requests.get(url, headers={"Authorization": auth_clickup})
        response.raise_for_status()
        members = response.json().get('team', {}).get('members', [])
        return ','.join([str(member['user']['id']) for member in members])
    except requests.RequestException as e:
        print(f"Error fetching team members: {e}")
        return ''


# Function to get tasks from ClickUp
def get_tasks(team_id, auth_clickup):
    url = f"https://api.clickup.com/api/v2/team/{team_id}/task?archived=false"
    response = requests.get(url, headers={"Authorization": auth_clickup})
    tasks = pd.json_normalize(response.json(), record_path=['tasks'])
    return tasks


# Function to get spaces from ClickUp
def get_spaces(team_id, auth_clickup):
    url = f"https://api.clickup.com/api/v2/team/{team_id}/space?archived=false"
    response = requests.get(url, headers={"Authorization": auth_clickup})
    spaces = pd.json_normalize(response.json(), record_path=['spaces'])
    return spaces


def get_folders(team_id, auth_clickup):
    url = f"https://api.clickup.com/api/v2/team/{team_id}/folder"  # Update with correct endpoint
    response = requests.get(url, headers={"Authorization": auth_clickup})
    folders = pd.json_normalize(response.json(), record_path=['folders'])  # Update path as per API response
    return folders


# Get time entries from ClickUp
def get_time_entries(team_id, start_posix, now_posix, members_id, auth_clickup):
    url = f"https://api.clickup.com/api/v2/team/{team_id}/time_entries?start_date={start_posix}&end_date={now_posix}&assignee={members_id}"
    response = requests.get(url, headers={"Authorization": auth_clickup})
    return pd.json_normalize(response.json(), record_path=['data'])


def shorten_name(full_name):
    parts = full_name.split()
    if len(parts) > 1:
        return f'{parts[0][0]} {parts[-1]}'
    else:
        return full_name


# Convert to POSIX time
def to_posix(dt):
    return int(dt.timestamp() * 1000)


# Define the scope
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']


# Load credentials
auth_clickup = os.getenv('CLICKUP_API_KEY') or json.load(open('../credentials.json'))['clickup']['api_key']
service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT') or json.load(open('../credentials.json'))['google']['service_account']
team_id = os.getenv('TEAM_ID') or json.load(open('../credentials.json'))['team']['id']
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
team_name = "PRpillar"
time_entries_tab = "TT DB"
time_local = 'Europe/Moscow'
sheet = client.open('TEST ClickUp').worksheet(time_entries_tab)

# Read existing data from Google Sheets into DataFrame
existing_data = sheet.get_all_values()
headers = existing_data.pop(0)
existing_df = pd.DataFrame(existing_data, columns=headers)


# Current time and time 10 weeks ago in POSIX format
now_posix = to_posix(datetime.now(pytz.timezone(time_local)))
start_posix = to_posix(datetime.now(pytz.timezone(time_local)) - pd.Timedelta(weeks=10))


# Fetch members, tasks, and spaces data
members_id = get_team_members(auth_clickup, team_id)
tasks_df = get_tasks(team_id, auth_clickup)
spaces_df = get_spaces(team_id, auth_clickup)
folders_df = get_folders(team_id, auth_clickup)

time_entries_df = get_time_entries(team_id, start_posix, now_posix, members_id, auth_clickup)

# Convert to datetime
time_entries_df['start'] = pd.to_datetime(time_entries_df['start'].astype(int), unit='ms')
time_entries_df['end'] = pd.to_datetime(time_entries_df['end'].astype(int), unit='ms')

# Convert 'duration' to numeric (float), errors='coerce' will set non-numeric values to NaN
time_entries_df['duration'] = pd.to_numeric(time_entries_df['duration'], errors='coerce')

# Now perform the division to convert milliseconds to hours
time_entries_df['duration_hours'] = time_entries_df['duration'] / 3600000

# Now convert to strings
time_entries_df['start'] = time_entries_df['start'].dt.strftime('%Y-%m-%d %H:%M:%S')
time_entries_df['end'] = time_entries_df['end'].dt.strftime('%Y-%m-%d %H:%M:%S')

# Add 'dt_load' column with the current timestamp
time_entries_df['dt_load'] = datetime.now(pytz.timezone(time_local)).strftime('%Y-%m-%d %H:%M:%S')

# Replace NaN with None
time_entries_df = time_entries_df.where(pd.notna(time_entries_df), None)


final_df = pd.merge(time_entries_df, tasks_df, left_on='task.id', right_on='id', how='left', suffixes=('', '_task'))
final_df = pd.merge(final_df, spaces_df, left_on='task_location.space_id', right_on='id', how='left', suffixes=('', '_space'))
final_df = pd.merge(final_df, folders_df, left_on='task_location.folder_id', right_on='id', how='left', suffixes=('', '_folder'))

final_df['Project'] = team_name
final_df['err'] = None

final_df = final_df.rename(columns={
    'id': 'ID',
    'name_space': 'Space',
    'name_folder': 'Folder',
    'list.name': 'List',
    'task.name': 'Task',
    'user.username': 'Team Member',
    'description': 'Description',
    'task_url': 'Link to the task',
    'start': 'Start',
    'end': 'End',
    'duration_hours': 'Hours',
    'err': 'err',
    'dt_load': 'dt_load'
})

column_order = ['ID', 'Project', 'Space', 'Folder', 'List', 'Task', 'Team Member', 
                'Description', 'Link to the task', 'Start', 'End', 'Hours', 'err', 'dt_load']

final_df = final_df[column_order]
final_df['Team Member'] = final_df['Team Member'].apply(shorten_name)
final_df = final_df.sort_values(by=['Team Member', 'Start'], ascending=[True, False])

# Merge (upsert) the new data with existing data
merged_df = pd.merge(existing_df, final_df, on='ID', how='outer', suffixes=('_existing', '_new'))

# Use existing data where available, otherwise use new data
for column in merged_df.columns:
    if '_existing' in column:
        base_column = column.replace('_existing', '')
        merged_df[base_column] = merged_df[column].combine_first(merged_df[f'{base_column}_new'])

# Drop the temporary columns
merged_df.drop(columns=[col for col in merged_df.columns if '_new' in col or '_existing' in col], inplace=True)
merged_df = merged_df[column_order]
merged_df = merged_df.sort_values(by=['Team Member', 'Start'], ascending=[True, False])

# Convert DataFrame to list of lists (each sublist is a row)
data_to_write = merged_df.fillna('').values.tolist()

# Clear existing data
sheet.clear()

# Write new data
sheet.update(range_name='A1', values=[merged_df.columns.values.tolist()] + data_to_write)
