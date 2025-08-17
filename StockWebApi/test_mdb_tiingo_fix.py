#!/usr/bin/env python3
"""
Test script for MDB on 06/04/2025 using Tiingo with improved rate limiting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from tiingo_service import tiingo_service

def test_mdb_tiingo_fix():
    """Test MDB on 06/04/2025 with Tiingo rate limiting fix"""
    
    ticker = "MDB"
    earning_date = datetime(2025, 6, 4)
    
    print(f"Testing {ticker} on {earning_date.strftime('%m/%d/%Y')} with Tiingo")
    print("=" * 60)
    
    # Check if Tiingo is available
    if not tiingo_service.is_available():
        print("❌ Tiingo service not available - no API key configured")
        return
    
    print(f"✅ Tiingo service available")
    print(f"📊 Remaining requests today: {tiingo_service.get_remaining_requests()}")
    
    # Reset rate limiting for testing
    tiingo_service.reset_rate_limiting()
    print(f"🔄 Rate limiting reset for testing")
    
    try:
        # Get 1-minute data for the earning date
        print(f"\n🔍 Fetching 1-minute data from Tiingo...")
        price_data = tiingo_service.get_1min_data_for_date(ticker, earning_date, prepost=True)
        
        if price_data is not None and not price_data.empty:
            print(f"✅ Successfully retrieved {len(price_data)} data points from Tiingo")
            
            # Show available times
            print(f"\n📅 Available times in the data:")
            unique_hours = sorted(price_data.index.hour.unique())
            for hour in unique_hours:
                hour_data = price_data[price_data.index.hour == hour]
                if len(hour_data) > 0:
                    print(f"   Hour {hour:02d}: {len(hour_data)} data points")
                    # Show first and last time in this hour
                    first_time = hour_data.index[0].strftime('%H:%M')
                    last_time = hour_data.index[-1].strftime('%H:%M')
                    print(f"      Range: {first_time} - {last_time}")
            
            # Look for specific times
            print(f"\n🔍 Searching for specific price points...")
            
            # Get 4:00 PM price (Close B4 Earning)
            price_400pm = None
            for timestamp, row in price_data.iterrows():
                if timestamp.hour == 16 and timestamp.minute == 0:
                    price_400pm = row['Close']
                    print(f"✅ Found EXACT 4:00 PM price: ${price_400pm:.2f} at {timestamp.strftime('%H:%M')}")
                    break
            
            if price_400pm is None:
                print("❌ 4:00 PM exact time not found, searching for closest fallback...")
                # Fallback to closest time around 4:00 PM
                for timestamp, row in price_data.iterrows():
                    if timestamp.hour == 16 and timestamp.minute >= 0 and timestamp.minute <= 10:
                        price_400pm = row['Close']
                        print(f"⚠️  Using fallback 4:00 PM price: ${price_400pm:.2f} at {timestamp.strftime('%H:%M')}")
                        break
            
            # Get 7:55 PM price (After Earning)
            price_755pm = None
            for timestamp, row in price_data.iterrows():
                if timestamp.hour == 19 and timestamp.minute == 55:
                    price_755pm = row['Close']
                    print(f"✅ Found EXACT 7:55 PM price: ${price_755pm:.2f} at {timestamp.strftime('%H:%M')}")
                    break
            
            if price_755pm is None:
                print("❌ 7:55 PM exact time not found, searching for closest fallback...")
                # Fallback to closest time around 7:55 PM
                for timestamp, row in price_data.iterrows():
                    if timestamp.hour == 19 and timestamp.minute >= 50:
                        price_755pm = row['Close']
                        print(f"⚠️  Using fallback 7:55 PM price: ${price_755pm:.2f} at {timestamp.strftime('%H:%M')}")
                        break
            
            # If still no 7:55 PM price, try to find any after-hours price after 4:00 PM
            if price_755pm is None:
                print(f"🔍 7:55 PM not found, searching for any after-hours price after 4:00 PM...")
                for timestamp, row in price_data.iterrows():
                    if timestamp.hour >= 17:  # After 5 PM
                        price_755pm = row['Close']
                        print(f"⚠️  Using after-hours fallback price: ${price_755pm:.2f} at {timestamp.strftime('%H:%M')}")
                        break
            
            # Calculate the correct after earning change
            if price_400pm is not None and price_755pm is not None:
                print(f"\n📊 After Earning Calculation:")
                print(f"   4:00 PM Price: ${price_400pm:.2f}")
                print(f"   7:55 PM Price: ${price_755pm:.2f}")
                
                # Correct calculation: (7:55 PM - 4:00 PM) / 4:00 PM * 100
                change_pct = ((price_755pm - price_400pm) / price_400pm) * 100
                after_earning_change = f"{change_pct:+.2f}%"
                
                print(f"   Change: {after_earning_change}")
                print(f"   Formula: (${price_755pm:.2f} - ${price_400pm:.2f}) / ${price_400pm:.2f} * 100 = {change_pct:.2f}%")
                
                # Check if this matches the expected values
                if abs(price_400pm - 199.73) < 1 and abs(price_755pm - 225.38) < 1:
                    print(f"\n🎯 MATCH FOUND! This appears to be the earnings date you're looking for!")
                    print(f"   Expected: 4:00 PM = $199.73, 7:55 PM = $225.38")
                    print(f"   Actual:   4:00 PM = ${price_400pm:.2f}, 7:55 PM = ${price_755pm:.2f}")
                    print(f"   Expected calculation: (225.38 - 199.73) / 199.73 * 100 = +12.85%")
                    print(f"   Actual calculation:  (${price_755pm:.2f} - ${price_400pm:.2f}) / ${price_400pm:.2f} * 100 = {change_pct:.2f}%")
                else:
                    print(f"\n⚠️  Prices don't match expected values:")
                    print(f"   Expected: 4:00 PM = $199.73, 7:55 PM = $225.38")
                    print(f"   Actual:   4:00 PM = ${price_400pm:.2f}, 7:55 PM = ${price_755pm:.2f}")
                    print(f"   Difference: 4:00 PM = ${abs(price_400pm - 199.73):.2f}, 7:55 PM = ${abs(price_755pm - 225.38):.2f}")
                
            else:
                print(f"\n❌ Missing price data:")
                print(f"   4:00 PM price: {price_400pm}")
                print(f"   7:55 PM price: {price_755pm}")
                
                # Show available times around these hours
                if price_400pm is None:
                    print(f"\n📅 Available times around 4:00 PM:")
                    for timestamp, row in price_data.iterrows():
                        if timestamp.hour == 16:
                            print(f"   {timestamp.strftime('%H:%M')}: ${row['Close']:.2f}")
                
                if price_755pm is None:
                    print(f"\n📅 Available times around 7:55 PM:")
                    for timestamp, row in price_data.iterrows():
                        if timestamp.hour == 19:
                            print(f"   {timestamp.strftime('%H:%M')}: ${row['Close']:.2f}")
                
                # Also show any after-hours data
                print(f"\n📅 After-hours data available:")
                for timestamp, row in price_data.iterrows():
                    if timestamp.hour >= 17:  # After 5 PM
                        print(f"   {timestamp.strftime('%H:%M')}: ${row['Close']:.2f}")
            
        else:
            print(f"❌ No data returned from Tiingo")
            
    except Exception as e:
        print(f"❌ Error testing Tiingo service: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"\n📊 Final rate limiting status:")
    print(f"   Requests made: {tiingo_service.requests_made}")
    print(f"   Remaining requests: {tiingo_service.get_remaining_requests()}")

if __name__ == "__main__":
    test_mdb_tiingo_fix()
