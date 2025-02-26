#!/usr/bin/env python3
"""
This script archives stale scans from the FossID Workbench.

It lists all scans, identifies the ones that have not been updated in a specified number
of days, and archives them. It supports a dry-run mode to display the scans that would be archived.
"""

import sys
import json
from datetime import datetime, timedelta
import logging
import argparse
import os
from typing import List, Tuple, Dict, Any
import helper_functions as hf
import requests
from tabulate import tabulate

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

def list_scans(url: str, username: str, token: str) -> Dict[str, Any]:
    """List all scans.
    
    Parameters:
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
    Returns:
        A dicitionary with each scan.
    """
    payload = {
        "group": "scans",
        "action": "list_scans",
        "data": {"username": username, "key": token},
    }
    return hf.make_api_call(url, payload)


def get_scan_info(url: str, username: str, token: str, scan_code: str) -> Dict[str, Any]:
    """Get scan info for each scan.
    
    Parameters:
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
        scan_code(str): The code for the scan to get the info on.
    
    Returns:
        A dicitonary with the info on the given scan code.
    """
    payload = {
        "group": "scans",
        "action": "get_information",
        "data": {"username": username, "key": token, "scan_code": scan_code},
    }
    return hf.make_api_call(url, payload)


def get_project_info(url: str, username: str, token: str, project_code: str) -> Dict[str, Any]:
    """Get the project name for each scan's project code.
    
    Parameters:
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
        project_code(str): The code for the project to get the info on.
        
    Returns:
        A dicitionary with the data on the given project.
    """
    payload = {
        "group": "projects",
        "action": "get_information",
        "data": {"username": username, "key": token, "project_code": project_code},
    }
    return hf.make_api_call(url, payload)


def archive_scan(url: str, username: str, token: str, scan_code: str) -> bool:
    """Archives a scan.
    
    Parameters:
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
        scan_code(str): The code for the scan to get the info on.

    Returns:
        Boolean; True if the scan was succesfully archived, false otherwise.    
    """
    payload = {
        "group": "scans",
        "action": "archive_scan",
        "data": {"username": username, "key": token, "scan_code": scan_code},
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error("Error archiving scan %s: %s", scan_code, str(e))
        return False


def find_old_scans(scans: Dict[str, Any], url: str, username: str, token: str, days: int) -> List[Tuple[str, str, str, datetime, datetime]]:
    """Find scans that were last updated before the specified days.
    
    Parameters:
        scans(dict[str, any]): A dicitonary containing the scans
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
        days(int): The amount of days passed for a scan to be old.
    
    Returns:
        A list of tuples that contains that have not been updated since the given
        amount of days.
    """

    old_scans = []
    time_limit = datetime.now() - timedelta(days=days)

    for scan_info in scans.values():

        scan_code = scan_info["code"]
        scan_details = get_scan_info(url, username, token, scan_code)

        if scan_details["is_archived"]:
            continue

        creation_date = datetime.strptime(scan_details["created"], "%Y-%m-%d %H:%M:%S")
        update_date = datetime.strptime(scan_details["updated"], "%Y-%m-%d %H:%M:%S")

        if update_date < time_limit:
            project_code = scan_details.get("project_code")
            project_name = "No Project"

            if project_code:
                project_info = get_project_info(url, username, token, project_code)
                project_name = project_info.get("project_name", "Unknown Project")
            old_scans.append(
                (
                    project_name,
                    scan_details["name"],
                    scan_code,
                    creation_date,
                    update_date,
                )
            )

    return old_scans


def display_scans(scans: List[Tuple[str, str, str, datetime, datetime]], dry_run: bool):
    """Display scans that would be archived.
    
    Parameters:
        scans(List[Tuple[str, str, str, datetime, datetime]]): The scans to check through.
        dry_run(boolean): True if the run should be a dry run, false otherwise.
    """
    if dry_run:
        logging.info("Dry Run enabled! These scans would be archived:")
    else:
        logging.info("These scans will be archived:")
        headers = ["PROJECT NAME", "SCAN NAME", "SCAN AGE (days)", "LAST MODIFIED"]
        table = [
            [project_name, scan_name, (datetime.now() - update_date).days, update_date]
            for project_name, scan_name, _, _, update_date in scans
        ]
        print(tabulate(table, headers, tablefmt="fancy_grid"))


def fetch_and_find_old_scans(url: str, username: str, token: str, days: int) -> List[Tuple[str, str, str, datetime, datetime]]:
    """Fetch scans and find the ones that are older than the specified number of days.
    
    Parameters:
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
        days(int): The amount of days passed for a scan to be old
    
    Returns:
        A list of tuples of the old scans.
    """
    logging.info("Fetching scans from Workbench...")
    try:
        scans = list_scans(url, username, token)
    except requests.exceptions.RequestException as e:
        logging.error("Failed to retrieve scans from Workbench: %s", str(e))
        logging.error("Please double-check the Workbench URL, Username, and Token.")
        sys.exit(1)
    logging.info("Finding scans last updated more than %d days ago...", days)
    return find_old_scans(scans, url, username, token, days)


def archive_scans(url: str, username: str, token: str, scans: List[Tuple[str, str, str, datetime, datetime]]):
    """Archive the specified scans.
    
    Parameters:
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
        scans(List[Tuple[str, str, str, datetime, datetime]]): The scans to archive.
    """
    for project_name, scan_name, scan_code, _, _ in scans:

        logging.info("Archiving scan: %s (%s)", scan_name, project_name)
        if archive_scan(url, username, token, scan_code):
            logging.info("Archived scan: %s", scan_name)
        else:
            logging.error("Failed to archive scan: %s", scan_name)


def main(url: str, username: str, token: str, days: int, dry_run: bool):
    """Main function to archive old scans.
    
    Parameters:
        url(str): The url to access the api.
        username(str): The username to use for the api.
        token(str): The required token to access the api.
        days(int): The required amount of days passed for a scan to be considered old.
        dry_run(boolean): True if dry run was enabled.
    """

    old_scans = fetch_and_find_old_scans(url, username, token, days)
    if not old_scans:
        logging.info("No scans were last updated more than %d days ago. Exiting.", days)
        return

    display_scans(old_scans, dry_run)

    if dry_run:
        return

    confirmation = input("This operation is irreversible, proceed? (y/n): ")
    if confirmation.lower() != "y":
        logging.info("Operation cancelled.")
        return

    archive_scans(url, username, token, old_scans)

#sets up the arguments
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive old scans.")
    parser.add_argument("--workbench-url", type=str, help="The Workbench API URL")
    parser.add_argument("--workbench-user", type=str, help="Your Workbench username")
    parser.add_argument("--workbench-token", type=str, help="Your Workbench API token")
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Scan age in days to consider old (default: 365)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display scans that would be archived without actually archiving them",
    )

    args = parser.parse_args()

    api_url = args.workbench_url or os.getenv("WORKBENCH_URL")
    api_username = args.workbench_user or os.getenv("WORKBENCH_USER")
    api_token = args.workbench_token or os.getenv("WORKBENCH_TOKEN")

    if not api_url or not api_username or not api_token:
        logging.error(
            "The Workbench URL, username, and token must be provided either as arguments\n"
            "or environment variables."
        )
        sys.exit(1)

    # Sanity check for Workbench URL
    if not api_url.endswith("/api.php"):
        api_url += "/api.php"

    #calls the main function to acrive the stale scans
    main(api_url, api_username, api_token, args.days, args.dry_run)
