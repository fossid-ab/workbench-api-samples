# post_scan_gates

This script helps clients gate their CI/CD pipelines based on information from Workbench.
This script can break your build if the scan code provided has:
- Any Files with Pending Identifications (Gate 1)
- Any Files with Policy Violations (Gate 2)

Files need to be Identified in order to be evaluated against Policy Rules.
Thereforce, the Policy Check won't run if any files are Pending Identification. 

You can use this script together with the [Workbench Agent](https://github.com/fossid-ab/workbench-agent/). 
Use an Environment Variables, such as a built-in from your build environment, to set the scan code.
Then use this script once the Workbench Agent completes its run!

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
python3 post_scan_gates.py --workbench-url <url> --workbench-user <user> --workbench-token <token>
```

# General Usage

Invoke the script by providing the scan code via `--scan-code`.
Please note you need to provide a **scan code**, not a scan name.

```python
python3 post_scan_gates.py --scan-code <code>
```

When executed, the script will check the provided scan code for files with Pending Identifications.
If any files contain Pending Identifications, a link is provided to the scan interface for users to review.

## Showing the Files Pending ID

By default, the script provides a link to Pending ID tab in the Scan Interface. 
You can also display a list of files Pending ID with the `--show-files` argument.

```python
python3 post_scan_gates.py --show-files
```

## Check for Policy Violations

By default, the script only checks for files with Pending Identifications.
Once all files have been Identified, you can check for policy violations with the `--policy-check` argument. 

```python
python3 post_scan_gates.py --policy-check
```

Please note the policy check will not run if any files contain Pending Identifications. 

## Adjusting the Status Check Interval

There is one time the script has to wait on Workbench in order to complete its run.
That is, when the scan is still running. Large scans may take a long time to complete.
By default, the script pings Workbench every 30 seconds to check the status of the operation.

This behavior can be overridden by specifying a `--check-interval` in seconds.

```python
python3 check_pending_id.py --check-interval [time in seconds]
```