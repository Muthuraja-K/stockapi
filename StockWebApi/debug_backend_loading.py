#!/usr/bin/env python3
"""
Debug the backend loading logic step by step
"""

def test_file_loading():
    """Test 1: Direct file loading"""
    print("=== Test 1: Direct file loading ===")
    try:
        with open('earningsummary.json', 'r') as f:
            import json
            data = json.load(f)
        
        print(f"✅ File loaded directly: {len(data)} items")
        if data:
            print(f"First item: {data[0]['ticker']}")
        print()
        
    except Exception as e:
        print(f"❌ Direct file loading failed: {e}")
        print()

def test_file_manager_import():
    """Test 2: File manager import"""
    print("=== Test 2: File manager import ===")
    try:
        from earning_summary_file_manager import earning_summary_manager
        print("✅ Import successful")
        print(f"Manager type: {type(earning_summary_manager)}")
        print()
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        print()

def test_file_manager_load():
    """Test 3: File manager load method"""
    print("=== Test 3: File manager load method ===")
    try:
        from earning_summary_file_manager import earning_summary_manager
        
        data = earning_summary_manager.load_earning_summary()
        print(f"✅ Load method successful: {len(data)} items")
        if data:
            print(f"First item: {data[0]['ticker']}")
        else:
            print("⚠️ No data returned from load method")
        print()
        
    except Exception as e:
        print(f"❌ Load method failed: {e}")
        print()

def test_main_logic():
    """Test 4: Simulate main.py logic"""
    print("=== Test 4: Simulate main.py logic ===")
    try:
        from earning_summary_file_manager import earning_summary_manager
        
        # Simulate what main.py does
        earning_data = earning_summary_manager.load_earning_summary()
        print(f"✅ Main logic simulation: {len(earning_data)} items")
        
        if earning_data:
            print(f"First item: {earning_data[0]['ticker']}")
            
            # Test period filtering
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
            
            # Test with 1W period (should return 0 for past dates)
            filtered_1w = _apply_period_filter(earning_data, "1W", "", "")
            print(f"After 1W period filter: {len(filtered_1w)} items")
            
        else:
            print("⚠️ No data to filter")
        print()
        
    except Exception as e:
        print(f"❌ Main logic simulation failed: {e}")
        print()

if __name__ == "__main__":
    print("🔍 DEBUGGING BACKEND LOADING LOGIC")
    print("=" * 60)
    
    test_file_loading()
    test_file_manager_import()
    test_file_manager_load()
    test_main_logic()
    
    print("=" * 60)
    print("✅ Debugging complete!")
