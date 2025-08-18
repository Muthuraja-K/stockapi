import logging
from datetime import datetime
import math

def fmt_currency(val):
    try:
        # Handle None, NaN, and infinite values
        if val is None:
            return 'N/A'
        
        f = float(val)
        
        # Check for NaN or infinite values
        if math.isnan(f) or math.isinf(f):
            return 'N/A'
            
        return f"${f:,.2f}"
    except Exception:
        return 'N/A'

def fmt_percent(val):
    try:
        # Handle None, NaN, and infinite values
        if val is None:
            return 'N/A'
            
        f = float(val)
        
        # Check for NaN or infinite values
        if math.isnan(f) or math.isinf(f):
            return 'N/A'
            
        return f"{f:.2f}%"
    except Exception:
        return 'N/A'

def fmt_market_cap(val):
    """
    Format market cap values to show billions and trillions with proper suffixes.
    Finviz returns market cap values in billions, so we need to multiply by 1,000,000,000.
    Examples: 3416.26 -> $3.42T, 2500 -> $2.50T, 750 -> $750.00B
    """
    try:
        if val is None or val == '' or val == 'N/A':
            return 'N/A'
            
        f = float(val)
        
        # Check for NaN or infinite values
        if math.isnan(f) or math.isinf(f):
            return 'N/A'
            
        # If value is less than 10,000, assume it's in billions (Finviz format)
        # If value is 10,000 or greater, assume it's already in actual dollars
        if f < 10000:
            # Finviz format: multiply by 1,000,000,000 to get actual value
            actual_value = f * 1000000000
        else:
            # Already in actual dollars
            actual_value = f
        
        # Now format the actual value
        if actual_value >= 1e12:  # Trillion
            return f"${actual_value/1e12:.2f}T"
        elif actual_value >= 1e9:  # Billion
            return f"${actual_value/1e9:.2f}B"
        elif actual_value >= 1e6:  # Million
            return f"${actual_value/1e6:.2f}M"
        elif actual_value >= 1e3:  # Thousand
            return f"${actual_value/1e3:.2f}K"
        else:
            return f"${actual_value:,.2f}"
    except Exception:
        return val

def format_finviz_market_cap(val):
    """
    Format Finviz 'Market Cap' values to $ + T/B/M/K.
    Handles both pre-formatted strings (e.g., '3.42T', '$750B') and numeric values where:
    - Large numeric (>= 1e6) is treated as millions (e.g., 3416257.65 -> 3,416,257.65M -> $3.42T)
    - Smaller numeric (< 1e6) is treated as billions (e.g., 3416.26 -> 3,416.26B -> $3.42T)
    """
    try:
        if val is None or val == '' or str(val).strip().upper() == 'N/A':
            return 'N/A'
        s = str(val).strip()
        # If already formatted with suffix
        if s.startswith('$') and s[-1] in ('T','B','M','K'):
            return s
        if (not s.startswith('$')) and s[-1] in ('T','B','M','K'):
            return f"${s}"
        # Parse numeric and infer scale
        f = float(s)
        if math.isnan(f) or math.isinf(f):
            return 'N/A'
        # Heuristic:
        # - Very large numbers (>= 1e13) assume already dollars
        # - Numbers >= 1e6 likely millions value from Finviz CSV
        # - Numbers < 1e6 likely billions value from Finviz CSV
        if f >= 1e13:
            actual_value = f
        elif f >= 1e6:
            actual_value = f * 1_000_000.0   # treat as millions
        else:
            actual_value = f * 1_000_000_000.0  # treat as billions
        if actual_value >= 1e12:
            return f"${actual_value/1e12:.2f}T"
        if actual_value >= 1e9:
            return f"${actual_value/1e9:.2f}B"
        if actual_value >= 1e6:
            return f"${actual_value/1e6:.2f}M"
        if actual_value >= 1e3:
            return f"${actual_value/1e3:.2f}K"
        return f"${actual_value:,.2f}"
    except Exception:
        return 'N/A'

def convert_ui_date_to_iso(ui_date):
    """
    Convert UI date format (YYYY-MM-DD) to ISO format (YYYY-MM-DD)
    Since UI now sends ISO format, this function validates and returns the same format
    """
    if not ui_date or ui_date.strip() == '':
        return None
    
    try:
        # Parse YYYY-MM-DD format (ISO format)
        date_obj = datetime.strptime(ui_date.strip(), '%Y-%m-%d')
        # Return the same format (already in ISO format)
        return date_obj.strftime('%Y-%m-%d')
    except ValueError as e:
        logging.warning(f"Invalid date format '{ui_date}': {e}")
        return None

def load_stocks():
    import json
    import os
    stock_path = 'stock.json'
    if not os.path.exists(stock_path):
        return []
    with open(stock_path, 'r') as f:
        return json.load(f)

def save_stocks(stocks):
    import json
    import os
    stock_path = 'stock.json'
    try:
        with open(stock_path, 'w') as f:
            json.dump(stocks, f, indent=2)
        logging.info(f"Successfully saved {len(stocks)} stocks to {stock_path}")
    except Exception as e:
        logging.error(f"Error saving stocks to {stock_path}: {e}")
        raise e

def load_sectors():
    import json
    import os
    sector_path = 'sector.json'
    if not os.path.exists(sector_path):
        return []
    with open(sector_path, 'r') as f:
        return json.load(f)

def save_sectors(sectors):
    import json
    sector_path = 'sector.json'
    with open(sector_path, 'w') as f:
        json.dump(sectors, f, indent=2)

def load_users():
    import json
    import os
    user_path = 'user.json'
    if not os.path.exists(user_path):
        return []
    with open(user_path, 'r') as f:
        return json.load(f)

def save_users(users):
    import json
    user_path = 'user.json'
    with open(user_path, 'w') as f:
        json.dump(users, f, indent=2) 