# get-project-policy

This script retrieves license policy information for a Workbench project and saves it to a local file.

## Purpose

The script connects to the Workbench API and fetches detailed policy information for a specified project. This is useful for retrieving the project license policy to use with the Diff Scanner.

## Setting Up

You need to provide a Workbench URL, User, and Token to use this script.
These can be provided as Arguments or Environment Variables (recommended).

### Environment Variables (Recommended)

```sh
export WORKBENCH_URL
export WORKBENCH_USER
export WORKBENCH_TOKEN
```

### Arguments

```python
python3 get_project_policy.py --api-url <url> --api-user <user> --api-token <token>
```

## General Usage

Invoke the script by providing the project code to get policy information for:

```python
python3 get_project_policy.py --project-code "company/project-name"
```

The script will save the policy information to a file named `.fossidpolicy` in the current directory by default.

### Custom Output File

If not running from the repository root, you can use `--output-file` to send the policy file to a specific place.

```python
python3 get_project_policy.py --project-code "company/project-name" --output-file "${{ github.workspace }}/.fossidpolicy"
``` 
