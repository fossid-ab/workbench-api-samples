#!/usr/bin/env python3
"""
This script is meant to be executed after a scan has been initiated in FossID Workbench.
This script will not initiate a scan - that is available with the Workbench Agent.

It first checks that the scan associated to the provided scan code completed.
Once the scan is done, it checks if the scan contains Pending Identifications.
If any files have Pending IDs, it exits with a message to the user with a link to review.
If there are no pending identifications and --policy-check is provided,
it checks for policy violations.
If there are policy violations, it exits with a message to the user with a link to review.
"""

import json
import time
import logging
import argparse
import os
import re
from typing import Dict, Any
import sys
import requests

# Constants
API_ACTION_CHECK_STATUS = "check_status"
API_ACTION_GET_PENDING_FILES = "get_pending_files"
API_ACTION_GET_POLICY_WARNINGS = "get_policy_warnings_info"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Create a session object for making requests
session = requests.Session()


def make_api_call(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to make API calls."""
    try:
        logging.debug("Making API call with payload: %s", json.dumps(payload, indent=2))
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


def check_scan_status(
    api_url: str, username: str, token: str, scan_code: str
) -> Dict[str, Any]:
    """Check the status of the scan."""
    payload = create_payload(username, token, scan_code, API_ACTION_CHECK_STATUS)
    return make_api_call(api_url, payload)


def check_pending_identifications(
    api_url: str, username: str, token: str, scan_code: str
) -> Dict[str, Any]:
    """Check for pending identifications in the scan."""
    payload = create_payload(username, token, scan_code, API_ACTION_GET_PENDING_FILES)
    return make_api_call(api_url, payload)


def check_policy_violations(
    api_url: str, username: str, token: str, scan_code: str
) -> Dict[str, Any]:
    """Check for policy violations in the scan."""
    payload = create_payload(username, token, scan_code, API_ACTION_GET_POLICY_WARNINGS)
    return make_api_call(api_url, payload)


def create_payload(
    username: str, token: str, scan_code: str, action: str
) -> Dict[str, Any]:
    """Create payload for API calls."""
    return {
        "group": "scans",
        "action": action,
        "data": {"username": username, "key": token, "scan_code": scan_code},
    }


def validate_and_get_api_url(url: str) -> str:
    """Validate and construct the API URL."""
    if not url.endswith("/api.php"):
        return url.rstrip("/") + "/api.php"
    return url


def generate_links(base_url: str, scan_id: int) -> Dict[str, str]:
    """Generate links for scan results."""
    return {
        "scan_link": (
            f"{base_url}/index.html?form=main_interface&action=scanview&sid={scan_id}"
            f"&current_view=pending_items"
        ),
        "policy_link": (
            f"{base_url}/index.html?form=main_interface&action=scanview&sid={scan_id}"
            f"&current_view=mark_as_identified"
        ),
        "main_scan_link": (
            f"{base_url}/index.html?form=main_interface&action=scanview&sid={scan_id}"
        ),
    }


def wait_for_scan_completion(api_url: str, config: Dict[str, Any]) -> None:
    """Wait for the scan to complete."""
    logging.info("Checking if the Scan is running...")
    scan_status = check_scan_status(
        api_url, config["username"], config["token"], config["scan_code"]
    )
    while scan_status.get("status") != "FINISHED":
        logging.info(
            "Scan Running: %s, waiting on completion...",
            scan_status.get("status", "UNKNOWN"),
        )
        time.sleep(config["interval"])
        scan_status = check_scan_status(
            api_url, config["username"], config["token"], config["scan_code"]
        )
    logging.info("The Scan completed!")


def check_pending_files(
    api_url: str, config: Dict[str, Any], links: Dict[str, str]
) -> bool:
    """Check for pending files and exit if any are found."""
    logging.info("Checking if any files have Pending Identifications...")
    pending_files = check_pending_identifications(
        api_url, config["username"], config["token"], config["scan_code"]
    )
    if pending_files:
        file_names = list(pending_files.values())
        if file_names:
            logging.info("This scan has Files with Pending Identifications.")
            if config["show_files"]:
                logging.info("Files to Review: %s", ", ".join(file_names))
            logging.info(
                "Review and Identify them in Workbench here: %s", links["scan_link"]
            )
            return True
    logging.info("No files have Pending Identifications.")
    return False


def check_policy(api_url: str, config: Dict[str, Any], links: Dict[str, str]) -> bool:
    """Check for policy violations and return True if any are found."""
    if config["policy_check"]:
        logging.info("Checking for Policy Warnings...")
        policy_violations = check_policy_violations(
            api_url, config["username"], config["token"], config["scan_code"]
        )
        policy_warnings = policy_violations.get("policy_warnings_list", [])
        if policy_warnings:
            logging.info("Policy violations found!")
            for warning in policy_warnings:
                if warning.get("license_id"):
                    logging.info(
                        "License Violation: %s - %s files",
                        warning["license_info"]["rule_lic_identifier"],
                        warning["findings"],
                    )
                else:
                    logging.info(
                        "Category Violation: %s - %s files",
                        warning["license_category"],
                        warning["findings"],
                    )
            logging.info(
                "View Files with Warnings in Workbench here: %s", links["policy_link"]
            )
            return True
        logging.info("No policy violations found.")
    return False


def get_scan_information(
    api_url: str, username: str, token: str, scan_code: str
) -> Dict[str, Any]:
    """Get scan information from the API."""
    payload = create_payload(username, token, scan_code, "get_information")
    return make_api_call(api_url, payload)


def set_env_variable(name: str, value: str):
    """Sets an environment variable."""
    os.environ[name] = value
    logging.info(f"Setting the environment variable '{name}'.")

def main():
    """Main function to orchestrate scan checks."""
    parser = argparse.ArgumentParser(
        description=(
            "Check scan status and pending identifications, "
            "and optionally check for policy violations."
        )
    )
    parser.add_argument("--workbench-url", type=str, help="The Workbench URL")
    parser.add_argument("--workbench-user", type=str, help="Your Workbench username")
    parser.add_argument("--workbench-token", type=str, help="Your Workbench API token")
    parser.add_argument(
        "--scan-code",
        type=str,
        required=True,
        help="The scan code to check the status for",
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=30,
        help="Interval in seconds to check the status (default: 30)",
    )
    parser.add_argument(
        "--show-files",
        action="store_true",
        help="Display the File Names with Pending IDs.",
    )
    parser.add_argument(
        "--policy-check",
        action="store_true",
        help="Checks for policy violations after checking for pending identifications.",
    )

    args = parser.parse_args()

    config = {
        "base_url": args.workbench_url or os.getenv("WORKBENCH_URL"),
        "username": args.workbench_user or os.getenv("WORKBENCH_USER"),
        "token": args.workbench_token or os.getenv("WORKBENCH_TOKEN"),
        "scan_code": args.scan_code,
        "interval": args.check_interval,
        "show_files": args.show_files,
        "policy_check": args.policy_check,
    }

    if not config["base_url"] or not config["username"] or not config["token"]:
        logging.error(
            "The Workbench URL, username, and token must be provided "
            "either as arguments or environment variables."
        )
        sys.exit(1)

    api_url = validate_and_get_api_url(config["base_url"])
    base_url_for_link = config["base_url"].replace("/api.php", "").rstrip("/")
    exit_code = 0  # Initialize exit_code to 0 (success)
    try:
        # Get scan information
        scan_info = get_scan_information(
            api_url, config["username"], config["token"], config["scan_code"]
        )
        scan_id = scan_info.get("id")

        if not scan_id:
            logging.error("Failed to retrieve scan ID from the API.")
            sys.exit(1)

        links = generate_links(base_url_for_link, scan_id)

        # print the scan URL and set it as an environment variable for future job steps
        print(f"\nFOSSID_SCAN_URL={links['main_scan_link']}\n")
        set_env_variable("FOSSID_SCAN_URL", links["main_scan_link"])

        wait_for_scan_completion(api_url, config)
        if check_pending_files(api_url, config, links):
            exit_code = 1  # Set exit_code to 1 if pending files are found
        if check_policy(api_url, config, links):
            exit_code = 1  # Set exit_code to 1 if policy violations are found

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logging.error("An error occurred: %s", str(e))
        sys.exit(1)

    sys.exit(exit_code)  # Exit with the appropriate code


if __name__ == "__main__":
    main()
