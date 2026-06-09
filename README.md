# FossID Workbench API Examples!
These scripts were built by the FossID Customer Experience teams in collaboration with Engineering to solve specific use cases raised by customers via the [FossID Support Portal](https://support.fossid.com/). 

### Supportability
These examples demonstrate how to interact with the Workbench API. We do our best to keep the examples updated, but there is no long-term maintainer for this code. We do not use GitHub Issues - for questions or issues with the scripts please use the [FossID Support Portal](https://support.fossid.com/). Thank you! 

## SDK-based setup

Sample scripts use the **Workbench SDK** from the [workbench-agent-ce](https://github.com/fossid-ab/workbench-agent-ce) submodule (pinned to `v0.9.0`). The SDK is not yet published to PyPI as `workbench-sdk`; import from `workbench_agent.api` until extraction happens.

```bash
git submodule update --init --recursive

python -m venv .venv
source .venv/bin/activate
pip install -r requirements-sdk.txt
```

Set credentials (API URL must end with `/api.php`):

```sh
export WORKBENCH_URL=https://workbench.example.com/api.php
export WORKBENCH_USER=your-user
export WORKBENCH_TOKEN=your-token
```

Shared helpers live in `lib/workbench_client.py`. SDK architecture and method reference: [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](vendor/workbench-agent-ce/src/workbench_agent/api/README.md).

When `workbench-sdk` is published, switch imports from `workbench_agent.api` to `workbench_sdk`.

## Example Scripts
The repo has scripts that help you:

### Archive Old Scans
This script helps clients archive stale scans based on when they were last modified.

### Post Scan Gates
This script checks scans for Pending Identifications and Policy Violations - useful for gating CI/CD pipelines.

### Post Scan Reports
This script downloads reports for a scan - useful if you want to include FossID reports as build artifacts.

### Quickly Scan a File
This script scans a single file using the Quick Scan API - helpful for quickly knowing if AI-generated code should be investigated further.

### Import Dependency Analysis
This script imports dependency analysis results to an existing scan - useful for adding dependency analysis results from running ORT or FossID-DA in a pipeline to your scans.

## Contributing
Contributions are welcome! We'll review any Pull Requests made.

