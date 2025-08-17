import json
import os
import requests
from typing import List, Dict, Any, Optional, Tuple

def get_company_name_from_finviz(ticker: str) -> str:
    """Get company name from Finviz CSV export API"""
    try:
        # Use the Finviz CSV export API for more reliable data
        url = f"https://elite.finviz.com/export.ashx?v=152&t={ticker}&auth=22a5d2df-8313-42f4-b2ab-cab5e0f26758"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse CSV response
        csv_content = response.text.strip()
        if not csv_content:
            return "Unknown Company"
        
        # Split by lines and get the data row (skip header)
        lines = csv_content.split('\n')
        if len(lines) < 2:
            return "Unknown Company"
        
        # Parse the data row (second line)
        data_line = lines[1]
        
        # Handle CSV parsing more carefully - split by "," and handle quoted fields
        data_parts = []
        current_part = ""
        in_quotes = False
        
        for char in data_line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                data_parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
        
        # Add the last part
        data_parts.append(current_part.strip())
        
        if len(data_parts) >= 3:  # Ensure we have enough columns
            company_name = data_parts[2]  # Company name is in the 3rd column (index 2)
            if company_name and company_name != "N/A" and company_name != "Unknown Company":
                return company_name
        
        return "Unknown Company"
        
    except Exception as e:
        print(f"Error getting company name for {ticker} from Finviz CSV API: {str(e)}")
        return "Unknown Company"

def load_stocks() -> List[Dict[str, Any]]:
    """Load stocks from the JSON file"""
    try:
        if os.path.exists('stock.json'):
            with open('stock.json', 'r') as file:
                return json.load(file)
        else:
            return []
    except Exception as e:
        print(f"Error loading stocks: {e}")
        return []

def save_stocks(stocks: List[Dict[str, Any]]) -> bool:
    """Save stocks to the JSON file"""
    try:
        with open('stock.json', 'w') as file:
            json.dump(stocks, file, indent=2)
        return True
    except Exception as e:
        print(f"Error saving stocks: {e}")
        return False

def get_stock_with_filters(sector: str = "", ticker: str = "", isleverage: Optional[bool] = None, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """Get stocks with filtering and pagination"""
    stocks = load_stocks()
    
    # Apply filters
    filtered_stocks = stocks
    
    if sector:
        filtered_stocks = [s for s in filtered_stocks if s.get('sector', '').lower() == sector.lower()]
    
    if ticker:
        filtered_stocks = [s for s in filtered_stocks if s.get('ticker', '').lower().startswith(ticker.lower())]
    
    if isleverage is not None:
        filtered_stocks = [s for s in filtered_stocks if s.get('isleverage', False) == isleverage]
    
    # Apply pagination
    total = len(filtered_stocks)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_stocks = filtered_stocks[start_index:end_index]
    
    return {
        'results': paginated_stocks,
        'total': total,
        'page': page,
        'per_page': per_page
    }

def get_stock_details(tickers: str = "", sector: str = "", isleverage: Optional[bool] = None, sort_by: Optional[str] = None, sort_order: str = "asc") -> List[Dict[str, Any]]:
    """Get stock details with filtering and sorting"""
    stocks = load_stocks()
    
    # Apply filters
    filtered_stocks = stocks
    
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
        filtered_stocks = [s for s in filtered_stocks if s.get('ticker', '').upper() in ticker_list]
    
    if sector:
        filtered_stocks = [s for s in filtered_stocks if s.get('sector', '').lower() == sector.lower()]
    
    if isleverage is not None:
        filtered_stocks = [s for s in filtered_stocks if s.get('isleverage', False) == isleverage]
    
    # Apply sorting
    if sort_by:
        reverse = sort_order.lower() == "desc"
        try:
            filtered_stocks.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        except:
            # If sorting fails, keep original order
            pass
    
    return filtered_stocks

def add_stock_to_file(ticker: str, sector: str, isleverage: bool = False) -> Tuple[bool, str]:
    """Add a new stock to the file"""
    try:
        stocks = load_stocks()
        
        # Check if ticker already exists
        if any(s.get('ticker', '').upper() == ticker.upper() for s in stocks):
            return False, f"Stock with ticker {ticker} already exists"
        
        # Automatically fetch company name from Finviz
        print(f"Fetching company name for {ticker} from Finviz...")
        company_name = get_company_name_from_finviz(ticker)
        print(f"Company name for {ticker}: {company_name}")
        
        new_stock = {
            'ticker': ticker.upper(),
            'sector': sector,
            'isleverage': isleverage,
            'company_name': company_name
        }
        
        stocks.append(new_stock)
        
        if save_stocks(stocks):
            return True, f"Stock {ticker} added successfully with company name: {company_name}"
        else:
            return False, "Failed to save stocks"
            
    except Exception as e:
        return False, f"Error adding stock: {str(e)}"

def update_stock_in_file(old_ticker: str, sector: str, isleverage: bool, new_ticker: str) -> Tuple[bool, str]:
    """Update a stock in the file"""
    try:
        stocks = load_stocks()
        
        # Find the stock to update
        stock_index = None
        for i, s in enumerate(stocks):
            if s.get('ticker', '').upper() == old_ticker.upper():
                stock_index = i
                break
        
        if stock_index is None:
            return False, f"Stock with ticker {old_ticker} not found"
        
        # Check if new ticker already exists (if changing ticker)
        if new_ticker.upper() != old_ticker.upper():
            if any(s.get('ticker', '').upper() == new_ticker.upper() for s in stocks):
                return False, f"Stock with ticker {new_ticker} already exists"
            
            # If ticker is changing, fetch new company name from Finviz
            print(f"Fetching company name for new ticker {new_ticker} from Finviz...")
            company_name = get_company_name_from_finviz(new_ticker)
            print(f"Company name for {new_ticker}: {company_name}")
        else:
            # Keep existing company name if ticker is not changing
            company_name = stocks[stock_index].get('company_name', 'Unknown Company')
        
        # Update the stock
        stocks[stock_index] = {
            'ticker': new_ticker.upper(),
            'sector': sector,
            'isleverage': isleverage,
            'company_name': company_name
        }
        
        if save_stocks(stocks):
            return True, f"Stock {old_ticker} updated successfully to {new_ticker}"
        else:
            return False, "Failed to save stocks"
            
    except Exception as e:
        return False, f"Error updating stock: {str(e)}"

def delete_stock_from_file(ticker: str) -> Tuple[bool, str]:
    """Delete a stock from the file"""
    try:
        stocks = load_stocks()
        
        # Find and remove the stock
        original_count = len(stocks)
        stocks = [s for s in stocks if s.get('ticker', '').upper() != ticker.upper()]
        
        if len(stocks) == original_count:
            return False, f"Stock with ticker {ticker} not found"
        
        if save_stocks(stocks):
            return True, f"Stock {ticker} deleted successfully"
        else:
            return False, "Failed to save stocks"
            
    except Exception as e:
        return False, f"Error deleting stock: {str(e)}"
