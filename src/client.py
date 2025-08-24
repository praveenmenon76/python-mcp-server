#!/usr/bin/env python
"""
MCP Client - A client for interacting with the MCP server

This module provides a client interface for communicating with the MCP server
using JSON-RPC protocol.
"""

import json
import logging
import requests
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class MCPClient:
    """
    Model Context Protocol (MCP) Client
    
    A client for interacting with the MCP server using JSON-RPC protocol.
    """
    
    def __init__(self, server_url: str = "http://localhost:8000/api/jsonrpc"):
        """
        Initialize the MCP client with the server URL.
        
        Args:
            server_url: The URL of the MCP server's JSON-RPC endpoint
        """
        self.server_url = server_url
        self.request_id = 1
        
    def _make_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a JSON-RPC request to the MCP server.
        
        Args:
            method: The JSON-RPC method to call
            params: The parameters to pass to the method
            
        Returns:
            The JSON-RPC response
        """
        # Create the JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id
        }
        
        self.request_id += 1
        
        try:
            # Make the HTTP request
            response = requests.post(
                self.server_url,
                json=request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the JSON-RPC response
            result = response.json()
            
            # Check for JSON-RPC errors
            if "error" in result:
                logger.error(f"JSON-RPC error: {result['error']}")
                return {"status": "error", "message": result["error"].get("message", "Unknown error")}
            
            return result.get("result", {})
            
        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return {"status": "error", "message": f"Request error: {str(e)}"}
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return {"status": "error", "message": f"Invalid JSON response: {str(e)}"}
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}
    
    def get_tools(self) -> List[Dict[str, str]]:
        """
        Get a list of all available tools from the MCP server.
        
        Returns:
            A list of tool information dictionaries
        """
        result = self._make_request("tools.list")
        
        if result.get("status") == "error":
            logger.error(f"Error getting tools: {result.get('message')}")
            return []
        
        return result.get("tools", [])
    
    def get_tool_details(self, tool_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name: The name of the tool to get details for
            
        Returns:
            A dictionary with tool details
        """
        result = self._make_request("tools.get", {"name": tool_name})
        
        if result.get("status") == "error":
            logger.error(f"Error getting tool details: {result.get('message')}")
            return {"name": tool_name, "available": False}
        
        return result.get("tool", {})
    
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given parameters.
        
        Args:
            tool_name: The name of the tool to execute
            params: The parameters to pass to the tool
            
        Returns:
            The result of the tool execution
        """
        result = self._make_request("tools.execute", {
            "tool": tool_name,
            "params": params
        })
        
        return result
