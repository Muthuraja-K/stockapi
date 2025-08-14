#!/usr/bin/env python3
"""
Test script to verify AH (After Hours) data functionality
"""

import json
from stock_history_operations import stock_history_ops

def test_ah_data():
    """Test AH data functionality"""
    print("Testing AH (After Hours) data functionality...")
    
    # Test 1: Check if AH data is in the combined data
    print("\n1. Testing combined stock data...")
    combined_data = stock_history_ops.get_combined_stock_data()
    
    if combined_data and combined_data.get('results'):
        print(f"Found {len(combined_data['results'])} stocks in combined data")
        
        # Check first few stocks for AH data
        for i, stock in enumerate(combined_data['results'][:5]):
            print(f"\nStock {i+1}: {stock['ticker']}")
            print(f"  Current Price: {stock.get('current_price', 'N/A')}")
            print(f"  AH Price: {stock.get('ah_price', 'N/A')}")
            print(f"  AH Change: {stock.get('ah_change', 'N/A')}")
    else:
        print("No combined data found")
    
    # Test 2: Check market data directly
    print("\n2. Testing market data directly...")
    market_data = stock_history_ops.load_stock_market_data()
    
    if market_data:
        print(f"Found {len(market_data)} stocks in market data")
        
        # Check first few stocks for AH data
        for i, stock in enumerate(market_data[:5]):
            print(f"\nMarket Data {i+1}: {stock['ticker']}")
            print(f"  Current Price: {stock.get('current_price', 'N/A')}")
            print(f"  AH Price: {stock.get('ah_price', 'N/A')}")
            print(f"  AH Change: {stock.get('ah_change', 'N/A')}")
    else:
        print("No market data found")
    
    # Test 3: Check if we can fetch new AH data from Finviz
    print("\n3. Testing Finviz AH data fetching...")
    try:
        # Test with a few tickers
        test_tickers = ['AAPL', 'MSFT', 'GOOGL']
        finviz_data = stock_history_ops.get_finviz_data_for_tickers(test_tickers)
        
        if finviz_data:
            print(f"Successfully fetched Finviz data for {len(finviz_data)} tickers")
            for ticker, data in finviz_data.items():
                print(f"\nFinviz Data for {ticker}:")
                print(f"  Price: {data.get('Price', 'N/A')}")
                print(f"  AH Price: {data.get('AH Price', 'N/A')}")
                print(f"  AH Change: {data.get('AH Change', 'N/A')}")
        else:
            print("No Finviz data fetched")
    except Exception as e:
        print(f"Error fetching Finviz data: {e}")
    
    print("\nAH data testing completed!")

if __name__ == "__main__":
    test_ah_data()
