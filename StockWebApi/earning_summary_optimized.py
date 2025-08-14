"""
Optimized Earnings Summary with Batch Processing and Working Day Logic

This module fetches earnings data for all stocks in a single batch operation
instead of making individual API calls per stock.

Working Day Logic for Period Filters:
- 1D (1 Day): Shows earnings for today if it's a working day (Mon-Fri), 
              otherwise shows earnings for the next working day
- 1W (1 Week): Shows earnings from today (or next working day if weekend) 
              to 7 days later, ensuring both start and end dates are working days
- 1M (1 Month): Shows earnings from today (or next working day if weekend) 
              to 30 days later, ensuring both start and end dates are working days

This ensures that users always see relevant earnings data for actual trading days.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from utils import load_stocks
from yahoo_finance_proxy import get_batch_ticker_info
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

def is_working_day(date: datetime) -> bool:
    """
    Check if a given date is a working day (Monday to Friday).
    
    Args:
        date: Date to check
        
    Returns:
        True if it's a working day, False otherwise
    """
    # Monday = 0, Sunday = 6
    # Note: This is a simplified version. In production, you might want to also check for market holidays
    return date.weekday() < 5

def get_next_working_day(date: datetime) -> datetime:
    """
    Get the next working day from a given date.
    
    Args:
        date: Starting date
        
    Returns:
        Next working day
    """
    current_date = date
    while not is_working_day(current_date):
        current_date += timedelta(days=1)
    return current_date

def get_previous_working_day(date: datetime) -> datetime:
    """
    Get the previous working day from a given date.
    
    Args:
        date: Starting date
        
    Returns:
        Previous working day
    """
    current_date = date
    while not is_working_day(current_date):
        current_date -= timedelta(days=1)
    return current_date

def calculate_period_dates(period: str, base_date: datetime = None) -> tuple[datetime, datetime]:
    """
    Calculate start and end dates for a given period based on working days.
    
    Args:
        period: Time period ('1D', '1W', '1M')
        base_date: Base date to calculate from (defaults to today)
        
    Returns:
        Tuple of (start_date, end_date)
    """
    if base_date is None:
        base_date = datetime.now()
    
    # Ensure base_date is set to start of day
    base_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == '1D':
        # For 1D: if today is working day, use today; otherwise use next working day
        if is_working_day(base_date):
            start_date = base_date
            end_date = base_date
        else:
            next_working = get_next_working_day(base_date)
            start_date = next_working
            end_date = next_working
            
    elif period == '1W':
        # For 1W: start from today (or next working day if today is weekend) to a week later
        if is_working_day(base_date):
            start_date = base_date
        else:
            start_date = get_next_working_day(base_date)
        
        # Calculate end date ensuring it's also a working day
        end_date = start_date + timedelta(days=7)
        while not is_working_day(end_date):
            end_date += timedelta(days=1)
            
    elif period == '1M':
        # For 1M: start from today (or next working day if today is weekend) to a month later
        if is_working_day(base_date):
            start_date = base_date
        else:
            start_date = get_next_working_day(base_date)
        
        # Calculate end date ensuring it's also a working day
        end_date = start_date + timedelta(days=30)
        while not is_working_day(end_date):
            end_date += timedelta(days=1)
    else:
        raise ValueError(f"Invalid period: {period}. Must be '1D', '1W', or '1M'")
    
    return start_date, end_date

def get_period_description(period: str, start_date: datetime, end_date: datetime) -> str:
    """
    Get a human-readable description of the period and its working day logic.
    
    Args:
        period: Time period ('1D', '1W', '1M')
        start_date: Start date of the period
        end_date: End date of the period
        
    Returns:
        Human-readable description of the period
    """
    today = datetime.now()
    is_today_working = is_working_day(today)
    
    if period == '1D':
        if start_date.date() == today.date():
            return f"Today ({start_date.strftime('%A, %B %d, %Y')}) - Working day"
        else:
            return f"Next working day: {start_date.strftime('%A, %B %d, %Y')} (today is weekend)"
    elif period == '1W':
        if start_date.date() == today.date():
            return f"This week: {start_date.strftime('%A, %B %d')} to {end_date.strftime('%A, %B %d, %Y')}"
        else:
            return f"Next week: {start_date.strftime('%A, %B %d')} to {end_date.strftime('%A, %B %d, %Y')} (starting from next working day)"
    elif period == '1M':
        if start_date.date() == today.date():
            return f"This month: {start_date.strftime('%A, %B %d')} to {end_date.strftime('%A, %B %d, %Y')}"
        else:
            return f"Next month: {start_date.strftime('%A, %B %d')} to {end_date.strftime('%A, %B %d, %Y')} (starting from next working day)"
    else:
        return f"Custom period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

def get_next_working_days(base_date: datetime, count: int = 5) -> List[datetime]:
    """
    Get the next N working days from a given date.
    
    Args:
        base_date: Starting date
        count: Number of working days to get
        
    Returns:
        List of working days
    """
    working_days = []
    current_date = base_date
    
    while len(working_days) < count:
        if is_working_day(current_date):
            working_days.append(current_date)
        current_date += timedelta(days=1)
    
    return working_days

def get_market_status_info() -> Dict[str, Any]:
    """
    Get current market status information including working day status and next working days.
    
    Returns:
        Dictionary with market status information
    """
    today = datetime.now()
    is_working = is_working_day(today)
    
    # Get next 5 working days
    next_working_days = get_next_working_days(today, 5)
    
    # Calculate period dates for reference
    period_info = {}
    for period in ['1D', '1W', '1M']:
        start_date, end_date = calculate_period_dates(period, today)
        period_info[period] = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'start_day': start_date.strftime('%A'),
            'end_day': end_date.strftime('%A'),
            'duration_days': (end_date - start_date).days + 1,
            'description': get_period_description(period, start_date, end_date)
        }
    
    return {
        'current_date': today.strftime('%Y-%m-%d'),
        'current_day': today.strftime('%A'),
        'is_working_day': is_working,
        'next_working_days': [d.strftime('%Y-%m-%d (%A)') for d in next_working_days],
        'period_info': period_info
    }

def get_earning_summary_optimized(sectors_param=None, period_param=None, date_from_param=None, date_to_param=None, page=1, per_page=10):
    """
    Get earning summary data with filtering and pagination using stockhistorymarketdata.json.
    
    Period filtering logic:
    - 1D: Shows earnings scheduled for today if it's a working day, otherwise shows earnings for the next working day
    - 1W: Shows earnings scheduled from today (or next working day if today is weekend) to 7 days later
    - 1M: Shows earnings scheduled from today (or next working day if today is weekend) to 30 days later
    - custom: Uses the provided date_from and date_to parameters
    
    Args:
        sectors_param: Comma-separated string of sectors to filter by
        period_param: Time period filter ('1D', '1W', '1M', 'custom')
        date_from_param: Start date for earning date filter (YYYY-MM-DD) - used when period is 'custom'
        date_to_param: End date for earning date filter (YYYY-MM-DD) - used when period is 'custom'
        page: Page number for pagination
        per_page: Number of items per page
    
    Returns:
        Dictionary with paginated earning data
    """
    try:
        # Load stock history market data from JSON file
        import json
        import os
        from datetime import datetime, timedelta
        
        # Load stockhistorymarketdata.json
        market_data_file = 'stockhistorymarketdata.json'
        if not os.path.exists(market_data_file):
            logger.error(f"Market data file {market_data_file} not found")
            return {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "results": []
            }
        
        with open(market_data_file, 'r') as f:
            market_data = json.load(f)
        
        if not market_data:
            logger.error("No market data found in stockhistorymarketdata.json")
            return {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "results": []
            }
        
        logger.info(f"Loaded {len(market_data)} stocks from stockhistorymarketdata.json")
        
        # Calculate date range based on period using working day logic
        today = datetime.now()
        start_date = None
        end_date = today
        
        if period_param:
            if period_param in ['1D', '1W', '1M']:
                # Use the new working day logic for these periods
                start_date, end_date = calculate_period_dates(period_param, today)
                logger.info(f"Period {period_param}: start_date={start_date.strftime('%Y-%m-%d')} ({start_date.strftime('%A')}), end_date={end_date.strftime('%Y-%m-%d')} ({end_date.strftime('%A')})")
                logger.info(f"Today is {today.strftime('%A')} - Working day: {is_working_day(today)}")
                
                # Show next few working days for debugging
                next_working = get_next_working_days(today, 5)
                logger.info(f"Next 5 working days: {[d.strftime('%Y-%m-%d (%A)') for d in next_working]}")
            elif period_param == 'custom':
                if date_from_param:
                    try:
                        start_date = datetime.strptime(date_from_param, '%Y-%m-%d')
                    except ValueError:
                        logger.error(f"Invalid start date format: {date_from_param}")
                        return {
                            "page": page,
                            "per_page": per_page,
                            "total": 0,
                            "results": []
                        }
                if date_to_param:
                    try:
                        end_date = datetime.strptime(date_to_param, '%Y-%m-%d')
                    except ValueError:
                        logger.error(f"Invalid end date format: {date_to_param}")
                        return {
                            "page": page,
                            "per_page": per_page,
                            "total": 0,
                            "results": []
                        }
        
        # Filter stocks by earning date within the period
        filtered_stocks = []
        valid_earning_dates_found = False
        
        for stock in market_data:
            ticker = stock.get('ticker', '')
            earning_date_str = stock.get('earning_date', '')
            
            if not ticker:
                continue
            
            # Try to parse earning date (format: "7/31/2025 4:30:00 PM")
            if earning_date_str and earning_date_str != 'N/A' and earning_date_str.strip():
                try:
                    earning_date = datetime.strptime(earning_date_str, '%m/%d/%Y %I:%M:%S %p')
                    valid_earning_dates_found = True
                    
                    # For 1D, 1W, 1M periods, we want earnings scheduled for those specific working days
                    if period_param in ['1D', '1W', '1M'] and start_date and end_date:
                        # Check if earning date falls within the working day period
                        if period_param == '1D':
                            # For 1D: exact match with the working day (same date)
                            if earning_date.date() != start_date.date():
                                continue
                        elif period_param == '1W':
                            # For 1W: within the 7-day working day range
                            if earning_date < start_date or earning_date > end_date:
                                continue
                        elif period_param == '1M':
                            # For 1M: within the 30-day working day range
                            if earning_date < start_date or earning_date > end_date:
                                continue
                    else:
                        # For custom periods or no period, use the original logic
                        if start_date and earning_date < start_date:
                            continue
                        if end_date and earning_date > end_date:
                            continue
                    
                    filtered_stocks.append(stock)
                    
                except ValueError:
                    logger.warning(f"Invalid earning date format for {ticker}: {earning_date_str}")
                    continue
            else:
                # No earning date available, include in results for now
                filtered_stocks.append(stock)
        
        # If no valid earning dates were found, return all stocks (fallback behavior)
        if not valid_earning_dates_found:
            logger.info("No valid earning dates found in data, returning all stocks as fallback")
            filtered_stocks = [stock for stock in market_data if stock.get('ticker')]
            logger.info(f"Fallback: returning {len(filtered_stocks)} stocks without earning date filtering")
        
        logger.info(f"Found {len(filtered_stocks)} stocks with earnings in the specified period")
        
        # Log some examples of filtered stocks for debugging
        if filtered_stocks and len(filtered_stocks) > 0:
            sample_stocks = filtered_stocks[:3]  # Show first 3 stocks
            logger.info(f"Sample filtered stocks: {[(s.get('ticker', ''), s.get('earning_date', '')) for s in sample_stocks]}")
        
        # Filter by sectors if provided
        if sectors_param:
            sectors_list = [s.strip() for s in sectors_param.split(',')]
            # Load stocks.json to get sector information
            stocks_data = load_stocks()
            stocks_dict = {stock.get('ticker', ''): stock.get('sector', '') for stock in stocks_data}
            
            filtered_stocks = [
                stock for stock in filtered_stocks 
                if stocks_dict.get(stock.get('ticker', ''), '') in sectors_list
            ]
            logger.info(f"After sector filtering: {len(filtered_stocks)} stocks")
        
        if not filtered_stocks:
            logger.warning("No stocks found after filtering")
            return {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "results": []
            }
        
        # Extract ticker symbols for batch processing
        tickers = [stock.get('ticker', '').upper() for stock in filtered_stocks if stock.get('ticker')]
        
        logger.info(f"Processing {len(tickers)} tickers for earnings summary")
        
        # Get earning information from Yahoo Finance for filtered stocks
        batch_data = get_batch_ticker_info(tickers)
        
        logger.info(f"Successfully fetched batch data for {len(batch_data)} tickers")
        
        # Process the data to extract earnings information
        earning_data = []
        
        for stock in filtered_stocks:
            ticker = stock.get('ticker', '').upper()
            if not ticker or ticker not in batch_data:
                continue
            
            try:
                ticker_data = batch_data[ticker]
                
                # Check if we have valid data
                if 'error' in ticker_data:
                    logger.warning(f"Skipping {ticker} due to error: {ticker_data['error']}")
                    continue
                
                # Extract current price from batch data
                current_price = ticker_data.get('current_price', 'N/A')
                if current_price == 'N/A':
                    continue
                
                # Extract company info from batch data
                company_info = {
                    'company_name': ticker_data.get('company_name', 'N/A'),
                    'market_cap': ticker_data.get('market_cap', 'N/A'),
                    'earning_date': stock.get('earning_date', 'N/A')  # Use from market data
                }
                
                # Get earning date from market data
                earning_date = company_info['earning_date']
                if earning_date == 'N/A' or not earning_date or earning_date.strip() == '':
                    continue
                
                # Create earnings data structure with real data
                last_two_earnings = get_enhanced_earnings_data(ticker, earning_date)
                
                # Get sector from stocks.json
                stocks_data = load_stocks()
                sector = 'Unknown'
                for stock_info in stocks_data:
                    if stock_info.get('ticker', '') == ticker:
                        sector = stock_info.get('sector', 'Unknown')
                        break
                
                earning_data.append({
                    "ticker": ticker,
                    "currentPrice": current_price,
                    "earningDate": earning_date,
                    "sector": sector,
                    "lastTwoEarnings": last_two_earnings,
                    "companyName": company_info['company_name'],
                    "marketCap": company_info['market_cap']
                })
                
            except Exception as e:
                logger.warning(f"Error processing data for {ticker}: {str(e)}")
                continue
        
        # Apply pagination
        total = len(earning_data)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_data = earning_data[start_index:end_index]
        
        logger.info(f"Earnings summary completed: {total} stocks processed, page {page} of {(total + per_page - 1) // per_page}")
        
        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "results": paginated_data
        }
        
    except Exception as e:
        logger.error(f"Error in get_earning_summary_optimized: {str(e)}")
        return {
            "page": page,
            "per_page": per_page,
            "total": 0,
            "results": []
        }

def format_revenue(revenue_value):
    """
    Helper function to format revenue in appropriate units.
    
    Args:
        revenue_value: Revenue value to format
        
    Returns:
        Formatted revenue string with appropriate unit (B for billions, M for millions, K for thousands)
    """
    if revenue_value == "N/A" or not pd.notna(revenue_value):
        return "N/A"
    
    if revenue_value >= 1e9:  # 1 billion or more
        return f"${revenue_value/1e9:.1f}B"
    elif revenue_value >= 1e6:  # 1 million or more
        return f"${revenue_value/1e6:.1f}M"
    elif revenue_value >= 1e3:  # 1 thousand or more
        return f"${revenue_value/1e3:.1f}K"
    else:
        return f"${revenue_value:.0f}"

def get_enhanced_earnings_data(ticker: str, earning_date_str: str) -> List[Dict[str, Any]]:
    """
    Get enhanced earnings data for a specific ticker including historical earnings.
    Now includes Close B4 Earning and After Earning data with proper pre/post market logic.
    
    Args:
        ticker: Stock ticker symbol
        earning_date_str: Earning date string in format "7/31/2025 4:30:00 PM"
    
    Returns:
        List of earnings data dictionaries for the previous 2 earnings
    """
    try:
        # Get the ticker object
        ticker_obj = yf.Ticker(ticker)
        
        # Get earnings dates (this is the current recommended way)
        earnings_dates = ticker_obj.earnings_dates
        if earnings_dates is None or earnings_dates.empty:
            logger.warning(f"No earnings dates data available for {ticker}")
            return []
        
        # Sort earnings by date (most recent first)
        earnings_dates = earnings_dates.sort_index(ascending=False)
        
        # Get the previous 2 earnings (excluding the most recent one)
        # This gives us the 2nd and 3rd most recent earnings
        last_two_earnings = []
        
        # Skip the most recent earning and get the next 2
        for i, (date, row) in enumerate(earnings_dates.head(3).iterrows()):
            # Skip the first (most recent) earning
            if i == 0:
                continue
            # Get the previous 2 earnings
            if i <= 2:
                try:
                    # Get earnings data from the row
                    actual_eps_raw = row.get('Reported EPS', 'N/A')
                    expected_eps_raw = row.get('EPS Estimate', 'N/A')
                    surprise_percent_raw = row.get('Surprise(%)', 'N/A')
                    
                    # Handle NaN values properly
                    actual_eps = 'N/A' if pd.isna(actual_eps_raw) else actual_eps_raw
                    expected_eps = 'N/A' if pd.isna(expected_eps_raw) else expected_eps_raw
                    surprise_percent = 'N/A' if pd.isna(surprise_percent_raw) else surprise_percent_raw
                    
                    # Get revenue data from multiple sources
                    actual_revenue = "N/A"
                    expected_revenue = "N/A"
                    
                    try:
                        # Try to get revenue estimates - check if it's not 0 or NaN
                        revenue_estimates = ticker_obj.revenue_estimate
                        if revenue_estimates is not None and not revenue_estimates.empty:
                            # Get the most recent quarter estimate (0q)
                            if '0q' in revenue_estimates.index:
                                expected_revenue = revenue_estimates.loc['0q', 'avg']
                                # Only use if it's a valid positive number
                                if pd.notna(expected_revenue) and expected_revenue > 0:
                                    expected_revenue = expected_revenue
                                else:
                                    expected_revenue = "N/A"
                            else:
                                # Try to find any valid revenue estimate
                                for col in revenue_estimates.index:
                                    if col in revenue_estimates.columns and 'avg' in revenue_estimates.columns:
                                        val = revenue_estimates.loc[col, 'avg']
                                        if pd.notna(val) and val > 0:
                                            expected_revenue = val
                                            break
                                if expected_revenue == "N/A":
                                    expected_revenue = "N/A"
                        
                        # Try to get historical revenue from financials
                        financials = ticker_obj.financials
                        if financials is not None and not financials.empty:
                            if 'Total Revenue' in financials.index:
                                # Get the most recent revenue data
                                revenue_row = financials.loc['Total Revenue']
                                if not revenue_row.empty:
                                    # Find the most recent non-NaN value
                                    for col in revenue_row.index:
                                        if pd.notna(revenue_row[col]) and revenue_row[col] > 0:
                                            actual_revenue = revenue_row[col]
                                            break
                    except Exception as e:
                        logger.warning(f"Error fetching revenue data for {ticker}: {str(e)}")
                    
                    # Calculate percentage difference if we have both values
                    percentage_diff = "N/A"
                    if actual_eps != 'N/A' and expected_eps != 'N/A' and expected_eps != 0:
                        try:
                            diff = ((actual_eps - expected_eps) / abs(expected_eps)) * 100
                            percentage_diff = f"{diff:+.2f}%"
                        except:
                            percentage_diff = "N/A"
                    
                    # Determine beat expectation
                    beat_expectation = "N/A"
                    if actual_eps != 'N/A' and expected_eps != 'N/A':
                        if actual_eps > expected_eps:
                            beat_expectation = "Beat"
                        elif actual_eps < expected_eps:
                            beat_expectation = "Miss"
                        else:
                            beat_expectation = "Met"
                    
                    # Now calculate the Close B4 Earning and After Earning data for this specific earning date
                    # Determine if earning started before or after market open
                    # Market open is typically 9:30 AM ET
                    earning_hour = date.hour
                    earning_minute = date.minute
                    is_before_market_open = (earning_hour < 9) or (earning_hour == 9 and earning_minute < 30)
                    
                    # Initialize new fields
                    close_b4_earning_price = "N/A"
                    close_b4_earning_change = "N/A"
                    after_earning_price = "N/A"
                    after_earning_change = "N/A"
                    
                    # Try Tiingo first for historical intraday data (much better than Yahoo Finance)
                    price_data = None
                    data_source = "None"
                    
                    try:
                        from tiingo_service import tiingo_service
                        
                        if tiingo_service.is_available():
                            # Try to get 1-minute data from Tiingo first
                            price_data = tiingo_service.get_1min_data_for_date(ticker, date, prepost=True)
                            if price_data is not None and not price_data.empty:
                                data_source = "Tiingo 1min"
                                logger.info(f"Using Tiingo 1-minute data for {ticker} at {date}")
                            else:
                                # Fallback to 5-minute data from Tiingo
                                price_data = tiingo_service.get_5min_data_for_date(ticker, date, prepost=True)
                                if price_data is not None and not price_data.empty:
                                    data_source = "Tiingo 5min"
                                    logger.info(f"Using Tiingo 5-minute data for {ticker} at {date}")
                                else:
                                    # Final fallback to daily data from Tiingo
                                    price_data = tiingo_service.get_daily_data_for_date(ticker, date, prepost=True)
                                    if price_data is not None and not price_data.empty:
                                        data_source = "Tiingo daily"
                                        logger.info(f"Using Tiingo daily data for {ticker} at {date}")
                    
                    except ImportError:
                        logger.info("Tiingo service not available, using Yahoo Finance fallback")
                    except Exception as e:
                        logger.warning(f"Tiingo service error for {ticker}: {str(e)}")
                    
                    # If Tiingo failed or not available, fallback to Yahoo Finance
                    if price_data is None or price_data.empty:
                        # Calculate days since earning for Yahoo Finance interval selection
                        # Convert both dates to naive datetime for arithmetic
                        current_time = datetime.now()
                        if current_time.tzinfo is not None:
                            current_time = current_time.replace(tzinfo=None)
                        
                        date_naive = date
                        if date_naive.tzinfo is not None:
                            date_naive = date_naive.replace(tzinfo=None)
                        
                        days_since_earning = (current_time - date_naive).days
                        
                        # Smart interval selection based on earning age for Yahoo Finance
                        if days_since_earning <= 30:
                            # Recent earning: try 1-minute data first
                            interval = '1m'
                            logger.info(f"Using Yahoo Finance 1-minute data for recent earning ({days_since_earning} days old)")
                        elif days_since_earning <= 60:
                            # Moderately old earning: try 5-minute data
                            interval = '5m'
                            logger.info(f"Using Yahoo Finance 5-minute data for moderately old earning ({days_since_earning} days old)")
                        else:
                            # Old earning: use daily data
                            interval = '1d'
                            logger.info(f"Using Yahoo Finance daily data for old earning ({days_since_earning} days old)")
                        
                        # Use yf.download() method to get data for the earning date AND previous day
                        try:
                            # Get data for the earning date AND previous day to calculate Close B4 Earning
                            start_date = (date - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                            end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                            
                            # Ensure start_date and end_date are timezone-aware
                            start_date_aware = start_date.replace(tzinfo=None) if start_date.tzinfo is None else start_date
                            end_date_aware = (end_date + timedelta(days=1)).replace(tzinfo=None) if (end_date + timedelta(days=1)).tzinfo is None else (end_date + timedelta(days=1))
                            
                            price_data = yf.download(
                                ticker, 
                                start=start_date_aware, 
                                end=end_date_aware, 
                                interval=interval, 
                                prepost=True,
                                progress=False
                            )
                            data_source = f"Yahoo Finance {interval} (with previous day)"
                            
                        except Exception as e:
                            logger.warning(f"Yahoo Finance data not available for {ticker} at {date}: {str(e)}")
                            price_data = None
                    
                    # Initialize default values
                    close_b4_earning_price = "N/A"
                    close_b4_earning_change = "N/A"
                    after_earning_price = "N/A"
                    after_earning_change = "N/A"
                    
                    # Process the price data if we have any
                    if price_data is not None and not price_data.empty:
                        # Filter data for the specific earning date
                        earning_date_data = price_data[price_data.index.date == date.date()]
                        
                        if not earning_date_data.empty:
                            # Calculate Close B4 Earning based on the exact rules specified
                            if is_before_market_open:
                                # Earning started before market open
                                # Rule: Previous day closing price at 3:59 PM vs earning date open price
                                
                                # Get previous day data
                                prev_day = date - timedelta(days=1)
                                prev_day_data = price_data[price_data.index.date == prev_day.date()]
                                
                                if not prev_day_data.empty:
                                    # Find previous day closing price at 3:59 PM
                                    prev_day_close = None
                                    for timestamp, row in prev_day_data.iterrows():
                                        if timestamp.hour == 15 and timestamp.minute >= 59:
                                            prev_day_close = row['Close']
                                            break
                                    
                                    if prev_day_close is None:
                                        # Fallback to last available price before 4 PM
                                        for timestamp, row in prev_day_data.iterrows():
                                            if timestamp.hour < 16:
                                                prev_day_close = row['Close']
                                            else:
                                                break
                                    
                                    # Get earning date open price at 9:30 AM
                                    earning_open = None
                                    for timestamp, row in earning_date_data.iterrows():
                                        if timestamp.hour == 9 and timestamp.minute >= 30:
                                            earning_open = row['Open']
                                            break
                                    
                                    if earning_open is None:
                                        # Fallback to first available price
                                        earning_open = earning_date_data['Open'].iloc[0]
                                    
                                    if earning_open is not None and prev_day_close is not None:
                                        # Convert to float if they're pandas Series
                                        prev_day_close_val = float(prev_day_close) if hasattr(prev_day_close, '__iter__') else prev_day_close
                                        earning_open_val = float(earning_open) if hasattr(earning_open, '__iter__') else earning_open
                                        
                                        # Validate that values are valid numbers and not zero
                                        if (isinstance(prev_day_close_val, (int, float)) and 
                                            isinstance(earning_open_val, (int, float)) and
                                            prev_day_close_val != 0 and 
                                            not math.isnan(prev_day_close_val) and 
                                            not math.isnan(earning_open_val)):
                                            
                                            close_b4_earning_price = f"${prev_day_close_val:.2f}"
                                            change_pct = ((earning_open_val - prev_day_close_val) / prev_day_close_val) * 100
                                            close_b4_earning_change = f"{change_pct:+.2f}%"
                                        else:
                                            logger.warning(f"Invalid price values for Close B4 Earning: prev_day_close={prev_day_close_val}, earning_open={earning_open_val}")
                                            close_b4_earning_price = "N/A"
                                            close_b4_earning_change = "N/A"
                                    
                                    # If we still don't have Close B4 Earning data, try daily data fallback
                                    if close_b4_earning_price == "N/A":
                                        logger.info(f"Attempting daily data fallback for Close B4 Earning for {ticker} at {date}")
                                        try:
                                            # Get daily data as fallback for Close B4 Earning calculation
                                            daily_data = ticker_obj.history(
                                                start=prev_day - timedelta(days=1), 
                                                end=date + timedelta(days=1), 
                                                interval='1d', 
                                                prepost=True
                                            )
                                            
                                            if not daily_data.empty and len(daily_data) >= 2:
                                                # Get previous day close and current day open from daily data
                                                prev_day_close_daily = daily_data.iloc[-2]['Close']  # Second to last row
                                                current_day_open_daily = daily_data.iloc[-1]['Open']  # Last row
                                                
                                                if (isinstance(prev_day_close_daily, (int, float)) and 
                                                    isinstance(current_day_open_daily, (int, float)) and
                                                    prev_day_close_daily != 0 and 
                                                    not math.isnan(prev_day_close_daily) and 
                                                    not math.isnan(current_day_open_daily)):
                                                    
                                                    close_b4_earning_price = f"${prev_day_close_daily:.2f}"
                                                    change_pct = ((current_day_open_daily - prev_day_close_daily) / prev_day_close_daily) * 100
                                                    close_b4_earning_change = f"{change_pct:+.2f}%"
                                                    logger.info(f"Set Close B4 Earning using daily data fallback: {close_b4_earning_price} ({close_b4_earning_change})")
                                                else:
                                                    logger.warning(f"Invalid daily data values for Close B4 Earning fallback: prev_close={prev_day_close_daily}, open={current_day_open_daily}")
                                                    
                                        except Exception as e:
                                            logger.warning(f"Daily data fallback for Close B4 Earning failed: {str(e)}")
                            else:
                                # Earning started after market
                                # Rule: Earning date closing price at 3:59 PM vs earning date open price
                                
                                # Get earning date closing price at 3:59 PM
                                earning_close = None
                                for timestamp, row in earning_date_data.iterrows():
                                    if timestamp.hour == 15 and timestamp.minute >= 59:
                                        earning_close = row['Close']
                                        break
                                
                                if earning_close is None:
                                    # Fallback to last available price before 4 PM
                                    for timestamp, row in earning_date_data.iterrows():
                                        if timestamp.hour < 16:
                                            earning_close = row['Close']
                                        else:
                                            break
                                
                                # Get earning date open price at 9:30 AM
                                earning_open = None
                                for timestamp, row in earning_date_data.iterrows():
                                    if timestamp.hour == 9 and timestamp.minute >= 30:
                                        earning_open = row['Open']
                                        break
                                
                                if earning_open is None:
                                    # Fallback to first available price
                                    earning_open = earning_date_data['Open'].iloc[0]
                                
                                if earning_open is not None and earning_close is not None:
                                    # Convert to float if they're pandas Series
                                    earning_close_val = float(earning_close.iloc[0]) if hasattr(earning_close, 'iloc') else earning_close
                                    earning_open_val = float(earning_open.iloc[0]) if hasattr(earning_open, 'iloc') else earning_open
                                    
                                    # Validate that values are valid numbers and not zero
                                    if (isinstance(earning_close_val, (int, float)) and 
                                        isinstance(earning_open_val, (int, float)) and
                                        earning_close_val != 0 and 
                                        not math.isnan(earning_close_val) and 
                                        not math.isnan(earning_open_val)):
                                        
                                        close_b4_earning_price = f"${earning_close_val:.2f}"
                                        change_pct = ((earning_open_val - earning_close_val) / earning_close_val) * 100
                                        close_b4_earning_change = f"{change_pct:+.2f}%"
                                    else:
                                        logger.warning(f"Invalid price values for Close B4 Earning (after market): earning_close={earning_close_val}, earning_open={earning_open_val}")
                                        close_b4_earning_price = "N/A"
                                        close_b4_earning_change = "N/A"
                                
                                # If we still don't have Close B4 Earning data, try daily data fallback
                                if close_b4_earning_price == "N/A":
                                    logger.info(f"Attempting daily data fallback for Close B4 Earning (after market) for {ticker} at {date}")
                                    try:
                                        # Get daily data as fallback for Close B4 Earning calculation
                                        daily_data = ticker_obj.history(
                                            start=date - timedelta(days=1), 
                                            end=date + timedelta(days=1), 
                                            interval='1d', 
                                            prepost=True
                                        )
                                        
                                        if not daily_data.empty and len(daily_data) >= 2:
                                            # Get previous day close and current day open from daily data
                                            prev_day_close_daily = daily_data.iloc[-2]['Close']  # Second to last row
                                            current_day_open_daily = daily_data.iloc[-1]['Open']  # Last row
                                            
                                            if (isinstance(prev_day_close_daily, (int, float)) and 
                                                isinstance(current_day_open_daily, (int, float)) and
                                                prev_day_close_daily != 0 and 
                                                not math.isnan(prev_day_close_daily) and 
                                                not math.isnan(current_day_open_daily)):
                                                
                                                close_b4_earning_price = f"${prev_day_close_daily:.2f}"
                                                change_pct = ((current_day_open_daily - prev_day_close_daily) / prev_day_close_daily) * 100
                                                close_b4_earning_change = f"{change_pct:+.2f}%"
                                                logger.info(f"Set Close B4 Earning (after market) using daily data fallback: {close_b4_earning_price} ({close_b4_earning_change})")
                                            else:
                                                logger.warning(f"Invalid daily data values for Close B4 Earning fallback (after market): prev_close={prev_day_close_daily}, open={current_day_open_daily}")
                                                
                                    except Exception as e:
                                        logger.warning(f"Daily data fallback for Close B4 Earning (after market) failed: {str(e)}")
                            
                            # Calculate After Earning based on the exact rules specified
                            if is_before_market_open:
                                # Earning started before market open
                                # Rule: 9:25 AM vs 4:05 PM (both on earning date)
                                
                                price_925am = None
                                price_405pm = None
                                
                                for timestamp, row in earning_date_data.iterrows():
                                    if timestamp.hour == 9 and timestamp.minute == 25:
                                        price_925am = row['Close']
                                    elif timestamp.hour == 16 and timestamp.minute == 5:
                                        price_405pm = row['Close']
                                
                                if price_925am is None:
                                    # Fallback to closest time around 9:25 AM
                                    for timestamp, row in earning_date_data.iterrows():
                                        if timestamp.hour == 9 and timestamp.minute >= 20 and timestamp.minute <= 30:
                                            price_925am = row['Close']
                                            break
                                
                                if price_405pm is None:
                                    # Fallback to closest time around 4:05 PM
                                    for timestamp, row in earning_date_data.iterrows():
                                        if timestamp.hour == 16 and timestamp.minute >= 0 and timestamp.minute <= 10:
                                            price_405pm = row['Close']
                                            break
                                
                                if price_925am is not None and price_405pm is not None:
                                    # Convert to float if they're pandas Series
                                    price_925am_val = float(price_925am.iloc[0]) if hasattr(price_925am, 'iloc') else price_925am
                                    price_405pm_val = float(price_405pm.iloc[0]) if hasattr(price_405pm, 'iloc') else price_405pm
                                    
                                    # Validate that values are valid numbers and not zero
                                    if (isinstance(price_925am_val, (int, float)) and 
                                        isinstance(price_405pm_val, (int, float)) and
                                        price_925am_val != 0 and 
                                        not math.isnan(price_925am_val) and 
                                        not math.isnan(price_405pm_val)):
                                        
                                        after_earning_price = f"${price_405pm_val:.2f}"
                                        change_pct = ((price_405pm_val - price_925am_val) / price_925am_val) * 100
                                        after_earning_change = f"{change_pct:+.2f}%"
                                    else:
                                        logger.warning(f"Invalid price values for After Earning (before market): price_925am={price_925am_val}, price_405pm={price_405pm_val}")
                                        after_earning_price = "N/A"
                                        after_earning_change = "N/A"
                                    
                                else:
                                    logger.warning(f"Missing price data for After Earning calculation (before market open): price_925am={price_925am}, price_405pm={price_405pm}")
                                    
                                    # Try to get daily data as fallback for After Earning calculation
                                    try:
                                        daily_data = ticker_obj.history(
                                            start=date - timedelta(days=1), 
                                            end=date + timedelta(days=1), 
                                            interval='1d', 
                                            prepost=True
                                        )
                                        
                                        if not daily_data.empty and len(daily_data) >= 1:
                                            current_day_close = daily_data.iloc[-1]['Close']
                                            current_day_open = daily_data.iloc[-1]['Open']
                                            
                                            if current_day_open is not None and current_day_close is not None:
                                                current_day_open_val = float(current_day_open.iloc[0]) if hasattr(current_day_open, 'iloc') else current_day_open
                                                current_day_close_val = float(current_day_close.iloc[0]) if hasattr(current_day_close, 'iloc') else current_day_close
                                                
                                                # Validate that values are valid numbers and not zero
                                                if (isinstance(current_day_open_val, (int, float)) and 
                                                    isinstance(current_day_close_val, (int, float)) and
                                                    current_day_open_val != 0 and 
                                                    not math.isnan(current_day_open_val) and 
                                                    not math.isnan(current_day_close_val)):
                                                    
                                                    after_earning_price = f"${current_day_close_val:.2f}"
                                                    change_pct = ((current_day_close_val - current_day_open_val) / current_day_open_val) * 100
                                                    after_earning_change = f"{change_pct:+.2f}%"
                                                else:
                                                    logger.warning(f"Invalid daily data values for After Earning fallback (before market): open={current_day_open_val}, close={current_day_close_val}")
                                                    after_earning_price = "N/A"
                                                    after_earning_change = "N/A"
                                                
                                    except Exception as e2:
                                        logger.warning(f"Daily data fallback for After Earning failed: {str(e2)}")
                            else:
                                # Earning started after market
                                # Rule: 4:00 PM vs 7:55 PM (both on earning date)
                                
                                price_400pm = None
                                price_755pm = None
                                
                                for timestamp, row in earning_date_data.iterrows():
                                    if timestamp.hour == 16 and timestamp.minute == 0:
                                        price_400pm = row['Close']
                                    elif timestamp.hour == 19 and timestamp.minute == 55:
                                        price_755pm = row['Close']
                                
                                if price_400pm is None:
                                    # Fallback to closest time around 4:00 PM
                                    for timestamp, row in earning_date_data.iterrows():
                                        if timestamp.hour == 16 and timestamp.minute >= 0 and timestamp.minute <= 10:
                                            price_400pm = row['Close']
                                            break
                                
                                if price_755pm is None:
                                    # Fallback to closest time around 7:55 PM
                                    for timestamp, row in earning_date_data.iterrows():
                                        if timestamp.hour == 19 and timestamp.minute >= 50:
                                            price_755pm = row['Close']
                                            break
                                
                                if price_400pm is not None and price_755pm is not None:
                                    # Validate that values are valid numbers and not zero
                                    if (isinstance(price_400pm, (int, float)) and 
                                        isinstance(price_755pm, (int, float)) and
                                        price_400pm != 0 and 
                                        not math.isnan(price_400pm) and 
                                        not math.isnan(price_755pm)):
                                        
                                        after_earning_price = f"${price_755pm:.2f}"
                                        change_pct = ((price_755pm - price_400pm) / price_400pm) * 100
                                        after_earning_change = f"{change_pct:+.2f}%"
                                        
                                        logger.info(f"Set After Earning for after market: {after_earning_price} ({after_earning_change})")
                                    else:
                                        logger.warning(f"Invalid price values for After Earning (after market): price_400pm={price_400pm}, price_755pm={price_755pm}")
                                        after_earning_price = "N/A"
                                        after_earning_change = "N/A"
                                else:
                                    logger.warning(f"Missing price data for After Earning calculation (after market): price_400pm={price_400pm}, price_755pm={price_755pm}")
                                    
                                    # Try to get daily data as fallback for After Earning calculation
                                    try:
                                        daily_data = ticker_obj.history(
                                            start=date - timedelta(days=1), 
                                            end=date + timedelta(days=1), 
                                            interval='1d', 
                                            prepost=True
                                        )
                                        
                                        if not daily_data.empty and len(daily_data) >= 1:
                                            current_day_close = daily_data.iloc[-1]['Close']
                                            current_day_open = daily_data.iloc[-1]['Open']
                                            
                                            if current_day_open is not None and current_day_close is not None:
                                                current_day_open_val = float(current_day_open.iloc[0]) if hasattr(current_day_open, 'iloc') else current_day_open
                                                current_day_close_val = float(current_day_close.iloc[0]) if hasattr(current_day_close, 'iloc') else current_day_close
                                                
                                                # Validate that values are valid numbers and not zero
                                                if (isinstance(current_day_open_val, (int, float)) and 
                                                    isinstance(current_day_close_val, (int, float)) and
                                                    current_day_open_val != 0 and 
                                                    not math.isnan(current_day_open_val) and 
                                                    not math.isnan(current_day_close_val)):
                                                    
                                                    after_earning_price = f"${current_day_close_val:.2f}"
                                                    change_pct = ((current_day_close_val - current_day_open_val) / current_day_open_val) * 100
                                                    after_earning_change = f"{change_pct:+.2f}%"
                                                else:
                                                    logger.warning(f"Invalid daily data values for After Earning fallback (after market): open={current_day_open_val}, close={current_day_close_val}")
                                                    after_earning_price = "N/A"
                                                    after_earning_change = "N/A"
                                                
                                    except Exception as e2:
                                        logger.warning(f"Daily data fallback for After Earning failed: {str(e2)}")
                    else:
                        logger.warning(f"No price data available for {ticker} at {date}")
                        
                        # Estimate Close B4 Earning
                        close_b4_earning_price = "N/A"
                        close_b4_earning_change = "N/A"
                        
                        # Estimate After Earning
                        after_earning_price = "N/A"
                        after_earning_change = "N/A"
                        
                        # Try to get daily data as fallback
                        try:
                            daily_data = ticker_obj.history(
                                start=date - timedelta(days=2), 
                                end=date + timedelta(days=2), 
                                interval='1d', 
                                prepost=True
                            )
                            
                            if not daily_data.empty and len(daily_data) >= 1:
                                current_day_close = daily_data.iloc[-1]['Close']
                                current_day_open = daily_data.iloc[-1]['Open']
                                
                                if current_day_open is not None and current_day_close is not None:
                                    current_day_open_val = float(current_day_open.iloc[0]) if hasattr(current_day_open, 'iloc') else current_day_open
                                    current_day_close_val = float(current_day_close.iloc[0]) if hasattr(current_day_close, 'iloc') else current_day_close
                                    
                                    after_earning_price = f"${current_day_close_val:.2f}"
                                    change_pct = ((current_day_close_val - current_day_open_val) / current_day_open_val) * 100
                                    after_earning_change = f"{change_pct:+.2f}%"
                                    
                                    logger.info(f"Set After Earning from daily data fallback: {after_earning_price} ({after_earning_change})")
                                else:
                                    logger.warning(f"Missing daily data for After Earning fallback: current_day_open={current_day_open}, current_day_close={current_day_close}")
                        except Exception as e:
                            logger.warning(f"Daily data fallback failed: {str(e)}")
                    
                    # Convert EPS values to strings
                    actual_eps_str = str(actual_eps) if actual_eps != 'N/A' else 'N/A'
                    expected_eps_str = str(expected_eps) if expected_eps != 'N/A' else 'N/A'
                    
                    # Convert revenue values to strings
                    if actual_revenue != 'N/A':
                        actual_revenue_str = f"${actual_revenue:,.0f}" if isinstance(actual_revenue, (int, float)) else str(actual_revenue)
                    else:
                        actual_revenue_str = "N/A"
                    
                    if expected_revenue != 'N/A':
                        expected_revenue_str = f"${expected_revenue:,.0f}" if isinstance(expected_revenue, (int, float)) else str(expected_revenue)
                    else:
                        expected_revenue_str = "N/A"
                    
                    # Add to last two earnings with calculated price data
                    last_two_earnings.append({
                        "earningDate": date.strftime('%m/%d/%Y'),
                        "closeB4EarningPrice": close_b4_earning_price,
                        "closeB4EarningChange": close_b4_earning_change,
                        "afterEarningPrice": after_earning_price,
                        "afterEarningChange": after_earning_change,
                        "beatExpectation": beat_expectation,
                        "actualValue": actual_eps_str,
                        "expectedValue": expected_eps_str,
                        "actualRevenue": actual_revenue_str,
                        "expectedRevenue": expected_revenue_str,
                        "percentageDifference": percentage_diff
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing earnings data for {ticker} at {date}: {str(e)}")
                    # Add a fallback entry with basic data
                    last_two_earnings.append({
                        "earningDate": date.strftime('%m/%d/%Y'),
                        "closeB4EarningPrice": "N/A",
                        "closeB4EarningChange": "N/A",
                        "afterEarningPrice": "N/A",
                        "afterEarningChange": "N/A",
                        "beatExpectation": "N/A",
                        "actualValue": "N/A",
                        "expectedValue": "N/A",
                        "actualRevenue": "N/A",
                        "expectedRevenue": "N/A",
                        "percentageDifference": "N/A"
                    })
                    continue
        
        return last_two_earnings
        
    except Exception as e:
        logger.error(f"Error getting enhanced earnings data for {ticker}: {str(e)}")
        return [{
            "earningDate": "N/A",
            "closeB4EarningPrice": "N/A",
            "closeB4EarningChange": "N/A",
            "afterEarningPrice": "N/A",
            "afterEarningChange": "N/A",
            "beatExpectation": "N/A",
            "actualValue": "N/A",
            "expectedValue": "N/A",
            "actualRevenue": "N/A",
            "expectedRevenue": "N/A",
            "percentageDifference": "N/A"
        }]

def get_earning_summary_enhanced(sectors_param=None, period_param=None, date_from_param=None, date_to_param=None, page=1, per_page=10):
    """
    Enhanced earnings summary that includes more detailed earnings data.
    This function can be enhanced to include earnings history, beat expectations, etc.
    """
    # For now, return the optimized version
    # This can be enhanced later to include more detailed earnings data
    return get_earning_summary_optimized(sectors_param, period_param, date_from_param, date_to_param, page, per_page)

def get_historical_price_data(ticker: str, date: str, interval: str = '1m'):
    """
    Get historical price data for a specific ticker and date.
    
    Args:
        ticker: Stock ticker symbol
        date: Date in MM/DD/YYYY or YYYY-MM-DD format
        interval: Data interval ('1m' for intraday, '1h' for hourly, '1d' for daily)
    
    Returns:
        Dictionary with price data for the specified date
    """
    try:
        # Parse the date - try both formats
        from datetime import datetime
        target_date = None
        
        # Try MM/DD/YYYY format first
        try:
            target_date = datetime.strptime(date, '%m/%d/%Y')
        except ValueError:
            # Try YYYY-MM-DD format
            try:
                target_date = datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return {
                    "error": f"Invalid date format: {date}. Expected format: MM/DD/YYYY or YYYY-MM-DD",
                    "ticker": ticker,
                    "date": date
                }
        
        # Get the ticker object
        ticker_obj = yf.Ticker(ticker)
        
        # Determine the data range based on interval
        if interval == '1m':
            # For intraday data, get the specific date
            start_date = target_date
            end_date = target_date + timedelta(days=1)
            data = ticker_obj.history(start=start_date, end=end_date, interval='1m', prepost=True)
        elif interval == '1h':
            # For hourly data, get the specific date
            start_date = target_date
            end_date = target_date + timedelta(days=1)
            data = ticker_obj.history(start=start_date, end=end_date, interval='1h', prepost=True)
        elif interval == '1d':
            # For daily data, get a few days around the target date
            start_date = target_date - timedelta(days=2)
            end_date = target_date + timedelta(days=2)
            data = ticker_obj.history(start=start_date, end=end_date, interval='1d', prepost=True)
        else:
            return {
                "error": f"Invalid interval: {interval}. Must be '1m', '1h', or '1d'",
                "ticker": ticker,
                "date": date
            }
        
        if data.empty:
            return {
                "error": f"No data available for {ticker} on {date}",
                "ticker": ticker,
                "date": date
            }
        
        # Convert the data to a list of dictionaries
        price_data = []
        for timestamp, row in data.iterrows():
            # Determine if this is pre-market or after-hours
            hour = timestamp.hour
            minute = timestamp.minute
            time_str = timestamp.strftime('%H:%M')
            
            # Market hours: 9:30 AM to 4:00 PM ET
            is_pre_market = hour < 9 or (hour == 9 and minute < 30)
            is_after_hours = hour >= 16
            
            price_data.append({
                "timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "time": time_str,  # Add time for chart display
                "price": float(row['Close']) if pd.notna(row['Close']) else None,  # Chart component expects 'price'
                "open": float(row['Open']) if pd.notna(row['Open']) else None,
                "high": float(row['High']) if pd.notna(row['High']) else None,
                "low": float(row['Low']) if pd.notna(row['Low']) else None,
                "close": float(row['Close']) if pd.notna(row['Close']) else None,
                "volume": int(row['Volume']) if pd.notna(row['Volume']) else 0,
                "isPreMarket": is_pre_market,
                "isAfterHours": is_after_hours
            })
        
        # Get OHLC data for the day
        if price_data:
            # Use the first and last data points for OHLC
            first_data = price_data[0]
            last_data = price_data[-1]
            
            # Calculate price change
            if first_data['open'] and last_data['close']:
                price_change = last_data['close'] - first_data['open']
                price_change_percent = (price_change / first_data['open']) * 100
                change_str = f"{'+' if price_change >= 0 else ''}{price_change:.2f}"
                change_percent_str = f"{'+' if price_change_percent >= 0 else ''}{price_change_percent:.2f}%"
            else:
                change_str = "N/A"
                change_percent_str = "N/A"
            
            # Separate intraday and after-hours data
            intraday_points = []
            after_hours_points = []
            
            for point in price_data:
                if point['isPreMarket'] or point['isAfterHours']:
                    after_hours_points.append(point)
                else:
                    intraday_points.append(point)
            
            return {
                "ticker": ticker,
                "date": date,
                "interval": interval,
                "open": first_data['open'],
                "high": max(p['high'] for p in price_data if p['high'] is not None),
                "low": min(p['low'] for p in price_data if p['low'] is not None),
                "close": last_data['close'],
                "change": change_str,
                "changePercent": change_percent_str,
                "intradayPoints": intraday_points,
                "afterHoursPoints": after_hours_points,
                "afterHoursChange": after_hours_points[-1]['close'] - after_hours_points[0]['open'] if len(after_hours_points) > 1 else 0,
                "afterHoursChangePercent": ((after_hours_points[-1]['close'] - after_hours_points[0]['open']) / after_hours_points[0]['open'] * 100) if len(after_hours_points) > 1 else 0,
                "count": len(price_data)
            }
        else:
            return {
                "error": f"No price data available for {ticker} on {date}",
                "ticker": ticker,
                "date": date
            }
        
    except Exception as e:
        logger.error(f"Error getting historical price data for {ticker}: {str(e)}")
        return {
            "error": f"Error retrieving data: {str(e)}",
            "ticker": ticker,
            "date": date
        }

# Keep the original function for backward compatibility
def get_earning_summary(sectors_param=None, period_param=None, date_from_param=None, date_to_param=None, page=1, per_page=10):
    """
    Backward compatibility wrapper - now calls the optimized version
    """
    return get_earning_summary_optimized(sectors_param, period_param, date_from_param, date_to_param, page, per_page)
