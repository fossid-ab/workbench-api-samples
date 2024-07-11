import requests
import json
from datetime import datetime, timedelta
import logging
import argparse
import os
from tabulate import tabulate

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a session object for making requests
session = requests.Session()

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
    response = session.post(api_url, json=payload)
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
    response = session.post(api_url, json=payload)
    response.raise_for_status()
    return response.json()['data']

# Function to get the Project Name for each Scan's Project Code
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
    response = session.post(api_url, json=payload)
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
    response = session.post(api_url, json=payload)
    response.raise_for_status()
    return response.status_code == 200

def main(api_url, api_username, api_token, days, dry_run):
    # Step 1: List all scans
    logging.info("Fetching Scans from Workbench...")
    try:
        scans = list_scans(api_url, api_username, api_token)
    except requests.exceptions.RequestException as e:
        logging.info("Failed to retrieve scans from Workbench.")
        logging.info("Please double check the Workbench URL, Username, and Token.")
        logging.error(f"Error: {str(e)}")
        exit(1)

    # Step 2: Get scan information and keep only scans last modified before the specified days
    logging.info(f"Finding scans that were last updated more than {days} days ago...")
    old_scans = []
    time_limit = datetime.now() - timedelta(days=days)
    for scan_id, scan_info in scans.items():
        scan_code = scan_info['code']
        scan_details = get_scan_info(api_url, api_username, api_token, scan_code)
        if scan_details['is_archived']:
            continue
        creation_date = datetime.strptime(scan_details['created'], "%Y-%m-%d %H:%M:%S")
        logging.debug(f"Scan: {scan_details['name']}, First Created: {creation_date}")
        update_date = datetime.strptime(scan_details['updated'], "%Y-%m-%d %H:%M:%S")
        logging.debug(f"Scan: {scan_details['name']}, Last Updated: {update_date}")
        if update_date < time_limit:
            project_code = scan_details.get('project_code')
            project_name = ''
            if project_code:
                logging.debug("Getting Project Name for Project Code: " + project_code)
                project_info = get_project_info(api_url, api_username, api_token, project_code)
                project_name = project_info.get('project_name', 'Unknown Project')
            else:
                project_name = 'No Project'
            old_scans.append((project_name, scan_details['name'], scan_code, creation_date, update_date))
    
    # Step 3: Notify if no Scans match the age criteria
    num_old_scans = len(old_scans)
    if num_old_scans == 0:
        logging.info(f"No scans were last updated more than {days} days ago.")
        logging.info(f"There is nothing to do! Exiting.")
        return
        
    # Dry run: Display the scans that would be archived
    if dry_run:
        logging.info("Dry Run enabled!")
        logging.info("These are the scans that would be archived:")
        headers = ["PROJECT NAME", "SCAN NAME", "SCAN AGE (days)", "LAST MODIFIED"]
        table = [[project_name, scan_name, (datetime.now() - creation_date).days, update_date]
                 for project_name, scan_name, creation_date, update_date in old_scans]
        print(tabulate(table, headers, tablefmt="fancy_grid"))
        return
    
    # Step 4: Prompt user for confirmation
    logging.info(f"{num_old_scans} scans were last updated more than {days} days ago.")
    logging.info("Please confirm you want to archive them.")
    confirmation = input("This operation is irreversible, proceed? (y/n): ")
    if confirmation.lower() != 'y':
        logging.info("Operation cancelled.")
        return
    
    # Step 5: Archive old scans
    for project_name, scan_name, scan_code, creation_date, update_date in old_scans:
        logging.info(f"Archiving scan with name: {scan_name}")
        try:
            if archive_scan(api_url, api_username, api_token, scan_code):
                logging.info(f"Archived scan with name: {scan_name}")
            else:
                logging.info(f"Failed to archive scan with name: {scan_name}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error archiving scan {scan_name}: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Archive old scans.')
    parser.add_argument('--workbench-url', type=str, help='The Workbench API URL')
    parser.add_argument('--workbench-user', type=str, help='Your Workbench username')
    parser.add_argument('--workbench-token', type=str, help='Your Workbench API token')
    parser.add_argument('--days', type=int, default=365, help='Scan age in days to consider old (default: 365)')
    parser.add_argument('--dry-run', action='store_true', help='Display scans that would be archived without actually archiving them')
    
    args = parser.parse_args()
    
    api_url = args.workbench_url or os.getenv('WORKBENCH_URL')
    api_username = args.workbench_user or os.getenv('WORKBENCH_USER')
    api_token = args.workbench_token or os.getenv('WORKBENCH_TOKEN')
    
    if not api_url or not api_username or not api_token:
        logging.info("The Workbench URL, username, and token must be provided either as arguments or environment variables.")
        exit(1)

    # Sanity check for Workbench URL
    if not api_url.endswith('/api.php'):
        api_url += '/api.php'
    
    main(api_url, api_username, api_token, args.days, args.dry_run)
