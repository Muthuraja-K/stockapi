#!/usr/bin/env python3
"""
Debug script to see the actual raw response from Tiingo API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from config import config

def debug_tiingo_response():
    """Debug the actual Tiingo API response"""
    
    ticker = "MDB"
    start_date = "2025-06-03"
    end_date = "2025-06-05"
    
    print(f"Debugging Tiingo API response for {ticker}")
    print(f"Date range: {start_date} to {end_date}")
    print("=" * 60)
    
    # Check if API key is available
    api_key = config.TIINGO_API_KEY
    if not api_key:
        print("❌ No Tiingo API key configured")
        return
    
    print(f"✅ API key available: {api_key[:10]}...")
    
    # Build API URL
    base_url = config.TIINGO_BASE_URL
    url = f"{base_url}/iex/{ticker}/prices"
    
    # Query parameters
    params = {
        'startDate': start_date,
        'endDate': end_date,
        'resampleFreq': '1min',
        'token': api_key,
        'extended': 'true'
    }
    
    print(f"🔗 API URL: {url}")
    print(f"📋 Parameters: {params}")
    
    try:
        # Make API request
        print(f"\n📡 Making API request...")
        response = requests.get(url, params=params)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"✅ Request successful!")
            
            # Get the raw response
            raw_data = response.text
            print(f"\n📄 Raw response (first 1000 chars):")
            print(raw_data[:1000])
            
            # Try to parse as JSON
            try:
                json_data = response.json()
                print(f"\n🔍 JSON response structure:")
                print(f"   Type: {type(json_data)}")
                print(f"   Length: {len(json_data) if isinstance(json_data, list) else 'N/A'}")
                
                if isinstance(json_data, list) and len(json_data) > 0:
                    print(f"\n📋 First item structure:")
                    first_item = json_data[0]
                    print(f"   Keys: {list(first_item.keys())}")
                    print(f"   First item: {first_item}")
                    
                    # Show all unique keys across all items
                    all_keys = set()
                    for item in json_data:
                        all_keys.update(item.keys())
                    print(f"\n🔑 All unique keys found: {sorted(all_keys)}")
                    
                elif isinstance(json_data, dict):
                    print(f"\n📋 Response is a dictionary:")
                    print(f"   Keys: {list(json_data.keys())}")
                    print(f"   Content: {json_data}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                print(f"📄 Raw response: {raw_data}")
                
        elif response.status_code == 429:
            print(f"⚠️  Rate limited!")
            retry_after = response.headers.get('Retry-After', 'Unknown')
            print(f"   Retry-After: {retry_after}")
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"📄 Error response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error making request: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tiingo_response()
