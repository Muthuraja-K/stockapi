import json
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import requests
from config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockHistoryOperations:
    def __init__(self):
        self.stockhistory_file = "stockhistory.json"
        self.stocks_file = "stock.json"
        self._cache_timestamp_file = "cache_timestamps.json"
    
    def _save_cache_timestamp(self, cache_type: str):
        """Save cache timestamp for a specific cache type"""
        try:
            timestamps = {}
            if os.path.exists(self._cache_timestamp_file):
                with open(self._cache_timestamp_file, 'r') as f:
                    timestamps = json.load(f)
            
            timestamps[cache_type] = datetime.now().isoformat()
            
            with open(self._cache_timestamp_file, 'w') as f:
                json.dump(timestamps, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not save cache timestamp for {cache_type}: {e}")
    
    def should_populate_history(self) -> bool:
        """Check if stock history should be populated based on cache timestamp"""
        try:
            if not os.path.exists(self._cache_timestamp_file):
                return True
            
            with open(self._cache_timestamp_file, 'r') as f:
                timestamps = json.load(f)
            
            if 'history' not in timestamps:
                return True
            
            last_update = datetime.fromisoformat(timestamps['history'])
            current_time = datetime.now()
            
            # Populate history if it's been more than 24 hours since last update
            return (current_time - last_update).total_seconds() > 24 * 3600
            
        except Exception as e:
            logger.warning(f"Error checking history population status: {e}")
            return True  # Default to populate if there's an error
    
    def should_populate_market_data(self) -> bool:
        """Check if market data should be populated based on cache timestamp"""
        try:
            if not os.path.exists(self._cache_timestamp_file):
                return True
            
            with open(self._cache_timestamp_file, 'r') as f:
                timestamps = json.load(f)
            
            if 'market' not in timestamps:
                return True
            
            last_update = datetime.fromisoformat(timestamps['market'])
            current_time = datetime.now()
            
            # Populate market data if it's been more than 1 hour since last update
            return (current_time - last_update).total_seconds() > 3600
            
        except Exception as e:
            logger.warning(f"Error checking market data population status: {e}")
            return True  # Default to populate if there's an error
    
    def get_finviz_data_for_tickers(self, tickers: List[str]) -> Dict[str, Dict]:
        """Get real-time market data from Finviz API for multiple tickers"""
        try:
            if not config.FINVIZ_AUTH_ID:
                logger.warning("FINVIZ_AUTH_ID not configured, skipping Finviz data fetch")
                return {}
            
            # Finviz CSV export API endpoint - using view 152 with column parameter to get specific fields
            url = f"https://elite.finviz.com/export.ashx"
            params = {
                'v': '152',  # View 152 as specified by user
                't': ','.join(tickers),
                'c': '1,6,7,65,66,67,68,71,72,81,86,87,88',  # Include Ticker (1) + Market Cap, P/E, Price, Change, Volume, Earnings Date, After-Hours Close, After-Hours Change, Prev Close, Open, High, Low
                'auth': config.FINVIZ_AUTH_ID
            }
            
            logger.info(f"Fetching Finviz data for {len(tickers)} tickers")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Finviz API request failed with status {response.status_code}")
                return {}
            
            # DEBUG: Log the actual response
            logger.info(f"Finviz API response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response text (first 500 chars): {response.text[:500]}")
            
            # Parse CSV response
            lines = response.text.strip().split('\n')
            if len(lines) < 2:  # Need header + at least one data row
                logger.warning("Finviz API returned insufficient data")
                return {}
            
            # Parse header to get column indices
            header = lines[0].split(',')
            column_map = {}
            for i, col in enumerate(header):
                column_map[col.strip()] = i
            
            logger.info(f"Available columns: {list(column_map.keys())}")
            logger.info(f"Column mapping: {column_map}")
            
            # Parse data rows
            finviz_data = {}
            for line in lines[1:]:  # Skip header
                if not line.strip():
                    continue
                
                values = line.split(',')
                if len(values) < len(header):
                    continue
                
                ticker = values[column_map.get('"Ticker"', 0)].strip().strip('"')  # Remove quotes
                if not ticker:
                    continue
                
                logger.info(f"Processing ticker: {ticker}, values: {values}")
                
                # Extract market data using actual column names from CSV
                finviz_data[ticker] = {
                    'Ticker': ticker,
                    'Market Cap': values[column_map.get('"Market Cap"', 0)].strip('"') if '"Market Cap"' in column_map else 'N/A',
                    'P/E': values[column_map.get('"P/E"', 0)].strip('"') if '"P/E"' in column_map else 'N/A',
                    'Price': values[column_map.get('"Price"', 0)].strip('"') if '"Price"' in column_map else 'N/A',
                    'Change': values[column_map.get('"Change"', 0)].strip('"') if '"Change"' in column_map else 'N/A',
                    'Volume': values[column_map.get('"Volume"', 0)].strip('"') if '"Volume"' in column_map else 'N/A',
                    'Earnings Date': values[column_map.get('"Earnings Date"', 0)].strip('"') if '"Earnings Date"' in column_map else 'N/A',
                    'After-Hours Close': values[column_map.get('"After-Hours Close"', 0)].strip('"') if '"After-Hours Close"' in column_map else 'N/A',
                    'After-Hours Change': values[column_map.get('"After-Hours Change"', 0)].strip('"') if '"After-Hours Change"' in column_map else 'N/A',
                    'Prev Close': values[column_map.get('"Prev Close"', 0)].strip('"') if '"Prev Close"' in column_map else 'N/A',
                    'Open': values[column_map.get('"Open"', 0)].strip('"') if '"Open"' in column_map else 'N/A',
                    'High': values[column_map.get('"High"', 0)].strip('"') if '"High"' in column_map else 'N/A',
                    'Low': values[column_map.get('"Low"', 0)].strip('"') if '"Low"' in column_map else 'N/A'
                }
            
            logger.info(f"Successfully fetched Finviz data for {len(finviz_data)} tickers")
            return finviz_data
            
        except Exception as e:
            logger.error(f"Error fetching Finviz data: {e}")
            return {}
    
    def populate_stock_market_data(self) -> bool:
        """Populate stock market data for all stocks using Finviz API and yfinance for missing fields"""
        try:
            logger.info("Starting stock market data population using Finviz and yfinance...")
            
            # Load stocks
            if not os.path.exists(self.stocks_file):
                logger.error(f"Stocks file {self.stocks_file} not found")
                return False
            
            with open(self.stocks_file, 'r') as f:
                stocks = json.load(f)
            
            if not stocks:
                logger.error("No stocks found in stocks file")
                return False
            
            logger.info(f"Found {len(stocks)} stocks to process for market data")
            
            # Get all tickers
            tickers = [stock.get('ticker') for stock in stocks if stock.get('ticker')]
            
            if not tickers:
                logger.error("No valid tickers found")
                return False
            
            # Fetch data from Finviz API for basic market data
            finviz_data = self.get_finviz_data_for_tickers(tickers)
            
            # Create market data structure
            market_data = []
            
            for stock in stocks:
                ticker = stock.get('ticker')
                sector = stock.get('sector', 'Unknown')
                
                if not ticker:
                    continue
                
                # Get Finviz data for this ticker
                ticker_finviz_data = finviz_data.get(ticker, {})
                # Only use Finviz data for stockhistorymarketdata, do not use yfinance
                # Extract today's metrics from Finviz data only
                today_metrics = {}
                try:
                    low = ticker_finviz_data.get('Low', 'N/A')
                    high = ticker_finviz_data.get('High', 'N/A')
                    open_price = ticker_finviz_data.get('Open', 'N/A')
                    close_price = ticker_finviz_data.get('Price', 'N/A')
                    prev_close = ticker_finviz_data.get('Prev Close', 'N/A')
                    ah_close = ticker_finviz_data.get('After-Hours Close', 'N/A')
                    ah_change = ticker_finviz_data.get('After-Hours Change', 'N/A')
                    change = ticker_finviz_data.get('Change', 'N/A')
                    volume = ticker_finviz_data.get('Volume', 'N/A')

                    # Convert numeric values and round to 2 decimal places
                    def safe_float(val):
                        try:
                            return round(float(val), 2)
                        except (ValueError, TypeError):
                            return None

                    low = safe_float(low) if low not in ('N/A', None, '') else None
                    high = safe_float(high) if high not in ('N/A', None, '') else None
                    open_price = safe_float(open_price) if open_price not in ('N/A', None, '') else None
                    close_price = safe_float(close_price) if close_price not in ('N/A', None, '') else None
                    prev_close = safe_float(prev_close) if prev_close not in ('N/A', None, '') else None
                    volume = int(volume) if isinstance(volume, (int, float, str)) and str(volume).replace('.', '', 1).isdigit() else None

                    today_metrics = {
                        "low": low,
                        "high": high,
                        "open": open_price,
                        "close": close_price,
                        "prev_close": prev_close,
                        "ah_close": ah_close,
                        "ah_change": ah_change,
                        "change": change,
                        "volume": volume
                    }
                except Exception as e:
                    logger.warning(f"Error extracting Finviz OHLC data for {ticker}: {e}")
                    today_metrics = {}

                # Compose the market data entry
                market_entry = {
                    "ticker": ticker,
                    "sector": sector,
                    "earning_date": ticker_finviz_data.get('Earnings Date', 'N/A'),
                    "market_cap": ticker_finviz_data.get('Market Cap', 'N/A'),
                    "pe_ratio": ticker_finviz_data.get('P/E', 'N/A'),
                    "price": ticker_finviz_data.get('Price', 'N/A'),
                    "after_hour_price": ticker_finviz_data.get('After-Hours Close', 'N/A'),
                    "volume": today_metrics.get("volume"),
                    "today": {
                        "low": today_metrics.get("low"),
                        "high": today_metrics.get("high"),
                        "open": today_metrics.get("open"),
                        "close": today_metrics.get("close"),
                        "prev_close": today_metrics.get("prev_close"),
                        "ah_change": today_metrics.get("ah_change"),
                        "change": today_metrics.get("change")
                    },
                    "last_updated": datetime.now().isoformat()
                }
                market_data.append(market_entry)
                logger.info(f"Processed market data for {ticker}")
            
            # Save market data to file
            market_data_file = "stockhistorymarketdata.json"
            try:
                with open(market_data_file, 'w') as f:
                    json.dump(market_data, f, indent=2)
                logger.info(f"Market data saved to {market_data_file}")
                
                # Save cache timestamp for successful population
                self._save_cache_timestamp('market')
                
                return True
                
            except Exception as e:
                logger.error(f"Error saving market data: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error in populate_stock_market_data: {e}")
            return False
    
    def populate_stock_history(self) -> bool:
        """Populate stock history data for all stocks"""
        try:
            logger.info("Starting stock history population...")
            
            # Load stocks
            if not os.path.exists(self.stocks_file):
                logger.error(f"Stocks file {self.stocks_file} not found")
                return False
            
            with open(self.stocks_file, 'r') as f:
                stocks = json.load(f)
            
            if not stocks:
                logger.error("No stocks found in stocks file")
                return False
            
            logger.info(f"Found {len(stocks)} stocks to process")
            
            # Get all tickers
            tickers = [stock.get('ticker') for stock in stocks if stock.get('ticker')]
            
            if not tickers:
                logger.error("No valid tickers found")
                return False
            
            logger.info(f"Processing tickers: {tickers}")
            
            # Download data
            try:
                # Download 1 year of data for all tickers (covers all periods we need)
                all_data = yf.download(tickers, period="1y", group_by='ticker', progress=False)
                logger.info("Data download completed successfully")
                
                # The issue is that when downloading multiple tickers, some may have incomplete data
                # Instead of trying to fill missing data, let's ensure we get the most recent data
                # by using a more robust data extraction approach
                logger.info("Data download completed - will handle missing data during processing")
                        
            except Exception as e:
                logger.error(f"Error downloading data: {e}")
                return False
            
            # Process each stock
            stock_history_data = []
            for stock in stocks:
                ticker = stock.get('ticker')
                sector = stock.get('sector', 'Unknown')
                isleverage = stock.get('isleverage', False)
                
                if not ticker:
                    continue
                
                try:
                    # Extract data for this specific ticker
                    if len(tickers) == 1:
                        # Single ticker case
                        hist = all_data
                    else:
                        # Multiple tickers case - data is multi-level
                        if ticker in all_data.columns.levels[0]:
                            hist = all_data[ticker]
                            # Ensure we have the complete date range by reindexing
                            hist = hist.reindex(all_data.index)
                        else:
                            logger.warning(f"Ticker {ticker} not found in downloaded data")
                            continue
                    
                    if hist.empty:
                        logger.warning(f"No data found for {ticker}")
                        continue
                    
                    # Define periods and their corresponding data ranges
                    # Ensure we get complete data by filtering out NaN values
                    periods_data = {}
                    
                    # For 5D, get the last 5 valid trading days
                    valid_5d = hist.dropna().tail(5)
                    if len(valid_5d) >= 5:
                        periods_data['5D'] = valid_5d
                    else:
                        # If we don't have 5 valid days, get what we have
                        periods_data['5D'] = valid_5d
                    
                    # For 1M, get the last 30 valid trading days
                    valid_1m = hist.dropna().tail(30)
                    if len(valid_1m) >= 30:
                        periods_data['1M'] = valid_1m
                    else:
                        periods_data['1M'] = valid_1m
                    
                    # For 6M, get the last 180 valid trading days
                    valid_6m = hist.dropna().tail(180)
                    if len(valid_6m) >= 180:
                        periods_data['6M'] = valid_6m
                    else:
                        periods_data['6M'] = valid_6m
                    
                    # For 1Y, use all valid data
                    periods_data['1Y'] = hist.dropna()
                    
                    # For 1D, get the last valid trading day
                    valid_1d = hist.dropna().tail(1)
                    if len(valid_1d) >= 1:
                        periods_data['1D'] = valid_1d
                    else:
                        periods_data['1D'] = valid_1d
                    
                    # FIXED: Helper function to get column data handling MultiIndex columns properly
                    def get_column_data(data, column_name):
                        """Get column data handling both single and multi-level columns"""
                        if isinstance(data.columns, pd.MultiIndex):
                            # Multi-level columns - look for the specific ticker column
                            col_key = (column_name, ticker)
                            if col_key in data.columns:
                                return data[col_key]
                            else:
                                # Fallback to first available column of this type
                                available_cols = [col for col in data.columns if col[0] == column_name]
                                if available_cols:
                                    return data[available_cols[0]]
                                else:
                                    return pd.Series(dtype=float)
                        else:
                            # Single-level columns (this is the case when data is extracted for a specific ticker)
                            if column_name in data.columns:
                                return data[column_name]
                            else:
                                # If column doesn't exist, return empty series
                                return pd.Series(dtype=float)
                    
                    history_data = {}
                    for period_name, period_data in periods_data.items():
                        try:
                            # FIXED: For 1D, we need at least 1 day; for other periods, we need at least 2 days
                            min_required_days = 1 if period_name == '1D' else 2
                            if not period_data.empty and len(period_data) >= min_required_days:
                                try:
                                    low_data = get_column_data(period_data, 'Low')
                                    high_data = get_column_data(period_data, 'High')
                                    
                                    if not low_data.empty and not high_data.empty:
                                        # Extract the actual values from the Series
                                        low = low_data.min()
                                        high = high_data.max()
                                        
                                        # If the result is still a Series, get the first value
                                        if isinstance(low, pd.Series):
                                            low = low.iloc[0] if not low.empty else None
                                        if isinstance(high, pd.Series):
                                            high = high.iloc[0] if not high.empty else None
                                        
                                        # Round to 2 decimal places for cleaner display
                                        if low is not None and not pd.isna(low):
                                            low = round(float(low), 2)
                                        if high is not None and not pd.isna(high):
                                            high = round(float(high), 2)
                                    else:
                                        low = None
                                        high = None
                                    
                                    # Validate low and high values
                                    if low is None or pd.isna(low) or not isinstance(low, (int, float)):
                                        low = None
                                    if high is None or pd.isna(high) or not isinstance(high, (int, float)):
                                        high = None
                                except Exception as e:
                                    logger.warning(f"Error getting low/high for {period_name} {ticker}: {e}")
                                    low = None
                                    high = None
                                
                                # Calculate percentage changes and additional data
                                percentage = None
                                open_val = None
                                close_val = None
                                high_low_percentage = None
                                
                                try:
                                    if period_name == '1D':
                                        # For 1D calculation - use today's open vs close (intraday change)
                                        if len(period_data) >= 1:
                                            period_sorted = period_data.sort_index()
                                            open_data = get_column_data(period_sorted, 'Open')
                                            close_data = get_column_data(period_sorted, 'Close')
                                            
                                            if not open_data.empty and not close_data.empty:
                                                # Find the last valid open and close prices
                                                today_open = None
                                                today_close = None
                                                
                                                for i in range(len(open_data) - 1, -1, -1):
                                                    open_val_temp = open_data.iloc[i]
                                                    # Convert to scalar if it's a Series
                                                    if isinstance(open_val_temp, pd.Series):
                                                        open_val_temp = open_val_temp.iloc[0] if not open_val_temp.empty else None
                                                    
                                                    if open_val_temp is not None and not pd.isna(open_val_temp) and open_val_temp != 0:
                                                        today_open = open_val_temp
                                                        break
                                                
                                                for i in range(len(close_data) - 1, -1, -1):
                                                    close_val_temp = close_data.iloc[i]
                                                    # Convert to scalar if it's a Series
                                                    if isinstance(close_val_temp, pd.Series):
                                                        close_val_temp = close_val_temp.iloc[0] if not close_val_temp.empty else None
                                                    
                                                    if close_val_temp is not None and not pd.isna(close_val_temp) and close_val_temp != 0:
                                                        today_close = close_val_temp
                                                        break
                                                
                                                if today_open is not None and today_close is not None:
                                                    percentage = ((today_close - today_open) / today_open) * 100
                                                    open_val = today_open
                                                    close_val = today_close
                                                
                                    else:
                                        # For other periods (5D, 1M, 6M, 1Y), calculate multiple metrics
                                        if len(period_data) >= 2:
                                            period_sorted = period_data.sort_index()
                                            open_data = get_column_data(period_sorted, 'Open')
                                            close_data = get_column_data(period_sorted, 'Close')
                                            
                                            if not close_data.empty:
                                                # Find first and last valid close prices for period-to-period change
                                                first_close = None
                                                last_close = None
                                                
                                                for i in range(len(close_data)):
                                                    close_val_temp = close_data.iloc[i]
                                                    # Convert to scalar if it's a Series
                                                    if isinstance(close_val_temp, pd.Series):
                                                        close_val_temp = close_val_temp.iloc[0] if not close_val_temp.empty else None
                                                    
                                                    if close_val_temp is not None and not pd.isna(close_val_temp) and close_val_temp != 0:
                                                        first_close = close_val_temp
                                                        break
                                                
                                                for i in range(len(close_data) - 1, -1, -1):
                                                    close_val_temp = close_data.iloc[i]
                                                    # Convert to scalar if it's a Series
                                                    if isinstance(close_val_temp, pd.Series):
                                                        close_val_temp = close_val_temp.iloc[0] if not close_val_temp.empty else None
                                                    
                                                    if close_val_temp is not None and not pd.isna(close_val_temp) and close_val_temp != 0:
                                                        last_close = close_val_temp
                                                        break
                                                
                                                if first_close is not None and last_close is not None:
                                                    percentage = ((last_close - first_close) / first_close) * 100
                                                    open_val = first_close
                                                    close_val = last_close
                                
                                except Exception as e:
                                    logger.warning(f"Error calculating {period_name} percentage for {ticker}: {e}")
                                    percentage = None
                                
                                # Calculate high-low percentage whenever we have valid low and high values
                                if low is not None and high is not None and low != 0:
                                    try:
                                        high_low_percentage = ((high - low) / low) * 100
                                    except Exception as e:
                                        logger.warning(f"Error calculating high-low percentage for {period_name} {ticker}: {e}")
                                        high_low_percentage = None
                                else:
                                    high_low_percentage = None
                                
                                # Format the data
                                if percentage is not None and not pd.isna(percentage):
                                    percentage_str = f"{percentage:.2f}%"
                                else:
                                    percentage_str = "N/A"
                                
                                # Format additional percentages
                                if high_low_percentage is not None and not pd.isna(high_low_percentage):
                                    high_low_percentage_str = f"{high_low_percentage:.2f}%"
                                else:
                                    high_low_percentage_str = "N/A"
                                
                                # Create the period data structure with all fields (consistent for all periods)
                                period_info = {
                                    "low": low,
                                    "high": high,
                                    "open": open_val,
                                    "close": close_val,
                                    "percentage": percentage_str,
                                    "high_low_percentage": high_low_percentage_str
                                }
                                
                                history_data[period_name] = period_info
                                
                            else:
                                history_data[period_name] = {
                                    "low": None,
                                    "high": None,
                                    "open": None,
                                    "close": None,
                                    "percentage": "N/A",
                                    "high_low_percentage": "N/A"
                                }
                                
                        except Exception as e:
                            logger.error(f"Error processing {period_name} for {ticker}: {e}")
                            history_data[period_name] = {
                                "low": None,
                                "high": None,
                                "open": None,
                                "close": None,
                                "percentage": "N/A",
                                "high_low_percentage": "N/A"
                            }
                    
                    # Create stock history entry
                    stock_entry = {
                        "ticker": ticker,
                        "sector": sector,
                        "isleverage": isleverage,
                        **history_data
                    }
                    
                    stock_history_data.append(stock_entry)
                    logger.info(f"Processed history for {ticker}")
                    
                except Exception as e:
                    logger.error(f"Error processing {ticker}: {e}")
                    # Add placeholder entry with all required fields
                    placeholder_data = {
                        "low": None, 
                        "high": None, 
                        "open": None,
                        "close": None,
                        "percentage": "N/A", 
                        "high_low_percentage": "N/A"
                    }
                    stock_entry = {
                        "ticker": ticker,
                        "sector": sector,
                        "isleverage": isleverage,
                        "1D": placeholder_data.copy(),
                        "5D": placeholder_data.copy(),
                        "1M": placeholder_data.copy(),
                        "6M": placeholder_data.copy(),
                        "1Y": placeholder_data.copy()
                    }
                    stock_history_data.append(stock_entry)
            
            # Save the data
            success = self.save_stock_history(stock_history_data)
            if success:
                logger.info(f"Successfully populated history for {len(stock_history_data)} stocks")
                # Save cache timestamp for successful population
                self._save_cache_timestamp('history')
            return success
            
        except Exception as e:
            logger.error(f"Error in populate_stock_history: {e}")
            return False
    
    def save_stock_history(self, data: List[Dict]) -> bool:
        """Save stock history data to file"""
        try:
            with open(self.stockhistory_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Stock history data saved to {self.stockhistory_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving stock history: {e}")
            return False
    
    def load_stock_history(self) -> List[Dict]:
        """Load stock history data from file"""
        try:
            if not os.path.exists(self.stockhistory_file):
                logger.warning(f"Stock history file {self.stockhistory_file} not found")
                return []
            
            with open(self.stockhistory_file, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error(f"Invalid data format in {self.stockhistory_file}")
                return []
            
            logger.info(f"Loaded {len(data)} stock history records")
            return data
                
        except Exception as e:
            logger.error(f"Error loading stock history: {e}")
            return []
    
    def load_stock_market_data(self) -> List[Dict]:
        """Load stock market data from file"""
        try:
            market_data_file = "stockhistorymarketdata.json"
            if not os.path.exists(market_data_file):
                logger.warning(f"Market data file {market_data_file} not found")
                return []
            
            with open(market_data_file, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error(f"Invalid data format in {market_data_file}")
                return []
            
            logger.info(f"Loaded {len(data)} market data records")
            return data
                
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            return []
    
    def get_combined_stock_data(self) -> Dict[str, Any]:
        """Get combined stock data from both history and market data files"""
        try:
            # Load both data sources
            history_data = self.load_stock_history()
            market_data = self.load_stock_market_data()
            
            # Create a lookup for market data by ticker
            market_lookup = {item['ticker']: item for item in market_data}
            
            # Combine the data
            combined_results = []
            for history_item in history_data:
                ticker = history_item.get('ticker')
                if ticker:
                    # Get corresponding market data
                    market_item = market_lookup.get(ticker, {})
                    
                    # Combine history and market data
                    combined_item = {
                        **history_item,  # Include all history data
                        **market_item    # Override with market data (if available)
                    }
                    combined_results.append(combined_item)
            
            return {
                "results": combined_results,
                "total": len(combined_results)
            }
            
        except Exception as e:
            logger.error(f"Error combining stock data: {e}")
            return {
                "results": [],
                "total": 0
            }
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status for both history and market data"""
        try:
            if not os.path.exists(self._cache_timestamp_file):
                return {
                    "history": "Never updated",
                    "market": "Never updated"
                }
            
            with open(self._cache_timestamp_file, 'r') as f:
                timestamps = json.load(f)
            
            return {
                "history": timestamps.get('history', 'Never updated'),
                "market": timestamps.get('market', 'Never updated')
            }
            
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {
                "history": "Error",
                "market": "Error"
            }

# Global instance
stock_history_ops = StockHistoryOperations()
