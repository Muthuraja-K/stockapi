#!/usr/bin/env python3
"""
Test script to debug stock history percentage calculations
"""

from stock_history_operations import StockHistoryOperations
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_stock_history_percentages():
    """Test the stock history percentage calculations"""
    
    print("🔍 Testing Stock History Percentage Calculations")
    print("=" * 60)
    
    try:
        # Initialize stock history operations
        stock_ops = StockHistoryOperations()
        
        # Load current stock history data
        current_history = stock_ops.load_stock_history()
        
        if not current_history:
            print("❌ No stock history data found")
            return
        
        print(f"✅ Loaded {len(current_history)} stock history entries")
        
        # Check first few stocks for percentage values
        print(f"\n📊 Checking percentage values for first 3 stocks:")
        
        for i, stock in enumerate(current_history[:3]):
            ticker = stock.get('ticker', 'Unknown')
            print(f"\n🎯 {ticker}:")
            
            # Check each period
            periods = ['1D', '5D', '1M', '6M', '1Y']
            
            for period in periods:
                period_data = stock.get(period, {})
                percentage = period_data.get('percentage', 'N/A')
                low = period_data.get('low', 'N/A')
                high = period_data.get('high', 'N/A')
                
                print(f"   {period}: {percentage} (Low: {low}, High: {high})")
        
        # Check if we need to refresh the data
        print(f"\n🔍 Checking if data needs refresh...")
        
        # Try to populate fresh data
        print(f"📈 Attempting to populate fresh stock history data...")
        
        success = stock_ops.populate_stock_history()
        
        if success:
            print(f"✅ Successfully populated fresh stock history data")
            
            # Load the fresh data
            fresh_history = stock_ops.load_stock_history()
            
            if fresh_history:
                print(f"\n📊 Fresh data percentage values for first 3 stocks:")
                
                for i, stock in enumerate(fresh_history[:3]):
                    ticker = stock.get('ticker', 'Unknown')
                    print(f"\n🎯 {ticker}:")
                    
                    # Check each period
                    for period in periods:
                        period_data = stock.get(period, {})
                        percentage = period_data.get('percentage', 'N/A')
                        low = period_data.get('low', 'N/A')
                        high = period_data.get('high', 'N/A')
                        
                        print(f"   {period}: {percentage} (Low: {low}, High: {high})")
            else:
                print(f"❌ Failed to load fresh data")
        else:
            print(f"❌ Failed to populate fresh stock history data")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_stock_history_percentages()
