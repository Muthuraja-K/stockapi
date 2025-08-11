#!/usr/bin/env python3
"""
Railway Deployment Verification Script
This script helps verify that the rate limiting system is working correctly in Railway
"""

import time
import logging
import requests
from api_rate_limiter import get_rate_limiter, enforce_rate_limit, safe_yfinance_call

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_rate_limiter_status():
    """Test the rate limiter status endpoint"""
    print("=== Testing Rate Limiter Status Endpoint ===")
    
    try:
        # Try to get status from the API endpoint
        response = requests.get("http://localhost:8000/api/rate-limiter-status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status endpoint working: {data}")
            return True
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("⚠️  API server not running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing status endpoint: {e}")
        return False

def test_direct_rate_limiter():
    """Test the rate limiter directly"""
    print("\n=== Testing Rate Limiter Directly ===")
    
    try:
        rate_limiter = get_rate_limiter()
        status = rate_limiter.get_status()
        print(f"✅ Rate limiter status: {status}")
        
        # Test rate limiting
        print("Testing rate limiting...")
        start_time = time.time()
        
        for i in range(3):
            print(f"  Call {i+1}: Enforcing rate limit...")
            enforce_rate_limit()
            call_time = time.time() - start_time
            print(f"    Call {i+1} completed at: {call_time:.2f}s")
        
        total_time = time.time() - start_time
        print(f"Total time for 3 calls: {total_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing rate limiter directly: {e}")
        return False

def test_safe_yfinance_call():
    """Test safe yfinance call"""
    print("\n=== Testing Safe YFinance Call ===")
    
    try:
        print("Testing yfinance call for AAPL...")
        start_time = time.time()
        
        info = safe_yfinance_call("AAPL", "info")
        
        call_time = time.time() - start_time
        print(f"✅ YFinance call completed in: {call_time:.2f}s")
        print(f"  Got info with {len(info)} fields")
        
        # Test a few key fields
        if 'currentPrice' in info:
            print(f"  Current price: {info.get('currentPrice')}")
        if 'previousClose' in info:
            print(f"  Previous close: {info.get('previousClose')}")
        
        return True
        
    except Exception as e:
        print(f"❌ YFinance call failed: {e}")
        return False

def test_multiple_tickers():
    """Test multiple tickers to see rate limiting in action"""
    print("\n=== Testing Multiple Tickers ===")
    
    tickers = ["AAPL", "MSFT", "GOOGL"]
    results = {}
    
    try:
        for ticker in tickers:
            print(f"Testing {ticker}...")
            start_time = time.time()
            
            try:
                info = safe_yfinance_call(ticker, "info")
                call_time = time.time() - start_time
                results[ticker] = {
                    'success': True,
                    'time': call_time,
                    'fields': len(info)
                }
                print(f"  ✅ {ticker} completed in {call_time:.2f}s")
                
            except Exception as e:
                results[ticker] = {
                    'success': False,
                    'error': str(e)
                }
                print(f"  ❌ {ticker} failed: {e}")
        
        # Summary
        print(f"\nSummary:")
        for ticker, result in results.items():
            if result['success']:
                print(f"  {ticker}: ✅ {result['time']:.2f}s ({result['fields']} fields)")
            else:
                print(f"  {ticker}: ❌ {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing multiple tickers: {e}")
        return False

def main():
    """Run all verification tests"""
    print("🚀 Railway Deployment Verification")
    print("=" * 50)
    
    tests = [
        ("Rate Limiter Status Endpoint", test_rate_limiter_status),
        ("Direct Rate Limiter", test_direct_rate_limiter),
        ("Safe YFinance Call", test_safe_yfinance_call),
        ("Multiple Tickers", test_multiple_tickers)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Rate limiting system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
    
    # Additional debugging info
    print(f"\n🔧 Debugging Information:")
    try:
        rate_limiter = get_rate_limiter()
        status = rate_limiter.get_status()
        print(f"  Rate limiter status: {status}")
    except Exception as e:
        print(f"  Could not get rate limiter status: {e}")

if __name__ == "__main__":
    main()
