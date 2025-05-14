# import-da

This script imports Dependency Analysis (DA) results into an existing Workbench scan.

Use this script to add dependency analysis data to a scan that has already been created by uploading an analyzer-result.json file to a scan. 


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
python3 import-da.py --api-url <url> --api-user <user> --api-token <token>
```

# General Usage

Invoke the script by providing the scan code and path to the analyzer-result.json file to upload.

```python
python3 import-da.py --scan-code <code> --file <path/to/analyzer-result.json>
```

Please note you need to provide a **scan code** of an existing scan, not a scan name.

## Adjusting Wait Parameters

By default, the script checks the import status every 2 seconds and will try up to 60 times.
These behaviors can be overridden with the following arguments:

```python
python3 import-da.py --wait-time <seconds> --max-tries <number>
```
