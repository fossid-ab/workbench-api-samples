# archive_stale_scans

Archive stale scans to reduce Workbench storage. Uses a two-step flow: **plan** (identify candidates) → **archive** (execute after review).

Archiving removes scan files but keeps results for review. It does **not** delete scans.

## Setup

```sh
pip install -r ../requirements-sdk.txt
```

### Workbench SDK

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

### Credentials

Environment variables (recommended) or `--workbench-url` / `--workbench-user` / `--workbench-token`:

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

Only scans visible to the authenticated user can be archived.

## Easy mode

Default age threshold is 365 days:

```bash
# Create the archive plan (uses WORKBENCH_* env vars)
python3 archive_stale_scans.py plan

# Review archive_plan.json, then archive
python3 archive_stale_scans.py archive
```

## Expert mode

### Step 1: Create a plan

```bash
python3 archive_stale_scans.py plan --days 365
python3 archive_stale_scans.py plan --days 180 -o my_plan.json
```

### Step 2: Review the plan

The JSON lists project code, scan name/code, dates, and age in days.

### Step 3: Execute

```bash
python3 archive_stale_scans.py archive
python3 archive_stale_scans.py archive -i my_plan.json
```

### Override credentials on the CLI

```bash
python3 archive_stale_scans.py plan \
  --workbench-url "https://workbench.example.com/api.php" \
  --workbench-user "admin" \
  --workbench-token "your-token" \
  --days 365
```

## Archive plan JSON schema

```json
{
  "created_at": "2025-01-15T10:30:00",
  "total_scans": 150,
  "scans": [
    {
      "project_code": "company/project",
      "scan_code": "Scan_456",
      "scan_name": "Baseline Scan",
      "creation_date": "2024-01-15T09:00:00",
      "last_modified": "2024-01-15T12:30:00",
      "age_days": 365
    }
  ]
}
```
