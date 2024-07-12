# cs-scan_archiver

This repo contains a script to help clients Archive Old Scans.
By default, the script looks for scans that haven't been updated in over 365 days, but this value can be changed.

### Archive vs Delete?

This script will not **delete** scans - instead it **archives** them. Archiving a scan removes the files associated with that scan, but keeps the results for future review. This will reduce overall storage usage by Workbench while keeping results for review.

# Setting Up

You need to provide a Workbench URL, User, and Token to use this script.
These can be provided as Arguments or Environment Variables (recommended).

### Environment Variables (Recommended)

```sh
export WORKBENCH_URL
export WORKBENCH_USER
export WORKBENCH_TOKEN
```

### Arguments

```python
python3 scan_archiver.py --workbench-url <url> --workbench-user <user> --workbench-token <token>
```

# Usage

## First - Create a Dry Run

The script includes a `--dry-run` option to create a list of scans that would be archived by the operation.

```python
python3 scan_archiver.py --dry-run
```

By default the script looks for scans that haven't been updated in more than 365 days, but that can be overridden.

```python
python3 scan_archiver.py --dry-run --days 365
```

## When ready, archive old scans

When ready to archive old scans, run it without the `--dry-run` option.

```python
python3 scan_archiver.py
```

By default the script looks for scans that haven't been updated in more than 365 days.
Use the `--days` option to override this default.

```python
python3 scan_archiver.py --days 365
```
