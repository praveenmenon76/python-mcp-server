"""
Agent Service API - Provides HTTP endpoints for interacting with the Agent Service.

This module implements a Flask-based REST API that exposes the Agent Service
functionality to clients. It serves as the primary entry point for all client
requests in the agent-centric architecture.
"""

import logging
import os
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from .agent_service import AgentService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
           template_folder='templates',  # Explicitly set the templates folder
           static_folder='static')       # Explicitly set the static folder if needed

# Initialize the agent service
agent_service = AgentService()

@app.route("/")
def index():
    """Serve the Agent Service home page."""
    return render_template("agent_index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    """Process a chat message through the Agent Service."""
    try:
        data = request.json
        query = data.get("query")
        context = data.get("context", {})
        
        if not query:
            return jsonify({"status": "error", "message": "Query is required"}), 400
            
        # Process the query through the agent service
        result = agent_service.process_query(query, context)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500

@app.route("/api/health", methods=["GET"])
def health():
    """Get health status of the Agent Service and its dependencies."""
    try:
        status = agent_service.get_health_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error checking health status: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/tools", methods=["GET"])
def list_tools():
    """Get a list of all available tools (both direct and MCP server tools)."""
    try:
        tools_info = agent_service._get_available_tools_info()
        return jsonify({"status": "success", "tools": tools_info})
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def start_agent_service(host="127.0.0.1", port=5000, debug=False):
    """Start the Agent Service API server."""
    logger.info(f"Starting Agent Service API on {host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.environ.get("AGENT_SERVICE_PORT", 5000))
    debug = os.environ.get("AGENT_SERVICE_DEBUG", "false").lower() == "true"
    
    # Start the server
    start_agent_service(port=port, debug=debug)