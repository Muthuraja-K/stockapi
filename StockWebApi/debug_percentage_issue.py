#!/usr/bin/env python3
"""
Focused debug script to identify where percentage calculation is failing
"""

from stock_history_operations import stock_history_ops
import yfinance as yf
import pandas as pd

def debug_percentage_issue():
    """Debug the percentage calculation step by step"""
    try:
        print("🔍 Debugging percentage calculation step by step...")
        
        # Test with RGTI
        test_ticker = "RGTI"
        print(f"Testing with ticker: {test_ticker}")
        
        # Download data for this ticker
        print(f"\n📥 Downloading 1Y data for {test_ticker}...")
        hist = yf.download(test_ticker, period="1y", progress=False)
        
        print(f"Data shape: {hist.shape}")
        print(f"Columns: {hist.columns.tolist()}")
        
        if not hist.empty:
            print(f"\n📊 First 3 rows:")
            print(hist.head(3))
            print(f"\nLast 3 rows:")
            print(hist.tail(3))
            
            # Test the exact logic from the code
            print(f"\n🧮 Testing exact logic from populate_stock_history:")
            
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
            
            # Test 1Y calculation step by step
            print(f"\n📊 Testing 1Y calculation step by step:")
            period_data = periods_data['one_year']
            print(f"1Y data shape: {period_data.shape}")
            
            if not period_data.empty and len(period_data) >= 2:
                print("✅ Period data validation passed")
                
                # Test low/high extraction
                try:
                    low_data = get_column_data(period_data, 'Low')
                    high_data = get_column_data(period_data, 'High')
                    
                    print(f"Low data type: {type(low_data)}")
                    print(f"High data type: {type(high_data)}")
                    
                    if not low_data.empty and not high_data.empty:
                        low = low_data.min()
                        high = high_data.max()
                        print(f"✅ Low/High extraction successful: Low={low}, High={high}")
                    else:
                        print("❌ Low/High data is empty")
                        low = None
                        high = None
                except Exception as e:
                    print(f"❌ Error in low/high extraction: {e}")
                    low = None
                    high = None
                
                # Test percentage calculation
                print(f"\n🧮 Testing percentage calculation:")
                percentage = None
                
                try:
                    # For other periods, use first and last close
                    period_sorted = period_data.sort_index()
                    close_data = get_column_data(period_sorted, 'Close')
                    
                    print(f"Close data type: {type(close_data)}")
                    print(f"Close data shape: {close_data.shape}")
                    
                    if not close_data.empty and len(close_data) >= 2:
                        print("✅ Close data validation passed")
                        
                        first_close = close_data.iloc[0]
                        last_close = close_data.iloc[-1]
                        
                        print(f"First close: {first_close} (type: {type(first_close)})")
                        print(f"Last close: {last_close} (type: {type(last_close)})")
                        
                        # Check for valid numeric values
                        if pd.isna(first_close) or pd.isna(last_close) or first_close == 0:
                            print("❌ Invalid values detected:")
                            print(f"   first_close is NaN: {pd.isna(first_close)}")
                            print(f"   last_close is NaN: {pd.isna(last_close)}")
                            print(f"   first_close == 0: {first_close == 0}")
                            percentage = None
                        else:
                            print("✅ Values look valid, calculating percentage...")
                            percentage = ((last_close - first_close) / first_close) * 100
                            print(f"Calculated percentage: {percentage}")
                            
                            # Validate percentage value
                            if pd.isna(percentage) or not isinstance(percentage, (int, float)):
                                print(f"❌ Percentage validation failed:")
                                print(f"   is NaN: {pd.isna(percentage)}")
                                print(f"   type: {type(percentage)}")
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
                
                # Test final formatting
                print(f"\n📝 Testing final formatting:")
                if percentage is not None and not pd.isna(percentage):
                    percentage_str = f"{percentage:.2f}%"
                    print(f"✅ Final percentage: {percentage_str}")
                else:
                    percentage_str = "N/A"
                    print(f"❌ Final percentage: {percentage_str}")
                
            else:
                print("❌ Period data validation failed")
                
        else:
            print("❌ No data downloaded")
            
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_percentage_issue()
