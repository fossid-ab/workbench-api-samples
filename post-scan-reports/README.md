# Post Scan Reports

Download Workbench reports after a scan finishes — useful as CI build artifacts.

**Use [Workbench Agent CE](https://github.com/fossid-ab/workbench-agent-ce)** for this workflow. The `post-scan-reports/` sample script is kept as a minimal SDK reference.

## Recommended: Workbench Agent CE

Run after a scan completes. See [download-reports](https://github.com/fossid-ab/workbench-agent-ce/wiki) in the CE Wiki.

### Credentials

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

### Examples

```bash
# Download all scan-level reports (credentials from env vars)
workbench-agent download-reports \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --report-scope scan

# Specific report types and output directory
workbench-agent download-reports \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --report-scope scan \
  --report-type xlsx,spdx \
  --report-save-path ./reports/

# Adjust status polling while waiting for scan/reports
workbench-agent download-reports \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --report-scope scan \
  --scan-wait-time 15
```

```bash
workbench-agent download-reports --help
```

## Workbench SDK (sample script)

SDK location in this repo:

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

The sample script uses `--scan-code` instead of project/scan names:

```sh
pip install -r ../requirements-sdk.txt

export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"

python3 post_scan_reports.py --scan-code "MyProject/MyScan"
python3 post_scan_reports.py --scan-code "MyProject/MyScan" --report-type xlsx
python3 post_scan_reports.py --scan-code "MyProject/MyScan" --output-dir ./reports/
python3 post_scan_reports.py --scan-code "MyProject/MyScan" --check-interval 15
```

`--workbench-url`, `--workbench-user`, and `--workbench-token` override the environment variables when set.
