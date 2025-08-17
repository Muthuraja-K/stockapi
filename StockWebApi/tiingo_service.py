"""
Tiingo API Service for Historical Intraday Data

This module provides access to Tiingo's financial data API for historical intraday data.
Tiingo offers much better historical data than Yahoo Finance, with 1-minute data
going back many years and higher rate limits.
"""

import logging
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from config import config

logger = logging.getLogger(__name__)

class TiingoService:
    """Service class for Tiingo API operations"""
    
    def __init__(self):
        self.api_key = config.TIINGO_API_KEY
        self.base_url = config.TIINGO_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        })
        # Rate limiting: Tiingo allows 1000 requests per day
        self.requests_per_day = 1000
        self.requests_made = 0
        self.last_request_time = None
        self.min_request_interval = 1.0  # Minimum 1 second between requests
    
    def get_intraday_data(self, ticker: str, start_date: datetime, end_date: datetime, 
                          interval: str = '1min', prepost: bool = True) -> Optional[pd.DataFrame]:
        """
        Get intraday data from Tiingo for a specific date range.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            interval: Data interval ('1min', '5min', '1hour', '1day')
            prepost: Whether to include pre/post market data
            
        Returns:
            DataFrame with intraday data or None if failed
        """
        try:
            if not self.api_key:
                logger.warning("Tiingo API key not configured, falling back to Yahoo Finance")
                return None
            
            # Rate limiting: Check if we need to wait
            if self.last_request_time:
                time_since_last = time.time() - self.last_request_time
                if time_since_last < self.min_request_interval:
                    sleep_time = self.min_request_interval - time_since_last
                    logger.info(f"Rate limiting: waiting {sleep_time:.2f} seconds before next request")
                    time.sleep(sleep_time)
            
            # Format dates for Tiingo API
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            # Build API URL - use /iex/ endpoint for intraday data
            url = f"{self.base_url}/iex/{ticker}/prices"
            
            # Query parameters
            params = {
                'startDate': start_str,
                'endDate': end_str,
                'resampleFreq': interval,
                'token': self.api_key
            }
            
            # Add prepost parameter if supported
            if prepost:
                params['extended'] = 'true'
            
            logger.info(f"Fetching Tiingo data for {ticker} from {start_str} to {end_str} with {interval} interval")
            
            # Make API request with retry logic
            max_retries = 3
            retry_delay = 5  # Start with 5 seconds
            
            for attempt in range(max_retries):
                try:
                    # Update request tracking
                    self.last_request_time = time.time()
                    self.requests_made += 1
                    
                    # Make API request
                    response = self.session.get(url, params=params)
                    
                    if response.status_code == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', retry_delay))
                        logger.warning(f"Rate limited by Tiingo API. Waiting {retry_after} seconds before retry {attempt + 1}/{max_retries}")
                        time.sleep(retry_after)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    elif response.status_code == 200:
                        break  # Success, exit retry loop
                    else:
                        response.raise_for_status()
                        
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise e
            
            # If we get here, we should have a successful response
            data = response.json()
            
            if not data:
                logger.warning(f"No data returned from Tiingo for {ticker}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Log the original columns for debugging
            logger.info(f"Tiingo API returned columns: {list(df.columns)}")
            
            # Standardize column names to uppercase to match expected format
            column_mapping = {
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'adjClose': 'Adj Close',
                'adjHigh': 'Adj High',
                'adjLow': 'Adj Low',
                'adjOpen': 'Adj Open',
                'adjVolume': 'Adj Volume'
            }
            
            # Rename columns if they exist
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df.rename(columns={old_name: new_name}, inplace=True)
            
            # Log the final columns after renaming
            logger.info(f"Columns after renaming: {list(df.columns)}")
            
            # Convert date columns to datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            # Sort by date
            df.sort_index(inplace=True)
            
            logger.info(f"Successfully fetched {len(df)} data points from Tiingo for {ticker}")
            return df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Tiingo API request failed for {ticker}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching Tiingo data for {ticker}: {str(e)}")
            return None
    
    def get_1min_data_for_date(self, ticker: str, target_date: datetime, 
                               prepost: bool = True) -> Optional[pd.DataFrame]:
        """
        Get 1-minute data for a specific date from Tiingo.
        
        Args:
            ticker: Stock ticker symbol
            target_date: Target date for data retrieval
            prepost: Whether to include pre/post market data
            
        Returns:
            DataFrame with 1-minute data for the specific date AND previous day
        """
        # Get data for the specific date AND previous day to calculate Close B4 Earning
        start_date = (target_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return self.get_intraday_data(ticker, start_date, end_date, '1min', prepost)
    
    def get_5min_data_for_date(self, ticker: str, target_date: datetime, 
                               prepost: bool = True) -> Optional[pd.DataFrame]:
        """
        Get 5-minute data for a specific date from Tiingo.
        
        Args:
            ticker: Stock ticker symbol
            target_date: Target date for data retrieval
            prepost: Whether to include pre/post market data
            
        Returns:
            DataFrame with 5-minute data for the specific date AND previous day
        """
        # Get data for the specific date AND previous day to calculate Close B4 Earning
        start_date = (target_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return self.get_intraday_data(ticker, start_date, end_date, '5min', prepost)
    
    def get_daily_data_for_date(self, ticker: str, target_date: datetime, 
                                prepost: bool = True) -> Optional[pd.DataFrame]:
        """
        Get daily data for a specific date from Tiingo.
        
        Args:
            ticker: Stock ticker symbol
            target_date: Target date for data retrieval
            prepost: Whether to include pre/post market data
            
        Returns:
            DataFrame with daily data for the specific date AND previous day
        """
        # Get data for the specific date AND previous day to calculate Close B4 Earning
        start_date = (target_date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return self.get_intraday_data(ticker, start_date, end_date, '1day', prepost)
    
    def is_available(self) -> bool:
        """
        Check if Tiingo service is available (has API key).
        
        Returns:
            True if Tiingo is available, False otherwise
        """
        return bool(self.api_key)
    
    def reset_rate_limiting(self):
        """Reset rate limiting counters - useful for testing or after long periods"""
        self.requests_made = 0
        self.last_request_time = None
        logger.info("Tiingo rate limiting counters reset")
    
    def get_remaining_requests(self) -> int:
        """Get remaining requests for today"""
        return max(0, self.requests_per_day - self.requests_made)
    
    def get_data_with_fallback(self, ticker: str, target_date: datetime, 
                              preferred_interval: str = '1min') -> Optional[pd.DataFrame]:
        """
        Get data with intelligent fallback strategy.
        
        Args:
            ticker: Stock ticker symbol
            target_date: Target date for data retrieval
            preferred_interval: Preferred interval ('1min', '5min', '1day')
            
        Returns:
            DataFrame with data or None if all attempts failed
        """
        if not self.is_available():
            logger.info(f"Tiingo not available for {ticker}, will use fallback")
            return None
        
        # Try preferred interval first
        if preferred_interval == '1min':
            data = self.get_1min_data_for_date(ticker, target_date)
            if data is not None and not data.empty:
                logger.info(f"Successfully got 1-minute data from Tiingo for {ticker}")
                return data
        
        # Fallback to 5-minute data
        if preferred_interval in ['1min', '5min']:
            data = self.get_5min_data_for_date(ticker, target_date)
            if data is not None and not data.empty:
                logger.info(f"Successfully got 5-minute data from Tiingo for {ticker}")
                return data
        
        # Final fallback to daily data
        data = self.get_daily_data_for_date(ticker, target_date)
        if data is not None and not data.empty:
            logger.info(f"Successfully got daily data from Tiingo for {ticker}")
            return data
        
        logger.warning(f"All Tiingo data attempts failed for {ticker}")
        return None

# Global instance
tiingo_service = TiingoService()
