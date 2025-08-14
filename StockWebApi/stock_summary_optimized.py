"""
Optimized Stock Summary Module
Fetches data for all stocks at once using batch operations and date ranges
Minimizes API calls by leveraging batch processing infrastructure
"""

# import yfinance as yf  # Not needed - using proxy system
import logging
import pandas as pd
from datetime import datetime, timedelta
from pandas import Timestamp
from utils import load_stocks, fmt_currency, fmt_percent, convert_ui_date_to_iso
# import concurrent.futures  # Not needed - using batch processing
from typing import List, Dict, Any, Tuple
import time
import json
import os
# from api_rate_limiter import safe_yfinance_call  # Not needed - using proxy system
from yahoo_finance_proxy import get_batch_ticker_info
import math

# Global cache for stock summary data
_summary_cache = {}
_summary_cache_ttl = 300  # 5 minutes cache TTL
_max_summary_cache_size = 500  # Maximum number of cached items

# Today filter cache - 1 minute TTL
_today_cache = {}
_today_cache_ttl = 60  # 1 minute cache TTL
_today_cache_file = "today_filter_cache.json"

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
            del _summary_cache[sorted_items[i]]
    
    logging.info(f"Summary cache cleanup: {len(expired_keys)} expired entries removed, cache size: {len(_summary_cache)}")

def cleanup_today_cache():
    """Clean up expired today filter cache entries"""
    global _today_cache
    current_time = time.time()
    
    # Remove expired entries
    expired_keys = [
        key for key, (_, timestamp) in _today_cache.items() 
        if current_time - timestamp > _today_cache_ttl
    ]
    for key in expired_keys:
        del _today_cache[key]
    
    logging.info(f"Today filter cache cleanup: {len(expired_keys)} expired entries removed, cache size: {len(_today_cache)}")

def get_today_cache_key(sectors_param: str, isleverage_param: bool) -> str:
    """Generate cache key for today filter data"""
    sectors_str = sectors_param if sectors_param else "all_sectors"
    
    # Handle leverage filter - None defaults to False (Ticker Only)
    if isleverage_param is None:
        leverage_str = "false"  # Default to "Ticker Only"
    else:
        leverage_str = str(isleverage_param).lower()
    
    return f"today_{sectors_str}_{leverage_str}"

def is_today_cache_valid(cache_key: str) -> bool:
    """Check if today filter cache is still valid (within 1 minute)"""
    global _today_cache
    cleanup_today_cache()  # Clean up expired entries first
    
    if cache_key not in _today_cache:
        return False
    
    _, timestamp = _today_cache[cache_key]
    current_time = time.time()
    return (current_time - timestamp) <= _today_cache_ttl

def get_today_cached_data(cache_key: str) -> List[Dict]:
    """Get cached today filter data if available and valid"""
    if is_today_cache_valid(cache_key):
        data, _ = _today_cache[cache_key]
        logging.info(f"Returning cached today filter data for key: {cache_key}")
        return data
    return None

def cache_today_data(cache_key: str, data: List[Dict]):
    """Cache today filter data with current timestamp"""
    global _today_cache
    current_time = time.time()
    _today_cache[cache_key] = (data, current_time)
    logging.info(f"Cached today filter data for key: {cache_key}")

def get_batch_stock_data_based_on_dates(stocks: List[Dict], date_from_iso: str, date_to_iso: str) -> Dict[str, Dict]:
    """
    Get data for all stocks at once based on date range
    Uses batch processing to minimize API calls
    """
    if not stocks:
        return {}
    
    # Extract ticker symbols
    tickers = [stock['ticker'] for stock in stocks]
    logging.info(f"Fetching batch data for {len(tickers)} tickers from {date_from_iso} to {date_to_iso}")
    
    try:
        # Get batch data using the existing optimized infrastructure
        batch_data = get_batch_ticker_info(tickers)
        
        # Process the batch data to extract date-specific information
        processed_data = {}
        
        for ticker, data in batch_data.items():
            if not data:
                continue
            
            # Extract current price and company info
            current_price_raw = data.get('current_price', 0)
            company_name = data.get('company_name', 'N/A')
            market_cap = data.get('market_cap', 'N/A')
            
            # Convert current_price from formatted string to float
            try:
                if isinstance(current_price_raw, str):
                    # Remove currency symbols and commas, convert to float
                    current_price = float(current_price_raw.replace('$', '').replace(',', ''))
                else:
                    current_price = float(current_price_raw)
                    
                # Validate the current price
                if math.isnan(current_price) or math.isinf(current_price) or current_price <= 0:
                    logging.debug(f"Skipping {ticker} - invalid current price: {current_price}")
                    continue
                    
            except (ValueError, TypeError) as e:
                logging.debug(f"Could not convert current_price for {ticker}: {current_price_raw} - {e}")
                continue
            
            # Determine which time period data to use based on date range
            start_date = Timestamp(date_from_iso) if date_from_iso else None
            end_date = Timestamp(date_to_iso) if date_to_iso else None
            
            # Calculate date difference to determine appropriate time period
            if start_date and end_date:
                date_diff = (end_date - start_date).days
            else:
                date_diff = 0
            
            # Select appropriate time period data
            time_period_data = None
            time_period_name = None
            
            if date_diff == 0:
                # Same date - use today's data
                time_period_data = data.get('today', {})
                time_period_name = 'today'
            elif date_diff <= 5:
                # 5 days or less - use five_day data
                time_period_data = data.get('five_day', {})
                time_period_name = 'five_day'
            elif date_diff <= 30:
                # 1 month or less - use one_month data
                time_period_data = data.get('one_month', {})
                time_period_name = 'one_month'
            elif date_diff <= 180:
                # 6 months or less - use six_month data
                time_period_data = data.get('six_month', {})
                time_period_name = 'six_month'
            else:
                # More than 6 months - use one_year data
                time_period_data = data.get('one_year', {})
                time_period_name = 'one_year'
            
            if not time_period_data or not isinstance(time_period_data, dict):
                continue
            
            # Extract percentage change and price data
            percentage_change = time_period_data.get('percentage', '0%')
            low_price = time_period_data.get('low', '$0')
            high_price = time_period_data.get('high', '$0')
            
            # Validate that percentage_change is a valid value
            if not percentage_change or percentage_change == 'N/A' or percentage_change == 'NIL':
                logging.debug(f"Skipping {ticker} - invalid percentage: {percentage_change}")
                continue
            
            # Convert percentage string to float for calculations
            try:
                if isinstance(percentage_change, str):
                    # Remove any non-numeric characters except decimal point and minus sign
                    clean_percentage = percentage_change.replace('%', '').replace('+', '').strip()
                    if not clean_percentage or clean_percentage == 'N/A' or clean_percentage == 'NIL':
                        logging.debug(f"Skipping {ticker} - empty percentage after cleaning: {clean_percentage}")
                        continue
                    percentage_value = float(clean_percentage)
                else:
                    percentage_value = float(percentage_change)
                    
                # Validate the percentage value
                if math.isnan(percentage_value) or math.isinf(percentage_value):
                    logging.debug(f"Skipping {ticker} - invalid percentage value: {percentage_value}")
                    continue
                    
            except (ValueError, TypeError) as e:
                logging.debug(f"Skipping {ticker} - could not convert percentage '{percentage_change}': {e}")
                continue
            
            # Calculate start and end prices based on percentage change
            # For positive change: start_price = current_price / (1 + percentage/100)
            # For negative change: start_price = current_price / (1 - percentage/100)
            try:
                if abs(percentage_value) < 0.01:  # If percentage is very small (less than 0.01%)
                    # Use current price for both start and end to avoid division by very small numbers
                    start_price = current_price
                    end_price = current_price
                elif percentage_value >= 0:
                    start_price = current_price / (1 + percentage_value / 100)
                    end_price = current_price
                else:
                    start_price = current_price / (1 - abs(percentage_value) / 100)
                    end_price = current_price
                
                # Validate that we don't have NaN or infinite values
                if not (isinstance(start_price, (int, float)) and isinstance(end_price, (int, float))):
                    start_price = current_price
                    end_price = current_price
                elif math.isnan(start_price) or math.isnan(end_price) or math.isinf(start_price) or math.isinf(end_price):
                    start_price = current_price
                    end_price = current_price
                    
            except (ZeroDivisionError, ValueError, TypeError) as e:
                logging.warning(f"Error calculating prices for {ticker}: {e}. Using current price for both.")
                start_price = current_price
                end_price = current_price
            
            # Store processed data
            processed_data[ticker] = {
                'start_price': start_price,
                'end_price': end_price,
                'current_price': current_price,
                'company_name': company_name,
                'market_cap': market_cap,
                'sector': data.get('sector', 'Unknown'),
                'isleverage': data.get('isleverage', False),
                'time_period_used': time_period_name,
                'percentage_change': percentage_value
            }
            
            # Log the processed data for debugging
            logging.debug(f"Processed {ticker}: start_price={start_price}, end_price={end_price}, current_price={current_price}, percentage={percentage_value}")
        
        logging.info(f"Successfully processed batch data for {len(processed_data)} tickers")
        return processed_data
        
    except Exception as e:
        logging.error(f"Error in batch data fetching: {e}")
        return {}

def process_stock_summary_from_batch_data(stock: Dict, batch_data: Dict, date_from_iso: str, date_to_iso: str, sector: str) -> Dict[str, Any]:
    """
    Process a single stock summary using pre-fetched batch data
    No API calls needed - all data comes from batch operation
    """
    try:
        ticker = stock['ticker']
        
        if ticker not in batch_data:
            return None
            
        data = batch_data[ticker]
        
        # Extract prices and data
        start_price = data.get('start_price', 0)
        end_price = data.get('end_price', 0)
        current_price = data.get('current_price', 0)
        percentage_change = data.get('percentage_change', 0)
        time_period_used = data.get('time_period_used', 'unknown')
        
        # Validate that all prices are valid numbers
        if not (isinstance(start_price, (int, float)) and isinstance(end_price, (int, float)) and isinstance(current_price, (int, float))):
            logging.warning(f"Invalid price data for {ticker}: start={start_price}, end={end_price}, current={current_price}")
            return None
            
        if not (isinstance(percentage_change, (int, float))):
            logging.warning(f"Invalid percentage data for {ticker}: {percentage_change}")
            return None
        
        # Check for NaN or infinite values
        if math.isnan(start_price) or math.isnan(end_price) or math.isnan(current_price) or math.isnan(percentage_change):
            logging.warning(f"NaN values detected for {ticker}: start={start_price}, end={end_price}, current={current_price}, percentage={percentage_change}")
            return None
            
        if math.isinf(start_price) or math.isinf(end_price) or math.isinf(current_price) or math.isinf(percentage_change):
            logging.warning(f"Infinite values detected for {ticker}: start={start_price}, end={end_price}, current={current_price}, percentage={percentage_change}")
            return None
        
        if not start_price or not end_price or not current_price:
            return None
        
        return {
            'ticker': ticker,
            'currentPrice': fmt_currency(current_price),
            'startDateClosePrice': fmt_currency(start_price),
            'endDateClosePrice': fmt_currency(end_price),
            'percentageChange': fmt_percent(round(percentage_change, 2)),
            'sector': sector,
            'isleverage': stock.get('isleverage', False),
            'raw_percentage': float(percentage_change),  # For calculating averages
            'companyName': data.get('company_name', 'N/A'),
            'marketCap': data.get('market_cap', 'N/A'),
            'timePeriodUsed': time_period_used  # Show which time period was used
        }
        
    except Exception as e:
        logging.error(f"Error processing stock {stock['ticker']} from batch data: {e}")
        return None

def process_sector_stocks_optimized(sector_stocks: List[Dict], batch_data: Dict, date_from_iso: str, date_to_iso: str, sector: str) -> Tuple[str, List[Dict], float]:
    """
    Process all stocks in a sector using pre-fetched batch data
    No API calls needed - all processing is done locally
    """
    if not sector_stocks:
        return sector, [], 0
    
    sector_data = []
    total_percentage = 0
    valid_percentages = 0
    
    # Process all stocks in the sector using batch data
    for stock in sector_stocks:
        try:
            result = process_stock_summary_from_batch_data(stock, batch_data, date_from_iso, date_to_iso, sector)
            if result is not None:
                sector_data.append(result)
                if 'raw_percentage' in result:
                    total_percentage += result['raw_percentage']
                    valid_percentages += 1
                    # Remove raw_percentage from final result
                    del result['raw_percentage']
                    
        except Exception as e:
            logging.error(f"Exception occurred while processing {stock['ticker']}: {e}")
            continue
    
    return sector, sector_data, total_percentage if valid_percentages > 0 else 0

def get_stock_summary_optimized(sectors_param, isleverage_param, date_from_param, date_to_param):
    """
    Get stock summary grouped by sectors with optimized batch processing
    Fetches data for all stocks at once instead of individual API calls
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

    # Filter stocks by leverage - mutually exclusive options:
    # - isleverage_param = False: "Ticker Only" (regular stocks only)
    # - isleverage_param = True: "Leverage Only" (leveraged stocks only)
    # - isleverage_param = None: Default to "Ticker Only" (regular stocks only)
    if isleverage_param is None:
        # Default to "Ticker Only" - show regular stocks only
        isleverage_bool = False
        logging.info("No leverage filter specified, defaulting to 'Ticker Only' (regular stocks)")
    else:
        isleverage_bool = bool(isleverage_param)
        logging.info(f"Leverage filter applied: {'Leverage Only' if isleverage_bool else 'Ticker Only'}")
    
    # Apply the leverage filter
    filtered_stocks = [stock for stock in filtered_stocks if stock.get('isleverage', False) == isleverage_bool]

    logging.info(f"Processing {len(filtered_stocks)} filtered stocks")

    # Fetch data for ALL stocks at once using batch processing
    logging.info("Starting batch data fetch for all stocks...")
    start_time = time.time()
    
    batch_data = get_batch_stock_data_based_on_dates(filtered_stocks, date_from_iso, date_to_iso)
    
    fetch_time = time.time() - start_time
    logging.info(f"Batch data fetch completed in {fetch_time:.2f}s for {len(batch_data)} stocks")

    # Group stocks by sector
    sector_groups = {}
    for stock in filtered_stocks:
        sector = stock.get('sector', 'Unknown')
        if sector not in sector_groups:
            sector_groups[sector] = []
        sector_groups[sector].append(stock)

    # Process each sector group using the batch data
    results = []
    total_processing_time = 0
    
    logging.info(f"Processing {len(sector_groups)} sectors using batch data")
    
    for sector, sector_stocks in sector_groups.items():
        try:
            start_time = time.time()
            
            sector_name, sector_data, total_percentage = process_sector_stocks_optimized(
                sector_stocks, batch_data, date_from_iso, date_to_iso, sector
            )
            
            processing_time = time.time() - start_time
            total_processing_time += processing_time
            
            if sector_data:
                # Calculate average percentage for the sector
                valid_percentages = len([s for s in sector_data if 'percentageChange' in s])
                average_percentage = '0%'
                if valid_percentages > 0 and total_percentage != 0:
                    try:
                        avg_pct = total_percentage / valid_percentages
                        # Validate the average percentage
                        if not math.isnan(avg_pct) and not math.isinf(avg_pct):
                            average_percentage = fmt_percent(round(avg_pct, 2))
                        else:
                            average_percentage = '0%'
                            logging.warning(f"Invalid average percentage for sector {sector_name}: {avg_pct}")
                    except (ZeroDivisionError, ValueError, TypeError) as e:
                        logging.warning(f"Error calculating average percentage for sector {sector_name}: {e}")
                        average_percentage = '0%'

                sector_result = {
                    'sector': sector_name,
                    'averagePercentage': average_percentage,
                    'stocks': sector_data
                }
                results.append(sector_result)
                logging.info(f"Completed processing sector {sector_name} with {len(sector_data)} stocks in {processing_time:.2f}s")
                
        except Exception as e:
            logging.error(f"Exception occurred while processing sector {sector}: {e}")
            continue

    total_time = time.time() - start_time
    logging.info(f"Stock summary processing completed in {total_time:.2f}s (fetch: {fetch_time:.2f}s, processing: {total_processing_time:.2f}s)")
    
    return results

def get_stock_summary_today(sectors_param, isleverage_param):
    """
    Get today's stock summary using Finviz API for real-time data.
    Implements 1-minute caching to minimize API calls.
    
    Args:
        sectors_param: Comma-separated string of sectors to filter by
        isleverage_param: Boolean to filter leveraged stocks
    
    Returns:
        List of sector groups with stock summary data
    """
    try:
        from stock_history_operations import stock_history_ops
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Generate cache key for this request
        cache_key = get_today_cache_key(sectors_param, isleverage_param)
        
        # Check if we have valid cached data
        cached_data = get_today_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"Returning cached today filter data for key: {cache_key}")
            return cached_data
        
        logger.info("Cache expired or missing, fetching fresh today's stock summary using Finviz API")
        
        # Get all stocks from stocks.json
        stocks_data = load_stocks()
        
        if not stocks_data:
            logger.error("No stocks data available")
            return {}
        
        # Filter by sectors if provided - use sectors from stock.json, not from Finviz
        if sectors_param:
            sectors_list = [s.strip() for s in sectors_param.split(',')]
            stocks_data = [
                stock for stock in stocks_data 
                if stock.get('sector', '') in sectors_list
            ]
            logger.info(f"Filtered to {len(stocks_data)} stocks in sectors: {sectors_list}")
        
        # Filter by leverage - mutually exclusive options:
        # - isleverage_param = False: "Ticker Only" (regular stocks only)
        # - isleverage_param = True: "Leverage Only" (leveraged stocks only)
        # - isleverage_param = None: Default to "Ticker Only" (regular stocks only)
        if isleverage_param is None:
            # Default to "Ticker Only" - show regular stocks only
            isleverage_bool = False
            logger.info("No leverage filter specified, defaulting to 'Ticker Only' (regular stocks)")
        else:
            isleverage_bool = bool(isleverage_param)
            logger.info(f"Leverage filter applied: {'Leverage Only' if isleverage_bool else 'Ticker Only'}")
        
        # Apply the leverage filter
        stocks_data = [
            stock for stock in stocks_data 
            if stock.get('isleverage', False) == isleverage_bool
        ]
        logger.info(f"Filtered to {len(stocks_data)} stocks with leverage filter: {'Leverage Only' if isleverage_bool else 'Ticker Only'}")
        
        if not stocks_data:
            logger.warning("No stocks found after filtering")
            return {}
        
        # Extract ticker symbols for Finviz API
        tickers = [stock.get('ticker', '') for stock in stocks_data if stock.get('ticker')]
        
        if not tickers:
            logger.error("No valid tickers found")
            return {}
        
        logger.info(f"Fetching Finviz data for {len(tickers)} tickers")
        
        # Get real-time data from Finviz API
        finviz_data = stock_history_ops.get_finviz_data_for_tickers(tickers)
        
        if not finviz_data:
            logger.error("No Finviz data received")
            return {}
        
        # Process the Finviz data and group by sectors
        sector_groups = {}
        
        for stock in stocks_data:
            ticker = stock.get('ticker', '')
            sector = stock.get('sector', 'Unknown')
            
            if ticker not in finviz_data:
                logger.warning(f"No Finviz data for {ticker}")
                continue
            
            finviz_stock_data = finviz_data[ticker]
            
            # Create stock summary entry with proper structure for frontend (matching 1D,1W,1M format)
            # Use specific Finviz columns: 1=Ticker, 81=Prev Close, 86=Open, 65=Price, 66=Change
            # For Today filter: startDateClosePrice = Prev Close, endDateClosePrice = Open
            current_price = finviz_stock_data.get('Price', 'N/A')  # Column 65
            prev_close = finviz_stock_data.get('Prev Close', 'N/A')  # Column 81
            open_price = finviz_stock_data.get('Open', 'N/A')  # Column 86
            change_percent = finviz_stock_data.get('Change', 'N/A')  # Column 66 (percentage change)
            
            # Format prices with currency symbol to match other periods
            def format_price(price_str):
                if price_str == 'N/A' or not price_str:
                    return 'N/A'
                try:
                    # Remove any existing formatting and convert to float
                    clean_price = str(price_str).replace('$', '').replace(',', '').strip()
                    if clean_price and clean_price != 'N/A':
                        price_val = float(clean_price)
                        return f"${price_val:.2f}"
                    return 'N/A'
                except (ValueError, TypeError):
                    return 'N/A'
            
            # Format percentage change to match other periods
            def format_percentage(percent_str):
                if percent_str == 'N/A' or not percent_str:
                    return 'N/A'
                try:
                    # Remove any existing formatting and convert to float
                    clean_percent = str(percent_str).replace('%', '').replace('+', '').strip()
                    if clean_percent and clean_percent != 'N/A':
                        percent_val = float(clean_percent)
                        return f"{percent_val:.2f}%"
                    return 'N/A'
                except (ValueError, TypeError):
                    return 'N/A'
            
            stock_entry = {
                'ticker': ticker,
                'companyName': stock.get('company_name', 'N/A'),  # Use company_name from stock.json
                'sector': sector,
                'currentPrice': format_price(current_price),  # Current price (Price column)
                'startDateClosePrice': format_price(prev_close),  # Prev Close Price (Prev Close column 81)
                'endDateClosePrice': format_price(open_price),  # Open Price (Open column 86)
                'percentageChange': format_percentage(change_percent),  # Percentage change (Change column)
                'volume': 'N/A',  # Not available in selected columns
                'marketCap': 'N/A',  # Not available in selected columns
                'peRatio': 'N/A',  # Not available in selected columns
                'forwardPE': 'N/A',  # Not available in selected columns
                'pegRatio': 'N/A',  # Not available in selected columns
                'debtToEquity': 'N/A',  # Not available in selected columns
                'profitMargin': 'N/A',  # Not available in selected columns
                'operatingMargin': 'N/A',  # Not available in selected columns
                'roa': 'N/A',  # Not available in selected columns
                'roe': 'N/A',  # Not available in selected columns
                'roi': 'N/A',  # Not available in selected columns
                'revenueGrowth': 'N/A',  # Not available in selected columns
                'earningsGrowth': 'N/A',  # Not available in selected columns
                'isleverage': stock.get('isleverage', False)  # Use isleverage from stock.json
            }
            
            # Group by sector
            if sector not in sector_groups:
                sector_groups[sector] = []
            
            sector_groups[sector].append(stock_entry)
        
        # Calculate average percentage for each sector and format the response
        # Return as dictionary with sector names as keys (matching frontend expectation)
        formatted_sector_groups = {}
        
        for sector, stocks in sector_groups.items():
            # Calculate average percentage change for the sector
            total_percentage = 0
            valid_percentages = 0
            
            for stock in stocks:
                change_percent = stock.get('percentageChange', 'N/A')
                if change_percent != 'N/A' and change_percent:
                    try:
                        # Remove % and convert to float
                        clean_percentage = str(change_percent).replace('%', '').replace('+', '').strip()
                        if clean_percentage and clean_percentage != 'N/A':
                            percentage_value = float(clean_percentage)
                            total_percentage += percentage_value
                            valid_percentages += 1
                    except (ValueError, TypeError):
                        continue
            
            # Calculate average percentage
            average_percentage = '0%'
            if valid_percentages > 0:
                avg_pct = total_percentage / valid_percentages
                average_percentage = f"{avg_pct:.2f}%"
            
            # Format sector group with proper structure
            sector_group = {
                'sector': sector,
                'averagePercentage': average_percentage,
                'stocks': stocks
            }
            
            # Store with sector name as key (matching frontend expectation)
            formatted_sector_groups[sector] = sector_group
        
        # Sort stocks within each sector by ticker
        for sector_group in formatted_sector_groups.values():
            sector_group['stocks'].sort(key=lambda x: x['ticker'])
        
        logger.info(f"Successfully processed {len(formatted_sector_groups)} sectors with Finviz data")
        
        # Convert dictionary to list format to match frontend expectation
        # Frontend expects: [{'sector': 'Energy', 'averagePercentage': '-2.81%', 'stocks': [...]}]
        # Backend was returning: {'Energy': {'sector': 'Energy', 'averagePercentage': '-2.81%', 'stocks': [...]}}
        formatted_list = list(formatted_sector_groups.values())
        
        # Cache the fresh data for 1 minute
        cache_today_data(cache_key, formatted_list)
        logger.info(f"Cached fresh today filter data for key: {cache_key}")
        
        return formatted_list
        
    except Exception as e:
        logger.error(f"Error in get_stock_summary_today: {str(e)}")
        return {}

def get_today_cache_status():
    """
    Get the current status of the Today filter cache
    
    Returns:
        Dictionary with cache status information
    """
    global _today_cache
    cleanup_today_cache()  # Clean up expired entries first
    
    current_time = time.time()
    cache_info = {
        'cache_size': len(_today_cache),
        'cache_ttl_seconds': _today_cache_ttl,
        'cache_ttl_minutes': _today_cache_ttl / 60,
        'entries': []
    }
    
    for cache_key, (data, timestamp) in _today_cache.items():
        age_seconds = current_time - timestamp
        age_minutes = age_seconds / 60
        remaining_seconds = _today_cache_ttl - age_seconds
        remaining_minutes = remaining_seconds / 60
        
        entry_info = {
            'key': cache_key,
            'age_seconds': round(age_seconds, 2),
            'age_minutes': round(age_minutes, 2),
            'remaining_seconds': round(remaining_seconds, 2),
            'remaining_minutes': round(remaining_minutes, 2),
            'is_valid': remaining_seconds > 0,
            'data_count': len(data) if data else 0
        }
        cache_info['entries'].append(entry_info)
    
    return cache_info

def clear_today_cache():
    """
    Clear all Today filter cache entries
    
    Returns:
        Dictionary with operation result
    """
    global _today_cache
    cache_size = len(_today_cache)
    _today_cache.clear()
    
    logging.info(f"Cleared Today filter cache with {cache_size} entries")
    return {
        'message': f'Today filter cache cleared successfully',
        'cleared_entries': cache_size,
        'current_cache_size': 0
    }

def refresh_today_cache(sectors_param: str = "", isleverage_param: bool = None):
    """
    Force refresh of Today filter cache by clearing existing cache and fetching fresh data
    
    Args:
        sectors_param: Comma-separated string of sectors to filter by
        isleverage_param: Boolean to filter leveraged stocks
    
    Returns:
        Dictionary with operation result
    """
    try:
        # Clear existing cache
        clear_result = clear_today_cache()
        
        # Fetch fresh data (this will automatically cache it)
        fresh_data = get_stock_summary_today(sectors_param, isleverage_param)
        
        return {
            'message': 'Today filter cache refreshed successfully',
            'cleared_entries': clear_result['cleared_entries'],
            'fresh_data_count': len(fresh_data) if fresh_data else 0,
            'cache_status': get_today_cache_status()
        }
        
    except Exception as e:
        logging.error(f"Error refreshing Today filter cache: {str(e)}")
        return {
            'error': f'Failed to refresh Today filter cache: {str(e)}',
            'cache_status': get_today_cache_status()
        }

# Legacy function for backward compatibility
def get_stock_summary(sectors_param, isleverage_param, date_from_param, date_to_param):
    """
    Legacy function - now calls the optimized version
    """
    return get_stock_summary_optimized(sectors_param, isleverage_param, date_from_param, date_to_param)
