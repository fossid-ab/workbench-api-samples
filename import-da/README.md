# Import Dependency Analysis

Import ORT or FossID-DA `analyzer-result.json` into an existing Workbench scan.

**Use [Workbench Agent CE](https://github.com/fossid-ab/workbench-agent-ce)** for this workflow. The `import-da/` sample script is kept as a minimal SDK reference; it takes a **scan code**, while the CE command resolves scans by **project name + scan name**.

## Recommended: Workbench Agent CE

See the [import-da command](https://github.com/fossid-ab/workbench-agent-ce/wiki) in the CE Wiki.

### Credentials

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

### Examples

```bash
# Import DA results (credentials from env vars)
workbench-agent import-da \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --path ./ort-output/analyzer-result.json

# Tune wait behaviour while polling import status
workbench-agent import-da \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --path ./analyzer-result.json \
  --scan-wait-time 2 \
  --scan-number-of-tries 60
```

```bash
workbench-agent import-da --help
```

## Workbench SDK (sample script)

SDK location in this repo:

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

The sample script targets an existing scan by code:

```sh
pip install -r ../requirements-sdk.txt

export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"

python3 import-da.py --scan-code "MyProject/MyScan" --file ./analyzer-result.json
python3 import-da.py --scan-code "MyProject/MyScan" --file ./analyzer-result.json \
  --wait-time 2 --max-tries 60
```

`--api-url`, `--api-user`, and `--api-token` override `WORKBENCH_URL`, `WORKBENCH_USER`, and `WORKBENCH_TOKEN` when set.
