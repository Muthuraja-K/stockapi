import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from api_rate_limiter import enforce_rate_limit, safe_yfinance_call

logger = logging.getLogger(__name__)

# Remove old rate limiting variables and functions - now using centralized rate limiter

class HistoryCache:
    def __init__(self, cache_file: str = "history.json"):
        self.cache_file = cache_file
        self.cache_data = {}
        self.last_update_date = None
        self.load_cache()
    
    def load_cache(self):
        """Load cached data from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.cache_data = data.get('stocks', {})
                    self.last_update_date = data.get('last_update_date')
                    logger.info(f"Loaded {len(self.cache_data)} stocks from cache")
            else:
                logger.info("No cache file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.cache_data = {}
    
    def save_cache(self):
        """Save cache data to file"""
        try:
            data = {
                'stocks': self.cache_data,
                'last_update_date': datetime.now().strftime('%Y-%m-%d'),
                'last_update_timestamp': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.cache_data)} stocks to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def needs_update(self) -> bool:
        """Check if cache needs daily update"""
        if not self.last_update_date:
            return True
        
        today = datetime.now().strftime('%Y-%m-%d')
        return self.last_update_date != today
    
    def get_cached_stock_data(self, symbol: str) -> Optional[Dict]:
        """Get cached data for a stock"""
        cached_data = self.cache_data.get(symbol)
        if cached_data:
            logger.debug(f"Cache hit for {symbol}")
        else:
            logger.debug(f"Cache miss for {symbol}")
        return cached_data
    
    def update_stock_cache(self, symbol: str, data: Dict):
        """Update cache for a specific stock"""
        self.cache_data[symbol] = data
        logger.debug(f"Updated cache for {symbol}")
    
    def has_stock_cache(self, symbol: str) -> bool:
        """Check if a stock exists in cache"""
        return symbol in self.cache_data
    
    def fetch_historical_data(self, symbol: str) -> Optional[Dict]:
        """Fetch 1-year historical data for a stock"""
        try:
            # Use centralized rate limiting
            enforce_rate_limit()
            
            # Use safe yfinance call instead of direct yf.Ticker
            hist = safe_yfinance_call(symbol, "history")
            
            if hist.empty:
                logger.warning(f"No historical data found for {symbol}")
                return None
            
            # Calculate various metrics from historical data (excluding current price and today's change)
            # Note: current_price and today_change will be fetched in real-time
            prev_day_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[-1]
            
            # Calculate percentage changes for different periods (excluding today's change)
            prev_day_change = ((hist['Close'].iloc[-2] - hist['Close'].iloc[-3]) / hist['Close'].iloc[-3] * 100) if len(hist) > 2 else 0
            five_day_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6] * 100) if len(hist) > 5 else 0
            one_month_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-21]) / hist['Close'].iloc[-21] * 100) if len(hist) > 20 else 0
            six_month_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-126]) / hist['Close'].iloc[-126] * 100) if len(hist) > 125 else 0
            one_year_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100) if len(hist) > 0 else 0
            
            # Calculate highs and lows (excluding today's high/low which will be fetched in real-time)
            prev_day_high = hist['High'].iloc[-2] if len(hist) > 1 else hist['High'].iloc[-1]
            prev_day_low = hist['Low'].iloc[-2] if len(hist) > 1 else hist['Low'].iloc[-1]
            prev_day_close = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[-1]
            
            # 5-day highs and lows
            five_day_high = hist['High'].iloc[-5:].max() if len(hist) >= 5 else hist['High'].iloc[-1]
            five_day_low = hist['Low'].iloc[-5:].min() if len(hist) >= 5 else hist['Low'].iloc[-1]
            
            # 1-month highs and lows
            one_month_high = hist['High'].iloc[-21:].max() if len(hist) >= 21 else hist['High'].iloc[-1]
            one_month_low = hist['Low'].iloc[-21:].min() if len(hist) >= 21 else hist['Low'].iloc[-1]
            
            # 6-month highs and lows
            six_month_high = hist['High'].iloc[-126:].max() if len(hist) >= 126 else hist['High'].iloc[-1]
            six_month_low = hist['Low'].iloc[-126:].min() if len(hist) >= 126 else hist['Low'].iloc[-1]
            
            # 1-year highs and lows
            one_year_high = hist['High'].max()
            one_year_low = hist['Low'].min()
            
            # Fetch earnings data using ticker.income_stmt
            earnings_data = []
            try:
                income_stmt = ticker.income_stmt
                logger.info(f"Income statement data for {symbol}: {income_stmt}")
                
                if income_stmt is not None and not income_stmt.empty:
                    logger.info(f"Income statement columns for {symbol}: {list(income_stmt.columns)}")
                    logger.info(f"Income statement shape for {symbol}: {income_stmt.shape}")
                    
                    # Get the last 2 quarters from income statement
                    last_quarters = income_stmt.tail(2)
                    for idx, quarter in last_quarters.iterrows():
                        # Extract EPS and Revenue data from income statement
                        eps_actual = quarter.get('Basic EPS', None) or quarter.get('Diluted EPS', None)
                        revenue_actual = quarter.get('Total Revenue', None) or quarter.get('Revenue', None)
                        
                        # For income statement, we don't have estimates, so set them to None
                        eps_estimate = None
                        revenue_estimate = None
                        
                        logger.debug(f"Quarter data for {symbol} on {idx}: eps_actual={eps_actual}, revenue_actual={revenue_actual}")
                        
                        earnings_data.append({
                            'date': idx.strftime('%Y-%m-%d'),
                            'eps_actual': eps_actual,
                            'eps_estimate': eps_estimate,
                            'revenue_actual': revenue_actual,
                            'revenue_estimate': revenue_estimate
                        })
                else:
                    logger.warning(f"No income statement data found for {symbol}")
                    
            except Exception as e:
                logger.warning(f"Error fetching income statement for {symbol}: {e}")
                # Try alternative method using ticker.earnings
                try:
                    earnings_alt = ticker.earnings
                    if earnings_alt is not None and not earnings_alt.empty:
                        logger.debug(f"Alternative earnings data for {symbol}: {earnings_alt}")
                        last_earnings = earnings_alt.tail(2)
                        for idx, earning in last_earnings.iterrows():
                            earnings_data.append({
                                'date': idx.strftime('%Y-%m-%d'),
                                'eps_actual': earning.get('Earnings', None),
                                'eps_estimate': earning.get('Earnings Estimate', None),
                                'revenue_actual': earning.get('Revenue', None),
                                'revenue_estimate': earning.get('Revenue Estimate', None)
                            })
                except Exception as e2:
                    logger.warning(f"Alternative earnings method also failed for {symbol}: {e2}")
            
            # Ensure at least 2 earnings entries
            while len(earnings_data) < 2:
                earnings_data.append({
                    'date': 'N/A', 'eps_actual': None, 'eps_estimate': None,
                    'revenue_actual': None, 'revenue_estimate': None
                })
            
            # Format all the data for storage (excluding current price and today's change)
            formatted_data = {
                'symbol': symbol,
                'historical_data': {
                    'prev_day_high': prev_day_high,
                    'prev_day_low': prev_day_low,
                    'prev_day_close': prev_day_close,
                    'five_day_high': five_day_high,
                    'five_day_low': five_day_low,
                    'one_month_high': one_month_high,
                    'one_month_low': one_month_low,
                    'six_month_high': six_month_high,
                    'six_month_low': six_month_low,
                    'one_year_high': one_year_high,
                    'one_year_low': one_year_low,
                    'percentage_changes': {
                        'prev_day': prev_day_change,
                        'five_day': five_day_change,
                        'one_month': one_month_change,
                        'six_month': six_month_change,
                        'one_year': one_year_change
                    }
                },
                'earnings_data': earnings_data,
                'last_updated': datetime.now().isoformat()
            }
            
            # Add formatted data for quick access (excluding current price and today's change)
            formatted_data['formatted'] = {
                'prev_day_high': self._format_currency(prev_day_high),
                'prev_day_low': self._format_currency(prev_day_low),
                'prev_day_close': self._format_currency(prev_day_close),
                'five_day_high': self._format_currency(five_day_high),
                'five_day_low': self._format_currency(five_day_low),
                'one_month_high': self._format_currency(one_month_high),
                'one_month_low': self._format_currency(one_month_low),
                'six_month_high': self._format_currency(six_month_high),
                'six_month_low': self._format_currency(six_month_low),
                'one_year_high': self._format_currency(one_year_high),
                'one_year_low': self._format_currency(one_year_low),
                'percentage_changes': {
                    'prev_day': self._format_percentage(prev_day_change),
                    'five_day': self._format_percentage(five_day_change),
                    'one_month': self._format_percentage(one_month_change),
                    'six_month': self._format_percentage(six_month_change),
                    'one_year': self._format_percentage(one_year_change)
                },
                'earnings_data': []
            }
            
            # Format earnings data
            for earning in earnings_data:
                formatted_earning = {
                    'date': earning['date'],
                    'eps_actual': self._format_currency(earning['eps_actual']) if earning['eps_actual'] is not None else 'N/A',
                    'eps_estimate': self._format_currency(earning['eps_estimate']) if earning['eps_estimate'] is not None else 'N/A',
                    'revenue_actual': self._format_currency(earning['revenue_actual']) if earning['revenue_actual'] is not None else 'N/A',
                    'revenue_estimate': self._format_currency(earning['revenue_estimate']) if earning['revenue_estimate'] is not None else 'N/A'
                }
                formatted_data['formatted']['earnings_data'].append(formatted_earning)
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def _format_currency(self, value) -> str:
        """Format currency values"""
        try:
            if pd.isna(value) or value == 'N/A':
                return 'N/A'
            if isinstance(value, str):
                return value
            if value >= 1e12:
                return f"${value/1e12:.1f}T"
            elif value >= 1e9:
                return f"${value/1e9:.1f}B"
            elif value >= 1e6:
                return f"${value/1e6:.1f}M"
            elif value >= 1e3:
                return f"${value/1e3:.1f}K"
            else:
                return f"${value:.2f}"
        except:
            return 'N/A'
    
    def _format_percentage(self, value) -> str:
        """Format percentage values"""
        try:
            if pd.isna(value) or value == 'N/A':
                return 'N/A'
            if isinstance(value, str):
                return value
            if value > 0:
                return f"+{value:.1f}%"
            else:
                return f"{value:.1f}%"
        except:
            return 'N/A'
    
    def update_all_stocks(self, symbols: List[str]) -> Dict[str, Dict]:
        """Update cache for all stocks"""
        logger.info(f"Starting daily update for {len(symbols)} stocks")
        
        updated_data = {}
        max_workers = min(5, len(symbols))  # Reduced from 20 to 5 to avoid rate limits
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_symbol = {executor.submit(self.fetch_historical_data, symbol): symbol for symbol in symbols}
            
            # Collect results
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result:
                        updated_data[symbol] = result
                        self.update_stock_cache(symbol, result)
                        logger.info(f"Updated cache for {symbol}")
                        # Add small delay between completions to avoid rate limiting
                        time.sleep(0.1)
                    else:
                        logger.warning(f"No data received for {symbol}")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
        
        # Save updated cache
        self.save_cache()
        logger.info(f"Daily update completed. Updated {len(updated_data)} stocks")
        
        return updated_data
    
    def get_current_price_only(self, symbol: str) -> Optional[float]:
        """Fetch only current price for a stock"""
        try:
            # Use centralized rate limiting
            enforce_rate_limit()
            
            # Use safe yfinance call instead of direct yf.Ticker
            ticker_info = safe_yfinance_call(symbol, "info")
            
            # Try to get current price from info
            current_price = ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice')
            
            if current_price:
                return float(current_price)
            
            # Fallback to historical data
            hist = safe_yfinance_call(symbol, "history")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    def get_realtime_data(self, symbol: str) -> Optional[Dict]:
        """Fetch real-time current price, today's high/low, and today's change"""
        try:
            # Use centralized rate limiting
            enforce_rate_limit()
            
            # Use safe yfinance call instead of direct yf.Ticker
            ticker_info = safe_yfinance_call(symbol, "info")
            
            # Get current price
            current_price = ticker_info.get('currentPrice') or ticker_info.get('regularMarketPrice')
            if not current_price:
                # Fallback to historical data
                hist = safe_yfinance_call(symbol, "history")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                else:
                    return None
            
            current_price = float(current_price)
            
            # Get today's high/low from info
            today_high = ticker_info.get('dayHigh') or ticker_info.get('regularMarketDayHigh')
            today_low = ticker_info.get('dayLow') or ticker_info.get('regularMarketDayLow')
            
            # If not available in info, try historical data
            if not today_high or not today_low:
                hist = safe_yfinance_call(symbol, "history")
                if not hist.empty:
                    today_high = float(hist['High'].iloc[-1])
                    today_low = float(hist['Low'].iloc[-1])
                else:
                    today_high = current_price
                    today_low = current_price
            
            today_high = float(today_high)
            today_low = float(today_low)
            
            # Get previous day close from cache or fetch if needed
            cached_data = self.get_cached_stock_data(symbol)
            if cached_data and 'historical_data' in cached_data:
                prev_day_close = cached_data['historical_data']['prev_day_close']
            else:
                # Fetch historical data to get previous day close
                hist = safe_yfinance_call(symbol, "history")
                if len(hist) > 1:
                    prev_day_close = float(hist['Close'].iloc[-2])
                else:
                    prev_day_close = current_price
            
            # Calculate today's change
            today_change = ((current_price - prev_day_close) / prev_day_close * 100) if prev_day_close > 0 else 0
            
            return {
                'current_price': current_price,
                'today_high': today_high,
                'today_low': today_low,
                'today_change': today_change,
                'prev_day_close': prev_day_close
            }
            
        except Exception as e:
            logger.error(f"Error fetching real-time data for {symbol}: {e}")
            return None
    
    def test_earnings_data(self, symbol: str) -> Dict:
        """Test function to debug earnings data retrieval"""
        result = {
            'symbol': symbol,
            'method1_income_stmt': None,
            'method2_ticker_earnings': None,
            'method3_ticker_earnings_dates': None
        }
        
        try:
            # Method 1: ticker.income_stmt - using centralized rate limiting
            enforce_rate_limit()
            ticker = yf.Ticker(symbol)
            income_stmt = ticker.income_stmt
            if income_stmt is not None and not income_stmt.empty:
                result['method1_income_stmt'] = {
                    'columns': list(income_stmt.columns),
                    'shape': income_stmt.shape,
                    'last_2_rows': income_stmt.tail(2).to_dict('records')
                }
            else:
                result['method1_income_stmt'] = 'No data'
        except Exception as e:
            result['method1_income_stmt'] = f'Error: {str(e)}'
        
        try:
            # Method 2: ticker.earnings - using centralized rate limiting
            enforce_rate_limit()
            ticker = yf.Ticker(symbol)
            earnings2 = ticker.earnings
            if earnings2 is not None and not earnings2.empty:
                result['method2_ticker_earnings'] = {
                    'columns': list(earnings2.columns),
                    'shape': earnings2.shape,
                    'last_2_rows': earnings2.tail(2).to_dict('records')
                }
            else:
                result['method2_ticker_earnings'] = 'No data'
        except Exception as e:
            result['method2_ticker_earnings'] = f'Error: {str(e)}'
        
        try:
            # Method 3: ticker.earnings_dates - using centralized rate limiting
            enforce_rate_limit()
            ticker = yf.Ticker(symbol)
            earnings3 = ticker.earnings_dates
            if earnings3 is not None and not earnings3.empty:
                result['method3_ticker_earnings_dates'] = {
                    'columns': list(earnings3.columns),
                    'shape': earnings3.shape,
                    'last_2_rows': earnings3.tail(2).to_dict('records')
                }
            else:
                result['method3_ticker_earnings_dates'] = 'No data'
        except Exception as e:
            result['method3_ticker_earnings_dates'] = f'Error: {str(e)}'
        
        return result

# Global cache instance
history_cache = HistoryCache() 