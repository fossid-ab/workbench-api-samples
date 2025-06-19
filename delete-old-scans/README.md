# Delete Old Scans

This script finds and **permanently deletes** old scans from the FossID Workbench that haven't been updated in a specified number of days.

## ⚠️ Important Warning

**This script PERMANENTLY DELETES scans from your FossID Workbench instance. Unlike archiving, deleted scans cannot be recovered. Use with extreme caution!**

## Features

- Lists all scans and identifies those not updated within a specified timeframe
- Displays scan information in a formatted table including project name, scan name, age, and last modified date
- Supports dry-run mode to preview which scans would be deleted without actually deleting them
- Skips already archived scans
- Requires explicit confirmation before proceeding with deletion
- Comprehensive logging and error handling

## Prerequisites

- Python 3.6 or higher
- Access to a FossID Workbench instance
- Valid Workbench API credentials (username and token)

## Installation

1. Clone or download this script
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

You can provide the Workbench connection details in two ways:

### Option 1: Command Line Arguments
```bash
python delete_old_scans.py --workbench-url "https://your-workbench.com" --workbench-user "your-username" --workbench-token "your-api-token"
```

### Option 2: Environment Variables
Set the following environment variables:
- `WORKBENCH_URL`: Your FossID Workbench URL
- `WORKBENCH_USER`: Your Workbench username  
- `WORKBENCH_TOKEN`: Your Workbench API token

```bash
export WORKBENCH_URL="https://your-workbench.com"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

## Usage

### Basic Usage
Delete scans older than 365 days (default):
```bash
python delete_old_scans.py
```

### Specify Custom Age Threshold
Delete scans older than 180 days:
```bash
python delete_old_scans.py --days 180
```

### Dry Run Mode (Recommended First Step)
Preview which scans would be deleted without actually deleting them:
```bash
python delete_old_scans.py --days 180 --dry-run
```

### Complete Example
```bash
python delete_old_scans.py \
  --workbench-url "https://your-workbench.com" \
  --workbench-user "your-username" \
  --workbench-token "your-api-token" \
  --days 90 \
  --dry-run
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--workbench-url` | The Workbench API URL | From `WORKBENCH_URL` env var |
| `--workbench-user` | Your Workbench username | From `WORKBENCH_USER` env var |
| `--workbench-token` | Your Workbench API token | From `WORKBENCH_TOKEN` env var |
| `--days` | Scan age in days to consider old | 365 |
| `--dry-run` | Preview mode - show what would be deleted without deleting | False |

## Safety Features

1. **Dry Run Mode**: Always test with `--dry-run` first to see what would be deleted
2. **Explicit Confirmation**: Requires typing "yes" (not just "y") to proceed with deletion
3. **Clear Warnings**: Multiple warnings about the permanent nature of deletion
4. **Archived Scan Protection**: Skips scans that are already archived
5. **Detailed Logging**: Comprehensive logging of all operations

## Sample Output

```
2024-01-15 10:30:00 - INFO - Fetching scans from Workbench...
2024-01-15 10:30:02 - INFO - Finding scans last updated more than 180 days ago...
2024-01-15 10:30:05 - INFO - These scans will be PERMANENTLY DELETED:

╒═══════════════════╤═══════════════════════╤═══════════════════╤═══════════════════════╕
│ PROJECT NAME      │ SCAN NAME             │ SCAN AGE (days)   │ LAST MODIFIED         │
╞═══════════════════╪═══════════════════════╪═══════════════════╪═══════════════════════╡
│ Legacy Project    │ old-scan-v1.0         │ 245               │ 2023-05-15 14:30:22   │
│ Deprecated App    │ unused-scan-2022      │ 312               │ 2023-03-08 09:15:45   │
╘═══════════════════╧═══════════════════════╧═══════════════════╧═══════════════════════╛

⚠️  WARNING: This operation will PERMANENTLY DELETE the scans listed above!
   Unlike archiving, deleted scans cannot be recovered.
Are you absolutely sure you want to proceed? (yes/no):
```

## Best Practices

1. **Always start with dry-run**: Use `--dry-run` to preview what would be deleted
2. **Start with a smaller timeframe**: Begin with a shorter period (e.g., 30 days) to test
3. **Review the output carefully**: Check the table of scans to be deleted before confirming
4. **Consider archiving first**: Use the archive script instead if you might need the scans later
5. **Backup important data**: Ensure any important scan results are backed up before deletion

## Troubleshooting

### Common Issues

1. **Authentication Error**: Verify your Workbench URL, username, and API token
2. **Network Timeout**: Check your network connection and Workbench availability
3. **Permission Denied**: Ensure your user account has permission to delete scans

### Error Messages

- `Failed to retrieve scans from Workbench`: Check your connection details and network
- `Error deleting scan`: The scan may be in use or you may lack permissions
- `API call failed`: Network or authentication issue

## Related Scripts

- `archive-stale-scans/`: Archives old scans instead of deleting them (recommended alternative)
- `delete-scan/`: Deletes a specific scan by scan code

## Support

For issues or questions, please refer to the FossID Workbench API documentation or contact your system administrator. 