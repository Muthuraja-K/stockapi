#!/usr/bin/env python3
"""
Test script to verify the new sentiment data structure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sentiment_analysis import get_sentiment_analysis
import json

def test_new_sentiment_structure():
    """Test the new sentiment data structure"""
    print("Testing new sentiment data structure...")
    
    # Test with a sample ticker
    ticker = "AAPL"
    print(f"\nTesting ticker: {ticker}")
    
    try:
        # Get sentiment data
        sentiment_data = get_sentiment_analysis(ticker)
        
        # Check if new fields exist
        print("\n✅ Sentiment data retrieved successfully")
        
        # Check major holders
        if 'major_holders' in sentiment_data:
            print("✅ Major holders data present")
            major = sentiment_data['major_holders']
            print(f"   - Insiders: {major['insider_percentage']}%")
            print(f"   - Institutions: {major['institutional_percentage']}%")
            print(f"   - Retail: {major['retail_percentage']}%")
            print(f"   - Total: {major['total_percentage']}%")
        else:
            print("❌ Major holders data missing")
        
        # Check top institutional holders
        if 'top_institutional_holders' in sentiment_data:
            print("✅ Top institutional holders data present")
            inst = sentiment_data['top_institutional_holders']
            print(f"   - Total institutions: {inst['total_institutions']}")
            print(f"   - Total percentage: {inst['total_percentage_held']}%")
            print(f"   - Sample holder: {inst['holdings'][0]['holder']}")
            print(f"   - Sample date: {inst['holdings'][0]['date_reported']}")
        else:
            print("❌ Top institutional holders data missing")
        
        # Check top mutual fund holders
        if 'top_mutual_fund_holders' in sentiment_data:
            print("✅ Top mutual fund holders data present")
            mf = sentiment_data['top_mutual_fund_holders']
            print(f"   - Total funds: {mf['total_funds']}")
            print(f"   - Total percentage: {mf['total_percentage_held']}%")
            print(f"   - Sample fund: {mf['holdings'][0]['holder']}")
            print(f"   - Sample date: {mf['holdings'][0]['date_reported']}")
        else:
            print("❌ Top mutual fund holders data missing")
        
        # Print full structure for verification
        print("\n📋 Full data structure keys:")
        for key in sentiment_data.keys():
            print(f"   - {key}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_sentiment_structure()
