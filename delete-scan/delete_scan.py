#!/usr/bin/env python3
"""
This script deletes a specific scan from FossID Workbench using the provided scan code.
"""

import argparse
import os
import sys
import logging

from workbench_agent.api.exceptions import WorkbenchApiError

from lib.workbench_client import client_from_env_or_args, normalize_api_url

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main(url: str, username: str, token: str, scan_code: str):
    """Main function to delete a scan."""
    logging.info("Attempting to delete scan with code: %s", scan_code)

    client = client_from_env_or_args(url=url, user=username, token=token)

    try:
        result = client.scan_deletion.delete_scan(scan_code)
        if result.success:
            logging.info("Successfully deleted scan: %s", scan_code)
        else:
            logging.error("Failed to delete scan: %s", scan_code)
            sys.exit(1)
    except WorkbenchApiError as e:
        logging.error("Workbench API error deleting scan %s: %s", scan_code, e)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a specific scan.")
    parser.add_argument("--workbench-url", type=str, help="The Workbench API URL")
    parser.add_argument("--workbench-user", type=str, help="Your Workbench username")
    parser.add_argument("--workbench-token", type=str, help="Your Workbench API token")
    parser.add_argument("--scan-code", type=str, required=True, help="The code of the scan to delete")

    args = parser.parse_args()

    api_url = args.workbench_url or os.getenv("WORKBENCH_URL")
    api_username = args.workbench_user or os.getenv("WORKBENCH_USER")
    api_token = args.workbench_token or os.getenv("WORKBENCH_TOKEN")

    if not api_url or not api_username or not api_token:
        logging.error(
            "The Workbench URL, username, and token must be provided either as arguments "
            "or environment variables."
        )
        sys.exit(1)

    api_url = normalize_api_url(api_url)

    main(api_url, api_username, api_token, args.scan_code)
