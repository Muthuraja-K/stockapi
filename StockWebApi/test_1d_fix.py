#!/usr/bin/env python3
"""Test script to verify 1D data is properly populated"""

import json
import os

def test_1d_data():
    """Test if 1D data is properly populated"""
    
    if not os.path.exists("stockhistory.json"):
        print("❌ stockhistory.json not found")
        return
    
    with open("stockhistory.json", 'r') as f:
        data = json.load(f)
    
    print(f"📊 Total stocks: {len(data)}")
    
    # Check first few stocks for 1D data
    for i, stock in enumerate(data[:5]):
        ticker = stock.get('ticker', 'Unknown')
        print(f"\n🔍 Stock {i+1}: {ticker}")
        
        # Check 1D data
        day_1d = stock.get('1D', {})
        if day_1d:
            print(f"   1D - Low: {day_1d.get('low')}")
            print(f"   1D - High: {day_1d.get('high')}")
            print(f"   1D - Open: {day_1d.get('open')}")
            print(f"   1D - Close: {day_1d.get('close')}")
            print(f"   1D - Percentage: {day_1d.get('percentage')}")
            print(f"   1D - High-Low %: {day_1d.get('high_low_percentage')}")
            print(f"   1D - Open-Close %: {day_1d.get('open_close_percentage')}")
        else:
            print("   ❌ 1D data missing")
        
        # Check 5D data for comparison
        day_5d = stock.get('5D', {})
        if day_5d:
            print(f"   5D - Low: {day_5d.get('low')}")
            print(f"   5D - High: {day_5d.get('high')}")
            print(f"   5D - Open: {day_5d.get('open')}")
            print(f"   5D - Close: {day_5d.get('close')}")
            print(f"   5D - Percentage: {day_5d.get('percentage')}")
            print(f"   5D - High-Low %: {day_5d.get('high_low_percentage')}")
            print(f"   5D - Open-Close %: {day_5d.get('open_close_percentage')}")
        else:
            print("   ❌ 5D data missing")

if __name__ == "__main__":
    test_1d_data()
