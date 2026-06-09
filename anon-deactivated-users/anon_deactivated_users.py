import logging
import argparse
import os
import sys

from workbench_agent.api.exceptions import WorkbenchApiError

from lib.workbench_client import (
    WorkbenchClient,
    list_all_users,
    normalize_api_url,
    update_user,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main(api_base_url, api_username, api_token, dry_run):
    api_url = normalize_api_url(api_base_url)
    client = WorkbenchClient(api_url, api_username, api_token)

    try:
        logging.info("Fetching all users...")
        users = list_all_users(client, include_deactivated=True)

        users_to_update = []
        for user in users:
            logging.debug(user)
            if user.get("is_deleted") == '1':
                user_id = user.get("id")
                updated_username = f"deactivated_{user_id}"
                logging.info("will update userID %s", user_id)
                users_to_update.append({
                    "original_username": user.get("username"),
                    "updated_username": updated_username
                })

        if dry_run:
            if users_to_update:
                logging.info("Dry Run enabled! The following users would be updated:")
                for user in users_to_update:
                    logging.info(
                        "Username: %s -> %s",
                        user['original_username'],
                        user['updated_username'],
                    )
            else:
                logging.info("No deactivated users found.")
            return

        if users_to_update:
            logging.info("%d users will be updated, continue? (y/n):", len(users_to_update))
            confirmation = input().lower()
            if confirmation != 'y':
                logging.info("Operation cancelled.")
                return

            for user in users_to_update:
                logging.info(
                    "Updating information for deactivated user: %s",
                    user['original_username'],
                )
                update_response = update_user(
                    client,
                    user_username=user['original_username'],
                    user_name="Deactivated",
                    user_surname="User",
                    user_email="deactivated@company.com",
                    user_password="deactivatedpassword",
                )
                logging.debug(update_response)
                if update_response.get("status") == "1":
                    logging.info(
                        "Successfully updated user %s to %s.",
                        user['original_username'],
                        user['updated_username'],
                    )
                else:
                    logging.error("Failed to update user %s.", user['original_username'])
        else:
            logging.info("No deactivated users found.")

    except WorkbenchApiError as e:
        logging.error("Workbench API error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Anonymize deactivated users in Workbench.')
    parser.add_argument('--workbench-url', type=str, help='The Workbench API URL')
    parser.add_argument('--workbench-user', type=str, help='Your Workbench username')
    parser.add_argument('--workbench-token', type=str, help='Your Workbench API token')
    parser.add_argument('--dry-run', action='store_true', help='Show the users that would be updated without making changes')

    args = parser.parse_args()

    api_base_url = args.workbench_url or os.getenv('WORKBENCH_URL')
    api_username = args.workbench_user or os.getenv('WORKBENCH_USER')
    api_token = args.workbench_token or os.getenv('WORKBENCH_TOKEN')

    if not api_base_url or not api_username or not api_token:
        logging.error(
            "The Workbench URL, username, and token must be provided either as "
            "arguments or environment variables."
        )
        sys.exit(1)

    main(api_base_url, api_username, api_token, args.dry_run)
