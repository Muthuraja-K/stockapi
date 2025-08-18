import requests
import json
import config

def test_finviz_api():
    """Test Finviz API to see what data is actually returned"""
    
    # Test with a single ticker
    tickers = ['OPEN']
    
    # Finviz CSV export API endpoint - using view 152 with column parameter
    url = "https://elite.finviz.com/export.ashx"
    params = {
        'v': '152',  # View 152
        't': ','.join(tickers),
        'c': '1,6,7,65,66,67,68,71,72,81,86,87,88',  # Include Ticker + Market Cap, P/E, Price, Change, Volume, Earnings Date, After-Hours Close, After-Hours Change, Prev Close, Open, High, Low
        'auth': config.config.FINVIZ_AUTH_ID
    }
    
    print(f"Testing Finviz API with params: {params}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Parse CSV response
            lines = response.text.strip().split('\n')
            print(f"Number of lines returned: {len(lines)}")
            
            if len(lines) >= 2:
                # Parse header
                header = lines[0].split(',')
                print(f"Header columns: {header}")
                
                # Parse data row
                values = lines[1].split(',')
                print(f"Data values: {values}")
                
                # Create column mapping
                column_map = {}
                for i, col in enumerate(header):
                    column_map[col.strip()] = i
                
                print(f"Column mapping: {column_map}")
                
                # Check specific fields
                ticker = values[column_map.get('"Ticker"', 0)].strip().strip('"')
                print(f"Ticker: {ticker}")
                
                # Check After-Hours Close
                if '"After-Hours Close"' in column_map:
                    ah_close_idx = column_map['"After-Hours Close"']
                    ah_close_value = values[ah_close_idx].strip('"')
                    print(f"After-Hours Close index: {ah_close_idx}")
                    print(f"After-Hours Close value: {ah_close_value}")
                else:
                    print("'After-Hours Close' column NOT FOUND in header!")
                
                # Check other fields
                for field in ['"Market Cap"', '"Price"', '"Change"', '"Volume"']:
                    if field in column_map:
                        idx = column_map[field]
                        value = values[idx].strip('"')
                        print(f"{field}: {value} (index: {idx})")
                    else:
                        print(f"{field} NOT FOUND in header!")
            else:
                print("Insufficient data returned")
        else:
            print(f"API request failed: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_finviz_api()
