#!/usr/bin/env python3

import os
import sys
import argparse
import requests
import json


class WorkbenchAPI:
    """Simple API client for Workbench"""

    def __init__(self, url, token, username):
        self.base_url = url.rstrip('/')
        self.api_token = token
        self.api_user = username
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json, text/plain',
            'Content-Type': 'application/json'
        })
        
    def get_project_policy(self, project_code):
        """Get license policy information for a project"""
        payload = {
            "group": "download",
            "action": "licenses_policy_info",
            "data": {
                "username": self.api_user,
                "key": self.api_token,
                "project_code": project_code
            }
        }
        
        return self._send_request(payload)
    
    def _send_request(self, payload):
        """
        Send an API request to the Workbench server
        """
        api_endpoint = f"{self.base_url}"
        try:
            response = self.session.post(
                api_endpoint,
                json=payload,
                auth=(self.api_user, self.api_token),
                timeout=300
            )
            
            if response.status_code != 200:
                print(f"Error: API request failed with status {response.status_code}")
                print(f"Response: {response.text[:500]}...")
                sys.exit(1)

            # Return the raw response object instead of parsing JSON
            return response
                
        except requests.exceptions.RequestException as e:
            print(f"Network error during API request: {e}")
            sys.exit(1)


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
    
    # Fix API URL if it doesn't end with '/api.php'
    if args.api_url and not args.api_url.endswith('/api.php'):
        if args.api_url.endswith('/'):
            args.api_url = args.api_url + 'api.php'
        else:
            args.api_url = args.api_url + '/api.php'
    
    # Validate required parameters
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
    
    # Initialize API client
    workbench = WorkbenchAPI(args.api_url, args.api_token, args.api_user)
    
    print(f"Fetching license policy information for project '{args.project_code}'...")
    response = workbench.get_project_policy(args.project_code)
    
    # Check if we got a valid response
    if response.status_code != 200:
        print(f"Error: Failed to fetch policy information. Status code: {response.status_code}")
        sys.exit(1)
    
    # Get content type to determine how to handle the response
    content_type = response.headers.get('Content-Type', '')
    
    # Save the response content to the output file
    with open(args.output_file, 'wb') as f:
        f.write(response.content)
    
    print(f"License policy information saved to '{args.output_file}'")


if __name__ == "__main__":
    main()
