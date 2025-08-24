#!/usr/bin/env python3
"""
Debug script to test each step of the earnings summary process
"""

import json
import sys
import os

def test_file_exists():
    """Test 1: Check if earningsummary.json exists"""
    print("=== Test 1: File Existence ===")
    file_path = 'earningsummary.json'
    exists = os.path.exists(file_path)
    print(f"File exists: {exists}")
    if exists:
        size = os.path.getsize(file_path)
        print(f"File size: {size} bytes")
    print()

def test_file_content():
    """Test 2: Check file content directly"""
    print("=== Test 2: File Content ===")
    try:
        with open('earningsummary.json', 'r') as f:
            data = json.load(f)
        
        print(f"Data type: {type(data)}")
        print(f"Data length: {len(data) if isinstance(data, list) else 'Not a list'}")
        
        if isinstance(data, list) and len(data) > 0:
            print(f"First item keys: {list(data[0].keys())}")
            print(f"First item ticker: {data[0].get('ticker', 'N/A')}")
        print()
        
    except Exception as e:
        print(f"Error reading file: {e}")
        print()

def test_file_manager_import():
    """Test 3: Test importing the file manager"""
    print("=== Test 3: File Manager Import ===")
    try:
        from earning_summary_file_manager import earning_summary_manager
        print("✅ Import successful")
        
        # Test the manager
        manager = earning_summary_manager
        print(f"Manager type: {type(manager)}")
        print(f"Manager class: {manager.__class__.__name__}")
        print()
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        print()

def test_file_manager_load():
    """Test 4: Test loading data through file manager"""
    print("=== Test 4: File Manager Load ===")
    try:
        from earning_summary_file_manager import earning_summary_manager
        
        data = earning_summary_manager.load_earning_summary()
        print(f"Loaded data type: {type(data)}")
        print(f"Loaded data length: {len(data) if isinstance(data, list) else 'Not a list'}")
        
        if isinstance(data, list) and len(data) > 0:
            print(f"First item: {data[0].get('ticker', 'N/A')}")
        print()
        
    except Exception as e:
        print(f"❌ Load failed: {e}")
        print()

def test_main_import():
    """Test 5: Test importing from main.py"""
    print("=== Test 5: Main Import ===")
    try:
        # Import the function that's used in main.py
        from earning_summary_file_manager import earning_summary_manager
        
        # Simulate what main.py does
        earning_data = earning_summary_manager.load_earning_summary()
        print(f"Main import data length: {len(earning_data) if isinstance(earning_data, list) else 'Not a list'}")
        
        if isinstance(earning_data, list) and len(earning_data) > 0:
            print(f"First item: {earning_data[0].get('ticker', 'N/A')}")
        print()
        
    except Exception as e:
        print(f"❌ Main import failed: {e}")
        print()

def test_period_filter():
    """Test 6: Test period filtering logic"""
    print("=== Test 6: Period Filtering ===")
    try:
        from earning_summary_file_manager import earning_summary_manager
        
        # Load data
        earning_data = earning_summary_manager.load_earning_summary()
        print(f"Before filtering: {len(earning_data)} items")
        
        # Test the period filter function from main.py
        def _apply_period_filter(earning_data, period, date_from, date_to):
            """Copy of the filter function from main.py"""
            if not period or period not in ['1D', '1W', '1M', 'custom']:
                return earning_data
            
            try:
                from datetime import datetime, timedelta
                
                today = datetime.now().date()
                filtered_data = []
                
                for stock in earning_data:
                    earning_date_str = stock.get('earningDate', '')
                    if not earning_date_str or earning_date_str == 'N/A':
                        continue
                    
                    try:
                        # Parse earning date
                        earning_date = datetime.strptime(earning_date_str, '%m/%d/%Y %I:%M:%S %p')
                        earning_date_only = earning_date.date()
                        
                        if period == '1W':
                            # Show earnings within the next 7 days
                            week_end = today + timedelta(days=7)
                            if today <= earning_date_only <= week_end:
                                filtered_data.append(stock)
                                
                    except ValueError:
                        continue
                
                return filtered_data
                
            except Exception as e:
                print(f"Filter error: {e}")
                return earning_data
        
        # Test with no period (should return all data)
        filtered_no_period = _apply_period_filter(earning_data, "", "", "")
        print(f"After no period filter: {len(filtered_no_period)} items")
        
        # Test with 1W period (should return 0 items for past dates)
        filtered_1w = _apply_period_filter(earning_data, "1W", "", "")
        print(f"After 1W period filter: {len(filtered_1w)} items")
        
        print()
        
    except Exception as e:
        print(f"❌ Period filter test failed: {e}")
        print()

if __name__ == "__main__":
    print("🔍 DEBUGGING EARNINGS SUMMARY STEP BY STEP")
    print("=" * 60)
    
    test_file_exists()
    test_file_content()
    test_file_manager_import()
    test_file_manager_load()
    test_main_import()
    test_period_filter()
    
    print("=" * 60)
    print("✅ Debugging complete!")
