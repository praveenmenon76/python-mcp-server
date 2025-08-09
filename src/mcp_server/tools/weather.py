import requests
import logging
import os
import yaml
from pathlib import Path
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
            return {"status": "error", "message": "API key not configured. Please set OPENWEATHERMAP_API_KEY environment variable."}
            
        try:
            params = {
                "q": location,
                "appid": self.api_key,
                "units": units
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if response.status_code == 200:
                # Format the response for easier consumption
                result = {
                    "location": f"{data['name']}, {data['sys']['country']}",
                    "description": data['weather'][0]['description'],
                    "temperature": f"{data['main']['temp']}°{'C' if units == 'metric' else 'F'}",
                    "feels_like": f"{data['main']['feels_like']}°{'C' if units == 'metric' else 'F'}",
                    "humidity": f"{data['main']['humidity']}%",
                    "wind": f"{data['wind']['speed']} {'m/s' if units == 'metric' else 'mph'}",
                    "timestamp": data['dt']
                }
                return {"status": "success", "data": result}
            else:
                return {"status": "error", "message": "Failed to fetch weather data"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API request failed: {str(e)}")
            return {"status": "error", "message": f"API request failed: {str(e)}"}
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing weather data: {str(e)}")
            return {"status": "error", "message": f"Error processing data: {str(e)}"}
    
    def as_tool_model(self):
        """Convert to Tool model for registration"""
        return Tool(
            name=self.name,
            description=self.description,
            version=self.version
        )