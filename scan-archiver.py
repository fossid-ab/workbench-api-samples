#!/usr/bin/env python3
"""
This script archives old scans from the FossID Workbench.

It lists all scans, identifies the ones that have not been updated in a specified number
of days, and archives them. It supports a dry-run mode to display the scans that would be archived.
"""

import sys
import requests
import json
from datetime import datetime, timedelta
import logging
import argparse
import os
from tabulate import tabulate
from typing import List, Tuple, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a session object for making requests
session = requests.Session()

def make_api_call(api_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to make API calls."""
    try:
        response = session.post(api_url, json=payload)
        response.raise_for_status()
        return response.json()['data']
    except requests.exceptions.RequestException as e:
        logging.error("API call failed: %s", str(e))
        raise

def list_scans(api_url: str, api_username: str, api_token: str) -> Dict[str, Any]:
    """List all scans."""
    payload = {
        "group": "scans",
        "action": "list_scans",
        "data": {
            "username": api_username,
            "key": api_token
        }
    }
    return make_api_call(api_url, payload)

def get_scan_info(api_url: str, api_username: str, api_token: str, scan_code: str) -> Dict[str, Any]:
    """Get scan info for each scan."""
    payload = {
        "group": "scans",
        "action": "get_information",
        "data": {
            "username": api_username,
            "key": api_token,
            "scan_code": scan_code
        }
    }
    return make_api_call(api_url, payload)

def get_project_info(api_url: str, api_username: str, api_token: str, project_code: str) -> Dict[str, Any]:
    """Get the project name for each scan's project code."""
    payload = {
        "group": "projects",
        "action": "get_information",
        "data": {
            "username": api_username,
            "key": api_token,
            "project_code": project_code
        }
    }
    return make_api_call(api_url, payload)

def archive_scan(api_url: str, api_username: str, api_token: str, scan_code: str) -> bool:
    """Archive a scan."""
    payload = {
        "group": "scans",
        "action": "archive_scan",
        "data": {
            "username": api_username,
            "key": api_token,
            "scan_code": scan_code
        }
    }
    try:
        response = session.post(api_url, json=payload)
        response.raise_for_status()
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error("Error archiving scan %s: %s", scan_code, str(e))
        return False

def find_old_scans(scans: Dict[str, Any], api_url: str, api_username: str, api_token: str, days: int
                  ) -> List[Tuple[str, str, str, datetime, datetime]]:
    """Find scans that were last updated before the specified days."""
    old_scans = []
    time_limit = datetime.now() - timedelta(days=days)
    for scan_info in scans.values():
        scan_code = scan_info['code']
        scan_details = get_scan_info(api_url, api_username, api_token, scan_code)
        if scan_details['is_archived']:
            continue
        creation_date = datetime.strptime(scan_details['created'], "%Y-%m-%d %H:%M:%S")
        update_date = datetime.strptime(scan_details['updated'], "%Y-%m-%d %H:%M:%S")
        if update_date < time_limit:
            project_code = scan_details.get('project_code')
            project_name = 'No Project'
            if project_code:
                project_info = get_project_info(api_url, api_username, api_token, project_code)
                project_name = project_info.get('project_name', 'Unknown Project')
            old_scans.append((project_name, scan_details['name'], scan_code, creation_date, update_date))
    return old_scans

def display_scans(scans: List[Tuple[str, str, str, datetime, datetime]], dry_run: bool):
    """Display scans that would be archived."""
    headers = ["PROJECT NAME", "SCAN NAME", "SCAN AGE (days)", "LAST MODIFIED"]
    table = [[project_name, scan_name, (datetime.now() - update_date).days, update_date]
             for project_name, scan_name, _, _, update_date in scans]
    print(tabulate(table, headers, tablefmt="fancy_grid"))
    if dry_run:
        logging.info("Dry Run enabled! These scans would be archived:")
    else:
        logging.info("These scans will be archived:")

def main(api_url: str, api_username: str, api_token: str, days: int, dry_run: bool):
    """Main function to archive old scans."""
    logging.info("Fetching scans from Workbench...")
    try:
        scans = list_scans(api_url, api_username, api_token)
    except Exception:
        logging.info("Failed to retrieve scans from Workbench.")
        logging.info("Please double-check the Workbench URL, Username, and Token.")
        sys.exit(1)

    logging.info("Finding scans last updated more than %d days ago...", days)
    old_scans = find_old_scans(scans, api_url, api_username, api_token, days)
    
    if not old_scans:
        logging.info("No scans were last updated more than %d days ago. Exiting.", days)
        return

    display_scans(old_scans, dry_run)

    if dry_run:
        return
    
    confirmation = input("This operation is irreversible, proceed? (y/n): ")
    if confirmation.lower() != 'y':
        logging.info("Operation cancelled.")
        return

    for project_name, scan_name, scan_code, creation_date, update_date in old_scans:
        logging.info("Archiving scan: %s", scan_name)
        if archive_scan(api_url, api_username, api_token, scan_code):
            logging.info("Archived scan: %s", scan_name)
        else:
            logging.info("Failed to archive scan: %s", scan_name)

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
        sys.exit(1)

    # Sanity check for Workbench URL
    if not api_url.endswith('/api.php'):
        api_url += '/api.php'

    main(api_url, api_username, api_token, args.days, args.dry_run)
