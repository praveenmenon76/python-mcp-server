#!/usr/bin/env python3
"""
Enhanced OpenAI API Key Diagnostic Tool

This script tests if your OpenAI API key is working correctly and provides detailed diagnostics.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_openai_key(api_key, verbose=False):
    """
    Test an OpenAI API key with direct API call

    Args:
        api_key: The API key to test
        verbose: Whether to enable verbose logging

    Returns:
        dict: Result of the test
    """
    if not api_key:
        return {"status": "error", "message": "No API key provided"}

    # Log key format information (safely)
    if verbose:
        logger.debug(
            f"API key format: starts with '{api_key[:6]}...', length: {len(api_key)}"
        )

    # Clean the key (remove quotes, whitespace)
    cleaned_key = api_key.strip().strip("\"'")
    if cleaned_key != api_key and verbose:
        logger.debug("Cleaned API key by removing whitespace or quotes")
        api_key = cleaned_key

    # Try different API endpoints to be thorough
    endpoints = [
        "https://api.openai.com/v1/models",  # List models (simplest call)
        "https://api.openai.com/v1/completions",  # Completions API (fallback)
    ]

    for endpoint in endpoints:
        try:
            logger.info(f"Testing API key with endpoint: {endpoint}")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            # For completions endpoint, we need to provide model and prompt
            if endpoint.endswith("/completions"):
                data = {
                    "model": "gpt-3.5-turbo-instruct",
                    "prompt": "Say hello",
                    "max_tokens": 5,
                }
                response = requests.post(
                    endpoint, headers=headers, json=data, timeout=10
                )
            else:
                response = requests.get(endpoint, headers=headers, timeout=10)

            # Handle different response status codes
            if response.status_code == 200:
                logger.info("✓ API key is valid!")
                return {
                    "status": "success",
                    "message": "API key is valid and working correctly!",
                }
            elif response.status_code == 401:
                error_data = response.json()
                error_message = error_data.get("error", {}).get(
                    "message", "Unknown authentication error"
                )
                logger.error(f"✗ Authentication failed: {error_message}")
                return {
                    "status": "error",
                    "message": f"Authentication failed: {error_message}",
                }
            else:
                logger.warning(f"Unexpected response code: {response.status_code}")
                try:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get(
                        "message", "Unknown error"
                    )
                    logger.error(f"API error: {error_message}")
                    return {
                        "status": "error",
                        "message": f"API error (HTTP {response.status_code}): {error_message}",
                    }
                except:
                    return {
                        "status": "error",
                        "message": f"API error (HTTP {response.status_code}): {response.text[:200]}",
                    }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            # Only return error if we've tried all endpoints
            if endpoint == endpoints[-1]:
                return {"status": "error", "message": f"Request error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}


def main():
    """Main function to test the OpenAI API key"""
    parser = argparse.ArgumentParser(description="Test your OpenAI API key")
    parser.add_argument("--api-key", type=str, help="OpenAI API key to test")
    parser.add_argument(
        "--from-env",
        action="store_true",
        help="Use OPENAI_API_KEY environment variable",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Enter API key interactively (more secure)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine which API key to use
    api_key = None

    if args.interactive:
        # Get API key interactively (more secure than command line)
        import getpass

        print("Enter your OpenAI API key (input will be hidden):")
        api_key = getpass.getpass()
    elif args.from_env:
        # Get API key from environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            return 1
    elif args.api_key:
        # Use API key from command line
        api_key = args.api_key
    else:
        # Try to get API key from config file
        try:
            # Navigate to the config directory
            config_path = Path(__file__).resolve().parent / "config" / "tools.yaml"

            if not config_path.exists():
                logger.error(f"Config file not found at {config_path}")
                logger.info(
                    "Please provide an API key using --api-key, --from-env, or --interactive"
                )
                return 1

            import yaml

            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Look for LLM settings in the tools config
            for tool in config.get("tools", []):
                if tool.get("name") == "LLMTool":
                    api_key = tool.get("settings", {}).get("api_key")
                    if api_key:
                        logger.info("Using API key from config file")
                        break

            if not api_key:
                logger.error("API key not found in config file")
                logger.info(
                    "Please provide an API key using --api-key, --from-env, or --interactive"
                )
                return 1

        except Exception as e:
            logger.error(f"Error loading API key from config: {str(e)}")
            logger.info(
                "Please provide an API key using --api-key, --from-env, or --interactive"
            )
            return 1

    # Test the API key
    result = test_openai_key(api_key, args.verbose)

    if result["status"] == "success":
        logger.info(f"✅ Success: {result['message']}")
        logger.info(
            "Your API key is working correctly and can be used with the LLM tool."
        )
        return 0
    else:
        logger.error(f"❌ Error: {result['message']}")
        logger.info("\nTroubleshooting tips:")
        logger.info(
            "1. Make sure your API key starts with 'sk-' and doesn't have extra quotes or spaces"
        )
        logger.info(
            "2. Check if your OpenAI account has billing set up and sufficient credit"
        )
        logger.info(
            "3. Try generating a new API key from https://platform.openai.com/api-keys"
        )
        logger.info(
            "4. Verify your internet connection and that api.openai.com is accessible"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
