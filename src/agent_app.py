"""
Agent-Centric MCP Application

This script starts the Agent Service as the primary entry point for client requests.
The Agent orchestrates between direct tools and the MCP Server for processing requests.

Usage:
    python agent_app.py
"""

import logging
import os
import sys
import argparse
import threading
import time
from dotenv import load_dotenv

# Add the src directory to the Python path if running from project root
if os.path.basename(os.getcwd()) == "MCP-Latest" and "src" not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "src"))
# If running from src directory, add current directory to path
elif os.path.basename(os.getcwd()) == "src" and os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def start_mcp_server(host="127.0.0.1", port=8000, debug=False):
    """Start the MCP Server as a service."""
    try:
        # Import here to avoid circular imports
        from app import app as mcp_app
        logger.info(f"Starting MCP Server on {host}:{port}")
        mcp_app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Error starting MCP Server: {str(e)}")

def start_agent_service(host="127.0.0.1", port=5000, debug=False):
    """Start the Agent Service as the main interface."""
    try:
        # Import here to avoid circular imports
        from agent_service.api import app as agent_app
        logger.info(f"Starting Agent Service on {host}:{port}")
        agent_app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Error starting Agent Service: {str(e)}")

def main():
    """Main entry point for the agent-centric application."""
    parser = argparse.ArgumentParser(description="Start the Agent-Centric MCP Application")
    parser.add_argument("--mcp-port", type=int, default=8000, help="Port for the MCP Server")
    parser.add_argument("--agent-port", type=int, default=5000, help="Port for the Agent Service")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    # Start MCP Server in a separate thread
    mcp_thread = threading.Thread(
        target=start_mcp_server,
        args=("127.0.0.1", args.mcp_port, args.debug),
        daemon=True
    )
    mcp_thread.start()
    logger.info(f"MCP Server thread started")
    
    # Give the MCP Server a moment to initialize
    time.sleep(2)
    
    # Start Agent Service in the main thread
    start_agent_service("127.0.0.1", args.agent_port, args.debug)

if __name__ == "__main__":
    main()