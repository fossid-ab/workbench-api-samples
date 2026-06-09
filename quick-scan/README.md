# Quick Scan

Quickly check whether a single local file matches anything in the FossID Knowledge Base.

**Use [Workbench Agent CE](https://github.com/fossid-ab/workbench-agent-ce)** for this workflow. The `quick-scan/` sample script in this repo is kept as a minimal SDK reference implementation.

## Recommended: Workbench Agent CE

Install or run via Docker — see the [Getting Started Guide](https://github.com/fossid-ab/workbench-agent-ce/wiki/Getting-Started).

### Credentials

Set environment variables (recommended) or pass `--api-url`, `--api-user`, and `--api-token`:

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

The API URL must point at `api.php`, not the Workbench UI base URL.

### Examples

```bash
# Quick scan a file (credentials from env vars)
workbench-agent quick-scan ./src/main.py

# Explicit path and raw JSON output
workbench-agent quick-scan --path ./src/main.py --raw

# Docker
docker run --rm \
  -e WORKBENCH_URL -e WORKBENCH_USER -e WORKBENCH_TOKEN \
  -v "$(pwd):/work" -w /work \
  ghcr.io/fossid-ab/workbench-agent-ce:latest \
  quick-scan ./src/main.py
```

```bash
workbench-agent quick-scan --help
```

## Workbench SDK (sample script)

The CE CLI uses the same SDK vendored in this repo:

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

To run the sample script instead:

```sh
pip install -r ../requirements-sdk.txt

export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"

python3 quick_scan.py path/to/file
python3 quick_scan.py path/to/file --raw
```

CLI flags `--workbench-url`, `--workbench-user`, and `--workbench-token` override the environment variables when set.
