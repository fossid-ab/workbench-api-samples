# FossID Workbench API Examples

These scripts were built by the FossID Customer Experience teams in collaboration with Engineering to solve specific use cases raised by customers via the [FossID Support Portal](https://support.fossid.com/).

### Supportability

These examples demonstrate how to interact with the Workbench API. We do our best to keep the examples updated, but there is no long-term maintainer for this code. We do not use GitHub Issues — for questions or issues with the scripts please use the [FossID Support Portal](https://support.fossid.com/). Thank you!

## Workbench Agent CE (recommended)

For day-to-day and CI/CD use, prefer **[Workbench Agent CE](https://github.com/fossid-ab/workbench-agent-ce)** — a maintained CLI and Docker image that wraps the same SDK:

| Sample folder | CE command |
|---------------|------------|
| `quick-scan/` | `workbench-agent quick-scan` |
| `post-scan-gates/` | `workbench-agent evaluate-gates` |
| `post-scan-reports/` | `workbench-agent download-reports` |
| `import-da/` | `workbench-agent import-da` |
| `delete-scan/` | `workbench-agent delete-scan` |

See the [Getting Started Guide](https://github.com/fossid-ab/workbench-agent-ce/wiki/Getting-Started) and per-folder READMEs for examples.

## Workbench SDK in this repo

Sample scripts that remain in this repo call the SDK vendored as a git submodule:

| Item | Location |
|------|----------|
| Submodule | [`vendor/workbench-agent-ce/`](vendor/workbench-agent-ce/) (pinned to `v0.9.0`) |
| SDK source | `vendor/workbench-agent-ce/src/workbench_agent/api/` |
| API architecture & methods | [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](vendor/workbench-agent-ce/src/workbench_agent/api/README.md) |
| Per-domain clients | [vendor/workbench-agent-ce/src/workbench_agent/api/clients/README.md](vendor/workbench-agent-ce/src/workbench_agent/api/clients/README.md) |
| Shared script helpers | [`lib/workbench_client.py`](lib/workbench_client.py) |

The SDK is not yet published to PyPI as `workbench-sdk`; import from `workbench_agent.api` until extraction happens (see [SDK_DISTRIBUTION_STRATEGY.md](vendor/workbench-agent-ce/src/workbench_agent/api/SDK_DISTRIBUTION_STRATEGY.md)).

### Setup

```bash
git submodule update --init --recursive

python -m venv .venv
source .venv/bin/activate
pip install -r requirements-sdk.txt
```

### Credentials

All scripts accept credentials via a root **`.env` file** (loaded automatically when `python-dotenv` is installed), **environment variables**, or CLI flags. Flags override env vars when both are set.

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

`WORKBENCH_URL` must be the API endpoint (`…/api.php`), not the Workbench UI URL.

| CLI flags (most scripts) | Environment variable |
|--------------------------|----------------------|
| `--workbench-url` | `WORKBENCH_URL` |
| `--workbench-user` | `WORKBENCH_USER` |
| `--workbench-token` | `WORKBENCH_TOKEN` |

Some older scripts use `--api-url` / `--api-user` / `--api-token` with the same env vars.

### Example (env vars only)

```bash
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="ci-user"
export WORKBENCH_TOKEN="your-token"

cd archive-stale-scans
python3 archive_stale_scans.py plan --days 365
```

## Example scripts

| Folder | Purpose |
|--------|---------|
| `archive-stale-scans/` | Archive stale scans (plan → review → archive) |
| `delete-old-scans/` | Permanently delete scans by age |
| `get-project-policy/` | Download project license policy JSON |
| `anon-deactivated-users/` | Anonymize deactivated user PII |
| `quick-scan/` | Quick-scan one file — **use CE** |
| `post-scan-gates/` | CI gates on pending IDs / policy — **use CE** |
| `post-scan-reports/` | Download scan reports — **use CE** |
| `import-da/` | Import DA results — **use CE** |
| `delete-scan/` | Delete one scan — **use CE** |

`old_generation_script/` is historical reference only.

## Contributing

Contributions are welcome! We'll review any Pull Requests made.
