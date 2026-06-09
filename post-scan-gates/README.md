# Post Scan Gates

Gate CI/CD pipelines on Workbench scan quality: pending identifications, policy warnings, and (optionally) vulnerabilities.

**Use [Workbench Agent CE](https://github.com/fossid-ab/workbench-agent-ce)** for this workflow. The `post-scan-gates/` sample script is kept as a minimal SDK reference; it takes a **scan code**, while the CE command resolves scans by **project name + scan name**.

## Recommended: Workbench Agent CE

Run after a scan completes (for example following `workbench-agent scan`). See the [Workbench Agent CE Wiki](https://github.com/fossid-ab/workbench-agent-ce/wiki).

### Credentials

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

### Examples

```bash
# Report pending IDs and policy warnings (informational; exit 0 unless --fail-on-* is set)
workbench-agent evaluate-gates \
  --project-name "MyProject" \
  --scan-name "v1.0.0"

# Fail the step on policy violations
workbench-agent evaluate-gates \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --fail-on-policy

# Fail on pending identifications
workbench-agent evaluate-gates \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --fail-on-pending

# Fail on high-or-above CVEs
workbench-agent evaluate-gates \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --fail-on-vuln-severity high

# Adjust status polling (default: 30s interval, 960 tries)
workbench-agent evaluate-gates \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --scan-wait-time 15
```

```bash
workbench-agent evaluate-gates --help
```

In CI, pass project/scan names via your pipeline variables. Credentials can stay in `WORKBENCH_*` env vars.

## Workbench SDK (sample script)

SDK location in this repo:

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

The sample script uses `--scan-code` and prints `FOSSID_SCAN_URL` for downstream job steps:

```sh
pip install -r ../requirements-sdk.txt

export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"

python3 post_scan_gates.py --scan-code "MyProject/MyScan"
python3 post_scan_gates.py --scan-code "MyProject/MyScan" --show-files
python3 post_scan_gates.py --scan-code "MyProject/MyScan" --policy-check
python3 post_scan_gates.py --scan-code "MyProject/MyScan" --check-interval 15
```

`--workbench-url`, `--workbench-user`, and `--workbench-token` override the environment variables when set.
