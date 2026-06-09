# anon_deactivated_users

Anonymize PII for users already deactivated in Workbench (Workbench does not support deleting users).

## What this script changes

For each **deactivated** user that is not already anonymized, the script calls `users` → `update` with these `data` fields (matching the Workbench API schema):

| Request field | Role | Value |
| --- | --- | --- |
| `user_username` | Identifies which user to update (current login name) | unchanged |
| `user_name` | Updated name | `Deactivated` |
| `user_surname` | Updated surname | `User` |
| `user_email` | Updated email | `deactivated@company.com` |
| `user_password` | Updated password | `deactivatedpassword` |
| `user_phone` | Updated phone | `""` (cleared) |
| `user_mobile` | Updated mobile | `""` (cleared) |

`username` and `key` (API credentials) are injected by the SDK transport.

**Field naming:** `user_username` is the existing login name used to find the record; `user_name` is the name field being written.

### Lookup key cannot be updated

The `users` → `update` endpoint treats `user_username` as a **lookup key only**. There is no request field to change the login username — the schema only defines it as *"Username for the user being updated"*, and profile fields (`user_name`, `user_surname`, `user_email`, etc.) are updated separately. Deactivated users therefore keep their original login name in the Users list; verify anonymization by checking name, surname, and email in the user details.

The script does **not** pass `reactivate_account` (that would reactivate the user).

Users that already have the target name, surname, and email are skipped.

## Setup

```sh
pip install -r ../requirements-sdk.txt
```

Uses the Workbench SDK for HTTP transport only (`send_api_request`); response parsing and business logic live in this script. A `UsersClient.update()` wrapper will be added to Workbench Agent CE later.

### Workbench SDK

- **Submodule:** `vendor/workbench-agent-ce/` (pinned to `v0.9.0`)
- **API docs:** [vendor/workbench-agent-ce/src/workbench_agent/api/README.md](../vendor/workbench-agent-ce/src/workbench_agent/api/README.md)

### Credentials

The script loads a `.env` file from the repo root automatically (via `python-dotenv`).
You can also export variables in your shell or pass `--workbench-*` flags (flags override env).

```sh
# .env or shell
WORKBENCH_URL="https://workbench.example.com/api.php"
WORKBENCH_USER="your-username"
WORKBENCH_TOKEN="your-api-token"
```

## Usage

### Dry run

Shows deactivated users that still need anonymization and their current PII. No changes are made.

```bash
python3 anon_deactivated_users.py --dry-run
```

### Apply changes

```bash
python3 anon_deactivated_users.py
```

The script lists affected users and prompts for confirmation (`y` or `yes`) before updating.

### Override credentials on the CLI

```bash
python3 anon_deactivated_users.py \
  --workbench-url "https://workbench.example.com/api.php" \
  --workbench-user "admin" \
  --workbench-token "your-token" \
  --dry-run
```
