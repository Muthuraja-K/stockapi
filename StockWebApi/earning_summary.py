import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
from utils import load_stocks

def get_after_hours_data(ticker: str, date: str):
    """
    Get specifically after-hours and pre-market data for a ticker on a specific date.
    
    Args:
        ticker: Stock ticker symbol
        date: Date in YYYY-MM-DD format
    
    Returns:
        Dictionary with after-hours and pre-market data
    """
    try:
        logging.info(f"Starting after-hours data fetch for {ticker} on {date}")
        
        # Validate date format and check if it's in the future
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return {
                "error": "Invalid date format. Please use YYYY-MM-DD format.",
                "ticker": ticker,
                "date": date
            }
        
        # Check if date is in the future
        current_date = datetime.now().date()
        if target_date.date() > current_date:
            return {
                "error": f"Date {date} is in the future. Yahoo Finance only provides data for past dates.",
                "ticker": ticker,
                "date": date
            }
        
        # Check if date is too far in the past (Yahoo Finance limitations)
        days_ago = (current_date - target_date.date()).days
        if days_ago > 60:
            return {
                "error": f"Date {date} is too far in the past. Yahoo Finance only provides detailed data for the last 60 days.",
                "ticker": ticker,
                "date": date
            }
        
        yf_ticker = yf.Ticker(ticker)
        
        # Get extended range data to capture all after-hours activity
        # Yahoo Finance often has data from 4 AM to 8 PM ET
        extended_start = target_date - timedelta(hours=8)  # Include pre-market from previous day
        extended_end = target_date + timedelta(days=1, hours=8)  # Include after-hours of current day
        
        logging.info(f"Fetching data from {extended_start} to {extended_end}")
        
        # Try to get 1-minute data for granular after-hours information
        try:
            detailed_data = yf_ticker.history(start=extended_start, end=extended_end, interval='1m')
            if not detailed_data.empty:
                interval_data = detailed_data
                use_detailed = True
                logging.info(f"Got 1-minute data with {len(detailed_data)} points")
            else:
                # Fallback to 5-minute data
                interval_data = yf_ticker.history(start=extended_start, end=extended_end, interval='5m')
                use_detailed = False
                logging.info(f"Got 5-minute data with {len(interval_data)} points")
        except Exception as e:
            logging.warning(f"Failed to get 1-minute data, falling back to 5-minute: {str(e)}")
            # Fallback to 5-minute data
            interval_data = yf_ticker.history(start=extended_start, end=extended_end, interval='5m')
            use_detailed = False
        
        if interval_data.empty:
            logging.warning(f"No interval data available for {ticker} on {date}")
            return {
                "error": "No after-hours data available for this date. The stock may not have traded on this date or data is not available.",
                "ticker": ticker,
                "date": date
            }
        
        # Get daily OHLC for reference
        daily_data = yf_ticker.history(start=target_date, end=target_date + timedelta(days=1), interval='1d')
        if not daily_data.empty:
            daily_row = daily_data.iloc[0]
            market_close = daily_row['Close']
            logging.info(f"Market close price: {market_close}")
        else:
            market_close = None
            logging.warning("No daily data available")
        
        # Process after-hours and pre-market data
        after_hours_points = []
        pre_market_points = []
        
        logging.info(f"Processing {len(interval_data)} interval data points")
        
        for timestamp, point in interval_data.iterrows():
            try:
                point_time = timestamp.time()
                point_date = timestamp.date()
                
                # Debug: log the point structure
                if len(after_hours_points) < 3:  # Log first few points for debugging
                    logging.info(f"Processing point: {timestamp}, columns: {point.index.tolist()}, Close: {point.get('Close', 'N/A')}")
                
                # Pre-market: 4:00 AM - 9:30 AM ET
                is_pre_market = (
                    point_date == target_date.date() and
                    4 <= point_time.hour < 9 and
                    (point_time.hour != 9 or point_time.minute < 30)
                )
                
                # After-hours: 4:00 PM - 8:00 PM ET (and sometimes later)
                is_after_hours = (
                    point_date == target_date.date() and
                    point_time.hour >= 16 and point_time.hour < 22
                )
                
                if is_pre_market or is_after_hours:
                    # Safely get the Close price
                    close_price = point.get('Close')
                    if close_price is None or pd.isna(close_price):
                        logging.warning(f"Skipping point with invalid Close price: {timestamp}")
                        continue
                    
                    point_data = {
                        "time": timestamp.strftime('%H:%M'),
                        "price": float(close_price),
                        "volume": int(point.get('Volume', 0)) if point.get('Volume') is not None else 0,
                        "isPreMarket": is_pre_market,
                        "isAfterHours": is_after_hours,
                        "timestamp": timestamp.isoformat()
                    }
                    
                    if is_pre_market:
                        pre_market_points.append(point_data)
                    else:
                        after_hours_points.append(point_data)
                        
            except Exception as point_error:
                logging.error(f"Error processing point {timestamp}: {str(point_error)}")
                continue
        
        # Sort points by time
        after_hours_points.sort(key=lambda x: x['time'])
        pre_market_points.sort(key=lambda x: x['time'])
        
        logging.info(f"Found {len(after_hours_points)} after-hours points and {len(pre_market_points)} pre-market points")
        
        # Calculate after-hours change if we have market close price
        after_hours_change = None
        after_hours_change_percent = None
        if market_close and after_hours_points:
            try:
                last_after_hours_price = after_hours_points[-1]['price']
                after_hours_change = last_after_hours_price - market_close
                after_hours_change_percent = (after_hours_change / market_close) * 100
                logging.info(f"After-hours change: {after_hours_change:.2f} ({after_hours_change_percent:.2f}%)")
            except Exception as calc_error:
                logging.error(f"Error calculating after-hours change: {str(calc_error)}")
        
        result = {
            "ticker": ticker,
            "date": date,
            "marketClose": market_close,
            "afterHoursPoints": after_hours_points,
            "preMarketPoints": pre_market_points,
            "afterHoursChange": after_hours_change,
            "afterHoursChangePercent": after_hours_change_percent,
            "totalAfterHoursPoints": len(after_hours_points),
            "totalPreMarketPoints": len(pre_market_points)
        }
        
        logging.info(f"Successfully returned after-hours data for {ticker}")
        return result
        
    except Exception as e:
        logging.error(f"Error getting after-hours data for {ticker} on {date}: {str(e)}")
        logging.error(f"Exception type: {type(e).__name__}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return {
            "error": f"Failed to get after-hours data: {str(e)}",
            "ticker": ticker,
            "date": date
        }


def get_historical_price_data(ticker: str, date: str, interval: str = '1m'):
    """
    Get historical price data for a specific ticker and date.
    
    Args:
        ticker: Stock ticker symbol
        date: Date in YYYY-MM-DD format
        interval: Data interval ('1m' for intraday, '1h' for hourly, '1d' for daily)
    
    Returns:
        Dictionary with price data for the specified date
    """
    try:
        # Convert date string to datetime object
        target_date = datetime.strptime(date, '%Y-%m-%d')
        
        # Get data for the target date (including intraday if available)
        # Try to get specified interval data for the specific date
        start_date = target_date
        end_date = target_date + timedelta(days=1)
        
        yf_ticker = yf.Ticker(ticker)
        
        # Get daily data for the target date
        daily_data = yf_ticker.history(start=start_date, end=end_date, interval='1d')
        
        if daily_data.empty:
            return {
                "error": "No data available for the specified date",
                "ticker": ticker,
                "date": date
            }
        
        # Get the daily OHLC data
        daily_row = daily_data.iloc[0]
        
        # Try to get interval data (1-minute, 1-hour, or daily intervals)
        try:
            # For better after-hours data, extend the range significantly
            # Yahoo Finance often has data from 4 AM to 8 PM ET
            extended_start = target_date - timedelta(hours=8)  # Include pre-market from previous day
            extended_end = target_date + timedelta(days=1, hours=8)  # Include after-hours of current day
            
            # Use 1-minute intervals for more granular data when available
            if interval == '1h':
                # For hourly charts, try to get 1-minute data first, then aggregate
                try:
                    detailed_data = yf_ticker.history(start=extended_start, end=extended_end, interval='1m')
                    if not detailed_data.empty:
                        interval_data = detailed_data
                        use_detailed = True
                    else:
                        # Fallback to hourly data
                        interval_data = yf_ticker.history(start=extended_start, end=extended_end, interval='1h')
                        use_detailed = False
                except:
                    # Fallback to hourly data
                    interval_data = yf_ticker.history(start=extended_start, end=extended_end, interval='1h')
                    use_detailed = False
            else:
                interval_data = yf_ticker.history(start=extended_start, end=extended_end, interval=interval)
                use_detailed = False
            
            if not interval_data.empty:
                # Calculate price change from open to close
                open_price = daily_row['Open']
                close_price = daily_row['Close']
                high_price = daily_row['High']
                low_price = daily_row['Low']
                
                price_change = close_price - open_price
                price_change_percent = (price_change / open_price) * 100
                
                # Format the change string
                if price_change >= 0:
                    change_str = f"+${price_change:.2f} (+{price_change_percent:.2f}%)"
                else:
                    change_str = f"${price_change:.2f} ({price_change_percent:.2f}%)"
                
                # Get interval price points for chart
                interval_points = []
                after_hours_points = []
                
                if len(interval_data) > 0:
                    # Filter data for the target date and after-hours
                    target_date_start = target_date
                    target_date_end = target_date + timedelta(days=1)
                    
                    for i, (timestamp, point) in enumerate(interval_data.iterrows()):
                        point_time = timestamp.time()
                        point_date = timestamp.date()
                        
                        # Enhanced time range detection for better after-hours coverage
                        # Market hours: 9:30 AM - 4:00 PM ET
                        is_market_hours = (
                            point_date == target_date.date() and
                            9 <= point_time.hour <= 16 and
                            (point_time.hour != 9 or point_time.minute >= 30) and
                            (point_time.hour != 16 or point_time.minute <= 0)
                        )
                        
                        # Extended after-hours: 4:00 PM - 8:00 PM ET (and sometimes later)
                        is_after_hours = (
                            point_date == target_date.date() and
                            point_time.hour >= 16 and point_time.hour < 22
                        )
                        
                        # Extended pre-market: 4:00 AM - 9:30 AM ET
                        is_pre_market = (
                            point_date == target_date.date() and
                            4 <= point_time.hour < 9 and
                            (point_time.hour != 9 or point_time.minute < 30)
                        )
                        
                        # For hourly charts, include data from 4 AM to 8 PM for comprehensive coverage
                        is_hourly_range = (
                            point_date == target_date.date() and
                            4 <= point_time.hour <= 20  # 4 AM to 8 PM
                        )
                        
                        point_data = {
                            "time": timestamp.strftime('%H:%M'),
                            "price": point['Close'],
                            "isMarketHours": is_market_hours,
                            "isAfterHours": is_after_hours,
                            "isPreMarket": is_pre_market,
                            "isHourlyRange": is_hourly_range
                        }
                        
                        # For hourly charts, include ALL points in the main array
                        if interval == '1h':
                            if is_hourly_range:
                                interval_points.append(point_data)
                            # Also categorize for display purposes
                            if is_market_hours:
                                pass  # Already added above
                            elif is_after_hours or is_pre_market:
                                after_hours_points.append(point_data)
                        else:
                            # For other intervals, separate market hours and after-hours
                            if is_market_hours:
                                interval_points.append(point_data)
                            elif is_after_hours or is_pre_market:
                                after_hours_points.append(point_data)
                
                # Log the data we found for debugging
                logging.info(f"Found {len(interval_points)} intraday points and {len(after_hours_points)} after-hours points for {ticker} on {date}")
                
                return {
                    "ticker": ticker,
                    "date": date,
                    "open": f"${open_price:.2f}",
                    "close": f"${close_price:.2f}",
                    "high": f"${high_price:.2f}",
                    "low": f"${low_price:.2f}",
                    "change": change_str,
                    "priceChange": price_change,
                    "priceChangePercent": price_change_percent,
                    "intradayPoints": interval_points,
                    "afterHoursPoints": after_hours_points,
                    "interval": interval,
                    "volume": daily_row['Volume']
                }
                
        except Exception as e:
            logging.warning(f"Could not get {interval} data for {ticker} on {date}: {str(e)}")
            # Fallback to daily data only
            open_price = daily_row['Open']
            close_price = daily_row['Close']
            high_price = daily_row['High']
            low_price = daily_row['Low']
            
            price_change = close_price - open_price
            price_change_percent = (price_change / open_price) * 100
            
            if price_change >= 0:
                change_str = f"+${price_change:.2f} (+{price_change_percent:.2f}%)"
            else:
                change_str = f"${price_change:.2f} ({price_change_percent:.2f}%)"
            
            return {
                "ticker": ticker,
                "date": date,
                "open": f"${open_price:.2f}",
                "close": f"${close_price:.2f}",
                "high": f"${high_price:.2f}",
                "low": f"${low_price:.2f}",
                "change": change_str,
                "priceChange": price_change,
                "priceChangePercent": price_change_percent,
                "intradayPoints": [],
                "afterHoursPoints": [],
                "interval": interval,
                "volume": daily_row['Volume']
            }
            
    except Exception as e:
        logging.error(f"Error getting historical price data for {ticker} on {date}: {str(e)}")
        return {
            "error": f"Error retrieving data: {str(e)}",
            "ticker": ticker,
            "date": date
        }

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
                    logging.debug(f"Ticker {ticker}: Raw earningsTimestamp: {earning_date}, type: {type(earning_date)}")
                    # Convert timestamp to date string
                    if isinstance(earning_date, (int, float)):
                        # Yahoo Finance timestamps are in UTC, but when we convert to local time,
                        # it can shift the date. Let's use UTC to preserve the original date
                        from datetime import timezone
                        # Store the original timestamp for logging
                        original_timestamp = earning_date
                        try:
                            earning_date = datetime.fromtimestamp(earning_date, tz=timezone.utc).strftime('%Y-%m-%d')
                            logging.debug(f"Ticker {ticker}: Timestamp {original_timestamp} converted to UTC date: {earning_date}")
                            
                            # Also log what local time would be for comparison
                            local_date = datetime.fromtimestamp(original_timestamp).strftime('%Y-%m-%d')
                            logging.debug(f"Ticker {ticker}: Local time would be: {local_date}")
                        except (ValueError, OSError) as e:
                            logging.warning(f"Ticker {ticker}: Invalid timestamp {original_timestamp}: {str(e)}")
                            continue
                    elif hasattr(earning_date, 'strftime'):
                        # It's already a datetime object
                        earning_date = earning_date.strftime('%Y-%m-%d')
                        logging.debug(f"Ticker {ticker}: Original date {earning_date}")
                    else:
                        logging.warning(f"Ticker {ticker}: Unsupported earningsTimestamp type: {type(earning_date)}, value: {earning_date}")
                        continue
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
                
                # Get last two earnings data
                last_two_earnings = []
                try:
                    # Get earnings calendar for the last few quarters
                    earnings_calendar = yf_ticker.earnings_dates
                    if earnings_calendar is not None and not earnings_calendar.empty:
                        # Get the last 2 earnings dates
                        last_earnings = earnings_calendar.head(2)
                        
                        for _, earning_row in last_earnings.iterrows():
                            earning_date_obj = earning_row.name
                            # Handle timezone-aware datetime objects - convert to UTC to preserve date
                            if earning_date_obj.tzinfo is not None:
                                earning_date_obj = earning_date_obj.tz_convert('UTC')
                            earning_date_str = earning_date_obj.strftime('%Y-%m-%d')
                            logging.debug(f"Ticker {ticker}: Earnings date from earnings_dates: {earning_date_obj}, formatted: {earning_date_str}")
                            
                            # Get beat expectation data
                            beat_expectation = "N/A"
                            actual_value = "N/A"
                            expected_value = "N/A"
                            percentage_difference = "N/A"
                            
                            try:
                                # First try to get earnings data from earnings property
                                try:
                                    earnings_data = yf_ticker.earnings
                                    if earnings_data is not None and not earnings_data.empty:
                                        # Get the most recent earnings data
                                        latest_earnings = earnings_data.iloc[0] if len(earnings_data) > 0 else None
                                        
                                        if latest_earnings is not None:
                                            # Check for EPS columns
                                            for col in latest_earnings.index:
                                                if 'eps' in col.lower() and 'actual' in col.lower():
                                                    eps_actual = latest_earnings[col]
                                                elif 'eps' in col.lower() and ('estimate' in col.lower() or 'expected' in col.lower()):
                                                    eps_estimate = latest_earnings[col]
                                                elif 'revenue' in col.lower() and 'actual' in col.lower():
                                                    revenue_actual = latest_earnings[col]
                                                elif 'revenue' in col.lower() and ('estimate' in col.lower() or 'expected' in col.lower()):
                                                    revenue_estimate = latest_earnings[col]
                                                    
                                            # Process EPS data if available
                                            if eps_actual is not None and eps_estimate is not None:
                                                if pd.notna(eps_actual) and pd.notna(eps_estimate):
                                                    actual_value = f"${eps_actual:.2f}"
                                                    expected_value = f"${eps_estimate:.2f}"
                                                    
                                                    if eps_estimate != 0:
                                                        percentage_diff = ((eps_actual - eps_estimate) / abs(eps_estimate)) * 100
                                                        if eps_actual > eps_estimate:
                                                            beat_expectation = f"Beat EPS (+{percentage_diff:.1f}%)"
                                                            percentage_difference = f"+{percentage_diff:.1f}%"
                                                        elif eps_actual < eps_estimate:
                                                            beat_expectation = f"Missed EPS ({percentage_diff:.1f}%)"
                                                            percentage_difference = f"{percentage_diff:.1f}%"
                                                        else:
                                                            beat_expectation = "Met EPS (0.0%)"
                                                            percentage_difference = "0.0%"
                                                    else:
                                                        beat_expectation = "Met EPS (0.0%)"
                                                        percentage_difference = "0.0%"
                                                        
                                            # Process revenue data if available
                                            elif revenue_actual is not None and revenue_estimate is not None:
                                                if pd.notna(revenue_actual) and pd.notna(revenue_estimate):
                                                    actual_value = f"${revenue_actual:,.0f}M"
                                                    expected_value = f"${revenue_estimate:,.0f}M"
                                                    
                                                    if revenue_estimate != 0:
                                                        percentage_diff = ((revenue_actual - revenue_estimate) / abs(revenue_estimate)) * 100
                                                        if revenue_actual > revenue_estimate:
                                                            beat_expectation = f"Beat Revenue (+{percentage_diff:.1f}%)"
                                                            percentage_difference = f"+{percentage_diff:.1f}%"
                                                        elif revenue_actual < revenue_estimate:
                                                            beat_expectation = f"Missed Revenue ({percentage_diff:.1f}%)"
                                                            percentage_difference = f"{percentage_diff:.1f}%"
                                                        else:
                                                            beat_expectation = "Met Revenue (0.0%)"
                                                            percentage_difference = "0.0%"
                                                    else:
                                                        beat_expectation = "Met Revenue (0.0%)"
                                                        percentage_difference = "0.0%"
                                except Exception as e:
                                    logging.debug(f"Could not get earnings data for {ticker}: {str(e)}")
                                
                                # If we still don't have data, try calendar_earnings property
                                if beat_expectation == "N/A":
                                    try:
                                        calendar_earnings = yf_ticker.calendar_earnings
                                        if calendar_earnings is not None and not calendar_earnings.empty:
                                            # Get the most recent calendar earnings
                                            latest_calendar = calendar_earnings.iloc[0] if len(calendar_earnings) > 0 else None
                                            
                                            if latest_calendar is not None:
                                                # Check for EPS and revenue columns
                                                for col in latest_calendar.index:
                                                    if 'eps' in col.lower() and 'actual' in col.lower():
                                                        eps_actual = latest_calendar[col]
                                                    elif 'eps' in col.lower() and ('estimate' in col.lower() or 'expected' in col.lower()):
                                                        eps_estimate = latest_calendar[col]
                                                    elif 'revenue' in col.lower() and 'actual' in col.lower():
                                                        revenue_actual = latest_calendar[col]
                                                    elif 'revenue' in col.lower() and ('estimate' in col.lower() or 'expected' in col.lower()):
                                                        revenue_estimate = latest_calendar[col]
                                                        
                                                # Process EPS data if available
                                                if eps_actual is not None and eps_estimate is not None:
                                                    if pd.notna(eps_actual) and pd.notna(eps_estimate):
                                                        actual_value = f"${eps_actual:.2f}"
                                                        expected_value = f"${eps_estimate:.2f}"
                                                        
                                                        if eps_estimate != 0:
                                                            percentage_diff = ((eps_actual - eps_estimate) / abs(eps_estimate)) * 100
                                                            if eps_actual > eps_estimate:
                                                                beat_expectation = f"Beat EPS (+{percentage_diff:.1f}%)"
                                                                percentage_difference = f"+{percentage_diff:.1f}%"
                                                            elif eps_actual < eps_estimate:
                                                                beat_expectation = f"Missed EPS ({percentage_diff:.1f}%)"
                                                                percentage_difference = f"{percentage_diff:.1f}%"
                                                            else:
                                                                beat_expectation = "Met EPS (0.0%)"
                                                                percentage_difference = "0.0%"
                                                        else:
                                                            beat_expectation = "Met EPS (0.0%)"
                                                            percentage_difference = "0.0%"
                                                            
                                                # Process revenue data if available
                                                elif revenue_actual is not None and revenue_estimate is not None:
                                                    if pd.notna(revenue_actual) and pd.notna(revenue_estimate):
                                                        actual_value = f"${revenue_actual:,.0f}M"
                                                        expected_value = f"${revenue_estimate:,.0f}M"
                                                        
                                                        if revenue_estimate != 0:
                                                            percentage_diff = ((revenue_actual - revenue_estimate) / abs(revenue_estimate)) * 100
                                                            if revenue_actual > revenue_estimate:
                                                                beat_expectation = f"Beat Revenue (+{percentage_diff:.1f}%)"
                                                                percentage_difference = f"+{percentage_diff:.1f}%"
                                                            elif revenue_actual < revenue_estimate:
                                                                beat_expectation = f"Missed Revenue ({percentage_diff:.1f}%)"
                                                                percentage_difference = f"{percentage_diff:.1f}%"
                                                            else:
                                                                beat_expectation = "Met Revenue (0.0%)"
                                                                percentage_difference = "0.0%"
                                                        else:
                                                            beat_expectation = "Met Revenue (0.0%)"
                                                            percentage_difference = "0.0%"
                                    except Exception as e:
                                        logging.debug(f"Could not get calendar earnings for {ticker}: {str(e)}")
                                
                                # If we still don't have data, try the earnings calendar approach
                                if beat_expectation == "N/A":
                                    # Check for the actual column names from earnings_dates
                                    eps_estimate = None
                                    eps_actual = None
                                    surprise_percent = None
                                    
                                    # Map the actual column names from earnings_dates
                                    if 'EPS Estimate' in earning_row:
                                        eps_estimate = earning_row['EPS Estimate']
                                    if 'Reported EPS' in earning_row:
                                        eps_actual = earning_row['Reported EPS']
                                    if 'Surprise(%)' in earning_row:
                                        surprise_percent = earning_row['Surprise(%)']
                                    
                                    # Process EPS data if available
                                    if eps_actual is not None and eps_estimate is not None:
                                        if pd.notna(eps_actual) and pd.notna(eps_estimate):
                                            actual_value = f"${eps_actual:.2f}"
                                            expected_value = f"${eps_estimate:.2f}"
                                            
                                            # Use surprise percentage if available, otherwise calculate
                                            if surprise_percent is not None and pd.notna(surprise_percent):
                                                percentage_difference = f"{surprise_percent:.1f}%"
                                                if surprise_percent > 0:
                                                    beat_expectation = f"Beat EPS (+{surprise_percent:.1f}%)"
                                                elif surprise_percent < 0:
                                                    beat_expectation = f"Missed EPS ({surprise_percent:.1f}%)"
                                                else:
                                                    beat_expectation = "Met EPS (0.0%)"
                                                    percentage_difference = "0.0%"
                                            else:
                                                # Calculate percentage difference manually
                                                if eps_estimate != 0:
                                                    percentage_diff = ((eps_actual - eps_estimate) / abs(eps_estimate)) * 100
                                                    percentage_difference = f"{percentage_diff:.1f}%"
                                                    if eps_actual > eps_estimate:
                                                        beat_expectation = f"Beat EPS (+{percentage_diff:.1f}%)"
                                                        percentage_difference = f"+{percentage_diff:.1f}%"
                                                    elif eps_actual < eps_estimate:
                                                        beat_expectation = f"Missed EPS ({percentage_diff:.1f}%)"
                                                        percentage_difference = f"{percentage_diff:.1f}%"
                                                    else:
                                                        beat_expectation = "Met EPS (0.0%)"
                                                        percentage_difference = "0.0%"
                                                else:
                                                    beat_expectation = "Met EPS (0.0%)"
                                                    percentage_difference = "0.0%"
                            
                            except Exception as e:
                                logging.debug(f"Could not determine beat expectation for {ticker}: {str(e)}")
                                beat_expectation = "N/A"
                                actual_value = "N/A"
                                expected_value = "N/A"
                                percentage_difference = "N/A"
                            
                            # Get historical data around the earning date
                            # Get data for 5 days before and after the earning date
                            start_date = earning_date_obj - timedelta(days=5)
                            end_date = earning_date_obj + timedelta(days=5)
                            
                            hist_data = yf_ticker.history(start=start_date, end=end_date)
                            
                            if not hist_data.empty:
                                # Previous day price before earning
                                prev_day_data = hist_data[hist_data.index < earning_date_obj]
                                previous_day_price = "N/A"
                                if not prev_day_data.empty:
                                    previous_day_price = f"${prev_day_data.iloc[-1]['Close']:.2f}"
                                
                                # Price before earning call (day of earning)
                                earning_day_data = hist_data[hist_data.index.date == earning_date_obj.date()]
                                price_before_call = "N/A"
                                if not earning_day_data.empty:
                                    price_before_call = f"${earning_day_data.iloc[0]['Open']:.2f}"
                                
                                # End of earning price (day after earning)
                                next_day_data = hist_data[hist_data.index.date > earning_date_obj.date()]
                                end_of_earning_price = "N/A"
                                if not next_day_data.empty:
                                    end_of_earning_price = f"${next_day_data.iloc[0]['Close']:.2f}"
                                
                                last_two_earnings.append({
                                    "earningDate": earning_date_str,
                                    "previousDayPrice": previous_day_price,
                                    "priceBeforeEarningCall": price_before_call,
                                    "endOfEarningPrice": end_of_earning_price,
                                    "beatExpectation": beat_expectation,
                                    "actualValue": actual_value,
                                    "expectedValue": expected_value,
                                    "percentageDifference": percentage_difference
                                })
                except Exception as e:
                    logging.warning(f"Error fetching earnings data for {ticker}: {str(e)}")
                    # Continue without earnings data
                
                earning_data.append({
                    "ticker": ticker,
                    "currentPrice": f"${current_price:.2f}" if current_price > 0 else "N/A",
                    "earningDate": earning_date,
                    "sector": stock.get('sector', 'Unknown'),
                    "lastTwoEarnings": last_two_earnings
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