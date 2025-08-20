import importlib
import logging
from pathlib import Path

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
        return self.tool_instances.get(tool_name)

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
