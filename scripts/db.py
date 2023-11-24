import requests
import pandas as pd
from datetime import datetime
import pytz
import json

# Load credentials from JSON
with open('../credentials.json') as f:
    credentials = json.load(f)

# Extracting credentials
auth_clickup = credentials['clickup']['api_key']
team_id = credentials['team']['id']
time_local = 'Europe/Moscow'  # Assuming timezone

# Convert to POSIX time
def to_posix(dt):
    return int(dt.timestamp() * 1000)

# Current time and time 10 weeks ago in POSIX format
now_posix = to_posix(datetime.now(pytz.timezone(time_local)))
start_posix = to_posix(datetime.now(pytz.timezone(time_local)) - pd.Timedelta(weeks=10))

# Get team members from ClickUp
def get_team_members(auth_clickup, team_id):
    url = f"https://api.clickup.com/api/v2/team/{team_id}"  # Corrected URL
    response = requests.get(url, headers={"Authorization": auth_clickup})
    print(response.json())  # Print the response for verification
    # You might need to adjust the following line based on the actual structure
    members = response.json().get('members', [])
    return ','.join([member['user']['id'] for member in members])

members_id = get_team_members(auth_clickup, team_id)

# Get time entries from ClickUp
def get_time_entries(team_id, start_posix, now_posix, members_id, auth_clickup):
    url = f"https://api.clickup.com/api/v2/team/{team_id}/time_entries?start_date={start_posix}&end_date={now_posix}&assignee={members_id}"
    response = requests.get(url, headers={"Authorization": auth_clickup})
    return pd.json_normalize(response.json(), record_path=['data'])

time_entries_df = get_time_entries(team_id, start_posix, now_posix, members_id, auth_clickup)

# Print the DataFrame for verification
print(time_entries_df.head())  # Print first few rows for checking
