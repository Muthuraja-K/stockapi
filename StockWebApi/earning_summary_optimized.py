"""
Optimized Earnings Summary with Batch Processing
This module fetches earnings data for all stocks in a single batch operation
instead of making individual API calls per stock.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from utils import load_stocks
from yahoo_finance_proxy import get_batch_ticker_info
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

def get_earning_summary_optimized(sectors_param=None, period_param=None, date_from_param=None, date_to_param=None, page=1, per_page=10):
    """
    Get earning summary data with filtering and pagination using stockhistorymarketdata.json.
    
    Args:
        sectors_param: Comma-separated string of sectors to filter by
        period_param: Time period filter ('1D', '1W', '1M')
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
        
        # Calculate date range based on period
        today = datetime.now()
        start_date = None
        end_date = today
        
        if period_param:
            if period_param == '1D':
                start_date = today - timedelta(days=1)
            elif period_param == '1W':
                start_date = today - timedelta(weeks=1)
            elif period_param == '1M':
                start_date = today - timedelta(days=30)
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
        for stock in market_data:
            ticker = stock.get('ticker', '')
            earning_date_str = stock.get('earning_date', '')
            
            if not ticker or not earning_date_str:
                continue
            
            # Parse earning date (format: "7/31/2025 4:30:00 PM")
            try:
                earning_date = datetime.strptime(earning_date_str, '%m/%d/%Y %I:%M:%S %p')
                
                # Check if earning date falls within the period
                if start_date and earning_date < start_date:
                    continue
                if end_date and earning_date > end_date:
                    continue
                
                filtered_stocks.append(stock)
                
            except ValueError:
                logger.warning(f"Invalid earning date format for {ticker}: {earning_date_str}")
                continue
        
        logger.info(f"Found {len(filtered_stocks)} stocks with earnings in the specified period")
        
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
                if earning_date == 'N/A':
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

def get_enhanced_earnings_data(ticker: str, earning_date_str: str) -> List[Dict[str, Any]]:
    """
    Get enhanced earnings data for a specific ticker including historical earnings.
    
    Args:
        ticker: Stock ticker symbol
        earning_date_str: Earning date string in format "7/31/2025 4:30:00 PM"
    
    Returns:
        List of earnings data dictionaries
    """
    try:
        # Parse the earning date
        earning_date = datetime.strptime(earning_date_str, '%m/%d/%Y %I:%M:%S %p')
        
        # Get the ticker object
        ticker_obj = yf.Ticker(ticker)
        
        # Get earnings dates (this is the current recommended way)
        earnings_dates = ticker_obj.earnings_dates
        if earnings_dates is None or earnings_dates.empty:
            logger.warning(f"No earnings dates data available for {ticker}")
            return []
        
        # Sort earnings by date (most recent first)
        earnings_dates = earnings_dates.sort_index(ascending=False)
        
        # Get the last 2 earnings (filter only actual earnings, not meetings)
        earnings_only = earnings_dates[earnings_dates['Event Type'] == 'Earnings']
        
        if earnings_only.empty:
            logger.warning(f"No earnings data available for {ticker}")
            return []
        
        # Get the last 2 earnings
        last_two_earnings = []
        
        for i, (date, row) in enumerate(earnings_only.head(2).iterrows()):
            try:
                # Get the date before earnings
                day_before = date - timedelta(days=1)
                
                # Get historical data for the day before earnings
                hist_data = ticker_obj.history(start=day_before, end=date, interval='1d')
                
                previous_day_price = "N/A"
                if not hist_data.empty:
                    previous_day_price = f"${hist_data['Close'].iloc[-1]:.2f}"
                
                # Get earnings data from the row
                actual_eps = row.get('Reported EPS', 'N/A')
                expected_eps = row.get('EPS Estimate', 'N/A')
                surprise_percent = row.get('Surprise(%)', 'N/A')
                
                # Get revenue data from multiple sources
                actual_revenue = "N/A"
                expected_revenue = "N/A"
                
                try:
                    # Try to get revenue estimates
                    revenue_estimates = ticker_obj.revenue_estimate
                    if revenue_estimates is not None and not revenue_estimates.empty:
                        # Get the most recent quarter estimate (0q)
                        if '0q' in revenue_estimates.index:
                            expected_revenue = revenue_estimates.loc['0q', 'avg']
                            if pd.notna(expected_revenue):
                                expected_revenue = expected_revenue
                    
                    # Try to get historical revenue from financials
                    financials = ticker_obj.financials
                    if financials is not None and not financials.empty:
                        if 'Total Revenue' in financials.index:
                            # Get the most recent revenue data
                            revenue_row = financials.loc['Total Revenue']
                            if not revenue_row.empty:
                                # Find the most recent non-NaN value
                                for col in revenue_row.index:
                                    if pd.notna(revenue_row[col]):
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
                
                # Get price data around earnings
                # For simplicity, we'll use the day before and day after
                day_after = date + timedelta(days=1)
                price_data = ticker_obj.history(start=date, end=day_after + timedelta(days=1), interval='1d')
                
                price_before_call = "N/A"
                end_of_earning_price = "N/A"
                
                if not price_data.empty:
                    if len(price_data) >= 1:
                        price_before_call = f"${price_data['Open'].iloc[0]:.2f}"
                    if len(price_data) >= 2:
                        end_of_earning_price = f"${price_data['Close'].iloc[1]:.2f}"
                
                # Determine beat expectation
                beat_expectation = "N/A"
                if actual_eps != 'N/A' and expected_eps != 'N/A':
                    if actual_eps > expected_eps:
                        beat_expectation = "Beat"
                    elif actual_eps < expected_eps:
                        beat_expectation = "Miss"
                    else:
                        beat_expectation = "Met"
                
                earnings_entry = {
                    "earningDate": date.strftime('%m/%d/%Y'),
                    "previousDayPrice": previous_day_price,
                    "priceBeforeEarningCall": price_before_call,
                    "endOfEarningPrice": end_of_earning_price,
                    "beatExpectation": beat_expectation,
                    "actualValue": f"${actual_eps:.2f}" if pd.notna(actual_eps) else "N/A",
                    "expectedValue": f"${expected_eps:.2f}" if pd.notna(expected_eps) else "N/A",
                    "actualRevenue": f"${actual_revenue/1e9:.1f}B" if actual_revenue != 'N/A' and pd.notna(actual_revenue) else "N/A",
                    "expectedRevenue": f"${expected_revenue/1e9:.1f}B" if expected_revenue != 'N/A' and pd.notna(expected_revenue) else "N/A",
                    "percentageDifference": percentage_diff
                }
                
                last_two_earnings.append(earnings_entry)
                
            except Exception as e:
                logger.warning(f"Error processing earnings entry for {ticker}: {str(e)}")
                # Add a fallback entry
                last_two_earnings.append({
                    "earningDate": date.strftime('%m/%d/%Y'),
                    "previousDayPrice": "N/A",
                    "priceBeforeEarningCall": "N/A",
                    "endOfEarningPrice": "N/A",
                    "beatExpectation": "N/A",
                    "actualValue": "N/A",
                    "expectedValue": "N/A",
                    "actualRevenue": "N/A",
                    "expectedRevenue": "N/A",
                    "percentageDifference": "N/A"
                })
        
        return last_two_earnings
        
    except Exception as e:
        logger.error(f"Error getting enhanced earnings data for {ticker}: {str(e)}")
        # Return fallback data
        return [{
            "earningDate": earning_date_str,
            "previousDayPrice": "N/A",
            "priceBeforeEarningCall": "N/A",
            "endOfEarningPrice": "N/A",
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
            data = ticker_obj.history(start=start_date, end=end_date, interval='1m')
        elif interval == '1h':
            # For hourly data, get the specific date
            start_date = target_date
            end_date = target_date + timedelta(days=1)
            data = ticker_obj.history(start=start_date, end=end_date, interval='1h')
        elif interval == '1d':
            # For daily data, get a few days around the target date
            start_date = target_date - timedelta(days=2)
            end_date = target_date + timedelta(days=2)
            data = ticker_obj.history(start=start_date, end=end_date, interval='1d')
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
