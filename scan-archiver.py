#!/usr/bin/env python3
# Copyright: FossID AB 2024

import requests
import json
from datetime import datetime, timedelta
import argparse
import os
from tabulate import tabulate

# Function to List all Scans
def list_scans(api_url, api_username, api_token):
    payload = {
        "group": "scans",
        "action": "list_scans",
        "data": {
            "username": api_username,
            "key": api_token
        }
    }
    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    return response.json()['data']

# Function to Get Scan Info for each scan
def get_scan_info(api_url, api_username, api_token, scan_code):
    payload = {
        "group": "scans",
        "action": "get_information",
        "data": {
            "username": api_username,
            "key": api_token,
            "scan_code": scan_code
        }
    }
    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    return response.json()['data']

# Function to the Project Info for each Scan
def get_project_info(api_url, api_username, api_token, project_code):
    payload = {
        "group": "projects",
        "action": "get_information",
        "data": {
            "username": api_username,
            "key": api_token,
            "project_code": project_code
        }
    }
    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    return response.json()['data']

# Function to Archive Scans
def archive_scan(api_url, api_username, api_token, scan_code):
    payload = {
        "group": "scans",
        "action": "archive_scan",
        "data": {
            "username": api_username,
            "key": api_token,
            "scan_code": scan_code
        }
    }
    response = requests.post(api_url, json=payload)
    response.raise_for_status()
    return response.status_code == 200

def main(api_url, api_username, api_token, months, dry_run):
    # Step 1: List all scans
    try:
        scans = list_scans(api_url, api_username, api_token)
    except requests.exceptions.RequestException as e:
        print("Failed to retrieve scans from Workbench.")
        print("Please double check the Workbench URL, Username, and Token.")
        print(f"Error: {str(e)}")
        exit(1)

    # Step 2: Get scan information and filter scans older than the specified months
    old_scans = []
    time_limit = datetime.now() - timedelta(days=30*months)
    for scan_id, scan_info in scans.items():
        scan_code = scan_info['code']
        scan_details = get_scan_info(api_url, api_username, api_token, scan_code)
        creation_date = datetime.strptime(scan_details['created'], "%Y-%m-%d %H:%M:%S")
        if creation_date < time_limit:
            project_code = scan_details.get('project_code')
            project_name = ''
            if project_code:
                project_info = get_project_info(api_url, api_username, api_token, project_code)
                project_name = project_info.get('project_name', 'Unknown Project')
            else:
                project_name = 'No Project'
            old_scans.append((project_name, scan_details['name'], creation_date))
    
    # Step 3: Notify if no Scans match the age criteria
    num_old_scans = len(old_scans)
    if num_old_scans == 0:
        print(f"No scans older than {months} months found.")
        return
        
    # Dry run: Display the scans that would be archived
    if dry_run:
        table = []
        for project_name, scan_name, creation_date in old_scans:
            age = (datetime.now() - creation_date).days // 30
            table.append([project_name, scan_name, age])
        headers = ["PROJECT NAME", "SCAN NAME", "SCAN AGE"]
        print(tabulate(table, headers, tablefmt="fancy_grid"))
        return
    
    # Step 4: Prompt user for confirmation
    print(f"{num_old_scans} scans are older than {months} months.")
    confirmation = input("Do you want to archive them? (y/n): ")
    if confirmation.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Step 5: Archive old scans
    for _, scan_name, _ in old_scans:
        if archive_scan(api_url, api_username, api_token, scan_name):
            print(f"Archived scan with name: {scan_name}")
        else:
            print(f"Failed to archive scan with name: {scan_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Archive old scans.')
    parser.add_argument('--workbench-url', type=str, help='The Workbench API URL')
    parser.add_argument('--workbench-user', type=str, help='Your Workbench username')
    parser.add_argument('--workbench-token', type=str, help='Your Workbench API token')
    parser.add_argument('--months', type=int, default=12, help='Scan age in months to consider old (default: 12)')
    parser.add_argument('--dry-run', action='store_true', help='Display scans that would be archived without actually archiving them')
    
    args = parser.parse_args()
    
    api_url = args.workbench_url or os.getenv('WORKBENCH_URL')
    api_username = args.workbench_user or os.getenv('WORKBENCH_USER')
    api_token = args.workbench_token or os.getenv('WORKBENCH_TOKEN')
    
    if not api_url or not api_username or not api_token:
        print("The Workbench URL, username, and token must be provided either as arguments or environment variables.")
        exit(1)

    # Sanity check for Workbench URL
    if not api_url.endswith('/api.php'):
        api_url += '/api.php'
    
    main(api_url, api_username, api_token, args.months, args.dry_run)
