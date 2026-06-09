# Delete Scan

Permanently delete a single scan from Workbench.

**Use [Workbench Agent CE](https://github.com/fossid-ab/workbench-agent-ce)** for this workflow. The `delete-scan/` sample script is kept as a minimal SDK reference; it takes a **scan code**, while the CE command resolves scans by **project name + scan name**.

## Recommended: Workbench Agent CE

Deletion is irreversible. See `workbench-agent delete-scan --help` and the [CE Wiki](https://github.com/fossid-ab/workbench-agent-ce/wiki).

### Credentials

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

### Examples

```bash
# Delete a scan (credentials from env vars)
workbench-agent delete-scan \
  --project-name "MyProject" \
  --scan-name "v1.0.0"

# Also remove identifications per API option
workbench-agent delete-scan \
  --project-name "MyProject" \
  --scan-name "v1.0.0" \
  --delete-identifications
```

```bash
workbench-agent delete-scan --help
```

## Workbench SDK (sample script)

SDK location in this repo:

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

```sh
pip install -r ../requirements-sdk.txt

export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"

python3 delete_scan.py --scan-code "MyProject/MyScan"
```

`--workbench-url`, `--workbench-user`, and `--workbench-token` override the environment variables when set.
