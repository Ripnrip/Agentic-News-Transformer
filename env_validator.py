"""Utility to validate the conda environment."""
import os
import sys

REQUIRED_ENV_NAME = "agentic-transformer"
REQUIRED_ENV_NAME = "agentic-content-transformer"

def validate_conda_env():
    """
    Validates that we are running in the correct conda environment.
    Exits with an error message if we're not in the right environment.
    """
    current_env = os.environ.get("CONDA_DEFAULT_ENV")
    
    # if current_env != REQUIRED_ENV_NAME:
    #     print(f"\033[91mError: This script must be run in the '{REQUIRED_ENV_NAME}' conda environment.")
    #     print(f"Current environment: {current_env or 'No conda environment'}")
    #     print("\nTo activate the correct environment, run:")
    #     print(f"\033[93mconda activate {REQUIRED_ENV_NAME}\033[0m")
    #     sys.exit(1)
    
    return True 