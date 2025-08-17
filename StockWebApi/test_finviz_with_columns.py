#!/usr/bin/env python3
"""
Test Finviz API with the c parameter to see what columns are returned
"""

import requests
from stock_history_operations import stock_history_ops
import json

def test_finviz_with_columns():
    """Test Finviz API with the c parameter"""
    try:
        # Get a few sample stocks
        stocks = stock_history_ops.load_stocks()[:3]
        tickers = [stock.get('ticker') for stock in stocks if stock.get('ticker')]
        
        if not tickers:
            print("No stocks found")
            return
        
        print(f"Testing with tickers: {tickers}")
        
        # Prepare Finviz API request with the SAME parameters as the code
        tickers_param = ','.join(tickers)
        params = {
            'v': '152',
            't': tickers_param,
            'auth': stock_history_ops.finviz_auth_id,
            'c': '1,6,65,68,66'  # Same as in the code
        }
        
        print(f"Making request to: {stock_history_ops.finviz_base_url}")
        print(f"Parameters: {params}")
        
        # Make the API call
        response = requests.get(stock_history_ops.finviz_base_url, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse CSV data
        csv_data = response.text
        lines = csv_data.strip().split('\n')
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response length: {len(csv_data)} characters")
        print(f"Number of lines: {len(lines)}")
        
        if len(lines) >= 1:
            # Show header
            header = lines[0]
            print(f"\nRaw header: {repr(header)}")
            
            # Parse header
            parsed_header = [h.strip().strip('"').strip('\r') for h in header.split(',')]
            print(f"\nParsed header: {parsed_header}")
            
            # Check for earnings-related columns
            earnings_columns = [col for col in parsed_header if 'earn' in col.lower()]
            print(f"\nEarnings-related columns: {earnings_columns}")
            
            # Show first data row
            if len(lines) >= 2:
                first_row = lines[1]
                print(f"\nFirst data row: {repr(first_row)}")
                
                # Parse first row
                values = first_row.split(',')
                if len(values) == len(parsed_header):
                    row_data = dict(zip(parsed_header, [v.strip().strip('"').strip('\r') for v in values]))
                    print(f"\nParsed first row: {json.dumps(row_data, indent=2)}")
                    
                    # Check specific columns that might contain earnings data
                    for col in parsed_header:
                        if 'earn' in col.lower() or 'date' in col.lower():
                            print(f"Column '{col}': {row_data.get(col, 'N/A')}")
                else:
                    print(f"Header has {len(parsed_header)} columns, first row has {len(values)} values")
        
        # Also test without the c parameter to compare
        print("\n" + "="*60)
        print("Testing WITHOUT c parameter for comparison:")
        
        params_no_c = {
            'v': '152',
            't': tickers_param,
            'auth': stock_history_ops.finviz_auth_id
        }
        
        response_no_c = requests.get(stock_history_ops.finviz_base_url, params=params_no_c, timeout=30)
        if response_no_c.status_code == 200:
            csv_data_no_c = response_no_c.text
            lines_no_c = csv_data_no_c.strip().split('\n')
            
            if len(lines_no_c) >= 1:
                header_no_c = lines_no_c[0]
                parsed_header_no_c = [h.strip().strip('"').strip('\r') for h in header_no_c.split(',')]
                print(f"Columns without c parameter: {parsed_header_no_c}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_finviz_with_columns()
