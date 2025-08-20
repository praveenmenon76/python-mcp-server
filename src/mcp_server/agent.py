import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentAgent:
    """
    Agent responsible for understanding user intent and delegating to the appropriate tools.
    Acts as an intermediary between the chatbot interface and the MCP server tools.
    """

    def __init__(self, mcp_server=None, llm_tool=None):
        """
        Initialize the Intent Agent.

        Args:
            mcp_server: The MCP Server instance to use for tool execution
            llm_tool: The LLM Tool to use for intent recognition (optional)
        """
        self.mcp_server = mcp_server
        self.llm_tool = llm_tool
        self.conversation_history = []
        self.use_enhanced_responses = True  # Flag to enable/disable enhanced responses

    def set_mcp_server(self, mcp_server):
        """Set the MCP server instance for this agent"""
        self.mcp_server = mcp_server

    def set_llm_tool(self, llm_tool):
        """Set the LLM tool for this agent"""
        self.llm_tool = llm_tool

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get information about all available tools from the MCP server"""
        if not self.mcp_server:
            logger.error("MCP Server not initialized")
            return []

        tools_info = []
        tool_names = self.mcp_server.get_registered_tools()

        for name in tool_names:
            tool = self.mcp_server.get_tool(name)
            if tool and hasattr(tool, "description"):
                tools_info.append({"name": name, "description": tool.description})
            else:
                tools_info.append(
                    {"name": name, "description": "No description available"}
                )

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
        if not self.mcp_server:
            return {"status": "error", "message": "MCP Server not initialized"}

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
        Execute a tool with the given parameters.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool

        Returns:
            Dict with the tool execution result
        """
        if tool_name == "unknown":
            return {
                "status": "error",
                "message": "I'm not sure how to help with that. Try asking about weather or stock prices.",
            }

        # Get the tool instance from the MCP server
        tool = self.mcp_server.get_tool_instance(tool_name)

        if not tool:
            return {
                "status": "error",
                "message": f"Sorry, {tool_name} is not available.",
            }

        # Store the raw tool data for enhanced processing
        raw_data = None

        # Execute the tool based on its type
        if tool_name == "WeatherTool":
            location = params.get("location")
            if not location:
                return {
                    "status": "error",
                    "message": "Please specify a location for the weather. For example: 'What's the weather in London?'",
                }

            logger.info(f"Executing WeatherTool with location: {location}")
            result = tool.get_weather(location)

            # Store the raw data for enhanced processing
            if result["status"] == "success":
                raw_data = result["data"]

                # This is the legacy formatted response that will be enhanced
                return {
                    "status": "success",
                    "message": (
                        f"Weather in {raw_data['location']} ({raw_data['country']}):\n"
                        f"Temperature: {raw_data['temperature']}°C\n"
                        f"Feels like: {raw_data['feels_like']}°C\n"
                        f"Condition: {raw_data['weather_description']}\n"
                        f"Humidity: {raw_data['humidity']}%\n"
                        f"Wind speed: {raw_data['wind_speed']} m/s"
                    ),
                    "data": raw_data,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Error fetching weather: {result['message']}",
                }

        elif tool_name == "StockPriceTool":
            symbol = params.get("symbol")
            if not symbol:
                return {
                    "status": "error",
                    "message": "Please specify a stock symbol. For example: 'Get stock price for AAPL'",
                }

            logger.info(f"Executing StockPriceTool with symbol: {symbol}")
            result = tool.get_stock_price(symbol)

            # Store the raw data for enhanced processing
            if result["status"] == "success":
                raw_data = result["data"]

                # This is the legacy formatted response that will be enhanced
                return {
                    "status": "success",
                    "message": (
                        f"Stock information for {raw_data['symbol']}:\n"
                        f"Current price: ${raw_data['price']}\n"
                        f"Change: {raw_data['change']} ({raw_data['change_percent']})\n"
                        f"Volume: {raw_data['volume']}\n"
                        f"Day's range: ${raw_data['low']} - ${raw_data['high']}\n"
                        f"Latest trading day: {raw_data['latest_trading_day']}"
                    ),
                    "data": raw_data,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Error fetching stock data: {result['message']}",
                }

        # For any other tools, just return whatever the tool returned
        try:
            # Call the tool's execute method
            result = self.mcp_server.execute_tool(tool_name, params)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error executing {tool_name}: {str(e)}",
            }

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
