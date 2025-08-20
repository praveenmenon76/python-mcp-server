import logging
import os
from pathlib import Path

import requests
import yaml

from ..types.models import Tool

logger = logging.getLogger(__name__)


class StockPriceTool:
    """Tool for fetching stock price information using Alpha Vantage API."""

    def __init__(self):
        self.name = "StockPriceTool"
        self.description = "Get current stock price information for a symbol"
        self.version = "1.0.0"
        # Load API key from configuration
        self.api_key = self._load_api_key()
        self.base_url = "https://www.alphavantage.co/query"
        # Common company names to ticker symbols mapping
        self.company_to_ticker = {
            # Banks
            "citi": "C",
            "citigroup": "C",
            "citibank": "C",
            "bofa": "BAC",
            "bank of america": "BAC",
            "jpmorgan": "JPM",
            "jp morgan": "JPM",
            "wells fargo": "WFC",
            "goldman": "GS",
            "goldman sachs": "GS",
            # Tech companies
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "facebook": "META",
            "meta": "META",
            "netflix": "NFLX",
            "tesla": "TSLA",
            "nvidia": "NVDA",
            "ibm": "IBM",
            "intel": "INTC",
            "amd": "AMD",
            "oracle": "ORCL",
            "salesforce": "CRM",
            # Other major companies
            "walmart": "WMT",
            "disney": "DIS",
            "coca cola": "KO",
            "coke": "KO",
            "pepsi": "PEP",
            "pepsico": "PEP",
            "mcdonald's": "MCD",
            "mcdonalds": "MCD",
            "starbucks": "SBUX",
            "nike": "NKE",
            "boeing": "BA",
            "ge": "GE",
            "general electric": "GE",
            "ford": "F",
            "gm": "GM",
            "general motors": "GM",
        }

    def _load_api_key(self):
        """Load API key from environment variable or config file"""
        # First try to get from environment variable (more secure)
        api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
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
                    if tool.get("name") == "StockPriceTool":
                        return tool.get("settings", {}).get("api_key")

            logger.warning("Could not find API key in configuration file")
        except Exception as e:
            logger.error(f"Error loading API key from config: {str(e)}")

        # If all else fails, return None (API calls will fail)
        return None

    def _get_ticker_symbol(self, input_text):
        """
        Convert company names to ticker symbols when needed.

        Args:
            input_text (str): Company name or ticker symbol

        Returns:
            str: Proper ticker symbol
        """
        if not input_text:
            return None

        # If it's all uppercase and 1-5 characters, and it's not a known company name in uppercase,
        # assume it's already a valid ticker
        if input_text.isupper() and 1 <= len(input_text) <= 5:
            # Check if the uppercase input might be a company name
            if input_text.lower() in self.company_to_ticker:
                ticker = self.company_to_ticker[input_text.lower()]
                logger.info(
                    f"Converted uppercase '{input_text}' to ticker symbol '{ticker}'"
                )
                return ticker
            return input_text

        # Check if it's in our mapping (case insensitive)
        normalized = input_text.lower().strip()
        if normalized in self.company_to_ticker:
            ticker = self.company_to_ticker[normalized]
            logger.info(f"Converted '{input_text}' to ticker symbol '{ticker}'")
            return ticker

        # If not found in mapping, return the input capitalized as a fallback
        return input_text.upper()

    def get_stock_price(self, symbol):
        """
        Get current stock price for a symbol or company name.

        Args:
            symbol (str): Stock symbol (e.g., AAPL) or company name (e.g., Apple)

        Returns:
            dict: Stock price information or error message
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "API key not configured. Please set ALPHAVANTAGE_API_KEY environment variable.",
            }

        # Convert company name to ticker symbol if needed
        ticker = self._get_ticker_symbol(symbol)

        if not ticker:
            return {
                "status": "error",
                "message": "Please provide a valid company name or stock symbol.",
            }

        logger.info(f"Fetching stock data for ticker: {ticker}")

        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": ticker,
                "apikey": self.api_key,
            }

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()

            data = response.json()

            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                # Check if the quote has actual data
                if not quote.get("01. symbol"):
                    return {
                        "status": "error",
                        "message": f"No data found for '{symbol}' (ticker: {ticker}). Please check if the company name or symbol is correct.",
                    }

                # Format the response for easier consumption
                result = {
                    "symbol": quote.get("01. symbol", ticker),
                    "price": quote.get("05. price", "N/A"),
                    "change": quote.get("09. change", "N/A"),
                    "change_percent": quote.get("10. change percent", "N/A"),
                    "volume": quote.get("06. volume", "N/A"),
                    "latest_trading_day": quote.get("07. latest trading day", "N/A"),
                    "previous_close": quote.get("08. previous close", "N/A"),
                    "open": quote.get("02. open", "N/A"),
                    "high": quote.get("03. high", "N/A"),
                    "low": quote.get("04. low", "N/A"),
                }

                # Add a note if we converted from a company name
                if ticker != symbol:
                    result["original_query"] = symbol

                return {"status": "success", "data": result}
            else:
                # Check for API limit or other error messages
                if "Note" in data:
                    return {"status": "error", "message": data["Note"]}

                return {
                    "status": "error",
                    "message": f"No data found for '{symbol}' (ticker: {ticker}). Please check if the company name or symbol is correct.",
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Stock API request failed: {str(e)}")
            return {"status": "error", "message": f"API request failed: {str(e)}"}
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing stock data: {str(e)}")
            return {"status": "error", "message": f"Error processing data: {str(e)}"}

    def as_tool_model(self):
        """Convert to Tool model for registration"""
        return Tool(name=self.name, description=self.description, version=self.version)
