#!/usr/bin/env python
"""
MCP Client Chatbot - A simple chatbot interface for the MCP server

This script launches a chatbot interface that allows users to interact with
the MCP server tools through natural language queries.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path to allow imports
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
sys.path.append(str(src_dir))

from mcp_server.chatbot import MCPChatbot

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