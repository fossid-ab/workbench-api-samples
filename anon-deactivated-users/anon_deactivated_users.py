import logging
import argparse
import os
from typing import Any, Dict, List

from workbench_agent.api.exceptions import WorkbenchApiError

from lib.workbench_client import (
    WorkbenchClient,
    load_dotenv_files,
    normalize_api_url,
    send_api_request,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Target values written to deactivated user records via users->update.
ANON_NAME = "Deactivated"
ANON_SURNAME = "User"
ANON_EMAIL = "deactivated@company.com"
ANON_PASSWORD = "deactivatedpassword"


def make_api_call(client: WorkbenchClient, payload: dict) -> dict:
    """Helper function to make API calls via the SDK transport."""
    try:
        return send_api_request(client, payload)
    except WorkbenchApiError as e:
        logging.error("API call failed: %s", e)
        raise


def is_user_deactivated(user: Dict[str, Any]) -> bool:
    """True when a user row from get_all_users is deactivated."""
    val = user.get("is_deleted")
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("1", "true", "yes")


def is_already_anonymized(user: Dict[str, Any]) -> bool:
    """True when name, surname, and email already match anonymized values."""
    return (
        user.get("name") == ANON_NAME
        and user.get("surename") == ANON_SURNAME
        and user.get("email") == ANON_EMAIL
    )


def get_all_users(client: WorkbenchClient) -> dict:
    payload = {
        "group": "users",
        "action": "get_all_users",
        "data": {
            "include_deactivated": "1",
        },
    }
    return make_api_call(client, payload)


def update_user(client: WorkbenchClient, lookup_username: str) -> dict:
    """
    Anonymize a deactivated user via ``users`` -> ``update``.

    Request schema (``username``/``key`` are injected by the SDK transport):

    - ``user_username``* — identifies the user to update (current login name)
    - ``user_name``* — updated name (first/display name)
    - ``user_surname``*, ``user_email``*, ``user_password``*
    - ``user_phone``, ``user_mobile`` — cleared to empty string
    """
    payload = {
        "group": "users",
        "action": "update",
        "data": {
            "user_username": lookup_username,
            "user_name": ANON_NAME,
            "user_surname": ANON_SURNAME,
            "user_email": ANON_EMAIL,
            "user_password": ANON_PASSWORD,
            "user_phone": "",
            "user_mobile": "",
        },
    }
    return make_api_call(client, payload)


def find_deactivated_users(users: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split deactivated users into those needing anonymization and those already done."""
    needs_update: List[Dict[str, Any]] = []
    already_anonymized: List[Dict[str, Any]] = []

    for user in users:
        if not is_user_deactivated(user):
            continue
        if is_already_anonymized(user):
            already_anonymized.append(user)
        else:
            needs_update.append(user)

    return needs_update, already_anonymized


def log_user_pii(user: Dict[str, Any], *, prefix: str) -> None:
    logging.info(
        "%s username=%s name=%s surename=%s email=%s",
        prefix,
        user.get("username"),
        user.get("name"),
        user.get("surename"),
        user.get("email"),
    )


def confirm_operation() -> bool:
    logging.info("Continue? (y/n): ")
    confirmation = input().strip().lower()
    return confirmation in ("y", "yes")


def main(api_base_url, api_username, api_token, dry_run):
    api_url = normalize_api_url(api_base_url)
    client = WorkbenchClient(api_url, api_username, api_token)

    try:
        logging.info("Fetching all users...")
        users_response = get_all_users(client)
        if users_response.get("status") != "1":
            logging.error("Failed to fetch users.")
            return

        users = users_response.get("data", [])
        if not isinstance(users, list):
            logging.error("Unexpected get_all_users response shape: %s", type(users))
            return

        needs_update, already_anonymized = find_deactivated_users(users)

        if already_anonymized:
            logging.info(
                "%d deactivated user(s) already anonymized (skipped).",
                len(already_anonymized),
            )
            for user in already_anonymized:
                log_user_pii(user, prefix="  skip")

        if not needs_update:
            if not already_anonymized:
                logging.info("No deactivated users found.")
            else:
                logging.info("No deactivated users need anonymization.")
            return

        logging.info(
            "%d deactivated user(s) need anonymization.",
            len(needs_update),
        )
        for user in needs_update:
            logging.info(
                "  will update user_username=%s (id=%s): "
                "user_name/user_surname/user_email -> %s / %s / %s; "
                "password/phone/mobile also set/cleared",
                user.get("username"),
                user.get("id"),
                ANON_NAME,
                ANON_SURNAME,
                ANON_EMAIL,
            )
            log_user_pii(user, prefix="    current")

        if dry_run:
            logging.info("Dry run complete — no changes made.")
            return

        if not confirm_operation():
            logging.info("Operation cancelled.")
            return

        updated = 0
        failed = 0
        for user in needs_update:
            lookup_username = user.get("username")
            logging.info(
                "Anonymizing deactivated user (user_username=%s)",
                lookup_username,
            )
            update_response = update_user(client, lookup_username=lookup_username)
            logging.debug(update_response)
            if update_response.get("status") == "1":
                updated += 1
                logging.info(
                    "Updated %s — user_name=%s, user_surname=%s, user_email=%s "
                    "(login username unchanged: %s).",
                    lookup_username,
                    ANON_NAME,
                    ANON_SURNAME,
                    ANON_EMAIL,
                    lookup_username,
                )
            else:
                failed += 1
                logging.error(
                    "Failed to anonymize %s: %s",
                    lookup_username,
                    update_response.get("message", update_response),
                )

        logging.info(
            "Done — %d updated, %d failed, %d already anonymized.",
            updated,
            failed,
            len(already_anonymized),
        )

    except WorkbenchApiError as e:
        logging.error("An error occurred: %s", e)


if __name__ == "__main__":
    load_dotenv_files()

    parser = argparse.ArgumentParser(
        description=(
            "Anonymize PII for deactivated Workbench users via users->update "
            "(user_name, user_surname, user_email, user_password, phone, mobile)."
        ),
    )
    parser.add_argument('--workbench-url', type=str, help='The Workbench API URL')
    parser.add_argument('--workbench-user', type=str, help='Your Workbench username')
    parser.add_argument('--workbench-token', type=str, help='Your Workbench API token')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show deactivated users that need anonymization without making changes',
    )

    args = parser.parse_args()

    api_base_url = args.workbench_url or os.getenv('WORKBENCH_URL')
    api_username = args.workbench_user or os.getenv('WORKBENCH_USER')
    api_token = args.workbench_token or os.getenv('WORKBENCH_TOKEN')

    if not api_base_url or not api_username or not api_token:
        logging.error(
            "The Workbench URL, username, and token must be provided via "
            ".env, environment variables, or --workbench-* flags."
        )
        exit(1)

    main(api_base_url, api_username, api_token, args.dry_run)
