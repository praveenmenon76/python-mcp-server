import logging
import os
import re
from pathlib import Path

import requests
import yaml

from ..types.models import Tool

logger = logging.getLogger(__name__)


class WeatherTool:
    """Tool for fetching weather information from OpenWeatherMap API."""

    def __init__(self):
        self.name = "WeatherTool"
        self.description = "Get current weather information for a location"
        self.version = "1.0.0"
        # Load API key from configuration instead of hardcoding
        self.api_key = self._load_api_key()
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        # Common city name corrections
        self.city_corrections = {
            "newyork": "New York",
            "nyc": "New York",
            "sf": "San Francisco",
            "la": "Los Angeles",
            "vegas": "Las Vegas",
            "dc": "Washington DC",
        }

    def _load_api_key(self):
        """Load API key from environment variable or config file"""
        # First try to get from environment variable (more secure)
        api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
        if api_key:
            return api_key

        # Fall back to config file if environment variable is not set
        try:
            # Navigate to the config directory
            src_dir = Path(__file__).resolve().parent.parent.parent
            config_path = src_dir / "config" / "tools.yaml"

            if config_path.exists():
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)

                # Look for the API key in the tools config
                for tool in config.get("tools", []):
                    if tool.get("name") == "WeatherTool":
                        return tool.get("settings", {}).get("api_key")

            logger.warning("Could not find API key in configuration file")
        except Exception as e:
            logger.error(f"Error loading API key from config: {str(e)}")

        # If all else fails, return None (API calls will fail)
        return None

    def _preprocess_location(self, location):
        """Preprocess location string to handle common city name formats"""
        if not location:
            return location

        # Convert to lowercase for comparison and remove extra spaces
        processed = location.strip().lower()

        # Check for common city name corrections
        if processed in self.city_corrections:
            return self.city_corrections[processed]

        # Fix concatenated city names (like "newyork" -> "New York")
        for wrong, correct in self.city_corrections.items():
            if processed == wrong.replace(" ", ""):
                return correct

        # Properly capitalize city names
        # This handles "new york" -> "New York"
        words = processed.split()
        if len(words) > 1:
            return " ".join(word.capitalize() for word in words)

        # Default to capitalizing first letter for single-word cities
        return location.strip().capitalize()

    def get_weather(self, location, units="metric"):
        """
        Get current weather for a location.

        Args:
            location (str): City name or city,country code
            units (str): Units of measurement: 'metric' (Celsius) or 'imperial' (Fahrenheit)

        Returns:
            dict: Weather information or error message
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "API key not configured. Please set OPENWEATHERMAP_API_KEY environment variable.",
            }

        # Preprocess the location to handle common formats
        processed_location = self._preprocess_location(location)
        logger.info(
            f"Looking up weather for: {processed_location} (original: {location})"
        )

        try:
            params = {"q": processed_location, "appid": self.api_key, "units": units}

            response = requests.get(self.base_url, params=params)

            if response.status_code == 404:
                # City not found - provide a helpful message
                logger.warning(f"City not found: {processed_location}")
                return {
                    "status": "error",
                    "message": f"Could not find weather data for '{location}'. Please check the spelling or try a different city.",
                }

            # For other errors, raise_for_status will trigger the exception handler
            response.raise_for_status()

            data = response.json()

            # Format the response for easier consumption
            result = {
                "location": data["name"],
                "country": data["sys"]["country"],
                "weather_description": data["weather"][0]["description"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "timestamp": data["dt"],
            }
            return {"status": "success", "data": result}

        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API request failed: {str(e)}")
            return {"status": "error", "message": f"API request failed: {str(e)}"}
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing weather data: {str(e)}")
            return {"status": "error", "message": f"Error processing data: {str(e)}"}

    def as_tool_model(self):
        """Convert to Tool model for registration"""
        return Tool(name=self.name, description=self.description, version=self.version)
