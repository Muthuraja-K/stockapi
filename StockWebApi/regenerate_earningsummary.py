#!/usr/bin/env python3
"""
Simple script to regenerate earningsummary.json with isleverage=false filter
"""

import json
from earning_summary_file_manager import populate_initial_earning_summary

def main():
    print("Starting regeneration of earningsummary.json with comprehensive filtering...")
    print("This will process only regular stock tickers (no leveraged ETFs, no crypto pairs)...")
    
    try:
        success = populate_initial_earning_summary()
        if success:
            print("✅ Successfully regenerated earningsummary.json with non-leveraged stocks only!")
            
            # Verify the result
            with open('earningsummary.json', 'r') as f:
                data = json.load(f)
            print(f"📊 File contains {len(data)} stocks")
            
            # Check for any leveraged stocks or crypto pairs (should be 0)
            excluded_count = 0
            for stock in data:
                ticker = stock['ticker']
                if (any(leveraged_ticker in ticker for leveraged_ticker in ['IONX', 'RGTX', 'QBTX', 'QUBX', 'ARCX']) or
                    ticker.endswith('-USD') or
                    any(pattern in ticker for pattern in ['2X', '3X', 'LONG', 'SHORT', 'BULL', 'BEAR'])):
                    excluded_count += 1
            
            if excluded_count == 0:
                print("✅ Confirmed: No leveraged stocks or crypto pairs in the file")
            else:
                print(f"⚠️ Warning: Found {excluded_count} excluded instruments")
                
        else:
            print("❌ Failed to regenerate earningsummary.json")
            
    except Exception as e:
        print(f"❌ Error during regeneration: {e}")

if __name__ == "__main__":
    main()
