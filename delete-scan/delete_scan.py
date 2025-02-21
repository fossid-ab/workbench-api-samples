#!/usr/bin/env python3
"""
This script deletes a specific scan from FossID Workbench using the provided scan code.
"""

import argparse
import os
import sys
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def delete_scan(url: str, username: str, token: str, scan_code: str) -> bool:
    """Delete a scan."""
    payload = {
        "group": "scans",
        "action": "delete_scan",
        "data": {"username": username, "key": token, "scan_code": scan_code},
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error("Error deleting scan %s: %s", scan_code, str(e))
        return False

def main(url: str, username: str, token: str, scan_code: str):
    """Main function to delete a scan."""
    logging.info(f"Attempting to delete scan with code: {scan_code}")
    
    if delete_scan(url, username, token, scan_code):
        logging.info(f"Successfully deleted scan: {scan_code}")
    else:
        logging.error(f"Failed to delete scan: {scan_code}")

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

    # Sanity check for Workbench URL
    if not api_url.endswith("/api.php"):
        api_url += "/api.php"

    main(api_url, api_username, api_token, args.scan_code)
