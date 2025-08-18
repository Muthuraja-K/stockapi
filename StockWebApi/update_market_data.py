#!/usr/bin/env python3
"""
Script to directly update stockhistorymarketdata.json with corrected market cap formatting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_history_operations import stock_history_ops
from utils import format_finviz_market_cap

def update_market_data():
    """Update the stockhistorymarketdata.json file with corrected market cap formatting"""
    
    print("Starting market data update...")
    
    try:
        # Force populate market data with corrected formatting
        success = stock_history_ops.populate_stock_market_data()
        
        if success:
            print("✅ Market data updated successfully!")
            print("Market cap values should now show correct formatting (e.g., $3.43T for AAPL)")
        else:
            print("❌ Failed to update market data")
            return False
            
    except Exception as e:
        print(f"❌ Error updating market data: {e}")
        return False
    
    return True

if __name__ == "__main__":
    update_market_data()
