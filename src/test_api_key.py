#!/usr/bin/env python3
"""
LLM API Key Diagnostic Tool

This script tests if your LLM API key is working correctly.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the src directory to the Python path to allow imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))  # Add the src directory


def main():
    """Main function to test the LLM API key"""
    parser = argparse.ArgumentParser(description="Test your LLM API key")
    parser.add_argument(
        "--api-key", type=str, help="LLM API key to test (overrides config)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "azure", "anthropic"],
        help="LLM provider (default: openai)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Import the LLMTool class
    try:
        from mcp_server.tools.llm import LLMTool
    except ImportError:
        logger.error(
            "Failed to import LLMTool. Make sure you're running this script from the project root."
        )
        sys.exit(1)

    # Create an instance of the LLMTool
    llm_tool = LLMTool()

    # Override API key if provided
    if args.api_key:
        llm_tool.api_key = args.api_key
        logger.info("Using provided API key")

    # Override provider if provided
    if args.provider:
        llm_tool.provider = args.provider
        logger.info(f"Using provider: {args.provider}")

    # Enable the tool (in case it's disabled in config)
    llm_tool.enabled = True

    # Print current configuration
    logger.info(f"Testing LLM API key for provider: {llm_tool.provider}")
    logger.info(
        f"API key: {llm_tool.api_key[:5]}{'*' * 10}{llm_tool.api_key[-4:] if llm_tool.api_key else ''}"
    )

    # Test the API key
    result = llm_tool.test_api_key()

    if result["status"] == "success":
        logger.info(f"✅ Success: {result['message']}")
        return 0
    else:
        logger.error(f"❌ Error: {result['message']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
