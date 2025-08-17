#!/usr/bin/env python3
"""
Test script to verify Tiingo integration in earning summary component
"""

from earning_summary_optimized import get_enhanced_earnings_data
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tiingo_earning():
    """Test the Tiingo integration for earning summary"""
    
    ticker = "MDB"
    # Test with the specific date mentioned by the user
    earning_date_str = "06/04/2025 4:30:00 PM"
    
    print(f"🔍 Testing Tiingo integration for {ticker} on {earning_date_str}")
    print("=" * 60)
    
    try:
        # Call the enhanced earning data function
        result = get_enhanced_earnings_data(ticker, earning_date_str)
        
        print(f"✅ Function call successful")
        print(f"📊 Result type: {type(result)}")
        
        if isinstance(result, list) and len(result) > 0:
            print(f"📊 Found {len(result)} earning entries")
            
            # Look for the specific date
            target_date = "06/04/2025"
            target_entry = None
            
            for entry in result:
                if entry.get('earningDate') == target_date:
                    target_entry = entry
                    break
            
            if target_entry:
                print(f"\n🎯 Found entry for {target_date}:")
                print(f"   Ticker: {target_entry.get('ticker')}")
                print(f"   Close B4 Earning Price: {target_entry.get('closeB4EarningPrice')}")
                print(f"   Close B4 Earning Change: {target_entry.get('closeB4EarningChange')}")
                print(f"   After Earning Price: {target_entry.get('afterEarningPrice')}")
                print(f"   After Earning Change: {target_entry.get('afterEarningChange')}")
                
                # Check if we got actual data instead of N/A
                after_price = target_entry.get('afterEarningPrice')
                after_change = target_entry.get('afterEarningChange')
                
                if after_price != 'N/A' and after_change != 'N/A':
                    print(f"\n✅ SUCCESS: Tiingo provided actual data!")
                    print(f"   After Earning Price: {after_price}")
                    print(f"   After Earning Change: {after_change}")
                else:
                    print(f"\n⚠️  Still showing N/A - may need to check Tiingo data availability")
                    
            else:
                print(f"\n❌ No entry found for {target_date}")
                print(f"📅 Available dates:")
                for entry in result:
                    print(f"   {entry.get('earningDate')}: {entry.get('ticker')}")
        else:
            print(f"❌ No data returned")
            print(f"📊 Result: {result}")
            
    except Exception as e:
        print(f"❌ Error calling function: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tiingo_earning()
