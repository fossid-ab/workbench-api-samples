#!/usr/bin/env python3
"""
This script is meant to be executed after a scan has been initiated in FossID Workbench.
This script will not initiate a scan - that is available with the Workbench Agent.

It first checks that the scan associated with the provided scan code completed.
Once the scan is done, it generates and downloads the reports for that scan.
By default, all available report types will be downloaded.
"""
import sys
import logging
import argparse
import os
from typing import Dict, Any, List

from workbench_agent.api.exceptions import WorkbenchApiError
from workbench_agent.api.utils.report_definitions import REPORT_DEFS

from lib.workbench_client import WorkbenchClient, normalize_api_url

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

SCAN_REPORT_TYPES = sorted(
    report_type
    for report_type, definition in REPORT_DEFS.items()
    if "scan" in definition["scopes"]
)


def resolve_report_types(report_type_arg: str) -> List[str]:
    if report_type_arg == "ALL":
        return list(SCAN_REPORT_TYPES)
    return [report_type_arg]


def main(config_data: Dict[str, Any]) -> None:
    """Main function to check scan status, generate and download report."""
    client = WorkbenchClient(
        config_data["url"], config_data["username"], config_data["token"]
    )
    scan_code = config_data["scan_code"]
    output_dir = config_data["output_dir"] or "."

    try:
        logging.info("Checking Scan: %s Status...", scan_code)
        client.status_check.check_scan_status(
            scan_code,
            wait=True,
            wait_retry_interval=config_data["check_interval"],
        )
        logging.info("Scan completed.")

        for report_type in resolve_report_types(config_data["report_type"]):
            logging.info("Generating and downloading %s report...", report_type)
            saved_path = client.reports.run_and_download_report(
                scope="scan",
                report_type=report_type,
                scan_code=scan_code,
                output_dir=output_dir,
                name_component=scan_code,
                wait_retry_interval=config_data["check_interval"],
            )
            logging.info("Report downloaded and saved as %s", saved_path)
    except WorkbenchApiError as e:
        logging.error("Workbench API error: %s", e)
        sys.exit(1)
    except OSError as e:
        logging.error("An OS error occurred: %s", e)
        sys.exit(1)


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

    config["url"] = normalize_api_url(config["url"])

    main(config)
