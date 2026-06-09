# Delete Old Scans

Find and **permanently delete** scans that have not been updated within a given number of days.

## ⚠️ Warning

Deletion is **permanent** and cannot be undone. Consider `archive-stale-scans/` first. Always run with `--dry-run` before deleting.

## Setup

```bash
pip install -r requirements.txt   # includes ../requirements-sdk.txt
```

### Workbench SDK

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

## Credentials

Environment variables (recommended) or CLI flags:

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

| CLI flag | Environment variable |
|----------|----------------------|
| `--workbench-url` | `WORKBENCH_URL` |
| `--workbench-user` | `WORKBENCH_USER` |
| `--workbench-token` | `WORKBENCH_TOKEN` |

## Usage

### Dry run (recommended first)

```bash
python delete_old_scans.py --days 180 --dry-run
```

### Delete with env vars only

```bash
python delete_old_scans.py --days 365
```

### Full example with CLI overrides

```bash
python delete_old_scans.py \
  --workbench-url "https://workbench.example.com/api.php" \
  --workbench-user "admin" \
  --workbench-token "your-token" \
  --days 90 \
  --dry-run
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--workbench-url` | API URL | `WORKBENCH_URL` |
| `--workbench-user` | Username | `WORKBENCH_USER` |
| `--workbench-token` | API token | `WORKBENCH_TOKEN` |
| `--days` | Age threshold in days | 365 |
| `--dry-run` | Preview without deleting | false |

## Safety

- Dry-run mode previews affected scans
- Live run requires typing `yes` to confirm
- Already-archived scans are skipped

## Related

- `archive-stale-scans/` — archive instead of delete (recommended)
- `delete-scan/` — delete one scan by code; prefer [Workbench Agent CE `delete-scan`](../delete-scan/README.md)
