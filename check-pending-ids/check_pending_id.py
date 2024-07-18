#!/usr/bin/env python3
"""
This script is meant to be executed after a scan has been initiated in FossID Workbench.
This script will not initiate a scan - that is available with the Workbench Agent.

It first checks that the scan associated to the provided scan code completed.
Once the scan is done, it checks if the scan contains Pending Identifications.
If it does, it exits with a message to the user saying to process all identifications, providing a link to the scan.
"""

import requests
import json
import time
import logging
import argparse
import os
import re
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a session object for making requests
session = requests.Session()

# Helper function to make API calls
def make_api_call(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to make API calls."""
    try:
        logging.debug(f"Making API call with payload: {json.dumps(payload, indent=2)}")
        response = session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logging.debug(f"Received response: {response.text}")
        return response.json().get('data', {})
    except requests.exceptions.RequestException as e:
        logging.error(f"API call failed: {str(e)}")
        logging.error(f"Response content: {response.text if response else 'No response'}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON response: {str(e)}")
        logging.error(f"Response content: {response.text if response else 'No response'}")
        raise

# Function to Check Scan Status
def check_scan_status(api_url, api_username, api_token, scan_code):
    payload = {
        "group": "scans",
        "action": "check_status",
        "data": {
            "username": api_username,
            "key": api_token,
            "scan_code": scan_code,
            "delay_response": "1"
        }
    }
    return make_api_call(api_url, payload)

# Function to Check for Pending Identifications
def check_pending_identifications(api_url, api_username, api_token, scan_code):
    payload = {
        "group": "scans",
        "action": "get_pending_files",
        "data": {
            "username": api_username,
            "key": api_token,
            "scan_code": scan_code
        }
    }
    return make_api_call(api_url, payload)

def main(api_base_url, api_username, api_token, scan_code, check_interval, show_files):
    # Ensure the API URL ends with /api.php and doesn't contain it twice
    if not api_base_url.endswith('/api.php'):
        api_url = api_base_url.rstrip('/') + '/api.php'
    else:
        api_url = api_base_url

    # Strip /api.php from the base URL for generating scan link
    base_url_for_link = api_base_url.replace('/api.php', '').rstrip('/')
    
    # Extract the numeric part from the scan code
    scan_id = re.search(r'\d+$', scan_code)
    if not scan_id:
        logging.error("Invalid scan code format. The scan code must end with a numeric identifier.")
        exit(1)
    scan_id = scan_id.group()
    scan_link = f"{base_url_for_link}/index.html?form=main_interface&action=scanview&sid={scan_id}&current_view=pending_items"
    
    try:
        # Step 1: Check for scan completion
        logging.info("Checking Scan Status...")
        scan_status = check_scan_status(api_url, api_username, api_token, scan_code)
        while scan_status['status'] != 'FINISHED':
            logging.info(f"Scan status: {scan_status['status']}, waiting to complete...")
            time.sleep(check_interval)  # Wait for check_interval seconds before checking again
            scan_status = check_scan_status(api_url, api_username, api_token, scan_code)
        logging.info("The Scan completed! Checking for Pending IDs.")

        # Step 2: Check for pending identifications
        logging.info("Checking for files Pending Identification...")
        pending_files = check_pending_identifications(api_url, api_username, api_token, scan_code)
        if pending_files:
            file_names = list(pending_files.values())
            if file_names:
                logging.info(f"Files with Pending Identifications found.")
                logging.info(f"Log into Workbench to view them here: {scan_link}")
                if show_files:
                    logging.info(f"Pending files: {', '.join(file_names)}")
                exit(1)
        logging.info("The scan has no files with Pending Identifications.")

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check scan status and pending identifications.')
    parser.add_argument('--workbench-url', type=str, help='The Workbench URL')
    parser.add_argument('--workbench-user', type=str, help='Your Workbench username')
    parser.add_argument('--workbench-token', type=str, help='Your Workbench API token')
    parser.add_argument('--scan-code', type=str, required=True, help='The scan code to check the status for')
    parser.add_argument('--check-interval', type=int, default=30, help='Interval in seconds to check the status (default: 30)')
    parser.add_argument('--show-files', action='store_true', help='Display the names of pending files')

    args = parser.parse_args()
    
    api_base_url = args.workbench_url or os.getenv('WORKBENCH_URL')
    api_username = args.workbench_user or os.getenv('WORKBENCH_USER')
    api_token = args.workbench_token or os.getenv('WORKBENCH_TOKEN')

    if not api_base_url or not api_username or not api_token:
        logging.info("The Workbench URL, username, and token must be provided either as arguments or environment variables.")
        exit(1)
    
    main(api_base_url, api_username, api_token, args.scan_code, args.check_interval, args.show_files)