import json
import os
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockHistoryOperations:
    def __init__(self):
        self.stockhistory_file = "stockhistory.json"
        self.stockhistory_market_file = "stockhistorymarketdata.json"
        self.stocks_file = "stock.json"
        from config import config
        self.finviz_auth_id = config.FINVIZ_AUTH_ID
        self.finviz_base_url = "https://elite.finviz.com/export.ashx"
        
    def load_stocks(self) -> List[Dict[str, Any]]:
        """Load stocks from stock.json file"""
        try:
            with open(self.stocks_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Stocks file {self.stocks_file} not found")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing stocks file: {e}")
            return []
    
    def load_stock_history(self) -> List[Dict[str, Any]]:
        """Load stock history data"""
        try:
            if os.path.exists(self.stockhistory_file):
                with open(self.stockhistory_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading stock history: {e}")
            return []
    
    def load_stock_market_data(self) -> List[Dict[str, Any]]:
        """Load stock market data"""
        try:
            if os.path.exists(self.stockhistory_market_file):
                with open(self.stockhistory_market_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading stock market data: {e}")
            return []
    
    def save_stock_history(self, data: List[Dict[str, Any]]) -> bool:
        """Save stock history data to file"""
        try:
            with open(self.stockhistory_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Stock history data saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving stock history: {e}")
            return False
    
    def save_stock_market_data(self, data: List[Dict[str, Any]]) -> bool:
        """Save stock market data to file"""
        try:
            with open(self.stockhistory_market_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Stock market data saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving stock market data: {e}")
            return False
    
    def populate_stock_history(self) -> bool:
        """Populate stock history data using yfinance download method for all stocks"""
        try:
            stocks = self.load_stocks()
            if not stocks:
                logger.error("No stocks found to populate history")
                return False
            
            logger.info(f"Starting to populate history for {len(stocks)} stocks")
            stock_history_data = []
            
            # Get all tickers
            tickers = [stock.get('ticker') for stock in stocks if stock.get('ticker')]
            if not tickers:
                logger.error("No valid tickers found")
                return False
            
            logger.info(f"Downloading data for {len(tickers)} tickers...")
            
            # Download all data at once using yf.download() - more efficient
            try:
                # Download 1 year of data for all tickers (covers all periods we need)
                all_data = yf.download(tickers, period="1y", group_by='ticker', progress=False)
                logger.info("Data download completed successfully")
            except Exception as e:
                logger.error(f"Error downloading data: {e}")
                return False
            
            # Process each stock
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
                        else:
                            logger.warning(f"Ticker {ticker} not found in downloaded data")
                            continue
                    
                    if hist.empty:
                        logger.warning(f"No data found for {ticker}")
                        continue
                    
                     # Define periods and their corresponding data ranges
                    periods_data = {
                         'previous_day': hist.tail(10),     # Last 10 days (to ensure we find 2 valid closes)
                         'five_day': hist.tail(5),          # Last 5 days
                         'one_month': hist.tail(30),        # Last 30 days
                         'six_month': hist.tail(180),       # Last 180 days
                         'one_year': hist                    # Full year
                     }
                   
                    # Helper function to get Close, Low, High data handling multi-level columns
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
                            if not period_data.empty and len(period_data) >= 2:
                                try:
                                    low_data = get_column_data(period_data, 'Low')
                                    high_data = get_column_data(period_data, 'High')
                                    
                                    if not low_data.empty and not high_data.empty:
                                        low = low_data.min()
                                        high = high_data.max()
                                    else:
                                        low = None
                                        high = None
                                    
                                    # Validate low and high values
                                    if pd.isna(low) or not isinstance(low, (int, float)):
                                        low = None
                                    if pd.isna(high) or not isinstance(high, (int, float)):
                                        high = None
                                except Exception as e:
                                    logger.warning(f"Error getting low/high for {period_name} {ticker}: {e}")
                                    low = None
                                    high = None
                                
                                # Calculate percentage change
                                percentage = None
                                try:
                                    if period_name == 'previous_day':
                                        # For previous day calculation
                                        if len(period_data) >= 2:
                                            # Sort by date to ensure proper order
                                            period_sorted = period_data.sort_index()
                                            close_data = get_column_data(period_sorted, 'Close')
                                            
                                            if not close_data.empty and len(close_data) >= 2:
                                                # Find last two valid closes (non-NaN) - search from end
                                                valid_closes = []
                                                for i in range(len(close_data) - 1, -1, -1):
                                                    if not pd.isna(close_data.iloc[i]) and close_data.iloc[i] != 0:
                                                        valid_closes.append(close_data.iloc[i])
                                                        if len(valid_closes) == 2:
                                                            break
                                                
                                                # Check if we have enough valid data points
                                                if len(valid_closes) >= 2:
                                                     today_close = valid_closes[0]      # Most recent valid close
                                                     yesterday_close = valid_closes[1]  # Second most recent valid close
                                                     
                                                     # Check for valid numeric values
                                                     if yesterday_close == 0:
                                                         percentage = None
                                                         if len(history_data) < 3:
                                                             logger.warning(f"{ticker} 1D: yesterday_close is 0, cannot calculate percentage")
                                                     else:
                                                         percentage = ((today_close - yesterday_close) / yesterday_close) * 100
                                                         
                                                         # Debug logging for first few stocks
                                                         if len(history_data) < 3:
                                                             logger.info(f"{ticker} 1D: Yesterday=${yesterday_close:.2f}, Today=${today_close:.2f}, Change={percentage:.2f}%")
                                                else:
                                                    percentage = None
                                                    
                                                    if len(history_data) < 3:
                                                        logger.warning(f"{ticker} 1D: Only found {len(valid_closes)} valid closes, need 2 for 1D calculation")
                                                        logger.warning(f"{ticker} 1D: All close values: {[f'${c:.2f}' if not pd.isna(c) else 'NaN' for c in close_data.tail(5).values]}")
                                            else:
                                                if len(history_data) < 3:
                                                    logger.warning(f"{ticker}: Not enough data points for 1D calculation")
                                                percentage = None
                                    else:
                                        # For other periods, use first and last close
                                        period_sorted = period_data.sort_index()
                                        close_data = get_column_data(period_sorted, 'Close')
                                        
                                        if not close_data.empty and len(close_data) >= 2:
                                            # Find first valid close (non-NaN)
                                            first_close = None
                                            for i in range(len(close_data)):
                                                if not pd.isna(close_data.iloc[i]) and close_data.iloc[i] != 0:
                                                    first_close = close_data.iloc[i]
                                                    break
                                            
                                            # Find last valid close (non-NaN) - search from end
                                            last_close = None
                                            for i in range(len(close_data) - 1, -1, -1):
                                                if not pd.isna(close_data.iloc[i]) and close_data.iloc[i] != 0:
                                                    last_close = close_data.iloc[i]
                                                    break
                                            
                                            # Check for valid numeric values
                                            if first_close is None or last_close is None or first_close == 0:
                                                percentage = None
                                            else:
                                                percentage = ((last_close - first_close) / first_close) * 100
                                        else:
                                            percentage = None
                                    
                                    # Validate percentage value
                                    if percentage is not None:
                                        if pd.isna(percentage) or not isinstance(percentage, (int, float)):
                                            percentage = None
                                        elif abs(percentage) > 100000:  # Unrealistic percentage change (1000x)
                                            percentage = None
                                            
                                except Exception as e:
                                    logger.warning(f"Error calculating {period_name} percentage for {ticker}: {e}")
                                    percentage = None
                                
                                # Add debug logging for percentage calculation
                                if len(history_data) < 3:  # Only log for first few stocks to avoid spam
                                    logger.info(f"{ticker} {period_name}: percentage={percentage}, type={type(percentage)}")
                                
                                # Add detailed debug logging for validation steps (only for first few stocks)
                                if len(history_data) < 3:  # Log for first 3 stocks to see pattern
                                    logger.info(f"{ticker} {period_name}: period_data.shape={period_data.shape}, period_data.empty={period_data.empty}")
                                    if not period_data.empty:
                                        period_sorted = period_data.sort_index()
                                        close_data = get_column_data(period_sorted, 'Close')
                                        logger.info(f"{ticker} {period_name}: close_data.shape={close_data.shape}, close_data.empty={close_data.empty}")
                                        if not close_data.empty and len(close_data) >= 2:
                                            first_close = close_data.iloc[0]
                                            last_close = close_data.iloc[-1]
                                            logger.info(f"{ticker} {period_name}: first_close={first_close}, last_close={last_close}")
                                            logger.info(f"{ticker} {period_name}: first_close_isna={pd.isna(first_close)}, last_close_isna={pd.isna(last_close)}, first_close==0={first_close == 0}")
                                        else:
                                            logger.warning(f"{ticker} {period_name}: close_data validation failed - empty={close_data.empty}, len={len(close_data) if not close_data.empty else 0}")
                                    else:
                                        logger.warning(f"{ticker} {period_name}: period_data is empty")
                                
                                # Format the data with proper fallbacks
                                if percentage is not None and not pd.isna(percentage):
                                    percentage_str = f"{percentage:.2f}%"
                                else:
                                    percentage_str = "N/A"
                                
                                # Add debug logging for final formatting
                                if len(history_data) < 3:  # Only log for first few stocks to avoid spam
                                    logger.info(f"{ticker} {period_name}: final_percentage={percentage_str}")
                                
                                history_data[period_name] = {
                                    "low": f"${low:.2f}" if not pd.isna(low) else "N/A",
                                    "high": f"${high:.2f}" if not pd.isna(high) else "N/A",
                                    "percentage": percentage_str
                                }
                            else:
                                history_data[period_name] = {
                                    "low": "N/A",
                                    "high": "N/A",
                                    "percentage": "N/A"
                                }
                        except Exception as e:
                            logger.warning(f"Error processing {period_name} for {ticker}: {e}")
                            history_data[period_name] = {
                                "low": "N/A",
                                "high": "N/A",
                                "percentage": "N/A"
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
                    # Add placeholder entry with consistent N/A values
                    placeholder_data = {"low": "N/A", "high": "N/A", "percentage": "N/A"}
                    stock_entry = {
                        "ticker": ticker,
                        "sector": sector,
                        "isleverage": isleverage,
                        "previous_day": placeholder_data.copy(),
                        "five_day": placeholder_data.copy(),
                        "one_month": placeholder_data.copy(),
                        "six_month": placeholder_data.copy(),
                        "one_year": placeholder_data.copy()
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
    
    def populate_stock_market_data(self) -> bool:
        """Populate stock market data using Finviz API"""
        try:
            stocks = self.load_stocks()
            if not stocks:
                logger.error("No stocks found to populate market data")
                return False
            
            logger.info(f"Starting to populate market data for {len(stocks)} stocks")
            
            # Get all tickers
            tickers = [stock.get('ticker') for stock in stocks if stock.get('ticker')]
            if not tickers:
                logger.error("No valid tickers found")
                return False
            
            # Prepare Finviz API request with AH data
            tickers_param = ','.join(tickers)
            params = {
                'v': '152',
                't': tickers_param,
                'auth': self.finviz_auth_id,
                'c': '1,6,65,68,66,67,71,72'  # Added columns 71=AH Price, 72=AH Change
            }
            
            try:
                response = requests.get(self.finviz_base_url, params=params, timeout=30)
                response.raise_for_status()
                
                # Parse CSV data
                csv_data = response.text
                lines = csv_data.strip().split('\n')
                
                if len(lines) < 2:  # Need header + at least one data row
                    logger.error("Invalid CSV response from Finviz")
                    return False
                
                # Parse header - clean up carriage returns and quotes
                header = [h.strip().strip('"').strip('\r') for h in lines[0].split(',')]
                
                # Parse data rows
                market_data = []
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    
                    values = line.split(',')
                    if len(values) != len(header):
                        continue
                    
                    # Create data dictionary - clean up values
                    row_data = dict(zip(header, [v.strip().strip('"').strip('\r') for v in values]))
                    
                    ticker = row_data.get('Ticker', '')
                    if not ticker:
                        continue
                    
                    # Find corresponding stock info
                    stock_info = next((s for s in stocks if s.get('ticker') == ticker), None)
                    if not stock_info:
                        continue
                    
                    # Extract market data
                    market_cap = row_data.get('Market Cap', 'N/A')
                    earning_date = row_data.get('Earnings Date', 'N/A')  # Fixed: was 'Earnings', now 'Earnings Date'
                    current_price = row_data.get('Price', 'N/A')
                    
                    # Extract today's data
                    today_change = row_data.get('Change', 'N/A')
                    
                    # Extract AH data
                    ah_price = row_data.get('After-Hours Close', 'N/A')
                    ah_change = row_data.get('After-Hours Change', 'N/A')
                    
                    # Format today's data (removed low and high, keeping only percentage)
                    # Clean up the percentage value - remove any existing % symbols and format properly
                    if today_change != 'N/A':
                        # Remove any existing % symbols and clean the value
                        clean_change = str(today_change).replace('%', '').strip()
                        try:
                            # Convert to float and format properly
                            change_val = float(clean_change)
                            formatted_percentage = f"{change_val:+.2f}%" if change_val != 0 else "0.00%"
                        except (ValueError, TypeError):
                            # If conversion fails, use the original value
                            formatted_percentage = f"{clean_change}%" if clean_change else "N/A"
                    else:
                        formatted_percentage = "N/A"
                    
                    today_data = {
                        "percentage": formatted_percentage
                    }
                    
                    # Create market data entry
                    market_entry = {
                        "ticker": ticker,
                        "market_cap": market_cap,
                        "earning_date": earning_date,
                        "current_price": current_price,
                        "today": today_data,
                        "ah_price": ah_price,
                        "ah_change": ah_change
                    }
                    
                    market_data.append(market_entry)
                
                # Save the data
                success = self.save_stock_market_data(market_data)
                if success:
                    logger.info(f"Successfully populated market data for {len(market_data)} stocks")
                    # Save cache timestamp for successful population
                    self._save_cache_timestamp('market')
                return success
                
            except requests.RequestException as e:
                logger.error(f"Error calling Finviz API: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error in populate_stock_market_data: {e}")
            return False
    
    def get_finviz_data_for_tickers(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get real-time data for specific tickers using Finviz API.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary with ticker as key and Finviz data as value
        """
        try:
            if not tickers:
                logger.warning("No tickers provided for Finviz data")
                return {}
            
            logger.info(f"Fetching Finviz data for {len(tickers)} tickers")
            
            # Prepare Finviz API request with required columns including AH data
            # Column mapping: 1=Ticker, 81=Prev Close, 86=Open, 65=Price, 66=Change, 71=AH Price, 72=AH Change
            tickers_param = ','.join(tickers)
            params = {
                'v': '152',
                't': tickers_param,
                'auth': self.finviz_auth_id,
                'c': '1,81,86,65,66,71,72'
            }
            
            try:
                response = requests.get(self.finviz_base_url, params=params, timeout=30)
                response.raise_for_status()
                
                # Parse CSV data
                csv_data = response.text
                lines = csv_data.strip().split('\n')
                
                if len(lines) < 2:  # Need header + at least one data row
                    logger.error("Invalid CSV response from Finviz")
                    return {}
                
                # Parse header - clean up carriage returns and quotes
                header = [h.strip().strip('"').strip('\r') for h in lines[0].split(',')]
                logger.debug(f"Finviz columns: {header}")
                
                # Parse data rows
                finviz_data = {}
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    
                    values = line.split(',')
                    if len(values) != len(header):
                        continue
                    
                    # Create data dictionary - clean up values
                    row_data = dict(zip(header, [v.strip().strip('"').strip('\r') for v in values]))
                    
                    ticker = row_data.get('Ticker', '')
                    if not ticker:
                        continue
                    
                    # Store all available data for this ticker
                    finviz_data[ticker] = row_data
                
                logger.info(f"Successfully fetched Finviz data for {len(finviz_data)} tickers")
                return finviz_data
                
            except requests.RequestException as e:
                logger.error(f"Error calling Finviz API: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"Error in get_finviz_data_for_tickers: {e}")
            return {}
    
    def get_combined_stock_data(self) -> Dict[str, Any]:
        """Get combined data from both history and market data files"""
        try:
            history_data = self.load_stock_history()
            market_data = self.load_stock_market_data()
            
            # Create lookup for market data
            market_lookup = {item['ticker']: item for item in market_data}
            
            # Combine the data
            combined_data = []
            for history_item in history_data:
                ticker = history_item['ticker']
                market_item = market_lookup.get(ticker, {})
                
                combined_item = {
                    **history_item,
                    "market_cap": market_item.get('market_cap', 'N/A'),
                    "earning_date": market_item.get('earning_date', 'N/A'),
                    "current_price": market_item.get('current_price', 'N/A'),
                    "today": market_item.get('today', history_item.get('today', {})),
                    "ah_price": market_item.get('ah_price', 'N/A'),
                    "ah_change": market_item.get('ah_change', 'N/A')
                }
                
                combined_data.append(combined_item)
            
            return {
                "results": combined_data,
                "total": len(combined_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting combined stock data: {e}")
            return {"results": [], "total": 0}
    
    def _get_cache_file_path(self, file_type: str) -> str:
        """Get cache file path for storing population timestamps"""
        return f"{file_type}_cache.json"
    
    def _load_cache_timestamp(self, file_type: str) -> datetime:
        """Load cached timestamp for when data was last populated"""
        try:
            cache_file = self._get_cache_file_path(file_type)
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    timestamp_str = cache_data.get('last_populated', '')
                    if timestamp_str:
                        return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.warning(f"Error loading cache timestamp for {file_type}: {e}")
        
        # Return a very old date if no cache found
        return datetime(2000, 1, 1)
    
    def _save_cache_timestamp(self, file_type: str, timestamp: datetime = None) -> bool:
        """Save cache timestamp for when data was last populated"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            cache_file = self._get_cache_file_path(file_type)
            cache_data = {
                'last_populated': timestamp.isoformat(),
                'file_type': file_type
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Cache timestamp saved for {file_type}: {timestamp}")
            return True
        except Exception as e:
            logger.error(f"Error saving cache timestamp for {file_type}: {e}")
            return False
    
    def should_populate_history(self) -> bool:
        """Check if we should populate history data based on cached date"""
        try:
            # Check if file exists and has data
            if not os.path.exists(self.stockhistory_file):
                logger.info("History file doesn't exist, should populate")
                return True
            
            # Check if file is empty
            try:
                with open(self.stockhistory_file, 'r') as f:
                    content = f.read().strip()
                    if not content or content == '[]':
                        logger.info("History file is empty, should populate")
                        return True
            except Exception as e:
                logger.warning(f"Error reading history file: {e}, should populate")
                return True
            
            # Check cached date vs current date
            cached_date = self._load_cache_timestamp('history')
            current_date = datetime.now().date()
            
            if cached_date.date() < current_date:
                logger.info(f"History cache date ({cached_date.date()}) is older than current date ({current_date}), should populate")
                return True
            
            logger.info(f"History cache date ({cached_date.date()}) is current, no need to populate")
            return False
            
        except Exception as e:
            logger.error(f"Error checking history population time: {e}")
            return True
    
    def should_populate_market_data(self) -> bool:
        """Check if we should populate market data based on cached datetime + 1 minute"""
        try:
            # Check if file exists and has data
            if not os.path.exists(self.stockhistory_market_file):
                logger.info("Market data file doesn't exist, should populate")
                return True
            
            # Check if file is empty
            try:
                with open(self.stockhistory_market_file, 'r') as f:
                    content = f.read().strip()
                    if not content or content == '[]':
                        logger.info("Market data file is empty, should populate")
                        return True
            except Exception as e:
                logger.warning(f"Error reading market data file: {e}, should populate")
                return True
            
            # Check cached datetime + 1 minute vs current datetime
            cached_datetime = self._load_cache_timestamp('market')
            current_datetime = datetime.now()
            
            # Add 1 minute to cached time for market data updates
            next_update_time = cached_datetime + timedelta(minutes=1)
            
            if current_datetime >= next_update_time:
                logger.info(f"Market data cache time ({cached_datetime}) + 1 minute is past current time ({current_datetime}), should populate")
                return True
            
            logger.info(f"Market data cache time ({cached_datetime}) + 1 minute is in future, no need to populate yet")
            return False
            
        except Exception as e:
            logger.error(f"Error checking market data population time: {e}")
            return True
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get current cache status for both history and market data"""
        try:
            history_cache = self._load_cache_timestamp('history')
            market_cache = self._load_cache_timestamp('market')
            current_time = datetime.now()
            
            return {
                "history": {
                    "last_populated": history_cache.isoformat(),
                    "next_population": (history_cache + timedelta(days=1)).isoformat(),
                    "should_populate": self.should_populate_history(),
                    "cache_age_hours": (current_time - history_cache).total_seconds() / 3600
                },
                "market": {
                    "last_populated": market_cache.isoformat(),
                    "next_population": (market_cache + timedelta(minutes=1)).isoformat(),
                    "should_populate": self.should_populate_market_data(),
                    "cache_age_minutes": (current_time - market_cache).total_seconds() / 60
                },
                "current_time": current_time.isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {
                "error": str(e),
                "current_time": datetime.now().isoformat()
            }

# Global instance
stock_history_ops = StockHistoryOperations()
