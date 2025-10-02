#!/usr/bin/env python3
"""
This script archives stale scans from the FossID Workbench using a
command-based approach.

Commands:
  plan    - Create a JSON plan of scans to be archived based on age criteria
  archive - Execute archiving based on a previously created JSON plan

This two-step approach allows for validation and modification of the
archive plan before execution.
"""

import sys
import json
from datetime import datetime, timedelta
import logging
import argparse
import os
from typing import List, Tuple, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration constants
RECORDS_PER_PAGE = 100  # Number of records to fetch per page from the List_Scans API
MAX_WORKERS = 10       # Maximum number of concurrent API requests for getting scan info
BATCH_SIZE = 50        # Number of scans to process concurrently in each batch
DEFAULT_DAYS = 365     # Default age threshold for stale scans
DEFAULT_PLAN_FILE = "archive_plan.json"  # Default plan file name
API_TIMEOUT = 10       # API request timeout in seconds
BATCH_DELAY = 0.1      # Delay between batches in seconds

# Create a session object for making requests
session = requests.Session()

# Global cache for project information to avoid redundant API calls
project_cache: Dict[str, Dict[str, Any]] = {}


class SmartSampler:
    """Encapsulate the smart sampling algorithm for better testability and maintainability."""
    
    def __init__(self, batch_size: int = BATCH_SIZE, max_workers: int = MAX_WORKERS):
        self.batch_size = batch_size
        self.max_workers = max_workers
    
    def calculate_indices(self, total_scans: int) -> List[int]:
        """Calculate indices using scalable sampling approach.
        
        Sampling strategy:
        - 0-99 scans: Process all (no sampling)
        - 100-999 scans: 10 samples  
        - 1,000-9,999 scans: 100 samples
        - 10,000-99,999 scans: 1,000 samples
        - And so on... (grows in powers of 10)
        
        This maintains ~2% sampling rate while scaling efficiently.
        """
        if total_scans == 0:
            return []
        
        if total_scans < 100:
            # For small datasets, process all scans (minimal overhead)
            return list(range(total_scans))
        
        # Calculate number of samples: 10^(floor(log10(total_scans)) - 1)
        import math
        num_samples = 10 ** (int(math.log10(total_scans)) - 1)
        
        # Ensure we don't exceed the dataset size
        num_samples = min(num_samples, total_scans)
        
        # Distribute samples evenly across the dataset
        indices = []
        for i in range(num_samples):
            idx = int((i / (num_samples - 1)) * (total_scans - 1)) if num_samples > 1 else total_scans // 2
            if idx not in indices:
                indices.append(idx)
        
        return sorted(indices)
    
    
    def identify_ranges(self, sample_ages: List[Tuple[int, bool, datetime]], 
                                  total_scans: int) -> List[Tuple[int, int]]:
        """Determine ranges to process based on sample analysis."""
        sample_ages.sort(key=lambda x: x[0])  # Sort by position
        
        ranges_to_process = []
        current_start = None
        
        for pos, is_old, _ in sample_ages:
            if is_old and current_start is None:
                current_start = pos
            elif not is_old and current_start is not None:
                ranges_to_process.append((current_start, pos))
                current_start = None
        
        # Handle case where old scans go to the end
        if current_start is not None:
            ranges_to_process.append((current_start, total_scans))
        
        return self._extend_and_merge_ranges(ranges_to_process, total_scans)
    
    def _extend_and_merge_ranges(self, ranges: List[Tuple[int, int]], 
                                total_scans: int) -> List[Tuple[int, int]]:
        """Extend ranges with buffer and merge overlapping ranges."""
        if not ranges:
            return ranges
        
        # Extend ranges with 5% buffer
        extended_ranges = []
        for start, end in ranges:
            buffer = max(50, int((end - start) * 0.05))
            safe_start = max(0, start - buffer)
            safe_end = min(total_scans, end + buffer)
            extended_ranges.append((safe_start, safe_end))
        
        # Merge overlapping ranges
        merged_ranges = [extended_ranges[0]]
        for start, end in extended_ranges[1:]:
            last_start, last_end = merged_ranges[-1]
            if start <= last_end:
                merged_ranges[-1] = (last_start, max(last_end, end))
            else:
                merged_ranges.append((start, end))
        
        return merged_ranges


def validate_and_get_credentials(args) -> Tuple[str, str, str]:
    """Validate and return API credentials from args or environment."""
    api_url = args.workbench_url or os.getenv("WORKBENCH_URL")
    api_username = args.workbench_user or os.getenv("WORKBENCH_USER")
    api_token = args.workbench_token or os.getenv("WORKBENCH_TOKEN")

    if not api_url or not api_username or not api_token:
        logging.error(
            "Workbench URL, username, and token must be provided as arguments "
            "or environment variables."
        )
        sys.exit(1)

    # Sanity check for Workbench URL
    if not api_url.endswith("/api.php"):
        api_url += "/api.php"

    return api_url, api_username, api_token


def make_api_call(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to make API calls."""
    try:
        logging.debug("Making API call with payload: %s",
                      json.dumps(payload, indent=2))
        response = session.post(url, json=payload, timeout=API_TIMEOUT)
        response.raise_for_status()
        logging.debug("Received response: %s", response.text)
        return response.json().get("data", {})
    except requests.exceptions.RequestException as e:
        logging.error("API call failed: %s", str(e))
        raise
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON response: %s", str(e))
        raise


def list_scans(url: str, username: str, token: str) -> Dict[str, Any]:
    """List all scans using pagination."""
    all_scans = {}
    page = 1

    while True:
        payload = {
            "group": "scans",
            "action": "list_scans",
            "data": {
                "username": username,
                "key": token,
                "records_per_page": RECORDS_PER_PAGE,
                "page": page
            },
        }
        scans_page = make_api_call(url, payload)

        if not scans_page:
            # No more data returned
            break

        # Merge this page's scans into the total
        all_scans.update(scans_page)

        # Check if we got a full page - if not, this was the last page
        if len(scans_page) < RECORDS_PER_PAGE:
            break

        page += 1

    return all_scans


def get_scan_info(
    url: str, username: str, token: str, scan_code: str
) -> Dict[str, Any]:
    """Get scan info for each scan."""
    payload = {
        "group": "scans",
        "action": "get_information",
        "data": {"username": username, "key": token, "scan_code": scan_code},
    }
    return make_api_call(url, payload)


def get_project_info(
    url: str, username: str, token: str, project_code: str
) -> Dict[str, Any]:
    """Get the project name for each scan's project code."""
    # Check cache first
    if project_code in project_cache:
        return project_cache[project_code]
    payload = {
        "group": "projects",
        "action": "get_information",
        "data": {"username": username, "key": token,
                 "project_code": project_code},
    }
    result = make_api_call(url, payload)

    # Cache the result
    project_cache[project_code] = result
    return result


def get_scan_info_batch(
    url: str, username: str, token: str, scan_codes: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Get scan information for multiple scans concurrently."""
    results = {}

    def fetch_single_scan(scan_code: str) -> Tuple[str, Dict[str, Any]]:
        try:
            scan_info = get_scan_info(url, username, token, scan_code)
            return scan_code, scan_info
        except Exception as e:
            logging.error("Failed to fetch scan info for %s: %s",
                          scan_code, str(e))
            return scan_code, {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_scan = {
            executor.submit(fetch_single_scan, scan_code): scan_code
            for scan_code in scan_codes
        }

        # Collect results as they complete
        for future in as_completed(future_to_scan):
            scan_code, scan_info = future.result()
            if scan_info:  # Only store successful results
                results[scan_code] = scan_info

    return results


def find_old_scans(
    scans: Dict[str, Any], url: str, username: str, token: str, days: int,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> Dict[str, Any]:
    """Intelligently sample scans to identify promising subsets for processing.
    
    For small datasets (<100 scans): Returns all scans (no sampling risk)
    For large datasets: Uses scalable sampling to identify ranges with old scans
    
    Args:
        scans: Dictionary of scan data
        url: API URL  
        username: API username
        token: API token
        days: Age threshold in days
        progress_callback: Optional callback function(stage, current, total)
        
    Returns:
        Dictionary of scans to process (either all scans or optimized subset)
    """
    scan_items = list(scans.items())
    total_scans = len(scan_items)
    
    # Handle empty dataset
    if total_scans == 0:
        return {}
    
    # For small datasets, return all scans (no sampling needed)
    if total_scans < 100:
        logging.info("Small dataset: processing all %d scans directly", total_scans)
        return scans
    
    # For large datasets, use smart sampling to identify promising ranges
    logging.info("Large dataset: using smart sampling to optimize processing...")
    
    sampler = SmartSampler()
    time_limit = datetime.now() - timedelta(days=days)
    
    # Sample the dataset
    sample_indices = sampler.calculate_indices(total_scans)
    sample_codes = [scan_items[i][1]["code"] for i in sample_indices]
    
    if progress_callback:
        progress_callback("sampling_dataset", 0, len(sample_codes))
    
    sampling_rate = (len(sample_codes) / total_scans) * 100
    logging.info("Sampling %d scans (%.2f%% of dataset)", len(sample_codes), sampling_rate)
    
    # Get details for samples
    if progress_callback:
        progress_callback("fetching_samples", 0, len(sample_codes))
    
    sample_details = get_scan_info_batch(url, username, token, sample_codes)
    
    if progress_callback:
        progress_callback("fetching_samples", len(sample_codes), len(sample_codes))
    
    # Analyze samples to find old/new patterns
    sample_ages = []
    for i, scan_code in enumerate(sample_codes):
        if scan_code in sample_details:
            try:
                scan_details = sample_details[scan_code]
                if not scan_details.get("is_archived"):
                    update_date = datetime.strptime(
                        scan_details["updated"], "%Y-%m-%d %H:%M:%S")
                    is_old = update_date < time_limit
                    sample_ages.append((sample_indices[i], is_old, update_date))
            except (KeyError, ValueError):
                continue
    
    if not sample_ages:
        logging.warning("No valid samples found, processing all scans")
        return scans
    
    # Identify promising ranges based on samples
    if progress_callback:
        progress_callback("identifying_ranges", 0, 1)
    
    ranges_to_process = sampler.identify_ranges(sample_ages, total_scans)
    
    if not ranges_to_process:
        if any(is_old for _, is_old, _ in sample_ages):
            ranges_to_process = [(0, total_scans // 2)]
            logging.info("No clear ranges found, processing first half as fallback")
        else:
            logging.info("No old scans detected in samples")
            return {}
    
    # Show optimization results
    total_to_process = sum(end - start for start, end in ranges_to_process)
    reduction_percent = ((total_scans - total_to_process - len(sample_codes)) / total_scans) * 100
    
    print(f"\n🚀 Smart Sampling Optimization Results:")
    print(f"   📊 Total samples taken: {len(sample_codes):,}")
    print(f"   🎯 Identified {len(ranges_to_process)} promising ranges containing {total_to_process:,} scans")
    print(f"   ⚡ Processing {(total_to_process / total_scans) * 100:.1f}% of total scans ({reduction_percent:.1f}% reduction)")
    
    if reduction_percent > 0:
        saved_width = int(30 * (reduction_percent / 100))
        process_width = 30 - saved_width
        optimization_bar = "🟩" * process_width + "⬜" * saved_width
        print(f"   📈 Optimization: [{optimization_bar}] {reduction_percent:.1f}% API calls saved")
    print()
    
    # Build filtered scan dictionary with only the promising ranges
    filtered_scans = {}
    for start, end in ranges_to_process:
        for i in range(start, end):
            scan_key, scan_data = scan_items[i]
            filtered_scans[scan_key] = scan_data
    
    logging.info("Smart sampling complete: filtered to %d scans for processing", len(filtered_scans))
    return filtered_scans


def process_scans(
    scans: Dict[str, Any], url: str, username: str, token: str, days: int,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> List[Tuple[Optional[str], str, str, datetime, datetime]]:
    """Process scans to find those older than the specified days.
    
    This function does the actual work of checking scan ages and filtering.
    It can work with any scan dictionary (full dataset or pre-filtered subset).
    
    Args:
        scans: Dictionary of scan data to process
        url: API URL
        username: API username  
        token: API token
        days: Age threshold in days
        progress_callback: Optional callback function(stage, current, total)
        
    Returns:
        List of old scans with their details
    """
    if not scans:
        if progress_callback:
            progress_callback("completed", 0, 0)
        return []
    
    scan_items = list(scans.items())
    total_scans = len(scan_items)
    time_limit = datetime.now() - timedelta(days=days)
    
    logging.info("Processing %d scans to find old entries...", total_scans)
    
    if progress_callback:
        progress_callback("processing_ranges", 0, total_scans)
    
    old_scans = []
    processed = 0
    
    # Process scans in batches
    for i in range(0, total_scans, BATCH_SIZE):
        batch = scan_items[i:i + BATCH_SIZE]
        scan_codes = [scan_info["code"] for _, scan_info in batch]
        
        processed += len(scan_codes)
        
        # Update progress callback
        if progress_callback:
            progress_callback("processing_ranges", processed, total_scans)
        
        if processed % 1000 == 0 or processed == total_scans:
            logging.info("Progress: %d/%d scans processed (%.1f%%)",
                         processed, total_scans, (processed / total_scans) * 100)
        
        # Fetch scan details concurrently for this batch
        scan_details_batch = get_scan_info_batch(url, username, token, scan_codes)
        
        # Process the results
        for _, scan_info in batch:
            scan_code = scan_info["code"]
            
            if scan_code not in scan_details_batch:
                continue
                
            scan_details = scan_details_batch[scan_code]
            
            # Skip archived scans
            if scan_details.get("is_archived"):
                continue
                
            try:
                creation_date = datetime.strptime(
                    scan_details["created"], "%Y-%m-%d %H:%M:%S")
                update_date = datetime.strptime(
                    scan_details["updated"], "%Y-%m-%d %H:%M:%S")
                
                if update_date < time_limit:
                    project_code = scan_details.get("project_code")
                    old_scans.append((
                        project_code,
                        scan_details["name"],
                        scan_code,
                        creation_date,
                        update_date,
                    ))
            except (KeyError, ValueError) as e:
                logging.warning("Invalid date format for scan %s: %s",
                                scan_code, str(e))
                continue
        
        # Add delay between batches
        if i + BATCH_SIZE < total_scans:
            time.sleep(BATCH_DELAY)
    
    logging.info("Processing complete: found %d old scans", len(old_scans))
    
    if progress_callback:
        progress_callback("completed", len(old_scans), len(old_scans))
    
    return old_scans


def archive_scan(url: str, username: str, token: str, scan_code: str) -> bool:
    """Archive a scan."""
    payload = {
        "group": "scans",
        "action": "archive_scan",
        "data": {"username": username, "key": token,
                 "scan_code": scan_code},
    }
    try:
        response = session.post(url, json=payload)
        response.raise_for_status()
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logging.error("Error archiving scan %s: %s", scan_code,
                      str(e))
        return False


def create_scan_plan(
    scans: List[Tuple[Optional[str], str, str, datetime, datetime]],
    url: str, username: str, token: str
) -> List[Dict[str, Any]]:
    """Create a plan with detailed scan information for archiving."""
    plan = []

    for project_code, scan_name, scan_code, creation_date, update_date \
            in scans:
        project_name = "No Project"
        if project_code:
            try:
                project_info = get_project_info(
                    url, username, token, project_code)
                project_name = project_info.get(
                    "project_name", "Unknown Project")
            except Exception as e:
                logging.warning(
                    "Failed to fetch project info for %s: %s",
                               project_code, str(e))
                project_name = f"Project {project_code}"

        scan_entry = {
            "project_name": project_name,
            "scan_code": scan_code,
            "scan_name": scan_name,
            "creation_date": creation_date.isoformat(),
            "last_modified": update_date.isoformat(),
            "age_days": (datetime.now() - update_date).days
        }
        plan.append(scan_entry)
    
    return plan


def save_plan_to_file(plan: List[Dict[str, Any]], filename: str) -> None:
    """Save the scan plan to a JSON file."""
    plan_data = {
        "created_at": datetime.now().isoformat(),
        "total_scans": len(plan),
        "scans": plan
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(plan_data, f, indent=2, ensure_ascii=False)

    logging.info("Scan plan saved to %s (%d scans)", filename, len(plan))


def load_plan_from_file(filename: str) -> List[Dict[str, Any]]:
    """Load scan plan from a JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        if "scans" not in plan_data:
            raise ValueError("Invalid plan file format: missing 'scans' key")

        scans = plan_data["scans"]
        logging.info("Loaded plan from %s (%d scans)", filename, len(scans))
        return scans

    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logging.error("Failed to load plan file %s: %s", filename, str(e))
        sys.exit(1)


def progress_display(stage: str, current: int, total: int) -> None:
    """Terminal-optimized progress display with visual progress bars."""
    if total == 0:
        percentage = 100
    else:
        percentage = (current / total) * 100
    
    stage_messages = {
        "sampling_dataset": "📊 Sampling dataset",
        "fetching_samples": "📥 Fetching sample data",
        "identifying_ranges": "🎯 Identifying processing ranges",
        "processing_ranges": "⚡ Processing scan ranges",
        "fallback_processing": "🔄 Processing all scans (fallback)",
        "completed": "✅ Completed"
    }
    
    message = stage_messages.get(stage, stage)
    
    # Create a visual progress bar for terminal
    if total > 0:
        bar_width = 30
        filled_width = int(bar_width * (current / total))
        bar = "█" * filled_width + "░" * (bar_width - filled_width)
        
        # Use \r to overwrite the line for smooth progress updates
        if stage == "processing_ranges" and current < total:
            # For processing ranges, use overwrite for smooth updates
            print(f"\r{message}: [{bar}] {current:,}/{total:,} ({percentage:.1f}%)", 
                  end="", flush=True)
        else:
            # For other stages, print new line
            if current == total or stage != "processing_ranges":
                print(f"\r{message}: [{bar}] {current:,}/{total:,} ({percentage:.1f}%)")
            else:
                print(f"\r{message}: [{bar}] {current:,}/{total:,} ({percentage:.1f}%)", 
                      end="", flush=True)
    else:
        print(f"{message}: Complete")
    
    # Add extra logging for key milestones
    if stage == "completed":
        print(f"\n🎉 Found {current:,} old scans ready for archiving!")
    elif stage == "identifying_ranges" and current == total:
        # This gets called after range identification
        pass  # We'll let the main algorithm log the optimization results


def fetch_and_find_old_scans(
    url: str, username: str, token: str, days: int
) -> List[Tuple[Optional[str], str, str, datetime, datetime]]:
    """Fetch scans and find ones older than the specified number of days."""
    logging.info("Fetching scans from Workbench...")
    try:
        scans = list_scans(url, username, token)
    except requests.exceptions.RequestException as e:
        logging.error("Failed to retrieve scans from Workbench: %s",
                      str(e))
        logging.error("Please check the Workbench URL, Username and Token.")
        sys.exit(1)
    logging.info("Found %d total scans", len(scans))
    logging.info("Finding scans last updated more than %d days ago...", days)

    # Step 1: Use smart sampling to filter the scan set
    filtered_scans = find_old_scans(
        scans, url, username, token, days, progress_display)
    
    # Step 2: Process the filtered scans to find old ones
    return process_scans(
        filtered_scans, url, username, token, days, progress_display)


def archive_scans_from_plan(
    url: str, username: str, token: str, plan: List[Dict[str, Any]]
):
    """Archive scans based on a plan loaded from JSON."""
    total_scans = len(plan)
    successful = 0
    failed = 0
    
    logging.info("Starting to archive %d scans...", total_scans)
    
    for i, scan_entry in enumerate(plan, 1):
        scan_code = scan_entry["scan_code"]
        scan_name = scan_entry["scan_name"]
        
        logging.info("(%d/%d) Archiving...", i, total_scans)
        
        if archive_scan(url, username, token, scan_code):
            successful += 1
        else:
            logging.error("Failed to archive scan: %s", scan_name)
            failed += 1
    
    logging.info("Archive operation completed: %d successful, %d failed", 
                 successful, failed)
    
    if failed > 0:
        logging.warning(
            "Some scans failed to archive. Check the logs above for details.")
        return False
    
    return True


def cmd_plan(url: str, username: str, token: str, days: int, output_file: str):
    """Create a plan of scans to be archived."""
    start_time = time.time()
    
    print(f"\n🔍 Creating archive plan for scans older than {days} days...")
    print("=" * 60)
    
    old_scans = fetch_and_find_old_scans(url, username, token, days)
    if not old_scans:
        print(f"\n📋 No scans found older than {days} days.")
        # Still create an empty plan file
        save_plan_to_file([], output_file)
        print(f"📄 Empty plan saved to: {output_file}")
        return
    
    print(f"\n📊 Creating detailed plan for {len(old_scans):,} scans...")
    
    # Create detailed plan with project information
    plan = create_scan_plan(old_scans, url, username, token)
    
    # Save plan to file
    save_plan_to_file(plan, output_file)
    
    processing_time = time.time() - start_time
    
    # Display completion message with visual formatting
    print(f"\n✅ Plan Creation Complete!")
    print("=" * 60)
    print(f"📄 Archive plan: {output_file}")
    print(f"📊 Scans to archive: {len(plan):,}")
    print(f"⏱️  Processing time: {processing_time:.2f} seconds")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the plan: cat {output_file}")
    print(f"   2. Execute archiving: python {__file__.split('/')[-1]} archive")
    print("=" * 60)


def cmd_archive(url: str, username: str, token: str, plan_file: str):
    """Archive scans based on a plan file."""
    start_time = time.time()

    print(f"\n📂 Loading archive plan from {plan_file}...")
    print("=" * 60)
    
    plan = load_plan_from_file(plan_file)
    
    if not plan:
        print("📋 No scans to archive (empty plan).")
        return

    print(f"📊 Loaded plan with {len(plan):,} scans to archive")
    
    # Show a summary of what will be archived
    if len(plan) <= 10:
        print(f"\n📋 Scans to be archived:")
        for i, scan in enumerate(plan[:10], 1):
            print(f"   {i}. {scan['scan_name']} ({scan['project_name']}) - {scan['age_days']} days old")
    else:
        print(f"\n📋 Sample of scans to be archived:")
        for i, scan in enumerate(plan[:5], 1):
            print(f"   {i}. {scan['scan_name']} ({scan['project_name']}) - {scan['age_days']} days old")
        print(f"   ... and {len(plan) - 5:,} more scans")
    
    # Confirm operation
    print(f"\n⚠️  WARNING: This will archive {len(plan):,} scans.")
    print("   This operation is IRREVERSIBLE!")
    confirmation = input(f"\n❓ Proceed with archiving? (y/n): ")
    
    if confirmation.lower() != "y":
        print("❌ Operation cancelled.")
        return

    print(f"\n🚀 Starting archive operation...")
    print("=" * 60)

    # Perform archiving
    success = archive_scans_from_plan(url, username, token, plan)

    total_time = time.time() - start_time
    
    if success:
        print(f"\n✅ Archive Operation Complete!")
        print("=" * 60)
        print(f"📊 Scans archived: {len(plan):,}")
        print(f"⏱️  Total time: {total_time:.2f} seconds")
        print("=" * 60)
    else:
        print(f"\n❌ Archive operation completed with errors!")
        print(f"⏱️  Total time: {total_time:.2f} seconds")
        print("📋 Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Archive old scans from FossID Workbench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  plan     Create a JSON plan of scans to be archived
  archive  Archive scans based on a JSON plan file

Examples:
  python archive_stale_scans.py plan --days 365
  python archive_stale_scans.py archive
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")
    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--workbench-url", type=str, help="The Workbench API URL")
    common_parser.add_argument(
        "--workbench-user", type=str, help="Your Workbench username")
    common_parser.add_argument(
        "--workbench-token", type=str, help="Your Workbench API token")
    # Plan command
    plan_parser = subparsers.add_parser(
        "plan", parents=[common_parser],
        help="Create a plan of scans to be archived"
    )
    plan_parser.add_argument(
        "--days", type=int, default=DEFAULT_DAYS,
        help=f"Scan age in days to consider old (default: {DEFAULT_DAYS})"
    )
    plan_parser.add_argument(
        "--output", "-o", type=str, default=DEFAULT_PLAN_FILE,
        help=f"Output JSON file for the archive plan "
             f"(default: {DEFAULT_PLAN_FILE})"
    )
    
    # Archive command
    archive_parser = subparsers.add_parser(
        "archive", parents=[common_parser],
        help="Archive scans based on a plan file"
    )
    archive_parser.add_argument(
        "--input", "-i", type=str, default=DEFAULT_PLAN_FILE,
        help=f"Input JSON plan file to execute (default: {DEFAULT_PLAN_FILE})"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get and validate API credentials
    api_url, api_username, api_token = validate_and_get_credentials(args)

    # Execute the appropriate command
    if args.command == "plan":
        cmd_plan(api_url, api_username, api_token, args.days, args.output)
    elif args.command == "archive":
        cmd_archive(api_url, api_username, api_token, args.input)
