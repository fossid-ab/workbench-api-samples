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

import logging
import argparse
import os
import sys

from workbench_agent.api.exceptions import WorkbenchApiError

from lib.workbench_client import WorkbenchClient, normalize_api_url

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def set_env_variable(name: str, value: str):
    """Sets an environment variable."""
    os.environ[name] = value
    logging.info("Setting the environment variable '%s'.", name)


def wait_for_scan_completion(client: WorkbenchClient, scan_code: str, interval: int) -> None:
    """Wait for the scan to complete."""
    logging.info("Checking if the Scan is running...")
    result = client.status_check.check_scan_status(
        scan_code,
        wait=True,
        wait_retry_interval=interval,
    )
    logging.info("The Scan completed with status: %s", result.status)


def check_pending_files(
    client: WorkbenchClient, scan_code: str, show_files: bool, pending_link: str
) -> bool:
    """Check for pending files and exit if any are found."""
    logging.info("Checking if any files have Pending Identifications...")
    pending_files = client.identification.get_pending_files(scan_code)
    if pending_files:
        file_names = list(pending_files.values())
        if file_names:
            logging.info("This scan has Files with Pending Identifications.")
            if show_files:
                logging.info("Files to Review: %s", ", ".join(file_names))
            logging.info(
                "Review and Identify them in Workbench here: %s", pending_link
            )
            return True
    logging.info("No files have Pending Identifications.")
    return False


def check_policy(
    client: WorkbenchClient, scan_code: str, policy_check: bool, policy_link: str
) -> bool:
    """Check for policy violations and return True if any are found."""
    if policy_check:
        logging.info("Checking for Policy Warnings...")
        policy_violations = client.policy.get_scan_identification_policy_warnings_info(
            scan_code
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
                "View Files with Warnings in Workbench here: %s", policy_link
            )
            return True
        logging.info("No policy violations found.")
    return False


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

    base_url = args.workbench_url or os.getenv("WORKBENCH_URL")
    username = args.workbench_user or os.getenv("WORKBENCH_USER")
    token = args.workbench_token or os.getenv("WORKBENCH_TOKEN")

    if not base_url or not username or not token:
        logging.error(
            "The Workbench URL, username, and token must be provided "
            "either as arguments or environment variables."
        )
        sys.exit(1)

    api_url = normalize_api_url(base_url)
    exit_code = 0

    try:
        client = WorkbenchClient(api_url, username, token)
        links = client.links.get_workbench_links(args.scan_code)

        print(f"\nFOSSID_SCAN_URL={links.scan['url']}\n")
        print(
            "Note: You need to be signed in to FossID Workbench to access the link above, "
            "otherwise you will see a spinning loading indicator."
        )
        set_env_variable("FOSSID_SCAN_URL", links.scan["url"])

        wait_for_scan_completion(client, args.scan_code, args.check_interval)
        if check_pending_files(
            client, args.scan_code, args.show_files, links.pending["url"]
        ):
            exit_code = 1
        if check_policy(
            client, args.scan_code, args.policy_check, links.policy["url"]
        ):
            exit_code = 1

    except WorkbenchApiError as e:
        logging.error("Workbench API error: %s", e)
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
