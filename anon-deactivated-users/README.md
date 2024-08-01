# anon_deactivated_users

This script will anonimize users that have been deactivated in Workbench. 

Since Workbench does not support deleting users, only deactivating them, this will help anonimize the PII from deactivated users so that it's not exposed in the user list. 

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
python3 anon_deactivated_users.py --workbench-url <url> --workbench-user <user> --workbench-token <token>
```

# General Usage
When executed, the script will check for deactivated users and prompt if they should be anonimized.

## First - Create a Dry Run

The script includes a `--dry-run` option to display the users that would be anonimized by the operation.

```python
python3 anon_deactivated_users.py --dry-run
```

## When ready, archive old scans

When ready to anonimize old users, run it without the `--dry-run` option.

```python
python3 anon_deactivated_users.py
```
