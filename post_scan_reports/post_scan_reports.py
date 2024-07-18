#!/usr/bin/env python3
"""
This script is meant to be executed after a scan has been initiated in FossID Workbench.

It first checks that the scan completed.
Once the scan is done, it generates and downloads the reports for that scan.
All available report types will be downloaded.
"""

import requests
import json
import time
import logging
import argparse
import os
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
def check_scan_status(api_url, api_username, api_token, scan_code, process_id=None):
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
    if process_id:
        payload['data']['process_id'] = process_id
    return make_api_call(api_url, payload)

# Function to Generate Report
def generate_report(api_url, api_username, api_token, scan_code, report_type):
    payload = {
        "group": "scans",
        "action": "generate_report",
        "data": {
            "username": api_username,
            "key": api_token,
            "scan_code": scan_code,
            "report_type": report_type,
            "selection_type": "include_all_licenses",
            "selection_view": "all",
            "async": "1"
        }
    }
    response_data = make_api_call(api_url, payload)
    process_queue_id = response_data.get('process_queue_id')
    generation_process = response_data.get('generation_process', {})
    generation_process_id = generation_process.get('id')
    return process_queue_id, generation_process_id

# Function to Download Report
def download_report(api_url, api_username, api_token, scan_code, process_queue_id, report_type):
    payload = {
        "group": "download",
        "action": "download_report",
        "data": {
            "username": api_username,
            "key": api_token,
            "report_entity": "scans",
            "process_id": process_queue_id
        }
    }
    response = session.post(api_url, json=payload, timeout=60)
    response.raise_for_status()
    
    file_extension = {
        "html": "html",
        "dynamic_top_matched_components": "html",
        "xlsx": "xlsx",
        "spdx": "rdf",
        "spdx_lite": "xlsx",
        "cyclone_dx": "json",
        "string_match": "xlsx"
    }.get(report_type, "zip")

    file_name = f"{scan_code}_{report_type}_report.{file_extension}"
    with open(file_name, 'wb') as f:
        f.write(response.content)
    logging.info(f"Report downloaded and saved as {file_name}")

def main(api_url, api_username, api_token, scan_code, report_type, check_interval):
    try:
        # Step 1: Check for scan completion
        logging.info("Checking Scan Status...")
        scan_status = check_scan_status(api_url, api_username, api_token, scan_code)
        while scan_status['status'] != 'FINISHED':
            logging.info(f"Scan status: {scan_status['status']}, waiting to complete...")
            time.sleep(check_interval)  # Wait for check_interval seconds before checking again
            scan_status = check_scan_status(api_url, api_username, api_token, scan_code)
        logging.info("Scan completed.")

        # List of all report types
        report_types = [
            "html", "dynamic_top_matched_components", "xlsx",
            "spdx", "spdx_lite", "cyclone_dx", "string_match"
        ]

        # Step 2: Generate and download reports
        if report_type == "ALL":
            for rpt_type in report_types:
                logging.info(f"Generating {rpt_type} report...")
                process_queue_id, generation_process_id = generate_report(api_url, api_username, api_token, scan_code, rpt_type)
                logging.info(f"Report generation started. Process ID: {process_queue_id}")

                # Check for report generation completion
                logging.info(f"Checking {rpt_type} Report Generation Status...")
                report_status = check_scan_status(api_url, api_username, api_token, scan_code, process_id=generation_process_id)
                while report_status['status'] != 'FINISHED':
                    logging.info(f"Report generation status: {report_status['status']}, waiting to complete...")
                    time.sleep(check_interval)  # Wait for check_interval seconds before checking again
                    report_status = check_scan_status(api_url, api_username, api_token, scan_code, process_id=generation_process_id)
                logging.info(f"{rpt_type} report generated.")

                # Download report
                logging.info(f"Downloading {rpt_type} report...")
                download_report(api_url, api_username, api_token, scan_code, process_queue_id, rpt_type)
        else:
            logging.info(f"Generating {rpt_type} report...")
            process_queue_id, generation_process_id = generate_report(api_url, api_username, api_token, scan_code, report_type)
            logging.info(f"Report generation started. Process ID: {process_queue_id}")

            # Step 3: Check for report generation completion
            logging.info(f"Checking {rpt_type} Report Generation Status...")
            report_status = check_scan_status(api_url, api_username, api_token, scan_code, process_id=generation_process_id)
            while report_status['status'] != 'FINISHED':
                logging.info(f" {rpt_type} Report generation status: {report_status['status']}, waiting to complete...")
                time.sleep(check_interval)  # Wait for check_interval seconds before checking again
                report_status = check_scan_status(api_url, api_username, api_token, scan_code, process_id=generation_process_id)
            logging.info(f"{rpt_type} Report generation completed.")

            # Step 4: Download report
            logging.info(f"Downloading {rpt_type} report...")
            download_report(api_url, api_username, api_token, scan_code, process_queue_id, report_type)

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check scan status, generate and download report.')
    parser.add_argument('--workbench-url', type=str, help='The Workbench API URL')
    parser.add_argument('--workbench-user', type=str, help='Your Workbench username')
    parser.add_argument('--workbench-token', type=str, help='Your Workbench API token')
    parser.add_argument('--scan-code', type=str, required=True, help='The scan code to check the status for')
    parser.add_argument('--report-type', type=str, default='ALL', help='The type of report to generate (default: ALL)')
    parser.add_argument('--check-interval', type=int, default=30, help='Interval in seconds to check the status (default: 30)')

    args = parser.parse_args()
    
    api_url = args.workbench_url or os.getenv('WORKBENCH_URL')
    api_username = args.workbench_user or os.getenv('WORKBENCH_USER')
    api_token = args.workbench_token or os.getenv('WORKBENCH_TOKEN')

    if not api_url or not api_username or not api_token:
        logging.info("The Workbench URL, username, and token must be provided either as arguments or environment variables.")
        exit(1)
    
    main(api_url, api_username, api_token, args.scan_code, args.report_type, args.check_interval)