import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_history_operations import StockHistoryOperations

def test_market_data_population():
    """Test the fixed populate_stock_market_data function"""
    
    print("Testing the fixed populate_stock_market_data function...")
    
    try:
        # Create instance
        operations = StockHistoryOperations()
        
        # Call the function
        result = operations.populate_stock_market_data()
        
        print(f"Function result: {result}")
        
        if result:
            print("✅ Market data population successful!")
            
            # Check the generated file
            if os.path.exists("stockhistorymarketdata.json"):
                print("✅ stockhistorymarketdata.json file created")
                
                # Read and check a sample entry
                import json
                with open("stockhistorymarketdata.json", 'r') as f:
                    data = json.load(f)
                
                if data:
                    sample = data[0]
                    print(f"\n📊 Sample entry for {sample.get('ticker')}:")
                    print(f"  Market Cap: {sample.get('market_cap')}")
                    print(f"  Price: {sample.get('price')}")
                    print(f"  After Hour Price: {sample.get('after_hour_price')}")
                    print(f"  Volume: {sample.get('volume')}")
                    print(f"  Earning Date: {sample.get('earning_date')}")
                    
                    # Check if Finviz data is properly populated
                    if sample.get('after_hour_price') != 'N/A':
                        print("✅ After Hour Price is now populated!")
                    else:
                        print("❌ After Hour Price is still N/A")
                        
                    if sample.get('market_cap') != 'N/A':
                        print("✅ Market Cap is now populated!")
                    else:
                        print("❌ Market Cap is still N/A")
                else:
                    print("❌ No data in the file")
            else:
                print("❌ stockhistorymarketdata.json file not created")
        else:
            print("❌ Market data population failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_market_data_population()
