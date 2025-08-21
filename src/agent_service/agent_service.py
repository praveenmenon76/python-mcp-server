"""
Agent Service Module - The central orchestrator that processes user requests.

This module provides an independent service that:
1. Receives requests directly from clients
2. Processes requests using LLM to determine intent
3. Routes requests to appropriate tools, including the MCP server
4. Enhances responses for user presentation
"""

import logging
import os
import json
import requests
from typing import Dict, List, Any, Optional

# Change relative import to absolute import
from mcp_server.tools.llm import LLMTool

logger = logging.getLogger(__name__)

class AgentService:
    """
    The central agent service that receives requests from clients and orchestrates
    processing across various tool providers, including the MCP server.
    """
    
    def __init__(self, mcp_server_url: str = None):
        """
        Initialize the Agent Service.
        
        Args:
            mcp_server_url (str, optional): URL of the MCP server API. 
                Defaults to localhost:8000 if not specified.
        """
        self.mcp_server_url = mcp_server_url or "http://localhost:8000"
        
        # Initialize the LLM tool for intent recognition and response enhancement
        self.llm_tool = LLMTool()
        
        # Check if the LLM tool is properly configured
        if not self.llm_tool.api_key:
            logger.warning("LLM Tool not properly configured. Intent recognition may be limited.")
        
        # Available direct tools (tools the agent can use without going through MCP server)
        self.direct_tools = {}
        
        # Cache of MCP server tools for quick reference
        self.mcp_tools_cache = None
        
        logger.info(f"Agent Service initialized with MCP server at {self.mcp_server_url}")
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a user query by determining intent and routing to appropriate tools.
        
        Args:
            query (str): The user's natural language query
            context (Dict[str, Any], optional): Additional context for processing
            
        Returns:
            Dict[str, Any]: The response with results or error information
        """
        if not query:
            return {"status": "error", "message": "Empty query received"}
        
        try:
            # Step 1: Determine intent using LLM
            intent_result = self._determine_intent(query, context)
            
            if intent_result.get("status") == "error":
                return intent_result
            
            intent_data = intent_result.get("data", {})
            tool_name = intent_data.get("tool")
            params = intent_data.get("params", {})
            
            # Check if the tool is "unknown" which means the intent couldn't be determined
            if tool_name == "unknown":
                return {
                    "status": "error", 
                    "message": "I'm not sure how to process that request. Please try asking about weather or stock prices in a more specific way."
                }
            
            # Step 2: Decide how to process the intent (direct tool or MCP server)
            if tool_name in self.direct_tools:
                # Use a direct tool if available
                logger.info(f"Using direct tool: {tool_name}")
                tool_result = self._execute_direct_tool(tool_name, params)
            else:
                # Otherwise route to MCP server
                logger.info(f"Routing to MCP server for tool: {tool_name}")
                tool_result = self._route_to_mcp_server(tool_name, params)
            
            # Step 3: Enhance the response using LLM if appropriate
            if tool_result.get("status") == "success" and self.llm_tool.api_key:
                enhanced_result = self._enhance_response(query, tool_name, tool_result)
                return enhanced_result
            else:
                return tool_result
                
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {"status": "error", "message": f"Failed to process query: {str(e)}"}
    
    def _determine_intent(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use LLM to determine the user's intent from their query.
        
        Args:
            query (str): The user's natural language query
            context (Dict[str, Any], optional): Additional context for intent determination
            
        Returns:
            Dict[str, Any]: The determined intent with tool name and parameters
        """
        # If LLM tool is not available, use basic intent matching
        if not self.llm_tool or not self.llm_tool.api_key:
            return self._basic_intent_matching(query)
        
        # Get available tools info to help the LLM understand options
        tools_info = self._get_available_tools_info()
        
        # Use LLM to determine intent
        result = self.llm_tool.process_query(query, context, tools_info)
        
        if result.get("status") == "success":
            return result
        else:
            logger.warning(f"LLM intent determination failed: {result.get('message')}")
            # Fall back to basic intent matching if LLM fails
            return self._basic_intent_matching(query)
    
    def _basic_intent_matching(self, query: str) -> Dict[str, Any]:
        """
        Basic rule-based intent matching based on keywords in the query.
        
        Args:
            query (str): The user's query
            
        Returns:
            Dict[str, Any]: Information about the detected intent
        """
        query = query.lower()
        
        # Weather intent
        if any(word in query for word in ["weather", "temperature", "forecast", "rain", "sunny", "cloudy"]):
            # Extract location - very simple implementation
            location = None
            words = query.split()
            for i, word in enumerate(words):
                if word in ["in", "at", "for"] and i + 1 < len(words):
                    location = words[i + 1]
                    # Check if the next word is also part of the location (e.g., "New York")
                    if i + 2 < len(words) and words[i + 2] not in ["and", "or", "but", ".", "?", "!"]:
                        location += " " + words[i + 2]
                    break
            
            # Default location if none found
            location = location or "London"
            
            return {
                "status": "success",
                "data": {
                    "tool": "WeatherTool",
                    "params": {"location": location},
                    "confidence": 0.7,
                    "explanation": "Basic keyword matching found weather-related terms"
                }
            }
        
        elif any(word in query for word in ["stock", "price", "market", "ticker", "share"]):
            # Extract ticker symbol - very simple implementation
            ticker = None
            words = query.split()
            for i, word in enumerate(words):
                if word in ["for", "of", "symbol"] and i + 1 < len(words):
                    ticker = words[i + 1].upper()
                    break
            
            if not ticker:
                # Just grab any uppercase word as a potential ticker
                for word in words:
                    if word.isupper() and len(word) <= 5:
                        ticker = word
                        break
            
            # Default ticker if none found
            ticker = ticker or "AAPL"
            
            return {
                "status": "success",
                "data": {
                    "tool": "StockPriceTool",
                    "params": {"symbol": ticker},  # Changed from "ticker" to "symbol"
                    "confidence": 0.7,
                    "explanation": "Basic keyword matching found stock-related terms"
                }
            }
        
        return {
            "status": "error",
            "message": "Could not determine intent from query. Try being more specific."
        }
    
    def _get_available_tools_info(self) -> List[Dict[str, str]]:
        """
        Get information about all available tools (both direct and MCP).
        
        Returns:
            List[Dict[str, str]]: List of tool information with name and description
        """
        tools_info = []
        
        # Add direct tools
        for name, tool in self.direct_tools.items():
            tools_info.append({
                "name": name,
                "description": getattr(tool, "description", f"Direct tool: {name}")
            })
        
        # Add MCP server tools
        mcp_tools = self._get_mcp_tools()
        for tool in mcp_tools:
            tools_info.append(tool)
        
        return tools_info
    
    def _get_mcp_tools(self) -> List[Dict[str, str]]:
        """
        Get the list of tools available from the MCP server.
        
        Returns:
            List[Dict[str, str]]: List of MCP tool information
        """
        # Use cached version if available
        if self.mcp_tools_cache:
            return self.mcp_tools_cache
        
        try:
            # Query the MCP server for available tools
            response = requests.get(f"{self.mcp_server_url}/api/tools")
            
            if response.status_code == 200:
                tools = response.json().get("tools", [])
                # Cache the results
                self.mcp_tools_cache = tools
                return tools
            else:
                logger.error(f"Failed to get tools from MCP server: {response.status_code}")
                return []
                
        except requests.RequestException as e:
            logger.error(f"Error connecting to MCP server: {str(e)}")
            return []
    
    def _route_to_mcp_server(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a request to the MCP server for processing by one of its tools.
        
        Args:
            tool_name (str): The name of the tool to use
            params (Dict[str, Any]): Parameters to pass to the tool
            
        Returns:
            Dict[str, Any]: The result from the MCP server
        """
        try:
            # Make a POST request to the MCP server
            payload = {
                "tool": tool_name,
                "params": params
            }
            
            response = requests.post(
                f"{self.mcp_server_url}/api/execute", 
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_message = f"MCP server returned error {response.status_code}"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_message = error_data["message"]
                except:
                    pass
                
                return {"status": "error", "message": error_message}
                
        except requests.RequestException as e:
            return {
                "status": "error",
                "message": f"Error connecting to MCP server: {str(e)}"
            }
    
    def _execute_direct_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a direct tool that's registered with the agent itself.
        
        Args:
            tool_name (str): The name of the direct tool to use
            params (Dict[str, Any]): Parameters to pass to the tool
            
        Returns:
            Dict[str, Any]: The result from the direct tool
        """
        tool = self.direct_tools.get(tool_name)
        
        if not tool:
            return {
                "status": "error",
                "message": f"Direct tool '{tool_name}' not found"
            }
        
        try:
            # The execute method is expected to exist on all direct tools
            result = tool.execute(**params)
            return result
        except Exception as e:
            logger.error(f"Error executing direct tool {tool_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error executing tool {tool_name}: {str(e)}"
            }
    
    def _enhance_response(self, query: str, tool_name: str, tool_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a tool's response with natural language using LLM.
        
        Args:
            query (str): The original user query
            tool_name (str): The name of the tool that was used
            tool_result (Dict[str, Any]): The raw result from the tool
            
        Returns:
            Dict[str, Any]: The enhanced response
        """
        if not self.llm_tool or not self.llm_tool.api_key:
            return tool_result
        
        # Create context for LLM enhancement
        context = {
            "user_query": query,
            "tool_name": tool_name,
            "response_status": tool_result.get("status"),
            "response_data": tool_result.get("data"),
            "response_message": tool_result.get("message"),
            "tool_response": tool_result
        }
        
        # Instruction for the LLM
        prompt = (
            "Generate a friendly, conversational response based on the tool's output. "
            "Include all relevant information from the data, but make it sound natural and helpful. "
            "If there was an error, explain it in a way that's easy to understand."
        )
        
        # Process with LLM
        enhanced = self.llm_tool.process_enhanced_response(prompt, context)
        
        if enhanced.get("status") == "success":
            # Return an enhanced version but keep the original data
            return {
                "status": "success",
                "message": enhanced.get("message"),
                "data": tool_result.get("data"),  # Preserve the original data
                "raw_response": tool_result.get("message")  # Keep the original message as well
            }
        else:
            # If enhancement fails, return the original response
            logger.warning(f"Response enhancement failed: {enhanced.get('message')}")
            return tool_result
    
    def register_direct_tool(self, tool_name: str, tool_instance: Any) -> bool:
        """
        Register a direct tool with the agent service.
        
        Args:
            tool_name (str): The name to register the tool under
            tool_instance (Any): The tool instance to register
            
        Returns:
            bool: True if registration was successful
        """
        if tool_name in self.direct_tools:
            logger.warning(f"Overwriting existing direct tool: {tool_name}")
        
        self.direct_tools[tool_name] = tool_instance
        logger.info(f"Registered direct tool: {tool_name}")
        return True
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent service and its dependencies.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        status = {
            "agent": "healthy",
            "llm_tool": "unavailable" if not self.llm_tool.api_key else "healthy",
            "direct_tools": list(self.direct_tools.keys()),
            "mcp_server": "unknown"
        }
        
        # Check MCP server connection
        try:
            response = requests.get(f"{self.mcp_server_url}/api/health")
            if response.status_code == 200:
                status["mcp_server"] = "healthy"
                # Add MCP tools info if available
                mcp_status = response.json()
                if "tools" in mcp_status:
                    status["mcp_tools"] = [t.get("name") for t in mcp_status["tools"]]
            else:
                status["mcp_server"] = f"unhealthy (status {response.status_code})"
        except requests.RequestException:
            status["mcp_server"] = "unreachable"
        
        return status