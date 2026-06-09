# get-project-policy

Download a project's license policy from Workbench and save it locally (for example for the Diff Scanner).

## Setup

```sh
pip install -r ../requirements-sdk.txt
```

### Workbench SDK

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

### Credentials

Environment variables (recommended) or `--api-url` / `--api-user` / `--api-token`:

```sh
export WORKBENCH_URL="https://workbench.example.com/api.php"
export WORKBENCH_USER="your-username"
export WORKBENCH_TOKEN="your-api-token"
```

## Usage

### With environment variables

```bash
python3 get_project_policy.py --project-code "company/project-name"
```

Output defaults to `.fossidpolicy` in the current directory.

### Custom output path

```bash
python3 get_project_policy.py \
  --project-code "company/project-name" \
  --output-file "${GITHUB_WORKSPACE}/.fossidpolicy"
```

### Override credentials on the CLI

```bash
python3 get_project_policy.py \
  --api-url "https://workbench.example.com/api.php" \
  --api-user "admin" \
  --api-token "your-token" \
  --project-code "company/project-name"
```
