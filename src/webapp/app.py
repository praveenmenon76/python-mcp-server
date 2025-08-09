import sys
import os
from pathlib import Path
import json
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the src directory to the Python path to allow imports
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent  # This points to the src directory
sys.path.append(str(src_dir))  # Add src to the Python path

# Now import from the correct path
from mcp_server.server import MCPServer
from mcp_server.agent import IntentAgent

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Initialize the MCP server and agent
mcp_server = MCPServer()
mcp_server.start()

# Get the LLM tool instance
llm_tool = mcp_server.get_tool_instance("LLMTool")

# Initialize the agent with the MCP server and LLM tool
agent = IntentAgent(mcp_server=mcp_server, llm_tool=llm_tool)

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get all available tools"""
    tool_details = agent.get_available_tools()
    return jsonify(tool_details)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat messages"""
    data = request.json
    user_message = data.get('message', '')
    context = data.get('context', {})
    
    if not user_message:
        return jsonify({'response': 'Please enter a message'})
    
    # Special commands
    if user_message.lower() in ["exit", "quit", "bye"]:
        return jsonify({'response': 'Goodbye!'})
    
    if user_message.lower() in ["help", "tools", "commands"]:
        tools = agent.get_available_tools()
        tool_descriptions = []
        for tool in tools:
            tool_descriptions.append(f"- {tool['name']}: {tool['description']}")
        
        help_text = "Available tools:\n" + "\n".join(tool_descriptions)
        return jsonify({'response': help_text})
    
    # Process the user message through the agent
    logger.info(f"Processing user message: {user_message}")
    response = agent.process_query(user_message, context)
    
    # Extract the response message
    if isinstance(response, dict):
        if "message" in response:
            response_text = response["message"]
        elif "data" in response and isinstance(response["data"], dict) and "message" in response["data"]:
            response_text = response["data"]["message"]
        else:
            # Fallback to JSON for unexpected response structures
            response_text = f"Processed successfully: {json.dumps(response)}"
    else:
        response_text = str(response)
    
    return jsonify({'response': response_text})

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    print("Starting MCP Web Application with Agent-based architecture...")
    app.run(debug=True, host='0.0.0.0', port=8080)