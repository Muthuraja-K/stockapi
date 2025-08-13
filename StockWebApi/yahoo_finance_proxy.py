"""
Optimized Yahoo Finance Integration with Batch Download
This module uses yf.download() with multiple tickers and groupby options
for maximum performance and efficiency
"""

import time
import logging
from typing import Dict, Any, List
from functools import wraps
from cache_manager import cache_result
from utils import fmt_currency, fmt_percent, fmt_market_cap
from cache_manager import get_cache
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

class SimpleRateLimiter:
    """Simple rate limiter without proxy complexity"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 10.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_call_time = 0
        self.min_interval = 0.5  # Minimum 0.5 second between calls
        
    def get_delay(self) -> float:
        """Get current delay based on success/failure patterns"""
        current_time = time.time()
        time_since_last = current_time - self.last_call_time
        
        # Ensure minimum interval
        if time_since_last < self.min_interval:
            return self.min_interval - time_since_last
        
        return self.current_delay
    
    def update_delay(self, success: bool):
        """Update delay based on success/failure"""
        if success:
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            
            # Gradually reduce delay on success
            if self.consecutive_successes >= 3:
                self.current_delay = max(self.base_delay, self.current_delay * 0.8)
                self.consecutive_successes = 0
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            
            # Increase delay on failure
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
    
    def wait(self):
        """Wait for the appropriate delay"""
        delay = self.get_delay()
        if delay > 0:
            time.sleep(delay)
        self.last_call_time = time.time()

# Global rate limiter instance
_rate_limiter = SimpleRateLimiter()

def get_rate_limiter() -> SimpleRateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter

@cache_result('batch')
def get_batch_ticker_info(tickers: List[str], max_batch_size: int = 50) -> Dict[str, Any]:
    """
    Get information for multiple tickers using yf.download() with groupby option
    This is the most efficient way to fetch data for multiple tickers
    
    Args:
        tickers: List of ticker symbols
        max_batch_size: Maximum number of tickers per batch (increased to 50 for yf.download)
    
    Returns:
        Dictionary with ticker data organized by symbol
    """
    if not tickers:
        return {}
    
    # Split tickers into batches
    batches = [tickers[i:i + max_batch_size] for i in range(0, len(tickers), max_batch_size)]
    all_results = {}
    
    logger.info(f"Processing {len(tickers)} tickers in {len(batches)} batches using yf.download()")
    
    for batch_num, batch in enumerate(batches):
        try:
            logger.info(f"Processing batch {batch_num + 1}/{len(batches)}: {len(batch)} tickers")
            
            # OPTIMIZATION: Use yf.download() with multiple tickers and groupby option
            # This is the most efficient way to get data for multiple tickers
            batch_results = process_ticker_batch_download(batch)
            
            all_results.update(batch_results)
            
            # Small delay between batches to respect API limits
            if batch_num < len(batches) - 1:  # Not the last batch
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error processing batch {batch_num + 1}: {e}")
            # Continue with next batch
    
    logger.info(f"Successfully processed {len(all_results)} tickers using yf.download()")
    return all_results

def process_ticker_batch_download(tickers: List[str]) -> Dict[str, Any]:
    """
    Process a batch of tickers using yf.download() with groupby option
    This is the most efficient method for batch processing
    
    Args:
        tickers: List of ticker symbols (max 50 for optimal performance)
    
    Returns:
        Dictionary with ticker data including all time period metrics
    """
    batch_results = {}
    cache_manager = get_cache()
    
    try:
        logger.info(f"Using yf.download() for batch of {len(tickers)} tickers")
        
        # OPTIMIZATION: Use yf.download() with multiple tickers and groupby option
        # This fetches data for all tickers in a single API call
        try:
            # Download historical data for all tickers in one call
            # groupby='ticker' organizes the data by ticker symbol
            hist_data = yf.download(
                tickers,
                period="1y",
                interval="1d",
                group_by='ticker',
                progress=False,
                ignore_tz=True,
                auto_adjust=True  # Explicitly set to avoid FutureWarning
            )
            
            logger.info(f"Downloaded data shape: {hist_data.shape}")
            
            # Process each ticker's data
            for ticker in tickers:
                try:
                    ticker_data = process_single_ticker_from_download(ticker, hist_data, cache_manager)
                    if ticker_data:
                        batch_results[ticker] = ticker_data
                        
                except Exception as e:
                    logger.error(f"Error processing ticker {ticker}: {e}")
                    batch_results[ticker] = {'error': f'Processing error: {str(e)}'}
                    
        except Exception as e:
            logger.error(f"Error in yf.download(): {e}")
            # Fallback to individual processing if batch download fails
            logger.info("Falling back to individual ticker processing")
            for ticker in tickers:
                try:
                    ticker_data = process_single_ticker_fallback(ticker, cache_manager)
                    if ticker_data:
                        batch_results[ticker] = ticker_data
                except Exception as e2:
                    logger.error(f"Error in fallback processing for {ticker}: {e2}")
                    batch_results[ticker] = {'error': f'Fallback error: {str(e2)}'}
        
        logger.info(f"Successfully processed batch of {len(tickers)} tickers")
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        # Return error for all tickers in batch
        for ticker in tickers:
            batch_results[ticker] = {'error': f'Batch processing error: {str(e)}'}
    
    return batch_results

def process_single_ticker_from_download(ticker: str, hist_data: pd.DataFrame, cache_manager) -> Dict[str, Any]:
    """
    Process a single ticker's data from the downloaded batch data
    
    Args:
        ticker: Ticker symbol
        hist_data: Historical data DataFrame from batch download
        cache_manager: Cache manager instance
    """
    try:
        # Extract ticker-specific data from the multi-ticker DataFrame
        if ticker in hist_data.columns.levels[0]:
            ticker_hist = hist_data[ticker]
        else:
            # Try alternative column structure
            ticker_hist = hist_data.xs(ticker, level=0, axis=1, drop_level=False)
        
        if ticker_hist.empty:
            logger.warning(f"No data found for {ticker} in batch download")
            return None
        
        # Calculate all time period metrics from the historical data
        current_price = ticker_hist['Close'].iloc[-1] if len(ticker_hist) > 0 else None
        
        if current_price is None:
            return None
        
        # Calculate today's metrics
        today_data = calculate_today_metrics(ticker_hist)
        
        # Calculate previous day metrics
        prev_day_data = calculate_prev_day_metrics(ticker_hist)
        
        # Calculate 5-day metrics
        five_day_data = calculate_five_day_metrics(ticker_hist)
        
        # Calculate 1-month metrics
        one_month_data = calculate_one_month_metrics(ticker_hist)
        
        # Calculate 6-month metrics
        six_month_data = calculate_six_month_metrics(ticker_hist)
        
        # Calculate 1-year metrics
        one_year_data = calculate_one_year_metrics(ticker_hist)
        
        # Get company info from cache or set defaults
        company_info = get_cached_company_info(ticker, cache_manager)
        
        # Format current price
        formatted_current_price = format_price(current_price)
        
        # Compile all data
        ticker_data = {
            'current_price': formatted_current_price,
            'company_name': company_info['company_name'],
            'market_cap': company_info['market_cap'],
            'earning_date': company_info['earning_date'],
            'today': format_time_data(today_data),
            'previous_day': format_time_data(prev_day_data),
            'five_day': format_time_data(five_day_data),
            'one_month': format_time_data(one_month_data),
            'six_month': format_time_data(six_month_data),
            'one_year': format_time_data(one_year_data),
            'data_points': len(ticker_hist)
        }
        
        logger.info(f"Successfully processed {ticker} with {len(ticker_hist)} data points from batch download")
        return ticker_data
        
    except Exception as e:
        logger.error(f"Error processing {ticker} from download data: {e}")
        return None

def process_single_ticker_fallback(ticker: str, cache_manager) -> Dict[str, Any]:
    """
    Fallback method for individual ticker processing if batch download fails
    """
    try:
        # Use individual yf.Ticker as fallback
        ticker_obj = yf.Ticker(ticker)
        
        # Get historical data
        hist_data = ticker_obj.history(period="1y")
        
        if hist_data.empty:
            return None
        
        # Process the same way as batch data
        return process_single_ticker_from_download(ticker, hist_data, cache_manager)
        
    except Exception as e:
        logger.error(f"Error in fallback processing for {ticker}: {e}")
        return None

def calculate_today_metrics(hist_data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate today's metrics from historical data"""
    if len(hist_data) >= 2:
        today_row = hist_data.iloc[-1]
        prev_row = hist_data.iloc[-2]
        return {
            'low': today_row['Low'],
            'high': today_row['High'],
            'percentage': ((today_row['Close'] - prev_row['Close']) / prev_row['Close']) * 100
        }
    return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}

def calculate_prev_day_metrics(hist_data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate previous day metrics from historical data"""
    if len(hist_data) >= 3:
        prev_row = hist_data.iloc[-2]
        prev_prev_row = hist_data.iloc[-3]
        return {
            'low': prev_row['Low'],
            'high': prev_row['High'],
            'percentage': ((prev_row['Close'] - prev_prev_row['Close']) / prev_prev_row['Close']) * 100
        }
    return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}

def calculate_five_day_metrics(hist_data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate 5-day metrics from historical data"""
    if len(hist_data) >= 5:
        current_close = hist_data.iloc[-1]['Close']
        five_day_ago_close = hist_data.iloc[-5]['Close']
        return {
            'low': hist_data.iloc[-5:]['Low'].min(),
            'high': hist_data.iloc[-5:]['High'].max(),
            'percentage': ((current_close - five_day_ago_close) / five_day_ago_close) * 100
        }
    return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}

def calculate_one_month_metrics(hist_data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate 1-month metrics from historical data"""
    if len(hist_data) >= 20:
        current_close = hist_data.iloc[-1]['Close']
        month_ago_close = hist_data.iloc[-20]['Close']
        return {
            'low': hist_data.iloc[-20:]['Low'].min(),
            'high': hist_data.iloc[-20:]['High'].max(),
            'percentage': ((current_close - month_ago_close) / month_ago_close) * 100
        }
    return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}

def calculate_six_month_metrics(hist_data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate 6-month metrics from historical data"""
    if len(hist_data) >= 120:
        current_close = hist_data.iloc[-1]['Close']
        six_month_ago_close = hist_data.iloc[-120]['Close']
        return {
            'low': hist_data.iloc[-120:]['Low'].min(),
            'high': hist_data.iloc[-120:]['High'].max(),
            'percentage': ((current_close - six_month_ago_close) / six_month_ago_close) * 100
        }
    return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}

def calculate_one_year_metrics(hist_data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate 1-year metrics from historical data"""
    if len(hist_data) >= 2:
        current_close = hist_data.iloc[-1]['Close']
        start_close = hist_data.iloc[0]['Close']
        
        # Always provide 1-year approximation based on available data
        if len(hist_data) >= 120:  # At least 6 months of data
            available_days = len(hist_data)
            extrapolation_factor = 252 / available_days  # 252 trading days in a year
            
            period_percentage = ((current_close - start_close) / start_close) * 100
            extrapolated_percentage = period_percentage * extrapolation_factor
            
            return {
                'low': hist_data['Low'].min(),
                'high': hist_data['High'].max(),
                'percentage': extrapolated_percentage
            }
        else:
            return {
                'low': hist_data['Low'].min() if len(hist_data) > 0 else 'N/A',
                'high': hist_data['High'].max() if len(hist_data) > 0 else 'N/A',
                'percentage': ((current_close - start_close) / start_close) * 100 if len(hist_data) > 1 else 'N/A'
            }
    return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}

def get_cached_company_info(ticker: str, cache_manager) -> Dict[str, Any]:
    """Get company info from cache or return defaults"""
    try:
        cached_info = cache_manager.get('company_info', ticker)
        if cached_info:
            return cached_info
    except:
        pass
    
    # Return default values if no cache
    return {
        'company_name': 'N/A',
        'market_cap': 'N/A',
        'earning_date': 'N/A'
    }

def format_price(price: float) -> str:
    """Format price as currency string"""
    if price is None:
        return 'N/A'
    try:
        return fmt_currency(float(price))
    except (ValueError, TypeError):
        return 'N/A'

def format_time_data(data: Dict) -> Dict[str, Any]:
    """Format time-based data with proper formatting"""
    if not data or data.get('low') == 'N/A':
        return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}
    return {
        'low': fmt_currency(data.get('low', 0)),
        'high': fmt_currency(data.get('high', 0)),
        'percentage': fmt_percent(data.get('percentage', 0))
    }

def pre_populate_cache_from_stock_file():
    """
    Pre-populate the smart cache with existing data from stock.json
    This reduces API calls by using already available data
    """
    try:
        import json
        from pathlib import Path
        
        stock_file = Path("stock.json")
        if not stock_file.exists():
            logger.warning("stock.json not found, skipping cache pre-population")
            return
        
        cache_manager = get_cache()
        
        with open(stock_file, 'r', encoding='utf-8') as f:
            stocks_data = json.load(f)
        
        logger.info(f"Pre-populating cache with {len(stocks_data)} stocks from stock.json")
        
        for stock in stocks_data:
            ticker = stock.get('ticker', '').upper()
            if not ticker:
                continue
            
            # Cache sector info (very low frequency changes)
            sector = stock.get('sector', 'N/A')
            isleverage = stock.get('isleverage', False)
            
            sector_info = {
                'sector': sector,
                'isleverage': isleverage
            }
            cache_manager.set('sector', ticker, sector_info)
            
            logger.info(f"Pre-populated sector info for {ticker}: {sector}")
        
        logger.info("Cache pre-population completed successfully")
        
    except Exception as e:
        logger.error(f"Error pre-populating cache: {e}")

def initialize_yahoo_finance_proxy():
    """Initialize the optimized Yahoo Finance system with batch download"""
    try:
        # Pre-populate cache with existing data from stock.json
        pre_populate_cache_from_stock_file()
        
        logger.info("Yahoo Finance system initialized successfully (optimized batch download mode)")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Yahoo Finance system: {e}")
        return False

# Removed duplicate get_cache_stats function - using the one from cache_manager

def clear_expired_cache():
    """Clear expired cache entries"""
    try:
        cache_manager = get_cache()
        cache_manager.clear_expired_cache()
    except Exception as e:
        logger.error(f"Error clearing expired cache: {e}")

def reset_proxy_system():
    """Reset the rate limiter (useful for testing)"""
    global _rate_limiter
    
    # Reset rate limiter
    _rate_limiter.current_delay = _rate_limiter.base_delay
    _rate_limiter.consecutive_failures = 0
    _rate_limiter.consecutive_successes = 0
    
    logger.info("Rate limiter reset successfully")

# Auto-initialize when module is imported
if __name__ != "__main__":
    initialize_yahoo_finance_proxy()
