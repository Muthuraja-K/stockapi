#!/usr/bin/env python3
"""
Test script for the API rate limiting functionality
"""

import time
import requests
import json
from api_rate_limiter import enforce_rate_limit, handle_429_error, handle_successful_call, get_rate_limiter

def test_rate_limiter():
    """Test the rate limiter functionality"""
    print("Testing API Rate Limiter...")
    
    # Get initial status
    rate_limiter = get_rate_limiter()
    print(f"Initial status: {rate_limiter.get_status()}")
    
    # Test basic rate limiting
    print("\n1. Testing basic rate limiting...")
    start_time = time.time()
    
    for i in range(5):
        enforce_rate_limit()
        print(f"  Call {i+1}: {time.time() - start_time:.2f}s")
    
    # Test 429 error handling
    print("\n2. Testing 429 error handling...")
    for i in range(3):
        handle_429_error()
        print(f"  Simulated 429 error {i+1}: {rate_limiter.get_status()}")
    
    # Test successful call handling
    print("\n3. Testing successful call handling...")
    handle_successful_call()
    print(f"  After successful call: {rate_limiter.get_status()}")
    
    # Test circuit breaker
    print("\n4. Testing circuit breaker...")
    for i in range(3):
        handle_429_error()
        print(f"  Additional 429 error {i+1}: {rate_limiter.get_status()}")
    
    # Check if circuit breaker is open
    if rate_limiter.is_circuit_open():
        print("  ✓ Circuit breaker is OPEN")
    else:
        print("  ✗ Circuit breaker is still closed")
    
    # Test rate limiting with circuit breaker open
    print("\n5. Testing rate limiting with circuit breaker open...")
    try:
        enforce_rate_limit()
        print("  ✗ Rate limiting should have failed")
    except Exception as e:
        print(f"  ✓ Rate limiting correctly blocked: {e}")
    
    print(f"\nFinal status: {rate_limiter.get_status()}")

def test_api_endpoints():
    """Test the API endpoints for rate limiter status"""
    print("\n" + "="*50)
    print("Testing API Endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        # Test rate limiter status endpoint
        print("\n1. Testing /api/rate-limiter-status...")
        response = requests.get(f"{base_url}/api/rate-limiter-status")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status endpoint working: {data}")
        else:
            print(f"  ✗ Status endpoint failed: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        print("  ⚠ API server not running. Start the server first with: python start_simple.py")
    except Exception as e:
        print(f"  ✗ Error testing endpoints: {e}")

if __name__ == "__main__":
    print("API Rate Limiter Test Suite")
    print("="*50)
    
    # Test the rate limiter directly
    test_rate_limiter()
    
    # Test the API endpoints
    test_api_endpoints()
    
    print("\n" + "="*50)
    print("Test completed!")
