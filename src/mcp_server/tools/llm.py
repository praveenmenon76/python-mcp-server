# Use absolute import for Python's built-in types module
import builtins
import json
import logging
import os
import sys  # Added for absolute import
import types as pytypes
from pathlib import Path

import requests
import yaml

from ..types.models import Tool

logger = logging.getLogger(__name__)


class LLMTool:
    """Tool for connecting to LLM APIs to process natural language requests."""

    def __init__(self):
        self.name = "LLMTool"
        self.description = "Process natural language using an LLM API"
        self.version = "1.0.0"
        # Load API settings from configuration
        self.settings = self._load_settings()
        self.provider = self.settings.get("provider", "openai")
        self.api_key = self._clean_api_key(self.settings.get("api_key"))
        self.model = self.settings.get("model", "gpt-3.5-turbo")
        self.enabled = self.settings.get("enabled", True)

        if not self.enabled:
            logger.info("LLM Tool is disabled in configuration")
        elif not self.api_key:
            logger.warning("No API key configured for LLM Tool")
        else:
            logger.info(
                f"LLM Tool initialized with provider: {self.provider}, model: {self.model}"
            )
            if self.api_key:
                # Log first and last few characters of API key for debugging
                masked_key = (
                    f"{self.api_key[:5]}...{self.api_key[-4:]}"
                    if len(self.api_key) > 10
                    else "***"
                )
                logger.debug(
                    f"API key format: {masked_key}, length: {len(self.api_key)}"
                )

        # API endpoints for different providers
        self.endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "azure": self.settings.get("azure_endpoint"),
            "anthropic": "https://api.anthropic.com/v1/messages",
        }

    def _clean_api_key(self, api_key):
        """Clean API key by removing quotes, whitespace, etc."""
        if not api_key:
            return None

        # Remove quotes and whitespace
        return api_key.strip().strip("\"'")

    def _load_settings(self):
        """Load LLM settings from environment variables or config file"""
        settings = {
            "provider": os.environ.get("LLM_PROVIDER", "openai"),
            "api_key": os.environ.get("LLM_API_KEY")
            or os.environ.get("OPENAI_API_KEY"),
            "model": os.environ.get("LLM_MODEL", "gpt-3.5-turbo"),
            "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
            "enabled": os.environ.get("LLM_ENABLED", "true").lower() == "true",
        }

        # Fall back to config file if environment variables are not set
        try:
            # Navigate to the config directory
            src_dir = Path(__file__).resolve().parent.parent.parent
            config_path = src_dir / "config" / "tools.yaml"

            if config_path.exists():
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)

                # Look for LLM settings in the tools config
                for tool in config.get("tools", []):
                    if tool.get("name") == "LLMTool":
                        tool_settings = tool.get("settings", {})
                        # Only update if environment variables weren't set
                        if not settings["api_key"]:
                            settings["api_key"] = tool_settings.get("api_key")
                        if (
                            settings["provider"] == "openai"
                            and "provider" in tool_settings
                        ):
                            settings["provider"] = tool_settings.get("provider")
                        if (
                            settings["model"] == "gpt-3.5-turbo"
                            and "model" in tool_settings
                        ):
                            settings["model"] = tool_settings.get("model")
                        if (
                            not settings["azure_endpoint"]
                            and "azure_endpoint" in tool_settings
                        ):
                            settings["azure_endpoint"] = tool_settings.get(
                                "azure_endpoint"
                            )
                        if "enabled" in tool_settings:
                            settings["enabled"] = tool_settings.get("enabled")
                        break

        except Exception as e:
            logger.error(f"Error loading LLM settings from config: {str(e)}")

        return settings

    def process_query(self, query, context=None, tools_info=None):
        """
        Process a natural language query using the configured LLM.

        Args:
            query (str): The user's natural language query
            context (dict, optional): Additional context to provide to the LLM
            tools_info (list, optional): Information about available tools

        Returns:
            dict: The processed result with extracted intent and parameters
        """
        # Check if the tool is enabled
        if not self.enabled:
            return {
                "status": "error",
                "message": "LLM Tool is disabled in configuration",
            }

        # Check if API key is configured
        if not self.api_key:
            return {
                "status": "error",
                "message": "LLM API key not configured. Please set LLM_API_KEY environment variable or update the config.",
            }

        # Test API key validity first
        key_test = self.test_api_key()
        if key_test["status"] == "error":
            return key_test

        # Construct the system prompt with tool information
        system_prompt = self._build_system_prompt(tools_info)

        # Construct the user message with the query and context
        user_message = self._build_user_message(query, context)

        try:
            # Call the appropriate LLM API based on the provider
            if self.provider == "openai":
                result = self._call_openai_api(system_prompt, user_message)
            elif self.provider == "azure":
                result = self._call_azure_api(system_prompt, user_message)
            elif self.provider == "anthropic":
                result = self._call_anthropic_api(system_prompt, user_message)
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported LLM provider: {self.provider}",
                }

            return result
        except requests.exceptions.RequestException as e:
            # More detailed error logging for debugging API issues
            logger.error(f"LLM API request failed: {str(e)}")

            # Add more detailed error information
            error_details = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    response_json = e.response.json()
                    error_details = (
                        f"{error_details} - Response: {json.dumps(response_json)}"
                    )
                except:
                    error_details = f"{error_details} - Status code: {e.response.status_code}, Content: {e.response.text[:200]}"

            return {
                "status": "error",
                "message": f"LLM API request failed: {error_details}",
            }
        except Exception as e:
            logger.error(f"Error in LLM processing: {str(e)}")
            return {"status": "error", "message": f"Error in LLM processing: {str(e)}"}

    def _build_system_prompt(self, tools_info):
        """Build the system prompt with information about available tools"""
        prompt = (
            "You are a helpful assistant that interprets user queries for an MCP (Model Context Protocol) server. "
            "Your task is to determine the user's intent and extract relevant parameters from their natural language query."
        )

        if tools_info:
            prompt += "\n\nAvailable tools:"
            for tool in tools_info:
                prompt += f"\n- {tool['name']}: {tool['description']}"

            prompt += (
                "\n\nFor each query, you should respond with a JSON object containing:"
                "\n- 'tool': The name of the tool to use"
                "\n- 'params': A dictionary of parameters to pass to the tool"
                "\n- 'confidence': A number between 0 and 1 indicating your confidence in this interpretation"
                "\n- 'explanation': A brief explanation of your reasoning"
                "\n\nIf you cannot determine the intent, respond with a JSON object with 'tool' set to 'unknown'."
            )

        return prompt

    def _build_user_message(self, query, context):
        """Build the user message with the query and context"""
        message = f"User query: {query}"

        if context:
            message += "\n\nAdditional context:"
            for key, value in context.items():
                message += f"\n- {key}: {value}"

        return message

    def _call_openai_api(self, system_prompt, user_message):
        """Call the OpenAI API to process the query"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.2,
        }

        # Log request details for debugging
        logger.debug(f"Making OpenAI API request to {self.endpoints['openai']}")
        logger.debug(f"Using model: {self.model}")

        response = requests.post(
            self.endpoints["openai"],
            headers=headers,
            json=data,
            timeout=30,  # Increased timeout for reliability
        )

        # Improved error handling with more detailed logging
        if response.status_code != 200:
            try:
                error_json = response.json()
                error_message = error_json.get("error", {}).get(
                    "message", "Unknown error"
                )
                error_type = error_json.get("error", {}).get(
                    "type", "Unknown error type"
                )
                logger.error(
                    f"OpenAI API error ({response.status_code}): {error_type} - {error_message}"
                )
                raise requests.exceptions.HTTPError(
                    f"OpenAI API error: {error_message}"
                )
            except json.JSONDecodeError:
                logger.error(
                    f"OpenAI API returned non-JSON response with status {response.status_code}"
                )
                response.raise_for_status()

        result = response.json()

        try:
            content = result["choices"][0]["message"]["content"]
            parsed_content = json.loads(content)
            return {"status": "success", "data": parsed_content}
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing OpenAI response: {str(e)}")
            return {
                "status": "error",
                "message": f"Error parsing LLM response: {str(e)}",
            }

    def _call_azure_api(self, system_prompt, user_message):
        """Call the Azure OpenAI API to process the query"""
        headers = {"Content-Type": "application/json", "api-key": self.api_key}

        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.2,
        }

        # Ensure the endpoint is set and properly formatted
        if not self.endpoints["azure"]:
            return {
                "status": "error",
                "message": "Azure OpenAI endpoint not configured",
            }

        # Azure endpoint needs to include the model name and api-version
        endpoint = self.endpoints["azure"]
        if not endpoint.endswith("completions"):
            endpoint = f"{endpoint}/openai/deployments/{self.model}/chat/completions?api-version=2023-05-15"

        response = requests.post(endpoint, headers=headers, json=data)

        response.raise_for_status()
        result = response.json()

        try:
            content = result["choices"][0]["message"]["content"]
            parsed_content = json.loads(content)
            return {"status": "success", "data": parsed_content}
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Azure response: {str(e)}")
            return {
                "status": "error",
                "message": f"Error parsing LLM response: {str(e)}",
            }

    def _call_anthropic_api(self, system_prompt, user_message):
        """Call the Anthropic API to process the query"""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": self.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        response = requests.post(
            self.endpoints["anthropic"], headers=headers, json=data
        )

        response.raise_for_status()
        result = response.json()

        try:
            content = result["content"][0]["text"]
            parsed_content = json.loads(content)
            return {"status": "success", "data": parsed_content}
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Anthropic response: {str(e)}")
            return {
                "status": "error",
                "message": f"Error parsing LLM response: {str(e)}",
            }

    def test_api_key(self):
        """
        Test the API key by making a simple request to the OpenAI API.

        Returns:
            dict: A dictionary with status and message indicating if the API key is valid
        """
        if not self.api_key:
            return {"status": "error", "message": "No API key configured"}

        if not self.enabled:
            return {
                "status": "error",
                "message": "LLM Tool is disabled in configuration",
            }

        try:
            # Different test approach based on provider
            if self.provider == "openai":
                # Use a simpler endpoint that doesn't consume as many tokens
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }

                # Simple request to models endpoint
                response = requests.get(
                    "https://api.openai.com/v1/models", headers=headers
                )

                # If we get a 401, the API key is invalid
                if response.status_code == 401:
                    error_message = "Invalid API key"
                    try:
                        error_data = response.json()
                        if "error" in error_data and "message" in error_data["error"]:
                            error_message = error_data["error"]["message"]
                    except:
                        pass

                    return {
                        "status": "error",
                        "message": f"Authentication failed: {error_message}",
                    }

                # Any other error
                response.raise_for_status()

                # If we get here, the API key is valid
                return {"status": "success", "message": "API key is valid"}

            elif self.provider == "azure":
                # Azure-specific endpoint test
                if not self.endpoints["azure"]:
                    return {
                        "status": "error",
                        "message": "Azure OpenAI endpoint not configured",
                    }

                headers = {"Content-Type": "application/json", "api-key": self.api_key}

                # For Azure, we can check the deployments endpoint
                response = requests.get(
                    f"{self.endpoints['azure']}/openai/deployments?api-version=2023-05-15",
                    headers=headers,
                )

                response.raise_for_status()
                return {
                    "status": "success",
                    "message": "API key is valid for Azure OpenAI",
                }

            elif self.provider == "anthropic":
                # Anthropic-specific endpoint test
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                }

                # Simple request to check auth
                response = requests.get(
                    "https://api.anthropic.com/v1/models", headers=headers
                )

                response.raise_for_status()
                return {
                    "status": "success",
                    "message": "API key is valid for Anthropic",
                }

            else:
                return {
                    "status": "error",
                    "message": f"Unsupported provider: {self.provider}",
                }

        except requests.exceptions.RequestException as e:
            error_details = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    response_json = e.response.json()
                    if "error" in response_json:
                        error_details = (
                            f"{error_details} - {json.dumps(response_json['error'])}"
                        )
                    else:
                        error_details = f"{error_details} - {json.dumps(response_json)}"
                except:
                    error_details = f"{error_details} - Status code: {e.response.status_code}, Content: {e.response.text[:200]}"

            return {"status": "error", "message": f"API test failed: {error_details}"}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error testing API key: {str(e)}",
            }

    def as_tool_model(self):
        """Convert to Tool model for registration"""
        return Tool(name=self.name, description=self.description, version=self.version)

    def process_enhanced_response(self, prompt, context):
        """
        Generate an enhanced, natural language response using the LLM.

        Args:
            prompt (str): Instructions for generating the enhanced response
            context (dict): Context information including tool response data

        Returns:
            dict: The enhanced response with natural language formatting
        """
        if not self.enabled:
            return {
                "status": "error",
                "message": "LLM Tool is disabled in configuration",
            }

        if not self.api_key:
            return {"status": "error", "message": "LLM API key not configured"}

        # Build the system message with instructions for response formatting
        system_message = (
            "You are a helpful assistant that generates natural, conversational responses. "
            "You should format the technical data into a friendly, conversational response. "
            f"{prompt}"
        )

        # Build the user message with context and data
        user_message = "Here is the context information:\n"

        # Add the user's original query
        user_message += f"User query: {context.get('user_query', 'Unknown query')}\n\n"

        # Add the tool response data
        user_message += f"Tool used: {context.get('tool_name', 'Unknown tool')}\n"
        user_message += (
            f"Response status: {context.get('response_status', 'unknown')}\n"
        )

        # Add the raw message from the tool response if available
        if context.get("response_message"):
            user_message += (
                f"Raw response message: {context.get('response_message')}\n\n"
            )

        # Add raw data if available
        if context.get("response_data"):
            user_message += (
                f"Response data: {json.dumps(context.get('response_data'))}\n\n"
            )
        elif (
            context.get("tool_response")
            and isinstance(context.get("tool_response"), dict)
            and context.get("tool_response").get("data")
        ):
            user_message += f"Response data: {json.dumps(context.get('tool_response').get('data'))}\n\n"

        user_message += "Generate a natural, conversational response that includes all the relevant information."

        try:
            # Call the appropriate LLM API based on the provider
            if self.provider == "openai":
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }

                data = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.7,  # Higher temperature for more creative responses
                }

                response = requests.post(
                    self.endpoints["openai"], headers=headers, json=data, timeout=30
                )

                if response.status_code != 200:
                    logger.error(
                        f"OpenAI API error: {response.status_code} - {response.text}"
                    )
                    return {
                        "status": "error",
                        "message": f"LLM API error: {response.status_code}",
                    }

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                return {"status": "success", "message": content}

            elif self.provider == "azure":
                # Azure implementation similar to OpenAI
                headers = {"Content-Type": "application/json", "api-key": self.api_key}

                data = {
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.7,
                }

                endpoint = self.endpoints["azure"]
                if not endpoint.endswith("completions"):
                    endpoint = f"{endpoint}/openai/deployments/{self.model}/chat/completions?api-version=2023-05-15"

                response = requests.post(endpoint, headers=headers, json=data)

                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                return {"status": "success", "message": content}

            elif self.provider == "anthropic":
                # Anthropic implementation
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                }

                data = {
                    "model": self.model,
                    "system": system_message,
                    "messages": [{"role": "user", "content": user_message}],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                }

                response = requests.post(
                    self.endpoints["anthropic"], headers=headers, json=data
                )

                response.raise_for_status()
                result = response.json()
                content = result["content"][0]["text"]

                return {"status": "success", "message": content}

            else:
                return {
                    "status": "error",
                    "message": f"Unsupported LLM provider: {self.provider}",
                }

        except Exception as e:
            logger.error(f"Error generating enhanced response: {str(e)}")
            return {
                "status": "error",
                "message": f"Error generating enhanced response: {str(e)}",
            }
