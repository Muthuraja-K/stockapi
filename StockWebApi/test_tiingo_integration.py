#!/usr/bin/env python3
"""
Test script for Tiingo integration

This script tests the Tiingo service to ensure it can fetch historical intraday data
for specific dates, which will be much better than Yahoo Finance for older earnings.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tiingo_service():
    """Test the Tiingo service functionality"""
    
    print("Testing Tiingo Service Integration")
    print("=" * 50)
    
    try:
        # Test if we can import the service
        from tiingo_service import tiingo_service
        print("✓ Tiingo service imported successfully")
        
        # Check if Tiingo is available (has API key)
        if tiingo_service.is_available():
            print("✓ Tiingo API key is configured")
            
            # Test with a recent date (should work with 1-minute data)
            test_date = datetime.now() - timedelta(days=5)
            print(f"\nTesting with recent date: {test_date.strftime('%Y-%m-%d')}")
            
            # Test 1-minute data
            print("Testing 1-minute data...")
            data_1min = tiingo_service.get_1min_data_for_date('AAPL', test_date)
            if data_1min is not None and not data_1min.empty:
                print(f"✓ 1-minute data: {len(data_1min)} data points")
                print(f"  Date range: {data_1min.index.min()} to {data_1min.index.max()}")
                print(f"  Columns: {list(data_1min.columns)}")
            else:
                print("✗ 1-minute data failed")
            
            # Test 5-minute data
            print("\nTesting 5-minute data...")
            data_5min = tiingo_service.get_5min_data_for_date('AAPL', test_date)
            if data_5min is not None and not data_5min.empty:
                print(f"✓ 5-minute data: {len(data_5min)} data points")
                print(f"  Date range: {data_5min.index.min()} to {data_5min.index.max()}")
            else:
                print("✗ 5-minute data failed")
            
            # Test with an older date (should still work with Tiingo)
            old_test_date = datetime.now() - timedelta(days=90)
            print(f"\nTesting with older date: {old_test_date.strftime('%Y-%m-%d')}")
            
            print("Testing 1-minute data for older date...")
            old_data_1min = tiingo_service.get_1min_data_for_date('AAPL', old_test_date)
            if old_data_1min is not None and not old_data_1min.empty:
                print(f"✓ 1-minute data for older date: {len(old_data_1min)} data points")
                print(f"  This demonstrates Tiingo's advantage over Yahoo Finance!")
            else:
                print("✗ 1-minute data for older date failed")
            
            # Test fallback strategy
            print("\nTesting fallback strategy...")
            fallback_data = tiingo_service.get_data_with_fallback('AAPL', old_test_date, '1min')
            if fallback_data is not None and not fallback_data.empty:
                print(f"✓ Fallback strategy successful: {len(fallback_data)} data points")
            else:
                print("✗ Fallback strategy failed")
                
        else:
            print("✗ Tiingo API key not configured")
            print("  To use Tiingo, set the TIINGO_API_KEY environment variable")
            print("  You can get a free API key from: https://api.tiingo.com/")
            
    except ImportError as e:
        print(f"✗ Failed to import Tiingo service: {e}")
        print("  Make sure tiingo package is installed: pip install tiingo")
    except Exception as e:
        print(f"✗ Error testing Tiingo service: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

def test_earning_summary_with_tiingo():
    """Test the earning summary with Tiingo integration"""
    
    print("\nTesting Earning Summary with Tiingo Integration")
    print("=" * 50)
    
    try:
        from earning_summary_optimized import get_enhanced_earnings_data
        
        # Test with a ticker that has earnings
        test_ticker = 'AAPL'
        test_earning_date = '08/10/2025 04:30:00 PM'
        
        print(f"Testing enhanced earnings data for {test_ticker}")
        print(f"Earning date: {test_earning_date}")
        
        result = get_enhanced_earnings_data(test_ticker, test_earning_date)
        
        if result:
            print(f"✓ Successfully got earnings data: {len(result)} earnings")
            for i, earning in enumerate(result):
                print(f"\nEarning {i+1}:")
                print(f"  Date: {earning.get('earningDate', 'N/A')}")
                print(f"  Close B4 Earning: {earning.get('closeB4EarningPrice', 'N/A')} ({earning.get('closeB4EarningChange', 'N/A')})")
                print(f"  After Earning: {earning.get('afterEarningPrice', 'N/A')} ({earning.get('afterEarningChange', 'N/A')})")
                print(f"  Beat Expectation: {earning.get('beatExpectation', 'N/A')}")
                print(f"  Actual EPS: {earning.get('actualValue', 'N/A')}")
                print(f"  Expected EPS: {earning.get('expectedValue', 'N/A')}")
        else:
            print("✗ Failed to get earnings data")
            
    except Exception as e:
        print(f"✗ Error testing earning summary: {e}")
    
    # Test AIRE specifically to debug the N/A issue
    print("\n" + "=" * 50)
    print("Testing AIRE Stock Specifically")
    print("=" * 50)
    
    try:
        from earning_summary_optimized import get_enhanced_earnings_data
        
        # Test with AIRE - check both possible earning dates
        test_ticker = 'AIRE'
        
        # Try the date from market data
        test_earning_date_1 = '08/14/2025 08:30:00 AM'
        print(f"Testing AIRE with earning date: {test_earning_date_1}")
        
        result1 = get_enhanced_earnings_data(test_ticker, test_earning_date_1)
        
        if result1:
            print(f"✓ Successfully got earnings data: {len(result1)} earnings")
            for i, earning in enumerate(result1):
                print(f"\nEarning {i+1}:")
                print(f"  Date: {earning.get('earningDate', 'N/A')}")
                print(f"  Close B4 Earning: {earning.get('closeB4EarningPrice', 'N/A')} ({earning.get('closeB4EarningChange', 'N/A')})")
                print(f"  After Earning: {earning.get('afterEarningPrice', 'N/A')} ({earning.get('afterEarningChange', 'N/A')})")
                print(f"  Beat Expectation: {earning.get('beatExpectation', 'N/A')}")
                print(f"  Actual EPS: {earning.get('actualValue', 'N/A')}")
                print(f"  Expected EPS: {earning.get('expectedValue', 'N/A')}")
        else:
            print("✗ Failed to get earnings data for AIRE with date 1")
        
        # Try the date mentioned by user
        test_earning_date_2 = '04/02/2025 08:30:00 AM'
        print(f"\nTesting AIRE with earning date: {test_earning_date_2}")
        
        result2 = get_enhanced_earnings_data(test_ticker, test_earning_date_2)
        
        if result2:
            print(f"✓ Successfully got earnings data: {len(result2)} earnings")
            for i, earning in enumerate(result2):
                print(f"\nEarning {i+1}:")
                print(f"  Date: {earning.get('earningDate', 'N/A')}")
                print(f"  Close B4 Earning: {earning.get('closeB4EarningPrice', 'N/A')} ({earning.get('closeB4EarningChange', 'N/A')})")
                print(f"  After Earning: {earning.get('afterEarningPrice', 'N/A')} ({earning.get('afterEarningChange', 'N/A')})")
                print(f"  Beat Expectation: {earning.get('beatExpectation', 'N/A')}")
                print(f"  Actual EPS: {earning.get('actualValue', 'N/A')}")
                print(f"  Expected EPS: {earning.get('expectedValue', 'N/A')}")
        else:
            print("✗ Failed to get earnings data for AIRE with date 2")
            
    except Exception as e:
        print(f"✗ Error testing AIRE earning summary: {e}")
    
    print("\n" + "=" * 50)
    print("Earning Summary test completed!")

if __name__ == "__main__":
    # Test Tiingo service
    test_tiingo_service()
    
    # Test earning summary with Tiingo
    test_earning_summary_with_tiingo()
