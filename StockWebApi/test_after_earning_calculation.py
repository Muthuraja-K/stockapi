#!/usr/bin/env python3
"""
Test script to verify the after earning calculation for MDB on a recent date
"""

import yfinance as yf
from datetime import datetime, timedelta
import math

def test_mdb_after_earning_calculation():
    """Test the after earning calculation for MDB on a recent date"""
    
    ticker = "MDB"
    # Use a recent date instead of future date
    earning_date = datetime.now() - timedelta(days=7)  # 7 days ago
    
    print(f"Testing After Earning calculation for {ticker} on {earning_date.strftime('%m/%d/%Y')}")
    print("=" * 60)
    
    # Get ticker object
    ticker_obj = yf.Ticker(ticker)
    
    # Get intraday data for the earning date
    start_date = earning_date - timedelta(days=1)
    end_date = earning_date + timedelta(days=1)
    
    print(f"Fetching intraday data from {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}")
    
    try:
        # Get 1-minute intraday data with prepost=True to include after-hours
        earning_date_data = ticker_obj.history(
            start=start_date,
            end=end_date,
            interval='1m',
            prepost=True
        )
        
        print(f"Retrieved {len(earning_date_data)} data points")
        
        if earning_date_data.empty:
            print("❌ No intraday data available")
            return
        
        # Show the data structure
        print(f"\nData columns: {earning_date_data.columns.tolist()}")
        print(f"First few rows:")
        print(earning_date_data.head())
        
        # Show available times
        print(f"\n📅 Available times in the data:")
        unique_hours = sorted(earning_date_data.index.hour.unique())
        for hour in unique_hours:
            hour_data = earning_date_data[earning_date_data.index.hour == hour]
            if len(hour_data) > 0:
                print(f"   Hour {hour:02d}: {len(hour_data)} data points")
                # Show first and last time in this hour
                first_time = hour_data.index[0].strftime('%H:%M')
                last_time = hour_data.index[-1].strftime('%H:%M')
                print(f"      Range: {first_time} - {last_time}")
        
        # Look for specific times
        print(f"\nSearching for specific price points...")
        
        # Get 4:00 PM price (Close B4 Earning)
        price_400pm = None
        for timestamp, row in earning_date_data.iterrows():
            if timestamp.hour == 16 and timestamp.minute == 0:
                price_400pm = row['Close']
                print(f"✅ Found EXACT 4:00 PM price: ${price_400pm:.2f} at {timestamp.strftime('%H:%M')}")
                break
        
        if price_400pm is None:
            print("❌ 4:00 PM exact time not found, searching for closest fallback...")
            # Fallback to closest time around 4:00 PM
            for timestamp, row in earning_date_data.iterrows():
                if timestamp.hour == 16 and timestamp.minute >= 0 and timestamp.minute <= 10:
                    price_400pm = row['Close']
                    print(f"⚠️  Using fallback 4:00 PM price: ${price_400pm:.2f} at {timestamp.strftime('%H:%M')}")
                    break
        
        # Get 7:55 PM price (After Earning)
        price_755pm = None
        for timestamp, row in earning_date_data.iterrows():
            if timestamp.hour == 19 and timestamp.minute == 55:
                price_755pm = row['Close']
                print(f"✅ Found EXACT 7:55 PM price: ${price_755pm:.2f} at {timestamp.strftime('%H:%M')}")
                break
        
        if price_755pm is None:
            print("❌ 7:55 PM exact time not found, searching for closest fallback...")
            # Fallback to closest time around 7:55 PM
            for timestamp, row in earning_date_data.iterrows():
                if timestamp.hour == 19 and timestamp.minute >= 50:
                    price_755pm = row['Close']
                    print(f"⚠️  Using fallback 7:55 PM price: ${price_755pm:.2f} at {timestamp.strftime('%H:%M')}")
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
            
        else:
            print(f"\n❌ Missing price data:")
            print(f"   4:00 PM price: {price_400pm}")
            print(f"   7:55 PM price: {price_755pm}")
            
            # Show available times around these hours
            print(f"\n📅 Available times around 4:00 PM:")
            for timestamp, row in earning_date_data.iterrows():
                if timestamp.hour == 16:
                    print(f"   {timestamp.strftime('%H:%M')}: ${row['Close']:.2f}")
            
            print(f"\n📅 Available times around 7:55 PM:")
            for timestamp, row in earning_date_data.iterrows():
                if timestamp.hour == 19:
                    print(f"   {timestamp.strftime('%H:%M')}: ${row['Close']:.2f}")
        
        # Also check daily data fallback
        print(f"\n📈 Daily Data Fallback Check:")
        try:
            daily_data = ticker_obj.history(
                start=earning_date - timedelta(days=1), 
                end=earning_date + timedelta(days=1), 
                interval='1d', 
                prepost=True
            )
            
            if not daily_data.empty and len(daily_data) >= 1:
                current_day_close = daily_data.iloc[-1]['Close']
                current_day_open = daily_data.iloc[-1]['Open']
                
                print(f"   Daily Open: ${current_day_open:.2f}")
                print(f"   Daily Close: ${current_day_close:.2f}")
                
                # This is the WRONG calculation that's being used as fallback
                wrong_change_pct = ((current_day_close - current_day_open) / current_day_open) * 100
                print(f"   WRONG Fallback Calculation: (Close - Open) / Open * 100 = {wrong_change_pct:.2f}%")
                print(f"   This should NOT be used for After Earning!")
                
        except Exception as e:
            print(f"   Daily data fallback failed: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error fetching data: {str(e)}")

if __name__ == "__main__":
    test_mdb_after_earning_calculation()
