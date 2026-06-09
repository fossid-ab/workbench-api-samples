#!/usr/bin/env python3

import os
import sys
import argparse

from workbench_agent.api.exceptions import WorkbenchApiError

from lib.workbench_client import client_from_env_or_args, normalize_api_url


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Import Dependency Analysis results to Workbench",
        epilog="""
Environment Variables for Credentials:
  WORKBENCH_URL    : API Endpoint URL (e.g., https://workbench.example.com/api.php)
  WORKBENCH_USER   : Workbench Username
  WORKBENCH_TOKEN  : Workbench API Token

Example Usage:
  # Import DA results to an existing scan
  python3 import-da.py --url https://workbench.example.com --username admin --token API_TOKEN --scan-code SCAN-123 --file analyzer-result.json
"""
    )

    parser.add_argument(
        '--api-url',
        help='Workbench API URL. Overrides WORKBENCH_URL env var.',
        default=os.getenv("WORKBENCH_URL"),
        required=not os.getenv("WORKBENCH_URL")
    )
    parser.add_argument(
        '--api-user',
        help='Workbench username. Overrides WORKBENCH_USER env var.',
        default=os.getenv("WORKBENCH_USER"),
        required=not os.getenv("WORKBENCH_USER")
    )
    parser.add_argument(
        '--api-token',
        help='Workbench API token. Overrides WORKBENCH_TOKEN env var.',
        default=os.getenv("WORKBENCH_TOKEN"),
        required=not os.getenv("WORKBENCH_TOKEN")
    )
    parser.add_argument('--scan-code', required=True, help='Scan code to import DA results to')
    parser.add_argument('--file', required=True, help='Path to analyzer-result.json file')
    parser.add_argument('--max-tries', type=int, default=60,
                        help='Maximum number of status check attempts when waiting')
    parser.add_argument('--wait-time', type=int, default=2,
                        help='Seconds to wait between status checks')

    args = parser.parse_args()

    if args.api_url:
        args.api_url = normalize_api_url(args.api_url)

    if not args.api_url:
        print("Error: Workbench URL is required. Provide with --url or set WORKBENCH_URL environment variable.")
        sys.exit(1)

    if not args.api_user:
        print("Error: Workbench username is required. Provide with --username or set WORKBENCH_USER environment variable.")
        sys.exit(1)

    if not args.api_token:
        print("Error: Workbench API token is required. Provide with --token or set WORKBENCH_TOKEN environment variable.")
        sys.exit(1)

    if not args.file or not os.path.exists(args.file):
        print(f"Error: File does not exist: {args.file}")
        sys.exit(1)

    return args


def main():
    """Main function"""
    args = parse_args()

    try:
        client = client_from_env_or_args(
            url=args.api_url,
            user=args.api_user,
            token=args.api_token,
        )
    except KeyError:
        print("Error: WORKBENCH_URL environment variable is required when --api-url is not set.")
        sys.exit(1)

    print(f"\nUploading {args.file} to scan {args.scan_code}...")
    try:
        client.scan_content.upload_da_results(scan_code=args.scan_code, path=args.file)
        print("Upload successful!")

        print("\nStarting dependency analysis import...")
        client.scan_operations.start_da_import(scan_code=args.scan_code)

        print("Waiting for import to complete...")
        result = client.status_check.check_dependency_analysis_status(
            args.scan_code,
            wait=True,
            wait_retry_count=args.max_tries,
            wait_retry_interval=args.wait_time,
        )

        if result.success:
            duration = result.duration or 0
            print(
                f"\nDependency Analysis import completed successfully in {duration:.2f} seconds!"
            )
            return True

        print(f"Error in Dependency Analysis: {result.error_message or result.status}")
        sys.exit(1)

    except WorkbenchApiError as e:
        print(f"Workbench API error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
