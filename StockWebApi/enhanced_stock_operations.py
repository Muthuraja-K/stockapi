import json
import logging
import yfinance as yf
from datetime import datetime, timedelta
from pandas import Timestamp
from utils import fmt_currency, fmt_percent, fmt_market_cap
import concurrent.futures
from typing import List, Dict, Any, Tuple
import pandas as pd
import time
from functools import lru_cache
import os
import requests
from bs4 import BeautifulSoup
import re

# Global cache for stock data to avoid repeated API calls
_stock_cache = {}
_cache_ttl = 300  # 5 minutes cache TTL
_max_cache_size = 1000  # Maximum number of cached items

# Rate limiting for API calls
_last_api_call_time = 0
_min_api_call_interval = 0.1  # Minimum 100ms between API calls

def cleanup_cache():
    """Clean up expired cache entries and limit cache size"""
    global _stock_cache
    current_time = time.time()
    
    # Remove expired entries
    expired_keys = [
        key for key, (_, timestamp) in _stock_cache.items() 
        if current_time - timestamp > _cache_ttl
    ]
    for key in expired_keys:
        del _stock_cache[key]
    
    # Limit cache size by removing oldest entries
    if len(_stock_cache) > _max_cache_size:
        # Sort by timestamp and remove oldest entries
        sorted_items = sorted(_stock_cache.items(), key=lambda x: x[1][1])
        items_to_remove = len(_stock_cache) - _max_cache_size
        for i in range(items_to_remove):
            del _stock_cache[sorted_items[i][0]]
    
    logging.info(f"Cache cleanup: {len(expired_keys)} expired entries removed, cache size: {len(_stock_cache)}")

def is_after_hours() -> bool:
    """Check if current time is after regular market hours (4:00 PM ET)"""
    try:
        # Get current time in ET (Eastern Time)
        # For simplicity, we'll use UTC-5 (EST) or UTC-4 (EDT)
        # In production, you might want to use pytz for proper timezone handling
        utc_now = datetime.utcnow()
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if utc_now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Convert to ET (UTC-5 for EST, UTC-4 for EDT)
        # This is a simplified approach - in production use proper timezone handling
        et_hour = (utc_now.hour - 5) % 24  # EST
        if et_hour < 0:
            et_hour += 24
        
        # After hours: 4:00 PM ET (16:00) to 9:30 AM ET (9:30) next day
        # Pre-market: 4:00 AM ET (4:00) to 9:30 AM ET (9:30)
        # Regular hours: 9:30 AM ET (9:30) to 4:00 PM ET (16:00)
        
        if et_hour >= 16 or et_hour < 9:  # After 4 PM or before 9:30 AM
            return True
        elif et_hour == 9 and utc_now.minute < 30:  # Before 9:30 AM
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking after hours: {e}")
        return False

def get_after_hours_data(ticker: str) -> Dict[str, Any]:
    """Get after-hours percentage change for a ticker"""
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Get after-hours data
        after_hours_data = {}
        
        # Only calculate after-hours data if it's actually after hours
        if not is_after_hours():
            logging.info(f"Not after hours, returning empty after-hours data for {ticker}")
            return after_hours_data
        
        try:
            # Try to get extended hours data
            # First attempt: Get intraday data with pre/post market
            live_data = ticker_obj.history(period='1d', interval='1m', prepost=True)
            
            if not live_data.empty:
                # Get ticker info for regular market prices
                info = ticker_obj.info
                regular_close = info.get('regularMarketPreviousClose') or info.get('previousClose')
                
                if regular_close:
                    # Get current price (including after-hours/pre-market)
                    current_price = live_data.iloc[-1]['Close']
                    
                    # Calculate extended hours percentage change
                    if current_price and regular_close:
                        ah_percentage = ((float(current_price) - float(regular_close)) / float(regular_close)) * 100
                        after_hours_data = {
                            'ah_percentage': float(ah_percentage),
                            'current_price': float(current_price),
                            'regular_close': float(regular_close)
                        }
                        logging.info(f"Calculated extended hours data for {ticker}: {ah_percentage}%")
                else:
                    # Fallback: Try to get current price vs previous close
                    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                    previous_close = info.get('previousClose')
                    
                    if current_price and previous_close:
                        ah_percentage = ((float(current_price) - float(previous_close)) / float(previous_close)) * 100
                        after_hours_data = {
                            'ah_percentage': float(ah_percentage),
                            'current_price': float(current_price),
                            'regular_close': float(previous_close)
                        }
                        logging.info(f"Calculated AH data using fallback method for {ticker}: {ah_percentage}%")
                        
        except Exception as e:
            logging.warning(f"Could not get after-hours data for {ticker}: {e}")
            
            # Ultimate fallback: try to get basic price info
            try:
                info = ticker_obj.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                previous_close = info.get('previousClose')
                
                if current_price and previous_close:
                    ah_percentage = ((float(current_price) - float(previous_close)) / float(previous_close)) * 100
                    after_hours_data = {
                        'ah_percentage': float(ah_percentage),
                        'current_price': float(current_price),
                        'regular_close': float(previous_close)
                    }
                    logging.info(f"Calculated AH data using info fallback for {ticker}: {ah_percentage}%")
            except Exception as fallback_error:
                logging.warning(f"Fallback AH data fetch also failed for {ticker}: {fallback_error}")
        
        return after_hours_data
    except Exception as e:
        logging.error(f"Error fetching after-hours data for {ticker}: {e}")
        return {}

@lru_cache(maxsize=1000)
def get_finviz_data(ticker: str) -> Dict[str, Any]:
    """Get real-time data from Finviz with caching and rate limiting"""
    global _last_api_call_time
    
    # Rate limiting
    current_time = time.time()
    time_since_last_call = current_time - _last_api_call_time
    if time_since_last_call < _min_api_call_interval:
        time.sleep(_min_api_call_interval - time_since_last_call)
    
    _last_api_call_time = time.time()
    
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract current price - try multiple selectors
        current_price = None
        price_selectors = [
            'span.fvz-price',
            'span[class*="price"]',
            'td[class*="price"]',
            'b[class*="price"]'
        ]
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                current_price = price_element.text.strip()
                break
        
        # Extract today's change - try multiple selectors
        today_change = None
        change_selectors = [
            'span.fvz-change',
            'span[class*="change"]',
            'td[class*="change"]',
            'span[class*="percent"]'
        ]
        for selector in change_selectors:
            change_element = soup.select_one(selector)
            if change_element:
                today_change = change_element.text.strip()
                break
        
        # Extract market cap
        market_cap = None
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                if 'Market Cap' in cells[0].text:
                    market_cap = cells[1].text.strip()
                    break
        
        # Extract earning date
        earning_date = None
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                if 'Earnings' in cells[0].text:
                    earning_date = cells[1].text.strip()
                    break
        
        # Log the extracted data for debugging
        if not current_price:
            logging.warning(f"No current price found for {ticker} on Finviz")
        if not today_change:
            logging.warning(f"No today change found for {ticker} on Finviz")
            
        return {
            'current_price': current_price,
            'today_change': today_change,
            'market_cap': market_cap,
            'earning_date': earning_date
        }
    except Exception as e:
        logging.error(f"Error fetching Finviz data for {ticker}: {e}")
        return {}

def get_yahoo_realtime_data(ticker: str) -> Dict[str, Any]:
    """Get real-time data from Yahoo Finance with different approaches for before/after market close"""
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Check if it's after hours
        is_after_hours_trading = is_after_hours()
        logging.info(f"Market status for {ticker}: {'After Hours' if is_after_hours_trading else 'Regular Hours'}")
        
        current_price = None
        today_change = None
        
        if is_after_hours_trading:
            # AFTER MARKET CLOSE: Use after-hours data
            logging.info(f"Using after-hours approach for {ticker}")
            try:
                # Get 1-minute interval data for today (includes after-hours)
                live_data = ticker_obj.history(period='1d', interval='1m', prepost=True)
                if not live_data.empty:
                    current_price = live_data.iloc[-1]['Close']
                    logging.info(f"Got after-hours live data for {ticker}: {current_price}")
                    
                    # Calculate today's change based on previous close
                    try:
                        info = ticker_obj.info
                        previous_close = info.get('previousClose')
                        if previous_close:
                            today_change = ((current_price - previous_close) / previous_close) * 100
                            logging.info(f"Calculated after-hours change for {ticker}: {today_change}%")
                    except Exception as e:
                        logging.warning(f"Could not calculate after-hours change for {ticker}: {e}")
                else:
                    logging.warning(f"No after-hours live data available for {ticker}")
            except Exception as e:
                logging.warning(f"Could not get after-hours live data for {ticker}: {e}")
            
            # Fallback for after-hours: try regular market price
            if not current_price:
                try:
                    info = ticker_obj.info
                    current_price = info.get('regularMarketPrice')
                    if current_price:
                        previous_close = info.get('previousClose')
                        if previous_close:
                            today_change = ((current_price - previous_close) / previous_close) * 100
                        logging.info(f"Using after-hours fallback data for {ticker}: {current_price}")
                except Exception as e:
                    logging.warning(f"Could not get after-hours fallback data for {ticker}: {e}")
        else:
            # BEFORE MARKET CLOSE: Use regular market data
            logging.info(f"Using regular market approach for {ticker}")
            try:
                # Get regular market data (1-minute intervals, no prepost)
                live_data = ticker_obj.history(period='1d', interval='1m', prepost=False)
                if not live_data.empty:
                    current_price = live_data.iloc[-1]['Close']
                    logging.info(f"Got regular market live data for {ticker}: {current_price}")
                    
                    # Calculate today's change based on previous close
                    try:
                        info = ticker_obj.info
                        previous_close = info.get('previousClose')
                        if previous_close:
                            today_change = ((current_price - previous_close) / previous_close) * 100
                            logging.info(f"Calculated regular market change for {ticker}: {today_change}%")
                    except Exception as e:
                        logging.warning(f"Could not calculate regular market change for {ticker}: {e}")
                else:
                    logging.warning(f"No regular market live data available for {ticker}")
            except Exception as e:
                logging.warning(f"Could not get regular market live data for {ticker}: {e}")
            
            # Fallback for regular hours: try regular market price from info
            if not current_price:
                try:
                    info = ticker_obj.info
                    current_price = info.get('regularMarketPrice')
                    if current_price:
                        previous_close = info.get('previousClose')
                        if previous_close:
                            today_change = ((current_price - previous_close) / previous_close) * 100
                        logging.info(f"Using regular market fallback data for {ticker}: {current_price}")
                except Exception as e:
                    logging.warning(f"Could not get regular market fallback data for {ticker}: {e}")
        
        logging.info(f"Final real-time data for {ticker} ({'After Hours' if is_after_hours_trading else 'Regular Hours'}): price={current_price}, change={today_change}")
        
        return {
            'current_price': float(current_price) if current_price is not None else None,
            'today_change': float(today_change) if today_change is not None else None
        }
    except Exception as e:
        logging.error(f"Error fetching Yahoo Finance real-time data for {ticker}: {e}")
        return {}

def get_yahoo_finance_data(ticker: str) -> Dict[str, Any]:
    """Get historical data from Yahoo Finance including after-hours data"""
    try:
        ticker_obj = yf.Ticker(ticker)
        
        # Get historical data for different periods with more data points
        hist_1d = ticker_obj.history(period='5d')  # Get more days to ensure we have enough data
        hist_5d = ticker_obj.history(period='10d')  # Get more days for 5-day calculation
        hist_1m = ticker_obj.history(period='2mo')  # Get more data for 1-month calculation
        hist_6m = ticker_obj.history(period='7mo')  # Get more data for 6-month calculation
        hist_1y = ticker_obj.history(period='2y')   # Get more data for 1-year calculation
        
        # Get info for market cap and earning date
        info = ticker_obj.info
        
        # Get current price including after-hours data
        current_price = None
        try:
            # Try to get real-time price with after-hours data
            # This includes pre-market and after-hours trading data
            live_price = ticker_obj.history(period='1d', interval='1m')
            if not live_price.empty:
                current_price = live_price.iloc[-1]['Close']
            else:
                # Fallback to regular close price
                current_price = info.get('regularMarketPrice', None)
        except Exception as e:
            logging.warning(f"Could not get live price for {ticker}: {e}")
            current_price = info.get('regularMarketPrice', None)
        
        # Process today's data (1D) - this should be the current day's data
        today_data = {}
        if len(hist_1d) >= 2:
            today_row = hist_1d.iloc[-1]  # Most recent day
            prev_row = hist_1d.iloc[-2]   # Previous day
            today_data = {
                'low': today_row['Low'],
                'high': today_row['High'],
                'percentage': ((today_row['Close'] - prev_row['Close']) / prev_row['Close']) * 100
            }
        
        # Process previous day data (1D) - this should be the previous trading day
        prev_day_data = {}
        if len(hist_1d) >= 3:
            prev_row = hist_1d.iloc[-2]      # Previous day
            prev_prev_row = hist_1d.iloc[-3] # Day before previous
            prev_day_data = {
                'low': prev_row['Low'],
                'high': prev_row['High'],
                'percentage': ((prev_row['Close'] - prev_prev_row['Close']) / prev_prev_row['Close']) * 100
            }
        elif len(hist_1d) >= 2:
            # If we only have 2 days, use the previous day as 1D data
            prev_row = hist_1d.iloc[-2]
            today_row = hist_1d.iloc[-1]
            prev_day_data = {
                'low': prev_row['Low'],
                'high': prev_row['High'],
                'percentage': ((prev_row['Close'] - today_row['Close']) / today_row['Close']) * 100
            }
        
        # Process 5-day data
        five_day_data = {}
        if len(hist_5d) >= 5:
            current_close = hist_5d.iloc[-1]['Close']
            five_day_ago_close = hist_5d.iloc[-5]['Close']
            five_day_data = {
                'low': hist_5d['Low'].min(),
                'high': hist_5d['High'].max(),
                'percentage': ((current_close - five_day_ago_close) / five_day_ago_close) * 100
            }
        elif len(hist_5d) >= 2:
            # Fallback if we don't have 5 days
            current_close = hist_5d.iloc[-1]['Close']
            start_close = hist_5d.iloc[0]['Close']
            five_day_data = {
                'low': hist_5d['Low'].min(),
                'high': hist_5d['High'].max(),
                'percentage': ((current_close - start_close) / start_close) * 100
            }
        
        # Process 1-month data
        one_month_data = {}
        if len(hist_1m) >= 20:
            current_close = hist_1m.iloc[-1]['Close']
            month_ago_close = hist_1m.iloc[-20]['Close']
            one_month_data = {
                'low': hist_1m['Low'].min(),
                'high': hist_1m['High'].max(),
                'percentage': ((current_close - month_ago_close) / month_ago_close) * 100
            }
        elif len(hist_1m) >= 5:
            # Fallback if we don't have 20 days
            current_close = hist_1m.iloc[-1]['Close']
            start_close = hist_1m.iloc[0]['Close']
            one_month_data = {
                'low': hist_1m['Low'].min(),
                'high': hist_1m['High'].max(),
                'percentage': ((current_close - start_close) / start_close) * 100
            }
        
        # Process 6-month data
        six_month_data = {}
        if len(hist_6m) >= 120:
            current_close = hist_6m.iloc[-1]['Close']
            six_month_ago_close = hist_6m.iloc[-120]['Close']
            six_month_data = {
                'low': hist_6m['Low'].min(),
                'high': hist_6m['High'].max(),
                'percentage': ((current_close - six_month_ago_close) / six_month_ago_close) * 100
            }
        elif len(hist_6m) >= 30:
            # Fallback if we don't have 120 days
            current_close = hist_6m.iloc[-1]['Close']
            start_close = hist_6m.iloc[0]['Close']
            six_month_data = {
                'low': hist_6m['Low'].min(),
                'high': hist_6m['High'].max(),
                'percentage': ((current_close - start_close) / start_close) * 100
            }
        
        # Process 1-year data
        one_year_data = {}
        if len(hist_1y) >= 252:
            # Full year of trading days
            current_close = hist_1y.iloc[-1]['Close']
            year_ago_close = hist_1y.iloc[-252]['Close']
            one_year_data = {
                'low': hist_1y['Low'].min(),
                'high': hist_1y['High'].max(),
                'percentage': ((current_close - year_ago_close) / year_ago_close) * 100
            }
        elif len(hist_1y) >= 200:
            # At least 200 trading days (about 10 months)
            current_close = hist_1y.iloc[-1]['Close']
            start_close = hist_1y.iloc[0]['Close']
            one_year_data = {
                'low': hist_1y['Low'].min(),
                'high': hist_1y['High'].max(),
                'percentage': ((current_close - start_close) / start_close) * 100
            }
        elif len(hist_1y) >= 60:
            # At least 60 trading days (about 3 months)
            current_close = hist_1y.iloc[-1]['Close']
            start_close = hist_1y.iloc[0]['Close']
            one_year_data = {
                'low': hist_1y['Low'].min(),
                'high': hist_1y['High'].max(),
                'percentage': ((current_close - start_close) / start_close) * 100
            }
        else:
            # Not enough data for 1Y calculation
            one_year_data = {
                'low': 'N/A',
                'high': 'N/A',
                'percentage': 'N/A'
            }
        
        # Get market cap and earning date
        market_cap = info.get('marketCap', 'N/A')
        earning_timestamp = info.get('earningsTimestamp', None)
        earning_date = 'N/A'
        
        if earning_timestamp and earning_timestamp != 'N/A':
            try:
                if isinstance(earning_timestamp, (int, float)):
                    earning_date = Timestamp(earning_timestamp, unit='s').strftime('%Y-%m-%d')
                else:
                    earning_date = Timestamp(earning_timestamp).strftime('%Y-%m-%d')
            except Exception:
                earning_date = 'N/A'
        
        return {
            'market_cap': market_cap,
            'earning_date': earning_date,
            'current_price': current_price,
            'today': today_data,
            'previous_day': prev_day_data,
            'five_day': five_day_data,
            'one_month': one_month_data,
            'six_month': six_month_data,
            'one_year': one_year_data
        }
    except Exception as e:
        logging.error(f"Error fetching Yahoo Finance data for {ticker}: {e}")
        return {}

def load_stocks():
    """Load stocks from stock.json file"""
    try:
        with open('stock.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_ticker_today_data(data: List[Dict[str, Any]]):
    """Save enhanced stock data to Ticker_Today.json"""
    try:
        with open('Ticker_Today.json', 'w') as file:
            json.dump(data, file, indent=2)
        logging.info(f"Saved {len(data)} stock records to Ticker_Today.json")
    except Exception as e:
        logging.error(f"Error saving Ticker_Today.json: {e}")

def load_ticker_today_data():
    """Load enhanced stock data from Ticker_Today.json"""
    try:
        with open('Ticker_Today.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def needs_daily_update() -> bool:
    """Check if Ticker_Today.json needs to be updated based on date"""
    try:
        # Check if file exists
        if not os.path.exists('Ticker_Today.json'):
            return True
        
        # Check file modification time
        file_mtime = os.path.getmtime('Ticker_Today.json')
        file_date = datetime.fromtimestamp(file_mtime).date()
        current_date = datetime.now().date()
        
        # Update if file is from a different date
        return file_date < current_date
    except Exception as e:
        logging.error(f"Error checking if daily update is needed: {e}")
        return True

def process_single_enhanced_stock(symbol: str, stocks: List[Dict]) -> Dict[str, Any]:
    """Process a single stock with enhanced data structure"""
    try:
        # Get sector and isxticker from stock.json
        stock_info = next((stock for stock in stocks if stock['ticker'] == symbol), None)
        sector = stock_info.get('sector', 'N/A') if stock_info else 'N/A'
        isxticker = stock_info.get('isxticker', False) if stock_info else False
        
        # Get data from Yahoo Finance
        yahoo_data = get_yahoo_finance_data(symbol)
        
        # Get real-time data from Finviz
        finviz_data = get_finviz_data(symbol)
        
        # Get current price - prioritize Yahoo Finance for after-hours data
        current_price = None
        
        # First try Yahoo Finance (includes after-hours)
        if yahoo_data.get('current_price'):
            try:
                current_price = fmt_currency(float(yahoo_data['current_price']))
            except (ValueError, TypeError):
                current_price = None
        
        # Fallback to Finviz if Yahoo Finance doesn't have current price
        if not current_price and finviz_data.get('current_price'):
            current_price = finviz_data.get('current_price')
        
        # Last resort: use today's high from Yahoo data
        if not current_price and yahoo_data.get('today', {}).get('high'):
            try:
                current_price = fmt_currency(yahoo_data['today'].get('high', 0))
            except:
                current_price = 'N/A'
        
        if not current_price:
            current_price = 'N/A'
            
        market_cap = finviz_data.get('market_cap') or yahoo_data.get('market_cap', 'N/A')
        earning_date = finviz_data.get('earning_date') or yahoo_data.get('earning_date', 'N/A')
        
        # Format market cap
        if market_cap and market_cap != 'N/A':
            try:
                market_cap = fmt_market_cap(float(market_cap))
            except (ValueError, TypeError):
                market_cap = 'N/A'
        
        # Format time-based data
        def format_time_data(data: Dict) -> Dict:
            if not data:
                return {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'}
            return {
                'low': fmt_currency(data.get('low', 0)),
                'high': fmt_currency(data.get('high', 0)),
                'percentage': fmt_percent(data.get('percentage', 0))
            }
        
        # Get today's change from Finviz or calculate from Yahoo data
        today_change = finviz_data.get('today_change')
        if not today_change and yahoo_data.get('today', {}).get('percentage') is not None:
            today_change = fmt_percent(yahoo_data['today']['percentage'])
        
        # Get after-hours percentage
        ah_data = get_after_hours_data(symbol)
        ah_percentage = 'NIL'
        if ah_data.get('ah_percentage') is not None:
            if is_after_hours():
                ah_percentage = fmt_percent(ah_data['ah_percentage'])
            else:
                ah_percentage = 'NIL'
        
        return {
            'ticker': symbol,
            'sector': sector,
            'isxticker': isxticker,
            'market_cap': market_cap,
            'earning_date': earning_date,
            'current_price': current_price,
            'today': format_time_data(yahoo_data.get('today', {})),
            'previous_day': format_time_data(yahoo_data.get('previous_day', {})),
            'five_day': format_time_data(yahoo_data.get('five_day', {})),
            'one_month': format_time_data(yahoo_data.get('one_month', {})),
            'six_month': format_time_data(yahoo_data.get('six_month', {})),
            'one_year': format_time_data(yahoo_data.get('one_year', {})),
            'ah_percentage': ah_percentage
        }
    except Exception as e:
        logging.error(f"Error processing enhanced stock data for {symbol}: {e}")
        return {
            'ticker': symbol,
            'sector': 'N/A',
            'isxticker': False,
            'market_cap': 'N/A',
            'earning_date': 'N/A',
            'current_price': 'N/A',
            'today': {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'},
            'previous_day': {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'},
            'five_day': {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'},
            'one_month': {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'},
            'six_month': {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'},
            'one_year': {'low': 'N/A', 'high': 'N/A', 'percentage': 'N/A'},
            'ah_percentage': 'NIL'
        }

def update_ticker_today_data():
    """Update Ticker_Today.json with fresh data from finance APIs"""
    stocks = load_stocks()
    symbols = [stock['ticker'] for stock in stocks]
    
    logging.info(f"Updating Ticker_Today.json with data for {len(symbols)} stocks")
    
    # Process stocks in parallel
    results = []
    max_workers = min(20, len(symbols))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(process_single_enhanced_stock, symbol, stocks): symbol 
            for symbol in symbols
        }
        
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                result = future.result()
                results.append(result)
                logging.info(f"Completed processing for {symbol}")
            except Exception as e:
                logging.error(f"Exception occurred while processing {symbol}: {e}")
                results.append(process_single_enhanced_stock(symbol, stocks))
    
    # Save to Ticker_Today.json
    save_ticker_today_data(results)
    return results

def force_update_ticker_today_data():
    """Force update Ticker_Today.json regardless of daily update check"""
    logging.info("Force updating Ticker_Today.json due to stock/sector changes")
    return update_ticker_today_data()

def get_enhanced_stock_details(tickers_param: str = "", sector_param: str = "", 
                              leverage_filter: str = "Ticker Only", sort_by: str = "today_percentage", 
                              sort_order: str = "desc") -> Dict[str, Any]:
    """
    Get enhanced stock details with new data structure
    leverage_filter options: "Ticker Only", "Leverage Only", "Both"
    """
    # Check if Ticker_Today.json exists and has data, or needs daily update
    ticker_today_data = load_ticker_today_data()
    
    if not ticker_today_data or needs_daily_update():
        logging.info("Ticker_Today.json is empty, doesn't exist, or needs daily update, updating with fresh data...")
        ticker_today_data = update_ticker_today_data()
    
    # Filter by ticker
    if tickers_param:
        requested_tickers = [t.strip().upper() for t in tickers_param.split(',') if t.strip()]
        ticker_today_data = [stock for stock in ticker_today_data 
                           if stock['ticker'].upper() in requested_tickers]
    
    # Filter by sector
    if sector_param:
        ticker_today_data = [stock for stock in ticker_today_data 
                           if stock['sector'].lower() == sector_param.lower()]
    
    # Filter by leverage type
    if leverage_filter == "Ticker Only":
        ticker_today_data = [stock for stock in ticker_today_data if not stock['isxticker']]
    elif leverage_filter == "Leverage Only":
        ticker_today_data = [stock for stock in ticker_today_data if stock['isxticker']]
    # "Both" means no filtering
    
    # Sort results
    if sort_by and ticker_today_data:
        logging.info(f"Sorting {len(ticker_today_data)} records by {sort_by} in {sort_order} order")
        try:
            sortable_columns = {
                'ticker': 'ticker',
                'earning_date': 'earning_date',
                'market_cap': 'market_cap',
                'current_price': 'current_price',
                'today_percentage': 'today.percentage',
                'previous_day_percentage': 'previous_day.percentage',
                'five_day_percentage': 'five_day.percentage',
                'one_month_percentage': 'one_month.percentage',
                'six_month_percentage': 'six_month.percentage',
                'one_year_percentage': 'one_year.percentage',
                'ah_percentage': 'ah_percentage'
            }
            
            if sort_by in sortable_columns:
                key = sortable_columns[sort_by]
                logging.info(f"Sorting by column: {sort_by} -> {key}")
                
                def sort_key(item):
                    if '.' in key:
                        # Handle nested keys like 'today.percentage'
                        keys = key.split('.')
                        value = item
                        for k in keys:
                            value = value.get(k, 'N/A')
                    else:
                        value = item.get(key, 'N/A')
                    
                    # Handle None values
                    if value is None:
                        value = 'N/A'
                    
                    # Extract numeric value from percentage strings
                    if 'percentage' in key:
                        try:
                            if value == 'N/A' or value == 'NIL':
                                return float('inf') if sort_order == 'asc' else float('-inf')
                            return float(str(value).replace('%', '').replace('+', ''))
                        except (ValueError, AttributeError):
                            return float('inf') if sort_order == 'asc' else float('-inf')
                    elif key == 'ah_percentage':
                        try:
                            if value == 'N/A':
                                return float('inf') if sort_order == 'asc' else float('-inf')
                            elif value == 'NIL':
                                # For NIL (no after-hours trading), use a middle value
                                # This ensures NIL values are sorted between positive and negative values
                                return 0.0
                            return float(str(value).replace('%', '').replace('+', ''))
                        except (ValueError, AttributeError):
                            return float('inf') if sort_order == 'asc' else float('-inf')
                    elif key == 'earning_date':
                        try:
                            if value == 'N/A' or value is None:
                                return '9999-12-31' if sort_order == 'asc' else '1900-01-01'
                            # Convert to string and ensure it's a valid date format
                            value_str = str(value).strip()
                            if not value_str or value_str == 'N/A':
                                return '9999-12-31' if sort_order == 'asc' else '1900-01-01'
                            return value_str
                        except:
                            return '9999-12-31' if sort_order == 'asc' else '1900-01-01'
                    elif key == 'current_price':
                        try:
                            if value == 'N/A':
                                return float('inf') if sort_order == 'asc' else float('-inf')
                            return float(str(value).replace('$', '').replace(',', ''))
                        except (ValueError, AttributeError):
                            return float('inf') if sort_order == 'asc' else float('-inf')
                    elif key == 'ticker':
                        return str(value).upper()  # Ensure ticker is string and uppercase
                    elif key == 'market_cap':
                        try:
                            if value == 'N/A':
                                return float('inf') if sort_order == 'asc' else float('-inf')
                            # Remove common market cap suffixes and convert to number
                            value_str = str(value).upper()
                            multiplier = 1
                            if 'T' in value_str:
                                multiplier = 1000000000000
                                value_str = value_str.replace('T', '')
                            elif 'B' in value_str:
                                multiplier = 1000000000
                                value_str = value_str.replace('B', '')
                            elif 'M' in value_str:
                                multiplier = 1000000
                                value_str = value_str.replace('M', '')
                            return float(value_str.replace('$', '').replace(',', '')) * multiplier
                        except (ValueError, AttributeError):
                            return float('inf') if sort_order == 'asc' else float('-inf')
                    else:
                        return str(value)  # Default to string comparison
                
                try:
                    ticker_today_data.sort(key=sort_key, reverse=(sort_order.lower() == 'desc'))
                    logging.info(f"Successfully sorted {len(ticker_today_data)} records")
                except Exception as sort_error:
                    logging.error(f"Sort operation failed: {sort_error}")
                    # Fallback: sort by ticker as a safe default
                    ticker_today_data.sort(key=lambda x: str(x.get('ticker', '')).upper())
                    logging.info(f"Fallback sorted {len(ticker_today_data)} records by ticker")
                
        except Exception as e:
            logging.error(f"Error sorting results: {e}")
            logging.error(f"Sort by: {sort_by}, Sort order: {sort_order}")
            # Log a few sample items to debug
            if ticker_today_data:
                sample_item = ticker_today_data[0]
                logging.error(f"Sample item keys: {list(sample_item.keys())}")
                if sort_by in sortable_columns:
                    key = sortable_columns[sort_by]
                    if '.' in key:
                        keys = key.split('.')
                        value = sample_item
                        for k in keys:
                            value = value.get(k, 'N/A')
                    else:
                        value = sample_item.get(key, 'N/A')
                    logging.error(f"Sample value for {key}: {value} (type: {type(value)})")
    
    return {
        'results': ticker_today_data,
        'total': len(ticker_today_data)
    }

def get_realtime_price_updates(tickers: List[str]) -> Dict[str, Dict[str, str]]:
    """Get real-time price, today's data, and after-hours updates for specified tickers using batch processing with after-hours support"""
    if not tickers:
        return {}
    
    # Limit batch size to prevent overwhelming the API
    max_batch_size = 50
    if len(tickers) > max_batch_size:
        logging.warning(f"Batch size {len(tickers)} exceeds limit of {max_batch_size}, truncating")
        tickers = tickers[:max_batch_size]
    
    # Check if it's after hours
    is_after_hours_trading = is_after_hours()
    logging.info(f"Starting real-time price updates for {len(tickers)} tickers: {tickers} ({'After Hours' if is_after_hours_trading else 'Regular Hours'})")
    
    updates = {}
    
    # Use ThreadPoolExecutor for parallel processing to avoid blocking
    # Limit workers to prevent too many concurrent requests
    max_workers = min(10, len(tickers))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all ticker requests - use Yahoo Finance for after-hours data
        future_to_ticker = {
            executor.submit(get_yahoo_realtime_data, ticker): ticker 
            for ticker in tickers
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                yahoo_data = future.result()
                current_price = yahoo_data.get('current_price')
                today_change = yahoo_data.get('today_change')
                
                logging.info(f"Raw Yahoo data for {ticker}: price={current_price}, change={today_change}")
                
                # Format the data
                if current_price:
                    try:
                        current_price = fmt_currency(float(current_price))
                    except (ValueError, TypeError):
                        current_price = 'N/A'
                
                if today_change is not None:
                    try:
                        today_change = fmt_percent(today_change)
                    except (ValueError, TypeError):
                        today_change = 'N/A'
                
                # Get after-hours percentage
                ah_data = get_after_hours_data(ticker)
                ah_percentage = 'NIL'
                if ah_data.get('ah_percentage') is not None:
                    if is_after_hours_trading:
                        try:
                            ah_percentage = fmt_percent(ah_data['ah_percentage'])
                        except (ValueError, TypeError):
                            ah_percentage = 'NIL'
                    else:
                        ah_percentage = 'NIL'
                
                # During after-hours, don't update today_change (keep it frozen)
                # Only update current_price and ah_percentage
                if is_after_hours_trading:
                    updates[ticker] = {
                        'current_price': current_price or 'N/A',
                        'today_change': 'FROZEN',  # Signal to frontend to use cached data
                        'ah_percentage': ah_percentage
                    }
                    logging.info(f"After-hours update for {ticker}: current_price={current_price}, today_change=FROZEN, ah_percentage={ah_percentage}")
                else:
                    # During regular hours, update all fields
                    updates[ticker] = {
                        'current_price': current_price or 'N/A',
                        'today_change': today_change or 'N/A',
                        'ah_percentage': ah_percentage
                    }
                    logging.info(f"Regular hours update for {ticker}: current_price={current_price}, today_change={today_change}, ah_percentage={ah_percentage}")
                
                logging.info(f"Processed real-time data for {ticker}: {updates[ticker]}")
                
            except Exception as e:
                logging.error(f"Error getting real-time data for {ticker}: {e}")
                # Add placeholder for failed requests
                if is_after_hours_trading:
                    updates[ticker] = {
                        'current_price': 'N/A',
                        'today_change': 'FROZEN',  # Keep frozen during after-hours
                        'ah_percentage': 'NIL'
                    }
                else:
                    updates[ticker] = {
                        'current_price': 'N/A',
                        'today_change': 'N/A',
                        'ah_percentage': 'NIL'
                    }
    
    logging.info(f"Completed real-time price updates for {len(updates)} tickers ({'After Hours' if is_after_hours_trading else 'Regular Hours'})")
    return updates
