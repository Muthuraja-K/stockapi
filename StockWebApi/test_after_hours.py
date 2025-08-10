#!/usr/bin/env python3
"""
Test script for the after-hours API endpoint
"""

import requests
import json
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_TICKER = "BBAI"

def test_after_hours_endpoint():
    """Test the after-hours endpoint with various date scenarios"""
    
    print("Testing After-Hours API Endpoint")
    print("=" * 50)
    
    # Test 1: Future date (should return 400)
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    print(f"\n1. Testing future date: {future_date}")
    try:
        response = requests.get(f"{BASE_URL}/api/after-hours/{TEST_TICKER}/{future_date}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Date too far in the past (should return 400)
    past_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    print(f"\n2. Testing date too far in past: {past_date}")
    try:
        response = requests.get(f"{BASE_URL}/api/after-hours/{TEST_TICKER}/{past_date}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Recent date (should work)
    recent_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    print(f"\n3. Testing recent date: {recent_date}")
    try:
        response = requests.get(f"{BASE_URL}/api/after-hours/{TEST_TICKER}/{recent_date}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        else:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Invalid date format (should return 400)
    invalid_date = "2025-13-45"
    print(f"\n4. Testing invalid date format: {invalid_date}")
    try:
        response = requests.get(f"{BASE_URL}/api/after-hours/{TEST_TICKER}/{invalid_date}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Empty ticker (should return 400)
    print(f"\n5. Testing empty ticker")
    try:
        response = requests.get(f"{BASE_URL}/api/after-hours//{recent_date}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    print("Note: Make sure the server is running on http://localhost:8000")
    print("You can start it with: uvicorn main:app --reload")
    print()
    
    try:
        test_after_hours_endpoint()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
