import importlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .tools.llm import LLMTool
from .tools.registry import ToolRegistry
from .tools.stock_price import StockPriceTool
from .tools.weather import WeatherTool
from .types.models import Tool

logger = logging.getLogger(__name__)


class MCPServer:
    def __init__(self):
        self.tools_registry = ToolRegistry()
        self.is_running = False
        # Initialize tools dictionary to store instances
        self.tool_instances = {}

    def start(self):
        logger.info("Starting MCP Server...")
        self.is_running = True
        # Initialize and register WeatherTool instance
        self._initialize_built_in_tools()
        # Load tools from configuration on startup
        self._load_tools_from_config()

    def stop(self):
        logger.info("Stopping MCP Server...")
        self.is_running = False

    def register_tool(self, name, tool_instance=None):
        """Register a tool by name, with optional instance"""
        if tool_instance:
            self.tool_instances[name] = tool_instance
            # If the tool has an as_tool_model method, use it for metadata
            if hasattr(tool_instance, "as_tool_model"):
                tool_model = tool_instance.as_tool_model()
                self.tools_registry.register_tool(name, tool_model)
            else:
                self.tools_registry.register_tool(name, tool_instance)
        else:
            self.tools_registry.register_tool(name)

    def unregister_tool(self, name):
        self.tools_registry.unregister_tool(name)
        if name in self.tool_instances:
            del self.tool_instances[name]

    def get_registered_tools(self):
        return self.tools_registry.get_registered_tools()

    def get_tool(self, tool_name):
        return self.tools_registry.get_tool(tool_name)

    def get_tool_instance(self, tool_name):
        """Get the actual tool instance with functionality"""
        # Try direct lookup first
        if tool_name in self.tool_instances:
            return self.tool_instances[tool_name]
        
        # Try case-insensitive lookup
        tool_name_lower = tool_name.lower()
        for name, instance in self.tool_instances.items():
            if name.lower() == tool_name_lower:
                return instance
                
        return None
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool
            
        Returns:
            Dict with the tool execution result
        """
        tool_instance = self.get_tool_instance(tool_name)
        
        if not tool_instance:
            return {
                "status": "error",
                "message": f"Tool '{tool_name}' not found"
            }
        
        # Get the actual name from the instance for consistent logging
        actual_tool_name = getattr(tool_instance, "name", tool_name)
        tool_name_lower = actual_tool_name.lower()
            
        # Execute the appropriate method based on the tool
        try:
            if tool_name_lower == "weathertool" or tool_name_lower == "weather":
                location = params.get("location")
                units = params.get("units", "metric")
                
                if not location:
                    return {
                        "status": "error",
                        "message": "Location parameter is required"
                    }
                    
                return tool_instance.get_weather(location, units)
                
            elif tool_name_lower == "stockpricetool" or tool_name_lower == "stock":
                # Accept either "ticker" or "symbol" parameter for compatibility
                symbol = params.get("symbol") or params.get("ticker")
                
                if not symbol:
                    return {
                        "status": "error",
                        "message": "Symbol parameter is required"
                    }
                    
                return tool_instance.get_stock_price(symbol)
                
            elif tool_name_lower == "llmtool" or tool_name_lower == "llm":
                query = params.get("query")
                context = params.get("context")
                
                if not query:
                    return {
                        "status": "error",
                        "message": "Query parameter is required"
                    }
                    
                return tool_instance.process_query(query, context)
                
            else:
                # For future tools, try a generic execute method if available
                if hasattr(tool_instance, "execute"):
                    return tool_instance.execute(**params)
                else:
                    return {
                        "status": "error", 
                        "message": f"Don't know how to execute tool '{actual_tool_name}'"
                    }
        except Exception as e:
            logger.exception(f"Error executing tool {actual_tool_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error executing tool: {str(e)}"
            }
    
    def handle_jsonrpc(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a JSON-RPC request.
        
        Args:
            request_data: The JSON-RPC request
            
        Returns:
            The JSON-RPC response
        """
        # Check for required JSON-RPC fields
        if "jsonrpc" not in request_data or request_data["jsonrpc"] != "2.0":
            return self._jsonrpc_error(-32600, "Invalid Request: Not a valid JSON-RPC 2.0 request", request_data.get("id"))
            
        if "method" not in request_data:
            return self._jsonrpc_error(-32600, "Invalid Request: Method not specified", request_data.get("id"))
            
        method = request_data["method"]
        params = request_data.get("params", {})
        request_id = request_data.get("id")
        
        # Handle different RPC methods
        try:
            if method == "tools.list":
                return self._jsonrpc_response(self._rpc_list_tools(), request_id)
                
            elif method == "tools.get":
                tool_name = params.get("name")
                if not tool_name:
                    return self._jsonrpc_error(-32602, "Invalid params: tool name not specified", request_id)
                    
                return self._jsonrpc_response(self._rpc_get_tool(tool_name), request_id)
                
            elif method == "tools.execute":
                tool_name = params.get("tool")
                tool_params = params.get("params", {})
                
                if not tool_name:
                    return self._jsonrpc_error(-32602, "Invalid params: tool name not specified", request_id)
                    
                return self._jsonrpc_response(self.execute_tool(tool_name, tool_params), request_id)
                
            else:
                return self._jsonrpc_error(-32601, f"Method not found: {method}", request_id)
                
        except Exception as e:
            logger.exception(f"Error handling JSON-RPC request: {str(e)}")
            return self._jsonrpc_error(-32603, f"Internal error: {str(e)}", request_id)
    
    def _jsonrpc_response(self, result: Any, request_id: Optional[Union[str, int]] = None) -> Dict[str, Any]:
        """
        Create a JSON-RPC response.
        
        Args:
            result: The result of the method call
            request_id: The ID from the request
            
        Returns:
            A JSON-RPC response dictionary
        """
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
    
    def _jsonrpc_error(self, code: int, message: str, request_id: Optional[Union[str, int]] = None) -> Dict[str, Any]:
        """
        Create a JSON-RPC error response.
        
        Args:
            code: The error code
            message: The error message
            request_id: The ID from the request
            
        Returns:
            A JSON-RPC error response dictionary
        """
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }
    
    def _rpc_list_tools(self) -> Dict[str, Any]:
        """
        RPC method to list all available tools.
        
        Returns:
            Dict with tool information
        """
        tools_list = []
        try:
            names = self.get_registered_tools()
            for name in names:
                meta = self.get_tool(name)
                if meta is not None:
                    tools_list.append({
                        "name": getattr(meta, "name", name),
                        "description": getattr(meta, "description", ""),
                        "version": getattr(meta, "version", ""),
                    })
                else:
                    tools_list.append({"name": name})
        except Exception as e:
            logger.exception(f"Failed to list tools: {str(e)}")
            return {"status": "error", "message": f"Failed to list tools: {str(e)}"}
            
        return {"status": "success", "tools": tools_list}
    
    def _rpc_get_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        RPC method to get detailed information about a specific tool.
        
        Args:
            tool_name: The name of the tool to get details for
            
        Returns:
            Dict with tool details
        """
        tool = self.get_tool(tool_name)
        
        if not tool:
            return {"status": "error", "message": f"Tool '{tool_name}' not found"}
            
        tool_info = {
            "name": getattr(tool, "name", tool_name),
            "description": getattr(tool, "description", ""),
            "version": getattr(tool, "version", ""),
            "available": True
        }
        
        # Add additional metadata if available
        for attr in ["parameters", "returns", "examples"]:
            if hasattr(tool, attr):
                tool_info[attr] = getattr(tool, attr)
                
        return {"status": "success", "tool": tool_info}

    def _initialize_built_in_tools(self):
        """Initialize and register built-in tools"""
        try:
            # Initialize WeatherTool
            weather_tool = WeatherTool()
            self.register_tool(weather_tool.name, weather_tool)
            logger.info(f"Registered built-in tool: {weather_tool.name}")

            # Initialize StockPriceTool
            stock_price_tool = StockPriceTool()
            self.register_tool(stock_price_tool.name, stock_price_tool)
            logger.info(f"Registered built-in tool: {stock_price_tool.name}")

            # Initialize LLMTool
            llm_tool = LLMTool()
            self.register_tool(llm_tool.name, llm_tool)
            logger.info(f"Registered built-in tool: {llm_tool.name}")
        except Exception as e:
            logger.exception(f"Error initializing built-in tools: {e}")

    def _load_tools_from_config(self):
        try:
            try:
                yaml = importlib.import_module("yaml")  # dynamic import
            except ImportError:
                logger.debug("PyYAML not installed; skipping YAML tool loading.")
                return
            src_dir = Path(__file__).resolve().parent.parent
            config_path = src_dir / "config" / "tools.yaml"
            if not config_path.exists():
                logger.debug("No tools.yaml found at %s", config_path)
                return
            with config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            tools = data.get("tools", [])
            for t in tools:
                name = t.get("name")
                if not name:
                    continue
                tool_obj = Tool(
                    name=name,
                    description=t.get("description", ""),
                    version=t.get("version", ""),
                )
                # Register tool name and metadata object
                try:
                    self.tools_registry.register_tool(name, tool_obj)
                    logger.debug("Registered tool from config: %s", name)
                except ValueError:
                    logger.debug("Tool already registered, skipping: %s", name)
        except Exception as e:
            logger.exception("Failed to load tools from config: %s", e)


if __name__ == "__main__":
    server = MCPServer()
    server.start()
