import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_history_operations import StockHistoryOperations
import json

def test_finviz_function():
    """Test the actual get_finviz_data_for_tickers function"""
    
    # Create instance
    operations = StockHistoryOperations()
    
    # Test with a single ticker
    tickers = ['OPEN']
    
    print(f"Testing get_finviz_data_for_tickers with tickers: {tickers}")
    
    try:
        # Call the actual function
        finviz_data = operations.get_finviz_data_for_tickers(tickers)
        
        print(f"Function returned: {finviz_data}")
        
        if finviz_data:
            for ticker, data in finviz_data.items():
                print(f"\nData for {ticker}:")
                for key, value in data.items():
                    print(f"  {key}: {value}")
        else:
            print("No data returned from function")
            
    except Exception as e:
        print(f"Error calling function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_finviz_function()
