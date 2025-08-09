import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
from utils import load_stocks

def get_earning_summary(sectors_param=None, date_from_param=None, date_to_param=None, page=1, per_page=10):
    """
    Get earning summary data with filtering and pagination.
    
    Args:
        sectors_param: Comma-separated string of sectors to filter by
        date_from_param: Start date for earning date filter (YYYY-MM-DD)
        date_to_param: End date for earning date filter (YYYY-MM-DD)
        page: Page number for pagination
        per_page: Number of items per page
    
    Returns:
        Dictionary with paginated earning data
    """
    try:
        # Load stocks from the JSON file
        stocks_data = load_stocks()
        if not stocks_data:
            logging.error("No stocks data found")
            return {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "results": []
            }
        
        # Filter by sectors if provided and filter out stocks where isxticker is false
        filtered_stocks = stocks_data
        if sectors_param:
            sectors_list = [s.strip() for s in sectors_param.split(',')]
            filtered_stocks = [stock for stock in stocks_data if stock.get('sector', '') in sectors_list]
        
        # Filter out stocks where isxticker is false
        filtered_stocks = [stock for stock in filtered_stocks if stock.get('isxticker', False) == False]
        
        # Get earning data for filtered stocks
        earning_data = []
        for stock in filtered_stocks:
            try:
                ticker = stock.get('ticker', '')
                if not ticker:
                    continue
                
                # Get stock info from yfinance
                yf_ticker = yf.Ticker(ticker)
                info = yf_ticker.info
                
                # Get current price
                current_price = info.get('currentPrice', 0)
                if current_price is None or current_price == 0:
                    # Try to get from historical data
                    hist = yf_ticker.history(period="1d")
                    if not hist.empty:
                        current_price = hist.iloc[-1]['Close']
                    else:
                        current_price = 0
                
                # Get earning date (next earnings date)
                earning_date = info.get('earningsTimestamp', None)
                if earning_date:
                    # Convert timestamp to date string
                    if isinstance(earning_date, (int, float)):
                        earning_date = datetime.fromtimestamp(earning_date).strftime('%Y-%m-%d')
                    else:
                        earning_date = earning_date.strftime('%Y-%m-%d')
                else:
                    # If no earnings date available, skip this stock
                    continue
                
                # Apply date range filter if provided
                if date_from_param or date_to_param:
                    earning_date_obj = datetime.strptime(earning_date, '%Y-%m-%d')
                    
                    if date_from_param:
                        date_from = datetime.strptime(date_from_param, '%Y-%m-%d')
                        if earning_date_obj < date_from:
                            continue
                    
                    if date_to_param:
                        date_to = datetime.strptime(date_to_param, '%Y-%m-%d')
                        if earning_date_obj > date_to:
                            continue
                
                earning_data.append({
                    "ticker": ticker,
                    "currentPrice": f"${current_price:.2f}" if current_price > 0 else "N/A",
                    "earningDate": earning_date,
                    "sector": stock.get('sector', 'Unknown')
                })
                
            except Exception as e:
                logging.warning(f"Error fetching data for {ticker}: {str(e)}")
                continue
        
        # Apply pagination
        total = len(earning_data)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_data = earning_data[start_index:end_index]
        
        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "results": paginated_data
        }
        
    except Exception as e:
        logging.error(f"Error in get_earning_summary: {str(e)}")
        return {
            "page": page,
            "per_page": per_page,
            "total": 0,
            "results": []
        } 