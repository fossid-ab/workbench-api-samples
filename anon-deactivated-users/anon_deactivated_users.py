import requests
import json
import logging
import argparse
import os
import helper_functions as hf

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_users(url, username, token):
    """  Gets all users in the system

    Parameters:
        url(str): The link to acess the api.
        username(str): The username to use to access the api.
        token(str): The token required to access the api.

    Returns:
        A dictionary with every user.
    """
    payload = {
        "group": "users",
        "action": "get_all_users",
        "data": {
            "username": username,
            "key": token,
            "include_deactivated": "1"
        }
    }
    logging.debug(hf.make_api_call(url, payload))
    return hf.make_api_call(url, payload)

def update_user(url, username, token, user_username, user_name, user_surname, user_email, user_password):
    """Updates the user information based on the given data from the parameters.

    Parameters:
        url(str): The link to access to the api.
        username(str): The username to use to access the api.
        token(str): The token required to access the api.
        user_username(str): The username of the user to update.
        user_name(str): The updated name for the username.
        user_surname(str): The updated surname for the username.
        user_email(str): The updated email for the username.
        user_password(str): The updated password for the username.

    Returns:
        A dictionary with updated data on the user.
    """
    payload = {
        "group": "users",
        "action": "update",
        "data": {
            "username": username,
            "key": token,
            "user_username": user_username,
            "user_name": user_name,
            "user_surname": user_surname,
            "user_email": user_email,
            "user_password": user_password
        }
    }
    return hf.make_api_call(url, payload)

def main(api_base_url, api_username, api_token, dry_run):
    """The main functionality of the script. Anonimizes users who have been deactivated
    
    Parameters:
        api_base_url(str): The base url for the FOSSID workbench.
        api_username(str): The username to use to access the api.
        api_token(str): The required token to access the api.
        dry_run(boolean): True if a dry run was requested.
    """
    # Ensure the API URL ends with /api.php
    if not api_base_url.endswith('/api.php'):
        api_url = api_base_url.rstrip('/') + '/api.php'
    else:
        api_url = api_base_url

    try:
        # Get all users
        logging.info("Fetching all users...")
        users_response = get_all_users(api_url, api_username, api_token)
        if users_response.get("status") != "1":
            logging.error("Failed to fetch users.")
            return

        users_to_update = []
        users = users_response.get("data", [])
        logging.debug(users_response.get("data", []))
        for user in users:
            logging.debug(user)
            if user.get("is_deleted") == '1':  # Only add users that are deactivated
                user_id = user.get("id")
                updated_username = f"deactivated_{user_id}"
                logging.info(f"will update userID {user_id}")
                users_to_update.append({
                    "original_username": user.get("username"),
                    "updated_username": updated_username
                })

        #Performes the dry run and then returns before anonimizing any users.
        if dry_run:
            if users_to_update:
                logging.info("Dry Run enabled! The following users would be updated:")
                for user in users_to_update:
                    logging.info(f"Username: {user['original_username']} -> {user['updated_username']}")
            else:
                logging.info("No deactivated users found.")
            return

        if users_to_update:
            logging.info(f"{len(users_to_update)} users will be updated, continue? (y/n):")
            confirmation = input().lower()
            if confirmation != 'y':
                logging.info("Operation cancelled.")
                return

            for user in users_to_update:
                logging.info(f"Updating information for deactivated user: {user['original_username']}")
                #logging.info(f"the new username will be {user['updated_username']}")
                update_response = update_user(api_url, api_username, api_token, 
                                              #user_username=user['updated_username'], 
                                              user_username=user['original_username'], 
                                              user_name="Deactivated", 
                                              user_surname="User", 
                                              user_email="deactivated@company.com", 
                                              user_password="deactivatedpassword")
                logging.debug(update_response)
                if update_response.get("status") == "1":
                    logging.info(f"Successfully updated user {user['original_username']} to {user['updated_username']}.")
                else:
                    logging.error(f"Failed to update user {user['original_username']}.")
        else:
            logging.info("No deactivated users found.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

#sets up the arugments to run the script
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
        logging.error("The Workbench URL, username, and token must be provided either as arguments or environment variables.")
        exit(1)

    #calls the main function to run the script and anonimize deactivited users
    main(api_base_url, api_username, api_token, args.dry_run)