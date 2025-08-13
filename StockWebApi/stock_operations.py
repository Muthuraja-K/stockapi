import json
import os
from typing import List, Dict, Any, Optional, Tuple

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
        
        new_stock = {
            'ticker': ticker.upper(),
            'sector': sector,
            'isleverage': isleverage
        }
        
        stocks.append(new_stock)
        
        if save_stocks(stocks):
            return True, f"Stock {ticker} added successfully"
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
        
        # Update the stock
        stocks[stock_index] = {
            'ticker': new_ticker.upper(),
            'sector': sector,
            'isleverage': isleverage
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
