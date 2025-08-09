import json
import logging
import threading
from typing import List, Dict, Any

def load_stocks():
    """Load stocks from stock.json file"""
    try:
        with open('stock.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_stocks(stocks):
    """Save stocks to stock.json file"""
    with open('stock.json', 'w') as file:
        json.dump(stocks, file, indent=2)

def update_ticker_today_background():
    """Update Ticker_Today.json in the background thread"""
    try:
        from enhanced_stock_operations import force_update_ticker_today_data
        force_update_ticker_today_data()
        logging.info("Ticker_Today.json updated successfully in background")
    except Exception as e:
        logging.error(f"Failed to update Ticker_Today.json in background: {e}")

def start_background_update():
    """Start Ticker_Today.json update in background thread"""
    thread = threading.Thread(target=update_ticker_today_background, daemon=True)
    thread.start()
    logging.info("Started background Ticker_Today.json update")

def get_stock_with_filters(sector_param, ticker_param, isxticker_param, page, per_page):
    """
    Get stocks with filtering and pagination
    """
    stocks = load_stocks()
    
    # Filter by sector
    if sector_param:
        stocks = [stock for stock in stocks if stock.get('sector', '').lower() == sector_param.lower()]
    
    # Filter by ticker
    if ticker_param:
        stocks = [stock for stock in stocks if ticker_param.lower() in stock.get('ticker', '').lower()]
    
    # Filter by isxticker
    if isxticker_param is not None:
        stocks = [stock for stock in stocks if stock.get('isxticker', False) == isxticker_param]
    
    # Calculate pagination
    total = len(stocks)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_stocks = stocks[start_index:end_index]
    
    return {
        'results': paginated_stocks,
        'total': total,
        'page': page,
        'per_page': per_page
    }

def get_stock_details(tickers_param, sector_param, isxticker_param, sort_by=None, sort_order='asc'):
    """
    Get detailed stock information with filtering and sorting
    """
    stocks = load_stocks()
    
    # Filter by tickers
    if tickers_param:
        requested_tickers = [t.strip().upper() for t in tickers_param.split(',') if t.strip()]
        stocks = [stock for stock in stocks if stock['ticker'].upper() in requested_tickers]
    
    # Filter by sector
    if sector_param:
        stocks = [stock for stock in stocks if stock['sector'].lower() == sector_param.lower()]
    
    # Filter by isxticker
    if isxticker_param is not None:
        stocks = [stock for stock in stocks if stock['isxticker'] == isxticker_param]
    
    # Sort results
    if sort_by and stocks:
        try:
            reverse = sort_order.lower() == 'desc'
            stocks.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        except Exception as e:
            logging.error(f"Error sorting results: {e}")
    
    return {
        'results': stocks,
        'total': len(stocks)
    }

def add_stock_to_file(ticker, sector, isxticker):
    """Add a new stock to the stock.json file"""
    try:
        stocks = load_stocks()
        
        # Check if ticker already exists
        if any(stock['ticker'].upper() == ticker.upper() for stock in stocks):
            return False, f"Ticker {ticker} already exists"
        
        # Add new stock
        new_stock = {
            'ticker': ticker.upper(),
            'sector': sector,
            'isxticker': isxticker
        }
        stocks.append(new_stock)
        save_stocks(stocks)
        
        # Update Ticker_Today.json with the new stock in background
        start_background_update()
        
        logging.info(f"Added stock: {ticker}")
        return True, f"Stock {ticker} added successfully"
    except Exception as e:
        logging.error(f"Error adding stock {ticker}: {e}")
        return False, f"Error adding stock: {str(e)}"

def update_stock_in_file(old_ticker, sector, isxticker, new_ticker=None):
    """Update an existing stock in the stock.json file"""
    try:
        stocks = load_stocks()
        
        # Find the stock to update
        stock_index = None
        for i, stock in enumerate(stocks):
            if stock['ticker'].upper() == old_ticker.upper():
                stock_index = i
                break
        
        if stock_index is None:
            return False, f"Ticker {old_ticker} not found"
        
        # Check if new ticker already exists (if changing ticker)
        if new_ticker and new_ticker.upper() != old_ticker.upper():
            if any(stock['ticker'].upper() == new_ticker.upper() for stock in stocks):
                return False, f"Ticker {new_ticker} already exists"
        
        # Update the stock
        updated_ticker = new_ticker.upper() if new_ticker else old_ticker.upper()
        stocks[stock_index] = {
            'ticker': updated_ticker,
            'sector': sector,
            'isxticker': isxticker
        }
        
        save_stocks(stocks)
        
        # Update Ticker_Today.json with the updated stock in background
        start_background_update()
        
        logging.info(f"Updated stock: {old_ticker} -> {updated_ticker}")
        return True, f"Stock {old_ticker} updated successfully"
    except Exception as e:
        logging.error(f"Error updating stock {old_ticker}: {e}")
        return False, f"Error updating stock: {str(e)}"

def delete_stock_from_file(ticker):
    """Delete a stock from the stock.json file"""
    try:
        stocks = load_stocks()
        
        # Find and remove the stock
        original_count = len(stocks)
        stocks = [stock for stock in stocks if stock['ticker'].upper() != ticker.upper()]
        
        if len(stocks) == original_count:
            return False, f"Ticker {ticker} not found"
        
        save_stocks(stocks)
        
        # Update Ticker_Today.json after deleting the stock in background
        start_background_update()
        
        logging.info(f"Deleted stock: {ticker}")
        return True, f"Stock {ticker} deleted successfully"
    except Exception as e:
        logging.error(f"Error deleting stock {ticker}: {e}")
        return False, f"Error deleting stock: {str(e)}"