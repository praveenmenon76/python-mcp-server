import sys
import os
from pathlib import Path

# Add the src directory to the Python path to allow imports
src_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(src_dir))

from src.mcp_server.tools.stock_price import StockPriceTool

def test_stock_price_tool():
    """Test the StockPriceTool by fetching data for a few stock symbols."""
    # Initialize the tool
    stock_tool = StockPriceTool()
    
    # Test with a few popular stock symbols
    symbols = ["AAPL", "MSFT", "GOOG", "AMZN"]
    
    print("Testing StockPriceTool:")
    print("-" * 50)
    
    for symbol in symbols:
        print(f"\nFetching data for {symbol}...")
        result = stock_tool.get_stock_price(symbol)
        
        if result["status"] == "success":
            data = result["data"]
            print(f"Symbol: {data['symbol']}")
            print(f"Current Price: {data['price']}")
            print(f"Change: {data['change']} ({data['change_percent']})")
            print(f"Volume: {data['volume']}")
            print(f"Latest Trading Day: {data['latest_trading_day']}")
            print(f"Day Range: {data['low']} - {data['high']}")
        else:
            print(f"Error: {result['message']}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_stock_price_tool()