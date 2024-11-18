import json
import time
import logging
import argparse
import os
import re
from typing import Dict, Any
import sys
import requests

def make_api_call(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to make API calls.
    
    Parameters:
        url(str): The url to access the API.
        payload(Dict[str, Any]): A dictionary that contains the data required by the API.
        
    Returns:
        Returns a dicitionary with the API response data
    """
    try:
        logging.debug("Making API call with payload: %s", json.dumps(payload, indent=2))
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logging.debug("Received response: %s", response.text)
        return response.json().get("data", {})
    except requests.exceptions.RequestException as e:
        logging.error("API call failed: %s", str(e))
        raise
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON response: %s", str(e))
        raise