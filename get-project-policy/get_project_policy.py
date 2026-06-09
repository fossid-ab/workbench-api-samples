#!/usr/bin/env python3

import os
import sys
import argparse
import json

from workbench_agent.api.exceptions import WorkbenchApiError

from lib.workbench_client import client_from_env_or_args, normalize_api_url


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Get project license policy information from Workbench and save to .fossidpolicy file",
        epilog="""
Environment Variables for Credentials:
  WORKBENCH_URL    : API Endpoint URL (e.g., https://workbench.example.com/api.php)
  WORKBENCH_USER   : Workbench Username
  WORKBENCH_TOKEN  : Workbench API Token

Example Usage:
  # Get policy information for a project
  python3 get_project_policy.py --project-code "company/project-name"
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
    parser.add_argument('--project-code', required=True, help='Project code to get policy for')
    parser.add_argument('--output-file', default='.fossidpolicy', help='Output file name (default: .fossidpolicy)')

    args = parser.parse_args()

    if args.api_url:
        args.api_url = normalize_api_url(args.api_url)

    if not args.api_url:
        print("Error: Workbench URL is required. Provide with --api-url or set WORKBENCH_URL environment variable.")
        sys.exit(1)

    if not args.api_user:
        print("Error: Workbench username is required. Provide with --api-user or set WORKBENCH_USER environment variable.")
        sys.exit(1)

    if not args.api_token:
        print("Error: Workbench API token is required. Provide with --api-token or set WORKBENCH_TOKEN environment variable.")
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

    print(f"Fetching license policy information for project '{args.project_code}'...")
    try:
        policy = client.policy.download_project_policy_json(args.project_code)
    except WorkbenchApiError as e:
        print(f"Error: Failed to fetch policy information: {e}")
        sys.exit(1)

    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(policy, f, indent=2)

    print(f"License policy information saved to '{args.output_file}'")


if __name__ == "__main__":
    main()
