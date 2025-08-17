#!/usr/bin/env python3
"""
Test script that mimics the exact multi-ticker scenario from the real code
"""

import yfinance as yf
import pandas as pd

def test_multi_ticker_scenario():
    """Test the exact multi-ticker scenario from populate_stock_history"""
    try:
        print("🔍 Testing exact multi-ticker scenario from populate_stock_history...")
        
        # Test with multiple tickers (like in the real code)
        test_tickers = ["RGTI", "QBTS", "QUBT"]
        print(f"Testing with tickers: {test_tickers}")
        
        # Download all data at once using yf.download() - exactly like in the code
        print(f"\n📥 Downloading data for {len(test_tickers)} tickers...")
        all_data = yf.download(test_tickers, period="1y", group_by='ticker', progress=False)
        print(f"Data shape: {all_data.shape}")
        print(f"Columns: {all_data.columns.tolist()}")
        
        # Test with RGTI specifically (exact logic from code)
        test_ticker = "RGTI"
        print(f"\n🧮 Testing with {test_ticker} using exact code logic:")
        
        # Extract data for this specific ticker (exact logic from code)
        if len(test_tickers) == 1:
            # Single ticker case
            hist = all_data
        else:
            # Multiple tickers case - data is multi-level
            if test_ticker in all_data.columns.levels[0]:
                hist = all_data[test_ticker]
            else:
                print(f"❌ Ticker {test_ticker} not found in downloaded data")
                return
        
        print(f"Extracted hist shape: {hist.shape}")
        print(f"Extracted hist columns: {hist.columns.tolist()}")
        
        if not hist.empty:
            # Define periods and their corresponding data ranges (exact logic from code)
            periods_data = {
                'previous_day': hist.tail(2),      # Last 2 days
                'five_day': hist.tail(5),          # Last 5 days
                'one_month': hist.tail(30),        # Last 30 days
                'six_month': hist.tail(180),       # Last 180 days
                'one_year': hist                    # Full year
            }
            
            # Helper function (exact copy from code)
            def get_column_data(data, column_name):
                """Get column data handling both single and multi-level columns"""
                if isinstance(data.columns, pd.MultiIndex):
                    # Multi-level columns - look for the specific ticker column
                    col_key = (column_name, test_ticker)
                    if col_key in data.columns:
                        return data[col_key]
                    else:
                        # Fallback to first available column of this type
                        available_cols = [col for col in data.columns if col[0] == column_name]
                        if available_cols:
                            return data[available_cols[0]]
                        else:
                            return pd.Series(dtype=float)
                else:
                    # Single-level columns (this is the case when data is extracted for a specific ticker)
                    if column_name in data.columns:
                        return data[column_name]
                    else:
                        # If column doesn't exist, return empty series
                        return pd.Series(dtype=float)
            
            # Test 1Y calculation (exact logic from code)
            print(f"\n📊 Testing 1Y calculation with exact code logic:")
            period_name = 'one_year'
            period_data = periods_data[period_name]
            
            if not period_data.empty and len(period_data) >= 2:
                print("✅ Period data validation passed")
                
                # Test low/high extraction (exact logic from code)
                try:
                    low_data = get_column_data(period_data, 'Low')
                    high_data = get_column_data(period_data, 'High')
                    
                    if not low_data.empty and not high_data.empty:
                        low = low_data.min()
                        high = high_data.max()
                        
                        # Validate low and high values (exact logic from code)
                        if pd.isna(low) or not isinstance(low, (int, float)):
                            low = None
                        if pd.isna(high) or not isinstance(high, (int, float)):
                            high = None
                        
                        print(f"✅ Low/High extraction successful: Low={low}, High={high}")
                    else:
                        print("❌ Low/High data is empty")
                        low = None
                        high = None
                except Exception as e:
                    print(f"❌ Error in low/high extraction: {e}")
                    low = None
                    high = None
                
                # Test percentage calculation (exact logic from code)
                print(f"\n🧮 Testing percentage calculation with exact code logic:")
                percentage = None
                
                try:
                    # For other periods, use first and last close (exact logic from code)
                    period_sorted = period_data.sort_index()
                    close_data = get_column_data(period_sorted, 'Close')
                    
                    if not close_data.empty and len(close_data) >= 2:
                        print("✅ Close data validation passed")
                        
                        first_close = close_data.iloc[0]
                        last_close = close_data.iloc[-1]
                        
                        print(f"First close: {first_close}")
                        print(f"Last close: {last_close}")
                        
                        # Check for valid numeric values (exact logic from code)
                        if pd.isna(first_close) or pd.isna(last_close) or first_close == 0:
                            print("❌ Invalid values detected")
                            percentage = None
                        else:
                            print("✅ Values look valid, calculating percentage...")
                            percentage = ((last_close - first_close) / first_close) * 100
                            print(f"Calculated percentage: {percentage}")
                            
                            # Validate percentage value (exact logic from code)
                            if pd.isna(percentage) or not isinstance(percentage, (int, float)):
                                print(f"❌ Percentage validation failed")
                                percentage = None
                            elif abs(percentage) > 100000:  # Unrealistic percentage change (1000x)
                                print(f"❌ Unrealistic percentage: {percentage}%")
                                percentage = None
                            else:
                                print(f"✅ Percentage validation passed: {percentage:.2f}%")
                    else:
                        print("❌ Close data validation failed")
                        percentage = None
                        
                except Exception as e:
                    print(f"❌ Error in percentage calculation: {e}")
                    import traceback
                    traceback.print_exc()
                    percentage = None
                
                # Test final formatting (exact logic from code)
                print(f"\n📝 Testing final formatting with exact code logic:")
                if percentage is not None and not pd.isna(percentage):
                    percentage_str = f"{percentage:.2f}%"
                    print(f"✅ Final percentage: {percentage_str}")
                else:
                    percentage_str = "N/A"
                    print(f"❌ Final percentage: {percentage_str}")
                
                # Test final data structure (exact logic from code)
                print(f"\n📊 Testing final data structure:")
                history_data_entry = {
                    "low": f"${low:.2f}" if not pd.isna(low) else "N/A",
                    "high": f"${high:.2f}" if not pd.isna(high) else "N/A",
                    "percentage": percentage_str
                }
                print(f"Final entry: {history_data_entry}")
                
            else:
                print("❌ Period data validation failed")
                
        else:
            print("❌ No data extracted")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_ticker_scenario()
