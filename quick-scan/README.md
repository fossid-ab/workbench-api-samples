# quick_scan

This script tests a single file using the Workbench Quick Scan API.

The output is simply whether or not the file has a match in the FossID Knowledge Base.
The call to action is to drop the file into Quick View in Workbench to dig deeper.

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
python3 quick_scan.py --workbench-url <url> --workbench-user <user> --workbench-token <token>
```

# General Usage

Invoke the script by providing the path to the file to test.

```python
python3 quick_scan.py path/to/file
```

Please note only one file can be scanned at a time.

## Getting the RAW Output

Like JSON? The `--raw` argument gives you the full match JSON to play with.

```python
python3 quick_scan.py path/to/file --raw
```