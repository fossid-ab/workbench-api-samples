# archive_stale_scans

This script helps clients archive scans to reduce the storage space used by Workbench.

The script uses a command-based approach with two steps: 
- **plan** (identify scans to archive), and 
- **archive** (execute the archiving). 

This allows for validation and review before performing any destructive operations.

### Archive vs Delete?

This script will not **delete** scans - instead it **archives** them. Archiving a scan removes the files associated with that scan, but keeps the results for future review. This will reduce overall storage usage by Workbench while keeping results for review.

# Pre-Requisites
You need to provide a Workbench URL, User, and Token to use this script.
These can be provided as Arguments or Environment Variables (recommended).

### Environment Variables (Recommended)

```sh
export WORKBENCH_URL
export WORKBENCH_USER
export WORKBENCH_TOKEN
```

### Arguments

```bash
python3 archive_stale_scans.py plan --workbench-url <url> --workbench-user <user> --workbench-token <token>
```

Please Note: this script can only archive scans that the User (identified by the User and Token) has access to.

# Easy Mode
By default, the script archives scans older than 365 days. Here's the tl;dr:

```bash
# Create the Archive Plan
python3 archive_stale_scans.py plan

# Archive the Scans in the Plan
python3 archive_stale_scans.py archive
```

# Expert Mode
Here's how you can customize the script's default behavior.

## Step 1: Create an Archive Plan
First, create a plan that identifies which scans will be archived. 
The `--days` argument lets you specify the age you consider stale.

```bash
python3 archive_stale_scans.py plan --days 365
```

You can customize where the output file is saved with `-o`:

```bash
python3 archive_stale_scans.py plan -o archive_plan.json
```

This writes a JSON file with information about each scan that would be archived to `archive_plan.json`.

## Step 2: Review the Plan

Before archiving, review the generated JSON file to verify which scans will be affected. The file contains:
- Project names
- Scan names and codes  
- Creation and last modified dates
- Age in days

## Step 3: Execute the Plan
When ready to proceed, execute the archive operation. 
By default, the plan is read from the directory where the script is executed.

```bash
python3 archive_stale_scans.py archive
```

You can also target a archive plan in another location with `-i`:

```bash
python3 archive_stale_scans.py archive -i archive_plan.json
```

## Archive Plan JSON Schema

The generated plan file contains structured data about each scan:

```json
{
  "created_at": "2025-01-15T10:30:00",
  "total_scans": 150,
  "scans": [
    {
      "project_name": "Sample Project", 
      "scan_code": "Scan_456",
      "scan_name": "Baseline Scan",
      "creation_date": "2024-01-15T09:00:00",
      "last_modified": "2024-01-15T12:30:00", 
      "age_days": 365
    }
  ]
}
```