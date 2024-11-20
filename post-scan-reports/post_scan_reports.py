#!/usr/bin/env python3
"""
This script is meant to be executed after a scan has been initiated in FossID Workbench.
This script will not initiate a scan - that is available with the Workbench Agent.

It first checks that the scan associated with the provided scan code completed.
Once the scan is done, it generates and downloads the reports for that scan.
By default, all available report types will be downloaded.
"""
import sys
import json
import time
import logging
import argparse
import os
from typing import Dict, Any, Tuple
import helper_functions as hf
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Create a session object for making requests
#session = requests.Session()

# List of all report types
REPORT_TYPES = [
    "html",
    "dynamic_top_matched_components",
    "xlsx",
    "spdx",
    "spdx_lite",
    "cyclone_dx",
    "string_match",
]

class ApiClient:
    """
    This class represents an API client for making requests to the FossID Workbench API.
    """

    def __init__(self, url: str, username: str, token: str):
        self.url = url
        self.username = username
        self.token = token

    #Helper function to make API calls.
    """def make_api_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logging.debug(
                "Making API call with payload: %s", json.dumps(payload, indent=2)
            )
            response = session.post(self.url, json=payload, timeout=10)
            response.raise_for_status()
            logging.debug("Received response: %s", response.text)
            return response.json().get("data", {})
        except requests.exceptions.RequestException as e:
            logging.error("API call failed: %s", str(e))
            raise
        except json.JSONDecodeError as e:
            logging.error("Failed to parse JSON response: %s", str(e))
            raise
"""

    def check_scan_status(self, scan_code: str, process_id: str = None) -> Dict[str, Any]:
        """Check Workbench scan status."""
        payload = {
            "group": "scans",
            "action": "check_status",
            "data": {
                "username": self.username,
                "key": self.token,
                "scan_code": scan_code,
                "delay_response": "1",
            },
        }
        if process_id:
            payload["data"]["process_id"] = process_id
        return self.make_api_call(payload)

    def generate_report(self, scan_code: str, report_type: str) -> Tuple[str, str]:
        """Generate Workbench report."""
        payload = {
            "group": "scans",
            "action": "generate_report",
            "data": {
                "username": self.username,
                "key": self.token,
                "scan_code": scan_code,
                "report_type": report_type,
                "selection_type": "include_all_licenses",
                "selection_view": "all",
                "async": "1",
            },
        }
        response_data = self.make_api_call(payload)
        return response_data.get("process_queue_id"), response_data.get(
            "generation_process", {}
        ).get("id")

    def create_output_dir(self, output_dir: str) -> str:
        """Create the output directory if it doesn't exist."""
        if output_dir and not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except PermissionError:
                logging.error(
                    "PermissionError while trying to create output directory: %s",
                    output_dir,
                )
                output_dir = ""
            except OSError as ex:
                logging.error(
                    "Error creating output directory: %s | %s", output_dir, str(ex)
                )
                output_dir = ""
        return output_dir

    def download_report(
        self, scan_code: str, process_queue_id: str, report_type: str, output_dir: str
    ) -> None:
        """Download report. If output_dir is set it will save it to that path."""
        payload = {
            "group": "download",
            "action": "download_report",
            "data": {
                "username": self.username,
                "key": self.token,
                "report_entity": "scans",
                "process_id": process_queue_id,
            },
        }
        response = requests.post(self.url, json=payload, timeout=120)
        response.raise_for_status()

        file_extension = {
            "html": "html",
            "dynamic_top_matched_components": "html",
            "xlsx": "xlsx",
            "spdx": "rdf",
            "spdx_lite": "xlsx",
            "cyclone_dx": "json",
            "string_match": "xlsx",
        }.get(report_type, "zip")

        file_name = f"{scan_code}_{report_type}_report.{file_extension}"
        output_dir = self.create_output_dir(output_dir)
        if output_dir:
            try:
                file_name = os.path.join(output_dir, file_name)
            except OSError as ex:
                logging.error(
                    "Error joining output dir with filename: %s | %s", output_dir, str(ex)
                )
        contents = self.process_report_contents(response, report_type)
        mode = "w" if isinstance(contents, str) else "wb"
        with open(file_name, mode, encoding="utf-8" if mode == "w" else None) as f:
            f.write(contents)
        logging.info("Report downloaded and saved as %s", file_name)

    def process_report_contents(self, response, report_type: str):
        """Process report contents based on report type."""
        contents = response.content
        if report_type == "dynamic_top_matched_components":
            try:
                json_response = response.json()
                data_info = json_response.get("data")
                if data_info:
                    report_info = data_info.get("report")
                    if report_info:
                        contents = report_info
            except json.JSONDecodeError as ex:
                logging.error(
                    "Error downloading dynamic_top_matched_components report | %s", str(ex)
                )
        return contents

def process_report_type(
    client: ApiClient,
    scan_code: str,
    report_type: str,
    check_interval: int,
    output_dir: str,
) -> None:
    """Process report type for the scan."""
    logging.info("Generating %s report...", report_type)
    process_queue_id, generation_process_id = client.generate_report(scan_code, report_type)
    logging.info("Report generation started. Process ID: %s", process_queue_id)
    logging.info("Checking %s Report Generation Status...", report_type)
    report_status = client.check_scan_status(scan_code, process_id=generation_process_id)
    while report_status["status"] != "FINISHED":
        logging.info(
            "Report generation status: %s, waiting to complete...",
            report_status["status"],
        )
        time.sleep(check_interval)
        report_status = client.check_scan_status(scan_code, process_id=generation_process_id)
    logging.info("%s Report generation completed.", report_type)
    logging.info("Downloading %s report...", report_type)
    client.download_report(scan_code, process_queue_id, report_type, output_dir)

def main(config_data: Dict[str, Any]) -> None:
    """Main function to check scan status, generate and download report."""
    client = ApiClient(config_data["url"], config_data["username"], config_data["token"])
    try:
        logging.info("Checking Scan: %s Status...", config_data["scan_code"])
        scan_status = client.check_scan_status(config_data["scan_code"])
        while scan_status["status"] != "FINISHED":
            logging.info(
                "Scan status: %s, waiting to complete...", scan_status["status"]
            )
            time.sleep(config_data["check_interval"])
            scan_status = client.check_scan_status(config_data["scan_code"])
        logging.info("Scan completed.")

        if config_data["report_type"] == "ALL":
            for rpt_type in REPORT_TYPES:
                process_report_type(
                    client, config_data["scan_code"], rpt_type,
                    config_data["check_interval"], config_data["output_dir"]
                )
        else:
            process_report_type(
                client, config_data["scan_code"], config_data["report_type"],
                config_data["check_interval"], config_data["output_dir"]
            )
    except requests.exceptions.RequestException as e:
        logging.error("A requests exception occurred: %s", str(e))
    except json.JSONDecodeError as e:
        logging.error("A JSON decoding error occurred: %s", str(e))
    except OSError as e:
        logging.error("An OS error occurred: %s", str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check scan status, generate and download report.",
        epilog="Example: python script.py --scan-code SCAN123 --report-types xlsx spdx",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--workbench-url", type=str, help="The Workbench API URL")
    parser.add_argument("--workbench-user", type=str, help="Your Workbench username")
    parser.add_argument("--workbench-token", type=str, help="Your Workbench API token")
    parser.add_argument(
        "--scan-code",
        type=str,
        required=True,
        help="The scan code to check the status for",
    )
    parser.add_argument(
        "--report-type",
        type=str,
        default="ALL",
        help="The type of report to generate (default: ALL)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(), required=False, help="Output directory"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=30,
        help="Interval in seconds to check the status (default: 30)",
    )

    args = parser.parse_args()

    config = {
        "url": args.workbench_url or os.getenv("WORKBENCH_URL"),
        "username": args.workbench_user or os.getenv("WORKBENCH_USER"),
        "token": args.workbench_token or os.getenv("WORKBENCH_TOKEN"),
        "scan_code": args.scan_code,
        "report_type": args.report_type,
        "check_interval": args.check_interval,
        "output_dir": args.output_dir,
    }

    if not config["url"] or not config["username"] or not config["token"]:
        logging.info(
            "The Workbench URL, username, and token must be provided "
            "either as arguments or environment variables."
        )
        sys.exit(1)

    main(config)
