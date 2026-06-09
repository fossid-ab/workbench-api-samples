#!/usr/bin/env python3
"""
This script finds and deletes old scans from the FossID Workbench.

It lists all scans, identifies the ones that have not been updated in a specified number
of days, and deletes them permanently. It supports a dry-run mode to display the scans
that would be deleted. Unlike archiving, deletion is permanent and cannot be undone.
"""

import sys
from datetime import datetime, timedelta
import logging
import argparse
import os
from typing import List, Tuple, Dict, Any

from tabulate import tabulate
from workbench_agent.api.exceptions import WorkbenchApiError

from lib.workbench_client import WorkbenchClient, normalize_api_url

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def find_old_scans(
    scans: List[Dict[str, Any]], client: WorkbenchClient, days: int
) -> List[Tuple[str, str, str, datetime, datetime]]:
    """Find scans that were last updated before the specified days."""
    old_scans = []
    time_limit = datetime.now() - timedelta(days=days)
    for scan_info in scans:
        scan_code = scan_info["code"]
        scan_details = client.scans.get_information(scan_code)
        if scan_details.get("is_archived"):
            continue
        creation_date = datetime.strptime(scan_details["created"], "%Y-%m-%d %H:%M:%S")
        update_date = datetime.strptime(scan_details["updated"], "%Y-%m-%d %H:%M:%S")
        if update_date < time_limit:
            project_code = scan_details.get("project_code")
            project_name = "No Project"
            if project_code:
                project_info = client.projects.get_information(project_code)
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
    """Display scans that would be deleted."""
    if dry_run:
        logging.info("Dry Run enabled! These scans would be PERMANENTLY DELETED:")
    else:
        logging.info("These scans will be PERMANENTLY DELETED:")
    headers = ["PROJECT NAME", "SCAN NAME", "SCAN AGE (days)", "LAST MODIFIED"]
    table = [
        [project_name, scan_name, (datetime.now() - update_date).days, update_date]
        for project_name, scan_name, _, _, update_date in scans
    ]
    print(tabulate(table, headers, tablefmt="fancy_grid"))


def fetch_and_find_old_scans(
    client: WorkbenchClient, days: int
) -> List[Tuple[str, str, str, datetime, datetime]]:
    """Fetch scans and find the ones that are older than the specified number of days."""
    logging.info("Fetching scans from Workbench...")
    try:
        scans = client.scans.list_scans()
    except WorkbenchApiError as e:
        logging.error("Failed to retrieve scans from Workbench: %s", e)
        logging.error("Please double-check the Workbench URL, Username, and Token.")
        sys.exit(1)
    logging.info("Finding scans last updated more than %d days ago...", days)
    return find_old_scans(scans, client, days)


def delete_scans(
    client: WorkbenchClient,
    scans: List[Tuple[str, str, str, datetime, datetime]],
):
    """Delete the specified scans permanently."""
    for project_name, scan_name, scan_code, _, _ in scans:
        logging.info("Deleting scan: %s (%s)", scan_name, project_name)
        try:
            result = client.scan_deletion.delete_scan(scan_code)
            if result.success:
                logging.info("Successfully deleted scan: %s", scan_name)
            else:
                logging.error("Failed to delete scan: %s", scan_name)
        except WorkbenchApiError as e:
            logging.error("Failed to delete scan %s: %s", scan_name, e)


def main(url: str, username: str, token: str, days: int, dry_run: bool):
    """Main function to delete old scans."""
    client = WorkbenchClient(url, username, token)
    old_scans = fetch_and_find_old_scans(client, days)
    if not old_scans:
        logging.info("No scans were last updated more than %d days ago. Exiting.", days)
        return

    display_scans(old_scans, dry_run)

    if dry_run:
        return

    print("\n⚠️  WARNING: This operation will PERMANENTLY DELETE the scans listed above!")
    print("   Unlike archiving, deleted scans cannot be recovered.")
    confirmation = input("Are you absolutely sure you want to proceed? (yes/no): ")
    if confirmation.lower() != "yes":
        logging.info("Operation cancelled.")
        return

    delete_scans(client, old_scans)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete old scans permanently.")
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
        help="Display scans that would be deleted without actually deleting them",
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

    api_url = normalize_api_url(api_url)

    main(api_url, api_username, api_token, args.days, args.dry_run)
