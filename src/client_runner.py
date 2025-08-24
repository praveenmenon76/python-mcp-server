#!/usr/bin/env python
"""
MCP Client Runner - A script to run the MCP client chatbot

This script launches a chatbot interface that allows users to interact with
the MCP server tools through natural language queries.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the Python path to allow imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

# Now we can safely import the client and chatbot
from client import MCPClient
from mcp_server.chatbot import MCPChatbot

logger = logging.getLogger(__name__)

def main():
    """Launch the MCP chatbot client"""
    print("=" * 60)
    print("MCP CHATBOT CLIENT".center(60))
    print("=" * 60)

    try:
        # Initialize and run the chatbot
        chatbot = MCPChatbot()
        chatbot.run_chatbot()
    except KeyboardInterrupt:
        print("\nChatbot terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\nThank you for using the MCP Chatbot!")

if __name__ == "__main__":
    main()