# Project Title: Time Tracking Automation 
## Description
This project contains a Python script designed to automate the process of fetching time tracking data from ClickUp, processing it, and then updating a Google Sheets document. It's intended to replace an existing R script with similar functionality. The script is set up to run automatically on an hourly basis using GitHub Actions.

## Features
* Fetches time tracking data from ClickUp API.
* Processes and transforms data in Python.
* Updates a Google Sheets document with the processed data.
* Automated execution using GitHub Actions.

## Setup and Installation
### Prerequisites
* Python 3.x
* Access to ClickUp API
* Google Cloud Platform account with a configured service account for Google Sheets access
* GitHub account for using GitHub Actions

## Installation
### 1. Clone the Repository:
``` git clone https://github.com/Agalak567/gcp_clickup.git ```
``` cd gcp_clickup ```

### 2. Install Required Python Packages:
``` pip install -r requirements.txt ```

## Configuration
### 1. GitHub Secrets:
Set up the following secrets in your GitHub repository for GitHub Actions:
* CLICKUP_API_KEY: Your ClickUp API key.
* GOOGLE_SERVICE_ACCOUNT: The JSON content of your Google service account key file.
* TEAM_ID: The team ID for your ClickUp account.

### 2. Local Setup:
For local testing, create a credentials.json file with your ClickUp API key, Google service account details, and team ID.

### 3. Google Sheets Document:
Ensure that your Google Sheets document is set up with the appropriate format and permissions for the service account.

## Usage
The script can be executed manually for testing:
``` source venv/bin/activate```
``` python scripts/db.py ```

For automated execution, the GitHub Actions workflow is configured to run the script daily.

## Contact

Alibek - a.zhubekov@prpillar.com

Project Link: https://github.com/Agalak567/gcp_clickup.git
