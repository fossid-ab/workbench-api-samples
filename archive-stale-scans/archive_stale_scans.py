#!/usr/bin/env python3
"""
This script archives stale scans from the FossID Workbench using a
command-based approach.

Commands:
  plan    - Create a JSON plan of scans to be archived based on age criteria
  archive - Execute archiving based on a previously created JSON plan

This two-step approach allows for validation and modification of the
archive plan before execution.
"""

import sys
import json
from datetime import datetime, timedelta
import logging
import argparse
import os
from typing import List, Tuple, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration constants
RECORDS_PER_PAGE = 100  # Number of records to fetch per page from the API
MAX_WORKERS = 10       # Maximum number of concurrent API requests
BATCH_SIZE = 50        # Number of scans to process concurrently in each batch

# Create a session object for making requests
session = requests.Session()

# Global cache for project information to avoid redundant API calls
project_cache: Dict[str, Dict[str, Any]] = {}


def make_api_call(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to make API calls."""
    try:
        logging.debug("Making API call with payload: %s",
                      json.dumps(payload, indent=2))
        response = session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logging.debug("Received response: %s", response.text)
        return response.json().get("data", {})
    except requests.exceptions.RequestException as e:
        logging.error("API call failed: %s", str(e))
        raise
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON response: %s", str(e))
        raise


def list_scans(url: str, username: str, token: str) -> Dict[str, Any]:
    """List all scans using pagination."""
    all_scans = {}
    page = 1

    while True:
        payload = {
            "group": "scans",
            "action": "list_scans",
            "data": {
                "username": username,
                "key": token,
                "records_per_page": RECORDS_PER_PAGE,
                "page": page
            },
        }
        scans_page = make_api_call(url, payload)

        if not scans_page:
            # No more data returned
            break

        # Merge this page's scans into the total
        all_scans.update(scans_page)

        # Check if we got a full page - if not, this was the last page
        if len(scans_page) < RECORDS_PER_PAGE:
            break

        page += 1

    return all_scans


def get_scan_info(
    url: str, username: str, token: str, scan_code: str
) -> Dict[str, Any]:
    """Get scan info for each scan."""
    payload = {
        "group": "scans",
        "action": "get_information",
        "data": {"username": username, "key": token, "scan_code": scan_code},
    }
    return make_api_call(url, payload)


def get_project_info(
    url: str, username: str, token: str, project_code: str
) -> Dict[str, Any]:
    """Get the project name for each scan's project code."""
    # Check cache first
    if project_code in project_cache:
        return project_cache[project_code]
    payload = {
        "group": "projects",
        "action": "get_information",
        "data": {"username": username, "key": token,
                 "project_code": project_code},
    }
    result = make_api_call(url, payload)

    # Cache the result
    project_cache[project_code] = result
    return result


def get_scan_info_batch(
    url: str, username: str, token: str, scan_codes: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Get scan information for multiple scans concurrently."""
    results = {}

    def fetch_single_scan(scan_code: str) -> Tuple[str, Dict[str, Any]]:
        try:
            scan_info = get_scan_info(url, username, token, scan_code)
            return scan_code, scan_info
        except Exception as e:
            logging.error("Failed to fetch scan info for %s: %s",
                          scan_code, str(e))
            return scan_code, {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_scan = {
            executor.submit(fetch_single_scan, scan_code): scan_code
            for scan_code in scan_codes
        }

        # Collect results as they complete
        for future in as_completed(future_to_scan):
            scan_code, scan_info = future.result()
            if scan_info:  # Only store successful results
                results[scan_code] = scan_info

    return results


def find_old_scans(
    scans: Dict[str, Any], url: str, username: str, token: str, days: int
) -> List[Tuple[Optional[str], str, str, datetime, datetime]]:
    """Find scans that were last updated before the specified days.
    Uses concurrent processing for improved performance.
    """
    old_scans = []
    time_limit = datetime.now() - timedelta(days=days)

    # Process scans in batches to avoid memory issues and enable concurrency
    scan_items = list(scans.items())
    total_scans = len(scan_items)

    logging.info("Processing %d scans in batches of %d with %d workers",
                 total_scans, BATCH_SIZE, MAX_WORKERS)
    for i in range(0, total_scans, BATCH_SIZE):
        batch = scan_items[i:i + BATCH_SIZE]
        scan_codes = [scan_info["code"] for _, scan_info in batch]

        logging.info("Processing batch %d/%d (%d scans)",
                     i // BATCH_SIZE + 1,
                     (total_scans + BATCH_SIZE - 1) // BATCH_SIZE,
                     len(scan_codes))

        # Fetch scan details concurrently for this batch
        scan_details_batch = get_scan_info_batch(
                url, username, token, scan_codes)

        # Process the results
        for _, scan_info in batch:
            scan_code = scan_info["code"]

            if scan_code not in scan_details_batch:
                logging.warning("Failed to get details for scan %s, skipping",
                                scan_code)
                continue

            scan_details = scan_details_batch[scan_code]

            # Skip archived scans
            if scan_details.get("is_archived"):
                continue

            try:
                creation_date = datetime.strptime(
                    scan_details["created"], "%Y-%m-%d %H:%M:%S")
                update_date = datetime.strptime(
                    scan_details["updated"], "%Y-%m-%d %H:%M:%S")
                if update_date < time_limit:
                    project_code = scan_details.get("project_code")
                    old_scans.append((
                        project_code,
                        scan_details["name"],
                        scan_code,
                        creation_date,
                        update_date,
                    ))
            except (KeyError, ValueError) as e:
                logging.warning("Invalid date format for scan %s: %s",
                                scan_code, str(e))
                continue

        # Add a small delay between batches to be nice to the API
        if i + BATCH_SIZE < total_scans:
            time.sleep(0.1)

    logging.info("Found %d old scans out of %d total scans",
                 len(old_scans), total_scans)
    return old_scans


def archive_scan(url: str, username: str, token: str, scan_code: str) -> bool:
    """Archive a scan."""
    payload = {
        "group": "scans",
        "action": "archive_scan",
        "data": {"username": username, "key": token,
                 "scan_code": scan_code},
    }
    try:
        response = session.post(url, json=payload)
        response.raise_for_status()
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error("Error archiving scan %s: %s", scan_code,
                      str(e))
        return False


def create_scan_plan(
    scans: List[Tuple[Optional[str], str, str, datetime, datetime]],
    url: str, username: str, token: str
) -> List[Dict[str, Any]]:
    """Create a plan with detailed scan information for archiving."""
    plan = []

    for project_code, scan_name, scan_code, creation_date, update_date \
            in scans:
        project_name = "No Project"
        if project_code:
            try:
                project_info = get_project_info(
                    url, username, token, project_code)
                project_name = project_info.get(
                    "project_name", "Unknown Project")
            except Exception as e:
                logging.warning(
                    "Failed to fetch project info for %s: %s",
                    project_code, str(e))
                project_name = f"Project {project_code}"

        scan_entry = {
            "project_name": project_name,
            "scan_code": scan_code,
            "scan_name": scan_name,
            "creation_date": creation_date.isoformat(),
            "last_modified": update_date.isoformat(),
            "age_days": (datetime.now() - update_date).days
        }
        plan.append(scan_entry)
    
    return plan


def save_plan_to_file(plan: List[Dict[str, Any]], filename: str) -> None:
    """Save the scan plan to a JSON file."""
    plan_data = {
        "created_at": datetime.now().isoformat(),
        "total_scans": len(plan),
        "scans": plan
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(plan_data, f, indent=2, ensure_ascii=False)

    logging.info("Scan plan saved to %s (%d scans)", filename, len(plan))


def load_plan_from_file(filename: str) -> List[Dict[str, Any]]:
    """Load scan plan from a JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        if "scans" not in plan_data:
            raise ValueError("Invalid plan file format: missing 'scans' key")

        scans = plan_data["scans"]
        logging.info("Loaded plan from %s (%d scans)", filename, len(scans))
        return scans

    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logging.error("Failed to load plan file %s: %s", filename, str(e))
        sys.exit(1)


def fetch_and_find_old_scans(
    url: str, username: str, token: str, days: int
) -> List[Tuple[Optional[str], str, str, datetime, datetime]]:
    """Fetch scans and find ones older than the specified number of days."""
    logging.info("Fetching scans from Workbench...")
    try:
        scans = list_scans(url, username, token)
    except requests.exceptions.RequestException as e:
        logging.error("Failed to retrieve scans from Workbench: %s",
                      str(e))
        logging.error("Please check the Workbench URL, Username and Token.")
        sys.exit(1)
    logging.info("Found %d total scans", len(scans))
    logging.info("Finding scans last updated more than %d days ago...", days)

    return find_old_scans(
            scans, url, username, token, days)


def archive_scans_from_plan(
    url: str, username: str, token: str, plan: List[Dict[str, Any]]
):
    """Archive scans based on a plan loaded from JSON."""
    total_scans = len(plan)
    successful = 0
    failed = 0
    
    logging.info("Starting to archive %d scans...", total_scans)
    
    for i, scan_entry in enumerate(plan, 1):
        scan_code = scan_entry["scan_code"]
        scan_name = scan_entry["scan_name"]
        project_name = scan_entry["project_name"]
        
        logging.info("(%d/%d) Archiving...", i, total_scans)
        
        if archive_scan(url, username, token, scan_code):
            successful += 1
        else:
            logging.error("Failed to archive scan: %s", scan_name)
            failed += 1
    
    logging.info("Archive operation completed: %d successful, %d failed", 
                 successful, failed)
    
    if failed > 0:
        logging.warning(
            "Some scans failed to archive. Check the logs above for details.")
        return False
    
    return True


def cmd_plan(url: str, username: str, token: str, days: int, output_file: str):
    """Create a plan of scans to be archived."""
    start_time = time.time()
    
    logging.info("Creating archive plan for scans older than %d days...", days)
    
    old_scans = fetch_and_find_old_scans(url, username, token, days)
    if not old_scans:
        logging.info("No scans found older than %d days.", days)
        # Still create an empty plan file
        save_plan_to_file([], output_file)
        return
    
    logging.info("Found %d scans to be archived", len(old_scans))
    
    # Create detailed plan with project information
    plan = create_scan_plan(old_scans, url, username, token)
    
    # Save plan to file
    save_plan_to_file(plan, output_file)
    
    processing_time = time.time() - start_time
    logging.info("Plan creation completed in %.2f seconds", processing_time)

    # Display completion message
    logging.info(
        "Archive plan created at %s. Please review the scans that will be "
        "archived then run the script with the archive command to finish "
        "the operation.", output_file
    )


def cmd_archive(url: str, username: str, token: str, plan_file: str):
    """Archive scans based on a plan file."""
    start_time = time.time()

    logging.info("Loading archive plan from %s...", plan_file)
    plan = load_plan_from_file(plan_file)
    
    if not plan:
        logging.info("No scans to archive (empty plan).")
        return

    logging.info("Loaded plan with %d scans to archive", len(plan))
    
    # Confirm operation
    confirmation = input(
        f"\nThis will archive {len(plan)} scans. "
        f"This operation is irreversible. Proceed? (y/n): ")
    if confirmation.lower() != "y":
        logging.info("Operation cancelled.")
        return

    # Perform archiving
    success = archive_scans_from_plan(url, username, token, plan)

    total_time = time.time() - start_time
    logging.info("Archive operation completed in %.2f seconds", total_time)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Archive old scans from FossID Workbench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  plan     Create a JSON plan of scans to be archived
  archive  Archive scans based on a JSON plan file

Examples:
  python archive_stale_scans.py plan --days 365 --output scans_to_archive.json
  python archive_stale_scans.py archive --input scans_to_archive.json
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")
    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--workbench-url", type=str, help="The Workbench API URL")
    common_parser.add_argument(
        "--workbench-user", type=str, help="Your Workbench username")
    common_parser.add_argument(
        "--workbench-token", type=str, help="Your Workbench API token")
    # Plan command
    plan_parser = subparsers.add_parser(
        "plan", parents=[common_parser],
        help="Create a plan of scans to be archived"
    )
    plan_parser.add_argument(
        "--days", type=int, default=365,
        help="Scan age in days to consider old (default: 365)"
    )
    plan_parser.add_argument(
        "--output", "-o", type=str, default="archive_plan.json",
        help="Output JSON file for the archive plan "
             "(default: archive_plan.json)"
    )
    
    # Archive command
    archive_parser = subparsers.add_parser(
        "archive", parents=[common_parser],
        help="Archive scans based on a plan file"
    )
    archive_parser.add_argument(
        "--input", "-i", type=str, default="archive_plan.json",
        help="Input JSON plan file to execute (default: archive_plan.json)"
    )
    
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get API credentials
    api_url = args.workbench_url or os.getenv("WORKBENCH_URL")
    api_username = args.workbench_user or os.getenv("WORKBENCH_USER")
    api_token = args.workbench_token or os.getenv("WORKBENCH_TOKEN")

    if not api_url or not api_username or not api_token:
        logging.error(
            "Workbench URL, username, and token must be provided as arguments "
            "or environment variables."
        )
        sys.exit(1)

    # Sanity check for Workbench URL
    if not api_url.endswith("/api.php"):
        api_url += "/api.php"

    # Execute the appropriate command
    if args.command == "plan":
        cmd_plan(api_url, api_username, api_token, args.days, args.output)
    elif args.command == "archive":
        cmd_archive(api_url, api_username, api_token, args.input)
