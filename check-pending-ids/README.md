# check_pending_ids

This script helps clients check if a scan contains Pending Identifications.
This is useful for gating CI/CD pipelines when there are Identifications to process.

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
python3 check_pending_id.py --workbench-url <url> --workbench-user <user> --workbench-token <token>
```

# General Usage

Invoke the script by providing the scan code via `--scan-code`.

```python
python3 check_pending_id.py --scan-code <code>
```

Please note you need to provide a **scan code**, not a scan name.

## Showing the Files Pending ID

By default, the only provides a link to Pending ID tab in the Scan Interface. 
You can also display a list of files Pending ID with the `--show-files` argument.

```python
python3 check_pending_id.py --show-files
```

## Adjusting the Status Check Interval

There is one time the script has to wait on Workbench in order to complete its run.
That is, when the scan is still running. Large scans may take a long time to complete.
By default, the script pings Workbench every 30 seconds to check the status of the operation.

This behavior can be overridden by specifying a `--check-interval` in seconds.

```python
python3 check_pending_id.py --check-interval [time in seconds]
```