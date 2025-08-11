#!/usr/bin/env python3
"""
Test script for the API Rate Limiting system
This script tests the centralized rate limiter to ensure it's working correctly
"""

import time
import logging
from api_rate_limiter import (
    get_rate_limiter, 
    enforce_rate_limit, 
    safe_yfinance_call, 
    safe_finviz_call,
    handle_429_error,
    handle_successful_call
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_rate_limiting():
    """Test basic rate limiting functionality"""
    print("\n=== Testing Basic Rate Limiting ===")
    
    rate_limiter = get_rate_limiter()
    print(f"Initial rate limiter status: {rate_limiter.get_status()}")
    
    # Test multiple rapid calls
    start_time = time.time()
    for i in range(5):
        print(f"Call {i+1}: Enforcing rate limit...")
        enforce_rate_limit()
        call_time = time.time()
        print(f"  Call {i+1} completed at: {call_time - start_time:.2f}s")
    
    total_time = time.time() - start_time
    print(f"Total time for 5 calls: {total_time:.2f}s")
    print(f"Expected minimum time: {5 * rate_limiter.min_interval:.2f}s")
    
    if total_time >= 5 * rate_limiter.min_interval:
        print("✅ Rate limiting working correctly")
    else:
        print("❌ Rate limiting not working correctly")

def test_safe_yfinance_call():
    """Test safe yfinance call functionality"""
    print("\n=== Testing Safe YFinance Call ===")
    
    try:
        # Test info call
        print("Testing yfinance info call...")
        start_time = time.time()
        info = safe_yfinance_call("AAPL", "info")
        info_time = time.time() - start_time
        print(f"  Info call completed in: {info_time:.2f}s")
        print(f"  Got info with {len(info)} fields")
        
        # Test history call
        print("Testing yfinance history call...")
        start_time = time.time()
        hist = safe_yfinance_call("AAPL", "history")
        hist_time = time.time() - start_time
        print(f"  History call completed in: {hist_time:.2f}s")
        print(f"  Got history with {len(hist)} data points")
        
        print("✅ Safe yfinance calls working correctly")
        
    except Exception as e:
        print(f"❌ Safe yfinance call failed: {e}")

def test_safe_finviz_call():
    """Test safe Finviz call functionality"""
    print("\n=== Testing Safe Finviz Call ===")
    
    try:
        print("Testing Finviz call...")
        start_time = time.time()
        data = safe_finviz_call("AAPL")
        finviz_time = time.time() - start_time
        print(f"  Finviz call completed in: {finviz_time:.2f}s")
        print(f"  Got data: {data}")
        
        print("✅ Safe Finviz call working correctly")
        
    except Exception as e:
        print(f"❌ Safe Finviz call failed: {e}")

def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\n=== Testing Circuit Breaker ===")
    
    rate_limiter = get_rate_limiter()
    
    # Simulate multiple 429 errors
    print("Simulating 429 errors to trigger circuit breaker...")
    for i in range(6):  # Should trigger circuit breaker after 5
        print(f"  Simulating 429 error {i+1}...")
        handle_429_error()
        print(f"    Consecutive 429 count: {rate_limiter.consecutive_429_errors}")
        print(f"    Circuit breaker open: {rate_limiter.is_circuit_open()}")
    
    # Try to make a call - should fail
    try:
        print("  Attempting to make API call with circuit breaker open...")
        enforce_rate_limit()
        print("❌ Circuit breaker not working - call succeeded")
    except Exception as e:
        if "Circuit breaker is open" in str(e):
            print("✅ Circuit breaker working correctly - call blocked")
        else:
            print(f"❌ Unexpected error: {e}")
    
    # Wait for circuit breaker to reset (or manually reset)
    print("  Waiting for circuit breaker timeout...")
    if rate_limiter.circuit_breaker_opened_at:
        remaining = rate_limiter.circuit_breaker_timeout - (time.time() - rate_limiter.circuit_breaker_opened_at)
        print(f"    Circuit breaker will reset in {remaining:.1f}s")
    
    # Manually reset for testing
    print("  Manually resetting circuit breaker...")
    with rate_limiter.lock:
        rate_limiter.consecutive_429_errors = 0
        rate_limiter.circuit_breaker_opened_at = None
    
    print(f"    Circuit breaker status: {rate_limiter.get_status()}")

def test_concurrent_calls():
    """Test concurrent calls with rate limiting"""
    print("\n=== Testing Concurrent Calls ===")
    
    import threading
    
    def make_api_call(thread_id):
        try:
            print(f"  Thread {thread_id}: Starting API call...")
            start_time = time.time()
            enforce_rate_limit()
            # Simulate API call
            time.sleep(0.1)
            call_time = time.time() - start_time
            print(f"  Thread {thread_id}: API call completed in {call_time:.2f}s")
        except Exception as e:
            print(f"  Thread {thread_id}: Error: {e}")
    
    # Start multiple threads
    threads = []
    start_time = time.time()
    
    for i in range(3):
        thread = threading.Thread(target=make_api_call, args=(i+1,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    print(f"Total time for 3 concurrent calls: {total_time:.2f}s")
    
    # Should take at least 6 seconds (3 calls * 2 seconds each)
    if total_time >= 6:
        print("✅ Concurrent rate limiting working correctly")
    else:
        print("❌ Concurrent rate limiting not working correctly")

def test_rate_limiter_status():
    """Test rate limiter status endpoint"""
    print("\n=== Testing Rate Limiter Status ===")
    
    rate_limiter = get_rate_limiter()
    status = rate_limiter.get_status()
    
    print("Rate limiter status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("✅ Rate limiter status working correctly")

def main():
    """Run all tests"""
    print("🚀 Starting API Rate Limiting Tests")
    print("=" * 50)
    
    try:
        test_basic_rate_limiting()
        time.sleep(1)
        
        test_safe_yfinance_call()
        time.sleep(1)
        
        test_safe_finviz_call()
        time.sleep(1)
        
        test_circuit_breaker()
        time.sleep(1)
        
        test_concurrent_calls()
        time.sleep(1)
        
        test_rate_limiter_status()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
