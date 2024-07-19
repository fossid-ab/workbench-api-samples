#!/usr/bin/env python3
"""
This script performs a quick scan of a single file using the FossID Workbench API.
It encodes the file in base64, sends it to the API, and prints the results.
"""

import sys
import json
import base64
import logging
import argparse
import os
from typing import Dict, Any
import requests

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


def quick_scan(
    scan_url: str, scan_user: str, scan_key: str, file_content: str
) -> Dict[str, Any]:
    """Perform the quick scan"""
    payload = {
        "group": "quick_scan",
        "action": "scan_one_file",
        "data": {
            "username": scan_user,
            "key": scan_key,
            "file_content": file_content,
            "limit": "1",
            "sensitivity": "10",
        },
    }
    return make_api_call(scan_url, payload)


def main(
    scan_url: str, scan_user: str, scan_key: str, file_path: str, raw_output: bool
):
    """Main function to perform the quick scan and print the results."""
    # Ensure the API URL ends with /api.php and doesn't contain it twice
    if not scan_url.endswith("/api.php"):
        scan_url = scan_url.rstrip("/") + "/api.php"

    # Read and encode the file content in base64
    with open(file_path, "rb") as file:
        file_content = base64.b64encode(file.read()).decode("utf-8")

    try:
        # Perform the quick scan
        logging.info("Performing quick scan...")
        scan_result = quick_scan(scan_url, scan_user, scan_key, file_content)
        if scan_result:
            for result in scan_result:
                result_data = json.loads(result)
                if raw_output:
                    print(json.dumps(result_data, indent=2))
                else:
                    component = result_data.get("component")
                    match_type = result_data.get("type")
                    if component:
                        artifact = component.get("artifact")
                        author = component.get("author")
                        quick_view_link = (
                            scan_url.replace("/api.php", "")
                            + "/?form=main_interface&action=quickview"
                        )
                        if match_type == "file":
                            message = (
                                f"This entire file seems to originate from the {artifact} "
                                f"repository by {author}. "
                                f"Drop this file into the Quick View in Workbench"
                                f"for more information. You can access it here: "
                                f"{quick_view_link}"
                            )
                        elif match_type == "partial":
                            remote_size = result_data["snippet"].get("remote_size")
                            message = (
                                f"This file has {remote_size} lines that look like they're from "
                                f"{artifact} by {author}. "
                                f"Drop this file into the Quick View in Workbench "
                                f"for more information. You can access it here: "
                                f"{quick_view_link}"
                            )
                        else:
                            message = "Unknown match type."
                        logging.info(message)
                    else:
                        logging.info("No matches found.")
        else:
            logging.info("No matches found.")
    except requests.exceptions.RequestException as e:
        logging.error("API call failed: %s", str(e))
        sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON response: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Perform a quick scan of a single file."
    )
    parser.add_argument("--workbench-url", type=str, help="The Workbench API URL")
    parser.add_argument("--workbench-user", type=str, help="Your Workbench username")
    parser.add_argument("--workbench-token", type=str, help="Your Workbench API token")
    parser.add_argument(
        "--raw", action="store_true", help="Display the raw output of the scan"
    )
    parser.add_argument("file_path", type=str, help="The path to the file to scan")

    args = parser.parse_args()

    api_url = args.workbench_url or os.getenv("WORKBENCH_URL")
    api_user = args.workbench_user or os.getenv("WORKBENCH_USER")
    api_key = args.workbench_token or os.getenv("WORKBENCH_TOKEN")

    if not api_url or not api_user or not api_key:
        logging.info(
            "The Workbench URL, username, and token must be provided either as "
            "arguments or environment variables."
        )
        sys.exit(1)

    main(api_url, api_user, api_key, args.file_path, args.raw)
