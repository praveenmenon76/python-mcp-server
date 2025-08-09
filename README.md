# Python MCP Server

## Overview
The Python MCP Server is a modular server application designed to manage and register tools efficiently. It provides a framework for extending functionality through tool registration and retrieval.

## Features
- Tool registration and management
- Modular architecture for easy extension
- Configurable settings for tools

## Getting Started

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Installation
1. Clone the repository:
   ```
   git clone https://github.com/yourusername/python-mcp-server.git
   ```
2. Navigate to the project directory:
   ```
   cd python-mcp-server
   ```
3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the Server
To start the MCP server, run the following command:
```
python src/app.py
```

### Tool Registration
The server includes functionality for registering tools. You can register a new tool by using the `ToolRegistry` class found in `src/mcp_server/tools/registry.py`.

### Configuration
Tool settings can be configured in the `src/config/tools.yaml` file. Modify this file to set default settings or tool metadata.

## Testing
To run the tests, execute:
```
pytest tests/
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.