#!/usr/bin/env python3

import os
import sys
import argparse
import time
import requests
import base64
import json


class WorkbenchAPI:
    """Simple API client for Workbench"""

    def __init__(self, url, token, username):
        self.base_url = url.rstrip('/')
        self.api_token = token
        self.api_user = username
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
    def upload_files(self, scan_code, file_path):
        """Upload a file to the specified scan using proper API format"""
        if not os.path.exists(file_path):
            print(f"Error: File does not exist: {file_path}")
            sys.exit(1)
            
        file_handle = None
        try:
            file_size = os.path.getsize(file_path)
            upload_basename = os.path.basename(file_path)
            
            # Encode headers
            name_b64 = base64.b64encode(upload_basename.encode()).decode("utf-8")
            scan_code_b64 = base64.b64encode(scan_code.encode()).decode("utf-8")
            
            headers = {
                "FOSSID-SCAN-CODE": scan_code_b64,
                "FOSSID-FILE-NAME": name_b64,
                "Accept": "*/*"  # Keep Accept broad
            }
            
            # For DA imports, set the special header
            headers["FOSSID-UPLOAD-TYPE"] = "dependency_analysis"
            print(f"Uploading DA results file '{upload_basename}' ({file_size} bytes)...")
            
            file_handle = open(file_path, "rb")
            upload_url = f"{self.base_url}"
            
            # Standard upload for smaller files
            resp = self.session.post(
                upload_url,
                headers=headers,
                data=file_handle,
                auth=(self.api_user, self.api_token),
                timeout=1800,
            )
            print(f"Upload Response Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Error response: {resp.text[:500]}...")
                sys.exit(1)
            
            print(f"Upload for '{upload_basename}' completed.")
                
        except requests.exceptions.RequestException as e:
            print(f"Network error during file upload: {e}")
            sys.exit(1)
        finally:
            # Ensure file handle is closed
            if file_handle and not file_handle.closed:
                file_handle.close()
                print(f"Closed file handle for {file_path}")
    
    def start_dependency_analysis(self, scan_code):
        """
        Start dependency analysis for a scan.
        """
        payload = {
            "group": "scans",
            "action": "run_dependency_analysis",
            "data": {
                "username": self.api_user,
                "key": self.api_token,
                "scan_code": scan_code,
                "import_only": "1",
            },
        }
        
        print(f"Importing DA results into Scan '{scan_code}'.")

        response = self._send_request(payload)
        if response.get("status") == "1":
            print(f"Dependency Analysis started for scan '{scan_code}'.")
        else:
            error_msg = response.get("error", "Unknown error")
            if "Scan not found" in error_msg or "row_not_found" in error_msg:
                print(f"Error: Scan '{scan_code}' not found")
                sys.exit(1)
            print(f"Error: Dependency Analysis for scan '{scan_code}' failed to start: {error_msg}")
            sys.exit(1)
            
        return response
    
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
                
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Network error during API request: {e}")
            sys.exit(1)
    
    def get_dependency_analysis_status(self, scan_code):
        """
        Get the status of dependency analysis for a scan.
        Uses the same approach as get_scan_status with type="DEPENDENCY_ANALYSIS".
        """
        payload = {
            "group": "scans",
            "action": "check_status",
            "data": {
                "username": self.api_user,
                "key": self.api_token,
                "scan_code": scan_code,
                "type": "DEPENDENCY_ANALYSIS",
            },
        }
        
        response = self._send_request(payload)
        
        # Check for successful response with data
        if response.get("status") == "1" and "data" in response:
            return response["data"]
        else:
            error_msg = response.get("error", "Unknown error")
            if "Scan not found" in error_msg or "row_not_found" in error_msg:
                print(f"Error: Scan '{scan_code}' not found")
                sys.exit(1)
            print(f"Error: Failed to retrieve DEPENDENCY_ANALYSIS status for scan '{scan_code}': {error_msg}")
            sys.exit(1)
  

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
    
    # Fix API URL if it doesn't end with '/api.php'
    if args.api_url and not args.api_url.endswith('/api.php'):
        if args.api_url.endswith('/'):
            args.api_url = args.api_url + 'api.php'
        else:
            args.api_url = args.api_url + '/api.php'
    
    # Validate required parameters
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
    
    # Initialize API client
    workbench = WorkbenchAPI(args.api_url, args.api_token, args.api_user)
    
    # Upload the file
    print(f"\nUploading {args.file} to scan {args.scan_code}...")
    workbench.upload_files(args.scan_code, args.file)
    print("Upload successful!")
    
    # Start dependency analysis import
    print("\nStarting dependency analysis import...")
    workbench.start_dependency_analysis(args.scan_code)
    
    # Wait for import to complete
    print("Waiting for import to complete...")
    start_time = time.time()
    tries = 0
    
    while tries < args.max_tries:
        status_data = workbench.get_dependency_analysis_status(args.scan_code)
        
        # Check status - can be in various formats
        is_finished = str(status_data.get("is_finished")) == "1" or status_data.get("is_finished") is True
        status = status_data.get("status", "UNKNOWN").upper()
        
        if is_finished or status == "FINISHED" or status == "READY":
            duration = time.time() - start_time
            print(f"\nDependency Analysis import completed successfully in {duration:.2f} seconds!")
            return True
        
        if status == "ERROR" or status == "FAILED":
            print(f"Error in Dependency Analysis: {status_data.get('message', 'Unknown error')}")
            sys.exit(1)
            
        print(f"Status: {status} - Waiting {args.wait_time} seconds...")
        time.sleep(args.wait_time)
        tries += 1
        
    print(f"Timeout waiting for DEPENDENCY_ANALYSIS to finish after {args.max_tries} tries")
    sys.exit(1)
    

if __name__ == "__main__":
    main()
