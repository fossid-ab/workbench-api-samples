# post_scan_reports

This script helps clients download reports after a scan.
By default, the script generates and downloads every report type once a scan completes.

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
python3 download_scan_reports.py --workbench-url <url> --workbench-user <user> --workbench-token <token>
```

# General Usage

Invoke the script by providing the scan code via `--scan-code`.

```python
python3 download_scan_reports.py --scan-code <code>
```

Please note you need to provide a **scan code**, not a scan name.

## Changing the Report Type

By default, the script downloads all available reports for the scan. 
Change this behavior by passing the `--report-type` argument.

```python
python3 scan_archiver.py --report-type ["html", "dynamic_top_matched_components", "xlsx", "spdx", "spdx_lite", "cyclone_dx", "string_match"]
```

Currently only one report type is supported at a time.

## Using together with the Workbench Agent

You can use this script together with the [Workbench Agent](https://github.com/fossid-ab/workbench-agent/). 
Use an Environment Variables, such as a built-in from your build environment, to set the scan code.
Then use this script once the Workbench Agent completes its run!