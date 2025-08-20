import json
import logging
import re
import sys
from pathlib import Path

# Add the src directory to the Python path to allow imports
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))  # Add the src directory

from mcp_server.agent import IntentAgent
from mcp_server.server import MCPServer

logger = logging.getLogger(__name__)


class MCPChatbot:
    def __init__(self):
        # Initialize and start the MCP server
        self.server = MCPServer()
        self.server.start()

        # Get the LLM tool instance from the server
        self.llm_tool = self.server.get_tool_instance("LLMTool")

        # Initialize the intent agent with the MCP server and LLM tool
        self.agent = IntentAgent(mcp_server=self.server, llm_tool=self.llm_tool)

        # Default to using enhanced responses if LLM is available
        self.use_enhanced_responses = True

        print("MCP Chatbot initialized. Server started.")
        self._print_available_tools()

    def _print_available_tools(self):
        """Print available tools to the user"""
        tools = self.agent.get_available_tools()
        print("\nAvailable tools:")
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")
        print("\n")

    def process_input(self, user_input):
        """Process user input using the intent agent"""
        if not user_input.strip():
            return "Please enter a question or command."

        # Handle exit commands
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            return "exit"

        # Handle help command
        if user_input.lower() in ["help", "tools", "commands"]:
            self._print_available_tools()
            return (
                "You can ask for weather information or stock prices. For example:\n"
                "- 'What's the weather in New York?'\n"
                "- 'Get stock price for AAPL'"
            )

        # Toggle enhanced responses mode
        if user_input.lower() in ["toggle enhanced", "toggle responses"]:
            self.use_enhanced_responses = not self.use_enhanced_responses
            self.agent.use_enhanced_responses = self.use_enhanced_responses
            return f"Enhanced responses {'enabled' if self.use_enhanced_responses else 'disabled'}"

        # Process the user input through the agent
        logger.info(f"Processing user input: {user_input}")
        response = self.agent.process_query(user_input)

        # Extract the message from the response
        if isinstance(response, dict):
            # Check if response is enhanced
            if response.get("enhanced", False):
                return response["message"]

            # Standard response extraction
            if "message" in response:
                return response["message"]
            elif (
                "data" in response
                and isinstance(response["data"], dict)
                and "message" in response["data"]
            ):
                return response["data"]["message"]
            else:
                return f"Processed successfully: {json.dumps(response)}"
        else:
            return response

    def run_chatbot(self):
        """Run the chatbot interface"""
        print("Welcome to the MCP Chatbot!")
        print("You can ask for weather information or stock prices.")
        print("Type 'help' to see available commands or 'exit' to quit.")
        print("Type 'toggle enhanced' to toggle enhanced responses.")

        while True:
            user_input = input("\nYou: ")
            response = self.process_input(user_input)

            if response == "exit":
                self.server.stop()
                break

            print(f"\nChatbot: {response}")


if __name__ == "__main__":
    chatbot = MCPChatbot()
    chatbot.run_chatbot()
