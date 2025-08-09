import sys
import os
from pathlib import Path

# Add the src directory to the Python path to allow imports
src_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(src_dir))

from src.mcp_server.server import MCPServer

def test_stock_price_tool_integration():
    """Test that StockPriceTool is properly registered with the MCP server."""
    # Initialize the MCP server
    server = MCPServer()
    server.start()
    
    print("Testing StockPriceTool Integration with MCP Server:")
    print("-" * 60)
    
    # Check if StockPriceTool is registered
    registered_tools = server.get_registered_tools()
    print(f"Registered tools: {registered_tools}")
    
    if "StockPriceTool" in registered_tools:
        print("\nStockPriceTool is successfully registered!")
        
        # Get the tool instance
        stock_tool = server.get_tool_instance("StockPriceTool")
        
        if stock_tool:
            print("Successfully retrieved StockPriceTool instance")
            
            # Test the tool with a sample stock symbol
            symbol = "AAPL"
            print(f"\nTesting with symbol: {symbol}")
            
            result = stock_tool.get_stock_price(symbol)
            if result["status"] == "success":
                data = result["data"]
                print(f"Symbol: {data['symbol']}")
                print(f"Current Price: {data['price']}")
                print(f"Change: {data['change']} ({data['change_percent']})")
                print(f"Volume: {data['volume']}")
            else:
                print(f"Error: {result['message']}")
        else:
            print("Error: Could not retrieve StockPriceTool instance")
    else:
        print("Error: StockPriceTool is not registered with the server")
    
    print("\nTest completed.")
    server.stop()

if __name__ == "__main__":
    test_stock_price_tool_integration()