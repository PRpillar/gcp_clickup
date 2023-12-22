import requests
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load credentials from JSON
with open('../credentials.json') as f:
    credentials = json.load(f)
service_account_info = credentials['google']['service_account']

# Define the scope
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Load credentials
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
auth_clickup = credentials['clickup']['api_key']
team_id = credentials['team']['id']
time_entries_tab = credentials['google']['sheets_links']["time_entries_tab"]
time_local = 'Europe/Moscow'  # Assuming timezone

# Convert to POSIX time
def to_posix(dt):
    return int(dt.timestamp() * 1000)

# Current time and time 10 weeks ago in POSIX format
now_posix = to_posix(datetime.now(pytz.timezone(time_local)))
start_posix = to_posix(datetime.now(pytz.timezone(time_local)) - pd.Timedelta(weeks=10))

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

members_id = get_team_members(auth_clickup, team_id)

print(members_id)

# Get time entries from ClickUp
def get_time_entries(team_id, start_posix, now_posix, members_id, auth_clickup):
    url = f"https://api.clickup.com/api/v2/team/{team_id}/time_entries?start_date={start_posix}&end_date={now_posix}&assignee={members_id}"
    response = requests.get(url, headers={"Authorization": auth_clickup})
    return pd.json_normalize(response.json(), record_path=['data'])

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
time_entries_df['dt_load'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Replace NaN with None
time_entries_df = time_entries_df.where(pd.notna(time_entries_df), None)

time_entries_df = time_entries_df.rename(columns={
    'id': 'ID',
    'task_url': 'Task URL',
    'task.name': 'Task Name',
    'task.custom_id': 'Task Custom ID',
    'task.status.status': 'Task Status',
    'user.username': 'Team Member',
    'start': 'Start',
    'end': 'End',
    'duration_hours': 'Hours',
})

# # Selecting the columns you need (adjust the list as per your requirements)
final_df = time_entries_df[['ID', 'Task URL', 'Task Name', 'Task Custom ID', 'Task Status', 'Team Member',
                            'Start', 'End', 'Hours', 'dt_load']]

# Convert DataFrame to list of lists (each sublist is a row)
data_to_write = final_df.values.tolist()

# Open the Google Sheet (replace 'your_sheet_name' with the actual name of your sheet)
sheet = client.open('TEST ClickUp').worksheet(time_entries_tab)  # or use .worksheet('worksheet_name')

# # Update the Google Sheet starting at cell A2
sheet.update('A2', data_to_write)

# print(time_entries_df.columns)
