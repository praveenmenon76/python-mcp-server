import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentAgent:
    """
    Agent responsible for understanding user intent and delegating to the appropriate tools.
    Acts as an intermediary between the chatbot interface and the MCP server tools.
    """

    def __init__(self, mcp_client=None, llm_tool=None):
        """
        Initialize the Intent Agent.

        Args:
            mcp_client: The MCP Client instance to use for tool execution
            llm_tool: The LLM Tool to use for intent recognition (optional)
        """
        # Store the client directly, don't try to create a new one to avoid circular imports
        self.mcp_client = mcp_client
        self.llm_tool = llm_tool
        self.conversation_history = []
        self.use_enhanced_responses = True  # Flag to enable/disable enhanced responses

    def set_mcp_client(self, mcp_client):
        """Set the MCP client instance for this agent"""
        self.mcp_client = mcp_client

    def set_llm_tool(self, llm_tool):
        """Set the LLM tool for this agent"""
        self.llm_tool = llm_tool

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get information about all available tools from the MCP server through the client"""
        if not self.mcp_client:
            logger.error("MCP Client not initialized")
            return []

        # Use the client to get tools from the server
        tools_info = self.mcp_client.get_tools()
        
        # If no tools were found, return an empty list
        if not tools_info:
            return []
            
        return tools_info

    def process_query(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user query to understand intent and execute the appropriate tool.

        Args:
            query: The user's natural language query
            context: Optional context information

        Returns:
            Dict with response information
        """
        if not self.mcp_client:
            return {"status": "error", "message": "MCP Client not initialized"}

        # Add query to conversation history
        self.conversation_history.append({"role": "user", "content": query})

        # Determine intent using LLM if available
        intent_result = self._determine_intent(query, context)

        # If intent determination failed, return the error
        if intent_result["status"] == "error":
            return intent_result

        # Get the tool name and parameters from the intent result
        tool_name = intent_result["data"].get("tool")
        params = intent_result["data"].get("params", {})
        confidence = intent_result["data"].get("confidence", 0)
        explanation = intent_result["data"].get("explanation", "")

        # Log the intent recognition details
        logger.info(f"Recognized intent: {tool_name} (confidence: {confidence})")
        logger.info(f"Parameters: {params}")
        logger.info(f"Explanation: {explanation}")

        # Execute the appropriate tool with the extracted parameters
        raw_response = self._execute_tool(tool_name, params)

        # Generate enhanced response if enabled and LLM is available
        response = raw_response
        if self.use_enhanced_responses and self.llm_tool and self.llm_tool.api_key:
            enhanced_response = self._generate_enhanced_response(
                query, raw_response, tool_name
            )
            if enhanced_response and enhanced_response.get("status") == "success":
                response = enhanced_response

        # Add response to conversation history
        if isinstance(response, str):
            self.conversation_history.append({"role": "assistant", "content": response})
        else:
            # If response is a dict, convert to string for history
            content = response.get("message", json.dumps(response))
            self.conversation_history.append({"role": "assistant", "content": content})

        return response

    def _determine_intent(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determine the user's intent from their query.

        Args:
            query: The user's natural language query
            context: Optional context information

        Returns:
            Dict with intent information (tool name and parameters)
        """
        # If LLM tool is available, use it for intent recognition
        if self.llm_tool and self.llm_tool.api_key:
            # Get information about available tools
            tools_info = self.get_available_tools()

            # Get recent conversation history for context (last 5 exchanges)
            recent_history = (
                self.conversation_history[-10:]
                if len(self.conversation_history) > 10
                else self.conversation_history
            )

            # Add conversation history to context if available
            if context is None:
                context = {}

            if recent_history:
                context["conversation_history"] = recent_history

            # Call the LLM to process the query
            llm_result = self.llm_tool.process_query(
                query, context=context, tools_info=tools_info
            )

            if llm_result["status"] == "success":
                return llm_result
            else:
                logger.warning(
                    f"LLM intent recognition failed: {llm_result['message']}"
                )
                # Fall back to rule-based intent recognition

        # Rule-based intent recognition as fallback
        return self._rule_based_intent_recognition(query)

    def _rule_based_intent_recognition(self, query: str) -> Dict[str, Any]:
        """
        Perform rule-based intent recognition (fallback method).

        Args:
            query: The user's natural language query

        Returns:
            Dict with intent information (tool name and parameters)
        """
        query_lower = query.lower()

        # Weather intent patterns
        weather_keywords = ["weather", "temperature", "forecast", "raining", "sunny"]
        if any(keyword in query_lower for keyword in weather_keywords):
            # Extract location using regex patterns
            import re

            location_patterns = [
                r"weather\s+(?:in|at|for)\s+([A-Za-z\s,]+)",
                r"weather\s+([A-Za-z\s,]+)",
                r"(?:in|at|for)\s+([A-Za-z\s,]+)",
            ]

            location = None
            for pattern in location_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    break

            return {
                "status": "success",
                "data": {
                    "tool": "WeatherTool",
                    "params": {"location": location},
                    "confidence": 0.7,
                    "explanation": "Rule-based intent recognition identified weather-related keywords",
                },
            }

        # Stock price intent patterns
        stock_keywords = ["stock", "price", "share", "ticker", "market", "trading"]
        if any(keyword in query_lower for keyword in stock_keywords):
            # Extract stock symbol using regex patterns
            import re

            symbol_patterns = [
                r"stock\s+(?:price|prices|quote|quotes)?\s+(?:for|of)\s+([A-Za-z\s]+)",
                r"([A-Za-z\s]+)\s+stock\s+(?:price|prices|quote|quotes)?",
                r"(?:price|prices|quote|quotes)\s+(?:for|of)\s+([A-Za-z\s]+)",
                r"(?:ticker|symbol)\s+([A-Za-z\s]+)",
            ]

            symbol = None
            for pattern in symbol_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    symbol = match.group(1).strip()
                    break

            # If no pattern matches but single word query, assume it's a symbol
            if not symbol:
                words = query.strip().split()
                if len(words) == 1 and words[0].isalpha():
                    symbol = words[0]

            return {
                "status": "success",
                "data": {
                    "tool": "StockPriceTool",
                    "params": {"symbol": symbol},
                    "confidence": 0.7,
                    "explanation": "Rule-based intent recognition identified stock-related keywords",
                },
            }

        # Unknown intent
        return {
            "status": "success",
            "data": {
                "tool": "unknown",
                "params": {},
                "confidence": 0.0,
                "explanation": "Could not determine intent from query",
            },
        }

    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given parameters using the MCP client.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool

        Returns:
            Dict with the tool execution result
        """
        if tool_name == "unknown":
            # If we have an LLM available, use it to generate a helpful response
            # even when the query doesn't match any specific tool
            if self.llm_tool and self.llm_tool.api_key:
                try:
                    # Prepare a context for the LLM
                    context = {
                        "query": params.get("query", "Unknown query"),
                        "available_tools": [tool["name"] for tool in self.get_available_tools()]
                    }
                    
                    # Create a prompt for a general response
                    prompt = (
                        "The user has asked a question that doesn't match any of our specific tools. "
                        "Please provide a helpful response that explains what kinds of questions I can answer. "
                        "Be conversational and friendly. If you can partially answer their question with general knowledge, "
                        "please do so, but make it clear what our limitations are."
                    )
                    
                    # Get a response from the LLM
                    llm_result = self.llm_tool.process_enhanced_response(prompt, context)
                    
                    if llm_result.get("status") == "success" and "message" in llm_result:
                        return {
                            "status": "success",
                            "message": llm_result["message"],
                            "data": {"query": params.get("query")},
                            "tool": "general_response"
                        }
                    
                except Exception as e:
                    logger.error(f"Error generating general response: {str(e)}")
            
            # Fall back to the default message if LLM response fails or is unavailable
            return {
                "status": "error",
                "message": "I'm not sure how to help with that. Try asking about weather or stock prices.",
            }

        # Use the client to execute the tool
        result = self.mcp_client.execute_tool(tool_name, params)
        
        # Check if there was an error with the client
        if result.get("status") == "error":
            return result
            
        # Process and format the response based on the tool type
        if tool_name == "WeatherTool" and result.get("status") == "success":
            raw_data = result.get("data", {})
            
            # Format the response for weather data
            return {
                "status": "success",
                "message": (
                    f"Weather in {raw_data.get('location', 'Unknown')} ({raw_data.get('country', '')}):\n"
                    f"Temperature: {raw_data.get('temperature', 'N/A')}°C\n"
                    f"Feels like: {raw_data.get('feels_like', 'N/A')}°C\n"
                    f"Condition: {raw_data.get('weather_description', 'N/A')}\n"
                    f"Humidity: {raw_data.get('humidity', 'N/A')}%\n"
                    f"Wind speed: {raw_data.get('wind_speed', 'N/A')} m/s"
                ),
                "data": raw_data,
            }
            
        elif tool_name == "StockPriceTool" and result.get("status") == "success":
            raw_data = result.get("data", {})
            
            # Format the response for stock price data
            return {
                "status": "success",
                "message": (
                    f"Stock information for {raw_data.get('symbol', 'Unknown')}:\n"
                    f"Current price: ${raw_data.get('price', 'N/A')}\n"
                    f"Change: {raw_data.get('change', 'N/A')} ({raw_data.get('change_percent', 'N/A')})\n"
                    f"Volume: {raw_data.get('volume', 'N/A')}\n"
                    f"Day's range: ${raw_data.get('low', 'N/A')} - ${raw_data.get('high', 'N/A')}\n"
                    f"Latest trading day: {raw_data.get('latest_trading_day', 'N/A')}"
                ),
                "data": raw_data,
            }
            
        # For any other tools, just return whatever the tool returned
        return result

    def _generate_enhanced_response(
        self, query: str, tool_response: Dict[str, Any], tool_name: str
    ) -> Dict[str, Any]:
        """
        Generate an enhanced, natural language response using the LLM based on the tool output.

        Args:
            query: The original user query
            tool_response: The raw response from the tool
            tool_name: The name of the tool that was executed

        Returns:
            Dict with enhanced response
        """
        if not self.llm_tool or not self.llm_tool.api_key:
            return None

        try:
            # Create a context dictionary with the tool response data
            context = {
                "user_query": query,
                "tool_name": tool_name,
                "tool_response": tool_response,
                "response_status": tool_response.get("status", "unknown"),
                "response_data": tool_response.get("data", {}),
                "response_message": tool_response.get("message", ""),
            }

            # Create a prompt for the LLM to generate a natural language response
            enhanced_prompt = (
                "Generate a natural, conversational response to the user's query based on the data provided. "
                "The response should be helpful, concise, and in a friendly tone. "
                "Include all relevant information from the data, but phrase it naturally as if in conversation. "
                "If there was an error, explain it clearly and suggest alternatives."
            )

            # Call the LLM to generate the enhanced response
            llm_result = self.llm_tool.process_enhanced_response(
                enhanced_prompt, context
            )

            if llm_result.get("status") == "success" and "message" in llm_result:
                # Return the enhanced response
                return {
                    "status": tool_response.get("status", "success"),
                    "message": llm_result["message"],
                    "data": tool_response.get("data", {}),
                    "enhanced": True,
                }

            logger.warning(
                "LLM enhanced response generation failed or returned unexpected format"
            )
            return None

        except Exception as e:
            logger.error(f"Error generating enhanced response: {str(e)}")
            return None
