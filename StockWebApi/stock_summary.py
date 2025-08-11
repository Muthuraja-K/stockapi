import yfinance as yf
import logging
import pandas as pd
from datetime import datetime, timedelta
from pandas import Timestamp
from utils import load_stocks, fmt_currency, fmt_percent, convert_ui_date_to_iso
import concurrent.futures
from typing import List, Dict, Any, Tuple
import time
from api_rate_limiter import enforce_rate_limit, safe_yfinance_call

# Global cache for stock summary data
_summary_cache = {}
_summary_cache_ttl = 300  # 5 minutes cache TTL
_max_summary_cache_size = 500  # Maximum number of cached items

# Remove old rate limiting variables and functions - now using centralized rate limiter

def cleanup_summary_cache():
    """Clean up expired cache entries and limit cache size"""
    global _summary_cache
    current_time = time.time()
    
    # Remove expired entries
    expired_keys = [
        key for key, (_, timestamp) in _summary_cache.items() 
        if current_time - timestamp > _summary_cache_ttl
    ]
    for key in expired_keys:
        del _summary_cache[key]
    
    # Limit cache size by removing oldest entries
    if len(_summary_cache) > _max_summary_cache_size:
        # Sort by timestamp and remove oldest entries
        sorted_items = sorted(_summary_cache.items(), key=lambda x: x[1][1])
        items_to_remove = len(_summary_cache) - _max_summary_cache_size
        for i in range(items_to_remove):
            del _summary_cache[sorted_items[i][0]]
    
    logging.info(f"Summary cache cleanup: {len(expired_keys)} expired entries removed, cache size: {len(_summary_cache)}")

def get_cached_summary_data(symbol: str, date_from_iso: str, date_to_iso: str) -> Tuple[Dict, pd.DataFrame]:
    """Get stock summary data from cache or fetch from API"""
    cache_key = f"{symbol}_{date_from_iso}_{date_to_iso}"
    current_time = time.time()
    
    # Periodic cache cleanup
    if len(_summary_cache) > _max_summary_cache_size * 0.8:  # Cleanup when 80% full
        cleanup_summary_cache()
    
    # Check if we have cached data that's still valid
    if cache_key in _summary_cache:
        cached_data, timestamp = _summary_cache[cache_key]
        if current_time - timestamp < _summary_cache_ttl:
            return cached_data
    
    # Fetch fresh data using centralized rate limiter
    try:
        # Use centralized rate limiting
        enforce_rate_limit()
        
        # Use safe yfinance call instead of direct yf.Ticker
        ticker_info = safe_yfinance_call(symbol, "info")
        
        # Determine the date range for historical data
        if date_from_iso and date_to_iso:
            # Both dates provided
            original_start_date = Timestamp(date_from_iso)
            original_end_date = Timestamp(date_to_iso)
            
            # Check if it's the same date
            if date_from_iso == date_to_iso:
                # Same date scenario - get data for that specific date plus some buffer for comparison
                logging.info(f"Stock summary same date scenario for {symbol}: date={date_from_iso}")
                start_date = original_start_date - timedelta(days=5)  # Get 5 days before for comparison
                end_date = original_end_date + timedelta(days=1)      # Get the target date
                hist = safe_yfinance_call(symbol, "history")
            else:
                # Different dates - subtract one day from from_date as requested
                start_date = original_start_date - timedelta(days=1)
                end_date = original_end_date
                buffer_end = end_date + timedelta(days=1)
                logging.info(f"Stock summary date range for {symbol}: original_from={date_from_iso}, adjusted_from={start_date.strftime('%Y-%m-%d')}, to={date_to_iso}")
                hist = safe_yfinance_call(symbol, "history")
            
            # If the actual start date in the data is different from our requested start date,
            # it means Yahoo Finance adjusted for weekends/holidays. This is expected behavior.
            if not hist.empty and len(hist) > 0:
                logging.info(f"Yahoo Finance data for {symbol}: actual_start={hist.index[0].strftime('%Y-%m-%d')}, actual_end={hist.index[-1].strftime('%Y-%m-%d')}")
        elif date_from_iso:
            # Only start date provided - subtract one day from from_date
            original_start_date = Timestamp(date_from_iso)
            start_date = original_start_date - timedelta(days=1)
            buffer_start = start_date - timedelta(days=5)
            logging.info(f"Stock summary date range for {symbol}: original_from={date_from_iso}, adjusted_from={start_date.strftime('%Y-%m-%d')}")
            hist = safe_yfinance_call(symbol, "history")
        elif date_to_iso:
            # Only end date provided
            end_date = Timestamp(date_to_iso)
            buffer_end = end_date + timedelta(days=5)
            logging.info(f"Stock summary date range for {symbol}: to={date_to_iso}")
            hist = safe_yfinance_call(symbol, "history")
        else:
            # No dates provided - use last year
            logging.info(f"Stock summary date range for {symbol}: using last year")
            hist = safe_yfinance_call(symbol, "history")
        
        # Cache the data
        _summary_cache[cache_key] = ((ticker_info, hist), current_time)
        
        return ticker_info, hist
    except Exception as e:
        logging.error(f"Error fetching summary data for {symbol}: {e}")
        return None, None

def process_single_stock_summary(stock: Dict, date_from_iso: str, date_to_iso: str, sector: str) -> Dict[str, Any]:
    """
    Process a single stock to get its summary information
    This function will be called in parallel
    Optimized for performance with caching and reduced API calls
    """
    try:
        # Get cached or fresh data
        data = get_cached_summary_data(stock['ticker'], date_from_iso, date_to_iso)
        if data is None:
            return None
        
        info, hist = data
        
        if hist is None or hist.empty:
            return None

        current_price = info.get('currentPrice', 0)
        if not current_price or current_price <= 0:
            return None

        # Optimize price calculations
        start_date_close_price = hist['Close'].iloc[0] if not hist.empty else 0
        end_date_close_price = hist['Close'].iloc[-1] if not hist.empty else 0

        # Calculate percentage change based on start and end closing prices
        percentage_change = 0
        if start_date_close_price > 0 and end_date_close_price > 0:
            percentage_change = ((end_date_close_price - start_date_close_price) / start_date_close_price) * 100
            
        # For same date scenarios, also provide intraday change information
        if date_from_iso == date_to_iso and not hist.empty:
            # Try to get intraday change (high - low) as a percentage for same date
            target_date_data = None
            target_date = Timestamp(date_from_iso)
            
            # Find data for the target date
            for idx, date in enumerate(hist.index):
                if date.date() == target_date.date():
                    target_date_data = hist.iloc[idx]
                    break
            
            if target_date_data is not None:
                # Use the target date's open vs close for percentage change
                open_price = target_date_data['Open']
                close_price = target_date_data['Close']
                if open_price > 0:
                    percentage_change = ((close_price - open_price) / open_price) * 100
                    logging.info(f"Same date percentage change for {stock['ticker']}: open={open_price}, close={close_price}, change={percentage_change}%")
                
                # Update prices to reflect the same date
                start_date_close_price = open_price
                end_date_close_price = close_price

        return {
            'ticker': stock['ticker'],
            'currentPrice': fmt_currency(current_price),
            'startDateClosePrice': fmt_currency(start_date_close_price),
            'endDateClosePrice': fmt_currency(end_date_close_price),
            'percentageChange': fmt_percent(round(percentage_change, 2)),
            'sector': sector,
            'isxticker': stock.get('isxticker', False),
            'raw_percentage': float(percentage_change)  # For calculating averages
        }

    except Exception as e:
        logging.error(f"Error processing stock {stock['ticker']}: {e}")
        return None

def process_sector_stocks(sector_stocks: List[Dict], date_from_iso: str, date_to_iso: str, sector: str) -> Tuple[str, List[Dict], float]:
    """
    Process all stocks in a sector using parallel processing
    Returns: (sector_name, stock_data_list, total_percentage)
    """
    if not sector_stocks:
        return sector, [], 0

    # Process stocks in parallel with reduced workers to avoid rate limiting
    max_workers = min(5, len(sector_stocks))  # Reduced from 30 to 5 to avoid rate limits
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks for this sector
        future_to_stock = {
            executor.submit(process_single_stock_summary, stock, date_from_iso, date_to_iso, sector): stock 
            for stock in sector_stocks
        }
        
        # Collect results as they complete
        sector_data = []
        total_percentage = 0
        valid_percentages = 0
        
        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                result = future.result()
                if result is not None:
                    sector_data.append(result)
                    if 'raw_percentage' in result:
                        total_percentage += result['raw_percentage']
                        valid_percentages += 1
                        # Remove raw_percentage from final result
                        del result['raw_percentage']
                    logging.info(f"Completed processing for {stock['ticker']} in sector {sector}")
                    # Add small delay between completions to avoid rate limiting
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"Exception occurred while processing {stock['ticker']}: {e}")
                continue

    return sector, sector_data, total_percentage if valid_percentages > 0 else 0

def get_stock_summary(sectors_param, isxticker_param, date_from_param, date_to_param):
    """
    Get stock summary grouped by sectors with filtering and date range support
    Now uses parallel processing for better performance with batch processing
    """
    stocks = load_stocks()

    # Convert UI date format to ISO format
    date_from_iso = convert_ui_date_to_iso(date_from_param)
    date_to_iso = convert_ui_date_to_iso(date_to_param)
    
    logging.info(f"Date validation: from='{date_from_param}' -> '{date_from_iso}', to='{date_to_param}' -> '{date_to_iso}'")

    # Filter stocks by sectors if provided
    filtered_stocks = stocks
    if sectors_param:
        requested_sectors = [s.strip().lower() for s in sectors_param.split(',') if s.strip()]
        filtered_stocks = [stock for stock in stocks if stock.get('sector', '').lower() in requested_sectors]

    # Filter stocks by isxticker if provided
    if isxticker_param is not None:
        isxticker_bool = str(isxticker_param).lower() == 'true'
        filtered_stocks = [stock for stock in filtered_stocks if stock.get('isxticker', False) == isxticker_bool]

    # Group stocks by sector
    sector_groups = {}
    for stock in filtered_stocks:
        sector = stock.get('sector', 'Unknown')
        if sector not in sector_groups:
            sector_groups[sector] = []
        sector_groups[sector].append(stock)

    # Process each sector group in parallel with batch processing
    results = []
    max_sector_workers = min(5, len(sector_groups))  # Reduced from 20 to 5 to avoid rate limits
    batch_size = 30  # Process stocks in batches of 30 per sector
    
    logging.info(f"Processing {len(sector_groups)} sectors with {max_sector_workers} workers in batches of {batch_size}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_sector_workers) as executor:
        # Submit all sector processing tasks
        future_to_sector = {
            executor.submit(process_sector_stocks_batched, sector_stocks, date_from_iso, date_to_iso, sector, batch_size): sector 
            for sector, sector_stocks in sector_groups.items()
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_sector):
            sector = future_to_sector[future]
            try:
                sector_name, sector_data, total_percentage = future.result()
                
                if sector_data:
                    # Calculate average percentage for the sector
                    valid_percentages = len([s for s in sector_data if 'percentageChange' in s])
                    average_percentage = '0%'
                    if valid_percentages > 0:
                        avg_pct = total_percentage / valid_percentages
                        average_percentage = fmt_percent(round(avg_pct, 2))

                    sector_result = {
                        'sector': sector_name,
                        'averagePercentage': average_percentage,
                        'stocks': sector_data
                    }
                    results.append(sector_result)
                    logging.info(f"Completed processing sector {sector_name} with {len(sector_data)} stocks")
                    
            except Exception as e:
                logging.error(f"Exception occurred while processing sector {sector}: {e}")
                continue

    return results

def process_sector_stocks_batched(sector_stocks: List[Dict], date_from_iso: str, date_to_iso: str, sector: str, batch_size: int = 30) -> Tuple[str, List[Dict], float]:
    """
    Process all stocks in a sector using parallel processing with batch processing
    Returns: (sector_name, stock_data_list, total_percentage)
    """
    if not sector_stocks:
        return sector, [], 0

    # Process stocks in parallel with batch processing
    max_workers = min(40, len(sector_stocks))  # Further increased for batch processing
    sector_data = []
    total_percentage = 0
    valid_percentages = 0
    
    # Process in batches to avoid overwhelming the API
    for i in range(0, len(sector_stocks), batch_size):
        batch_stocks = sector_stocks[i:i + batch_size]
        batch_workers = min(max_workers, len(batch_stocks))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_workers) as executor:
            # Submit batch tasks for this sector
            future_to_stock = {
                executor.submit(process_single_stock_summary, stock, date_from_iso, date_to_iso, sector): stock 
                for stock in batch_stocks
            }
            
            # Collect batch results as they complete
            for future in concurrent.futures.as_completed(future_to_stock):
                stock = future_to_stock[future]
                try:
                    result = future.result()
                    if result is not None:
                        sector_data.append(result)
                        if 'raw_percentage' in result:
                            total_percentage += result['raw_percentage']
                            valid_percentages += 1
                            # Remove raw_percentage from final result
                            del result['raw_percentage']
                        logging.info(f"Completed processing for {stock['ticker']} in sector {sector}")
                except Exception as e:
                    logging.error(f"Exception occurred while processing {stock['ticker']}: {e}")
                    continue
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < len(sector_stocks):
            time.sleep(0.1)

    return sector, sector_data, total_percentage if valid_percentages > 0 else 0