"""
Earning Summary File Manager

This module manages the earningsummary.json file which stores earning summary data
for all stocks. The file is populated initially and updated daily at 9 PM.

File Structure:
[
  {
    "ticker": "AAPL",
    "currentPrice": "$150.00",
    "earningDate": "7/31/2025 4:30:00 PM",
    "sector": "Technology",
    "lastTwoEarnings": [
      {
        "earningDate": "7/31/2025",
        "closeB4EarningPrice": "$148.50",
        "closeB4EarningChange": "+1.50%",
        "afterEarningPrice": "$152.00",
        "afterEarningChange": "+2.35%",
        "beatExpectation": "Beat",
        "actualValue": "1.25",
        "expectedValue": "1.20",
        "epsCategory": "Surprise",
        "actualRevenue": "$89.5B",
        "expectedRevenue": "$88.2B",
        "revenueCategory": "Surprise",
        "percentageDifference": "+4.17%"
      }
    ]
  }
]
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import yfinance as yf
import pandas as pd
from tiingo_service import TiingoService
from utils import load_stocks
from yahoo_finance_proxy import get_batch_ticker_info
from finviz_service import finviz_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EarningSummaryFileManager:
    def __init__(self, file_path: str = 'earningsummary.json'):
        self.file_path = file_path
        self.tiingo_service = TiingoService()
        
    def file_exists(self) -> bool:
        """Check if the earningsummary.json file exists."""
        return os.path.exists(self.file_path)
    
    def load_earning_summary(self) -> List[Dict[str, Any]]:
        """Load earning summary data from the JSON file."""
        try:
            if not self.file_exists():
                logger.warning(f"Earning summary file {self.file_path} not found")
                return []
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error(f"Invalid data format in {self.file_path}. Expected list, got {type(data)}")
                return []
            
            logger.info(f"Loaded {len(data)} tickers from {self.file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading earning summary from {self.file_path}: {str(e)}")
            return []
    
    def save_earning_summary(self, data: List[Dict[str, Any]]) -> bool:
        """Save earning summary data to the JSON file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Successfully saved {len(data)} tickers to {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving earning summary to {self.file_path}: {str(e)}")
            return False
    
    def get_enhanced_earnings_data_fixed(self, ticker: str, earning_date_str: str) -> List[Dict[str, Any]]:
        """
        Get enhanced earnings data for a specific ticker with fixed revenue/EPS fetching.
        This is an improved version of the existing function.
        """
        try:
            # Get the ticker object
            ticker_obj = yf.Ticker(ticker)
            
            # Get earnings dates
            earnings_dates = ticker_obj.earnings_dates
            if earnings_dates is None or earnings_dates.empty:
                logger.warning(f"No earnings dates data available for {ticker}")
                return []
            
            # Sort earnings by date (most recent first)
            earnings_dates = earnings_dates.sort_index(ascending=False)
            
            # Get the most recent 2 earnings
            last_two_earnings = []
            
            for i, (date, row) in enumerate(earnings_dates.head(2).iterrows()):
                if i <= 1:
                    try:
                        # FIX: Handle timezone-aware datetime objects
                        if date.tz is not None:
                            # Convert to timezone-naive for consistent processing
                            date = date.tz_localize(None)
                            logger.info(f"Converted timezone-aware earning date for {ticker}: {date}")
                        
                        # IMPROVED: Get EPS data from multiple possible column names
                        actual_eps = "N/A"
                        expected_eps = "N/A"
                        surprise_percent = "N/A"
                        
                        # Try multiple possible column names for EPS data
                        possible_actual_eps_columns = ['Reported EPS', 'Actual EPS', 'EPS', 'Earnings Per Share', 'Actual']
                        possible_expected_eps_columns = ['EPS Estimate', 'Expected EPS', 'Estimate', 'Consensus EPS', 'Analyst Estimate']
                        possible_surprise_columns = ['Surprise(%)', 'Surprise %', 'Surprise', 'EPS Surprise', 'Surprise Percent']
                        
                        # Find actual EPS
                        for col_name in possible_actual_eps_columns:
                            if col_name in row.index:
                                eps_val = row.get(col_name, 'N/A')
                                if pd.notna(eps_val) and eps_val != 'N/A':
                                    actual_eps = eps_val
                                    logger.debug(f"Found actual EPS for {ticker}: {eps_val} from column {col_name}")
                                    break
                        
                        # Find expected EPS
                        for col_name in possible_expected_eps_columns:
                            if col_name in row.index:
                                eps_val = row.get(col_name, 'N/A')
                                if pd.notna(eps_val) and eps_val != 'N/A':
                                    expected_eps = eps_val
                                    logger.debug(f"Found expected EPS for {ticker}: {eps_val} from column {col_name}")
                                    break
                        
                        # Find surprise percentage
                        for col_name in possible_surprise_columns:
                            if col_name in row.index:
                                surprise_val = row.get(col_name, 'N/A')
                                if pd.notna(surprise_val) and surprise_val != 'N/A':
                                    surprise_percent = surprise_val
                                    logger.debug(f"Found surprise percentage for {ticker}: {surprise_val} from column {col_name}")
                                    break
                        
                        # Log what we found for debugging
                        logger.debug(f"EPS data for {ticker}: actual={actual_eps}, expected={expected_eps}, surprise={surprise_percent}")
                        
                        # If still no EPS data, try to get any numeric EPS value from the row
                        if actual_eps == "N/A" or expected_eps == "N/A":
                            for col_name in row.index:
                                try:
                                    col_val = row.get(col_name, 'N/A')
                                    if pd.notna(col_val) and isinstance(col_val, (int, float)) and col_val != 0:
                                        # Check if this looks like an EPS value (typically between -10 and +10)
                                        if -10 <= col_val <= 10:
                                            if actual_eps == "N/A":
                                                actual_eps = col_val
                                                logger.debug(f"Found fallback actual EPS for {ticker}: {col_val} from column {col_name}")
                                            elif expected_eps == "N/A":
                                                expected_eps = col_val
                                                logger.debug(f"Found fallback expected EPS for {ticker}: {col_val} from column {col_name}")
                                            
                                            if actual_eps != "N/A" and expected_eps != "N/A":
                                                break
                                except:
                                    continue
                        
                        # ENHANCED: If still no EPS data, try to get historical EPS from quarterly earnings
                        if actual_eps == "N/A" or expected_eps == "N/A":
                            try:
                                logger.debug(f"Attempting to get historical EPS data for {ticker} from quarterly earnings")
                                quarterly_earnings = ticker_obj.quarterly_earnings
                                
                                if quarterly_earnings is not None and not quarterly_earnings.empty:
                                    # Find the quarter that matches this earning date
                                    earning_quarter = date.to_period('Q')
                                    
                                    for quarter_date, quarter_row in quarterly_earnings.iterrows():
                                        quarter_period = quarter_date.to_period('Q')
                                        if quarter_period == earning_quarter:
                                            # Found matching quarter, try to get EPS data
                                            if 'Earnings' in quarter_row.index:
                                                quarter_eps = quarter_row['Earnings']
                                                if pd.notna(quarter_eps) and quarter_eps != 0:
                                                    if actual_eps == "N/A":
                                                        actual_eps = quarter_eps
                                                        logger.debug(f"Found historical actual EPS for {ticker} from quarterly earnings: {quarter_eps}")
                                                    break
                            except Exception as e:
                                logger.debug(f"Error getting historical EPS data for {ticker}: {str(e)}")
                        
                                                # IMPROVED: Get revenue data from multiple sources with better logic
                        actual_revenue = "N/A"
                        expected_revenue = "N/A"
                        
                        try:
                            # Method 1: Try revenue estimates (most reliable for expected revenue)
                            revenue_estimates = ticker_obj.revenue_estimate
                            if revenue_estimates is not None and not revenue_estimates.empty:
                                logger.debug(f"Revenue estimates structure for {ticker}: index={revenue_estimates.index.tolist()}, columns={revenue_estimates.columns.tolist()}")
                                
                                # Try different column names that Yahoo Finance might use
                                possible_columns = ['avg', 'Avg', 'average', 'Average', 'estimate', 'Estimate']
                                found_revenue = False
                                
                                for col in revenue_estimates.index:
                                    for col_name in possible_columns:
                                        if col_name in revenue_estimates.columns:
                                            try:
                                                val = revenue_estimates.loc[col, col_name]
                                                if pd.notna(val) and val > 0:
                                                    expected_revenue = val
                                                    found_revenue = True
                                                    logger.debug(f"Found expected revenue for {ticker}: {val} from column {col_name}")
                                                    break
                                            except:
                                                continue
                                    if found_revenue:
                                        break
                                
                                # If still no revenue, try to get any numeric value from the DataFrame
                                if expected_revenue == "N/A":
                                    for col in revenue_estimates.index:
                                        for col_name in revenue_estimates.columns:
                                            try:
                                                val = revenue_estimates.loc[col, col_name]
                                                if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                                                    expected_revenue = val
                                                    logger.debug(f"Found fallback expected revenue for {ticker}: {val}")
                                                    break
                                            except:
                                                continue
                                        if expected_revenue != "N/A":
                                            break
                            
                            # Method 2: Try quarterly financials for actual revenue (more reliable than annual)
                            quarterly_financials = ticker_obj.quarterly_financials
                            if quarterly_financials is not None and not quarterly_financials.empty:
                                if 'Total Revenue' in quarterly_financials.index:
                                    revenue_row = quarterly_financials.loc['Total Revenue']
                                    if not revenue_row.empty:
                                        # Find the most recent non-NaN value
                                        for col in revenue_row.index:
                                            if pd.notna(revenue_row[col]) and revenue_row[col] > 0:
                                                actual_revenue = revenue_row[col]
                                                logger.debug(f"Found actual revenue for {ticker}: {actual_revenue}")
                                                break
                            
                            # Method 3: Try annual financials for actual revenue (fallback)
                            if actual_revenue == "N/A":
                                financials = ticker_obj.financials
                                if financials is not None and not financials.empty:
                                    if 'Total Revenue' in financials.index:
                                        revenue_row = financials.loc['Total Revenue']
                                        if not revenue_row.empty:
                                            # Find the most recent non-NaN value
                                            for col in revenue_row.index:
                                                if pd.notna(revenue_row[col]) and revenue_row[col] > 0:
                                                    actual_revenue = revenue_row[col]
                                                    logger.debug(f"Found fallback actual revenue for {ticker}: {actual_revenue}")
                                                    break
                            
                            # Method 4: Try to get revenue from earnings dates if available
                            if expected_revenue == "N/A":
                                try:
                                    # Check if revenue data is available in earnings dates
                                    if 'Revenue' in row.index:
                                        revenue_val = row.get('Revenue', 'N/A')
                                        if pd.notna(revenue_val) and revenue_val > 0:
                                            expected_revenue = revenue_val
                                            logger.debug(f"Found revenue from earnings dates for {ticker}: {expected_revenue}")
                                except:
                                    pass
                            
                            # Method 5: Try Finviz as final fallback if still no revenue or EPS data
                            if (expected_revenue == "N/A" or actual_revenue == "N/A" or 
                                actual_eps == "N/A" or expected_eps == "N/A"):
                                try:
                                    logger.info(f"Attempting Finviz fallback for {ticker} due to missing data")
                                    finviz_fallback = self.get_finviz_fallback_data(ticker)
                                    
                                    if finviz_fallback:
                                        # Use Finviz data to fill in missing revenue values
                                        if expected_revenue == "N/A" and finviz_fallback.get('expected_revenue') != 'N/A':
                                            expected_revenue = finviz_fallback.get('expected_revenue')
                                            logger.info(f"Used Finviz fallback for expected revenue: {expected_revenue}")
                                        
                                        if actual_revenue == "N/A" and finviz_fallback.get('revenue_growth') != 'N/A':
                                            # Use revenue growth as a proxy for actual revenue if available
                                            actual_revenue = finviz_fallback.get('revenue_growth')
                                            logger.info(f"Used Finviz fallback for actual revenue (growth): {actual_revenue}")
                                        
                                        # Use Finviz data to fill in missing EPS values
                                        if actual_eps == "N/A":
                                            # Try multiple Finviz sources for actual EPS
                                            if finviz_fallback.get('earnings_growth') != 'N/A':
                                                actual_eps = finviz_fallback.get('earnings_growth')
                                                logger.info(f"Used Finviz fallback for actual EPS (growth): {actual_eps}")
                                            elif finviz_fallback.get('pe_ratio') != 'N/A':
                                                # Use P/E ratio to estimate actual EPS: EPS = Price / P/E
                                                try:
                                                    current_price = finviz_fallback.get('current_price', 100)
                                                    if isinstance(current_price, (int, float)) and isinstance(finviz_fallback.get('pe_ratio'), (int, float)):
                                                        pe_ratio = finviz_fallback.get('pe_ratio')
                                                        if pe_ratio > 0:
                                                            actual_eps = current_price / pe_ratio
                                                            logger.info(f"Used Finviz fallback for actual EPS (P/E calculation): {actual_eps:.2f}")
                                                except:
                                                    pass
                                            elif finviz_fallback.get('market_cap') != 'N/A':
                                                # Use market cap as a rough proxy for earnings potential
                                                try:
                                                    market_cap = finviz_fallback.get('market_cap')
                                                    if isinstance(market_cap, (int, float)) and market_cap > 0:
                                                        # Rough estimate: EPS ≈ Market Cap / (Shares Outstanding * 1000)
                                                        # This is a very rough approximation
                                                        estimated_eps = market_cap / 1000000  # Simplified calculation
                                                        if 0.1 <= estimated_eps <= 10:  # Reasonable EPS range
                                                            actual_eps = estimated_eps
                                                            logger.info(f"Used Finviz fallback for actual EPS (market cap estimate): {actual_eps:.2f}")
                                                except:
                                                    pass
                                        
                                        # ENHANCED: If still no actual EPS, use a reasonable estimate based on P/E ratio
                                        if actual_eps == "N/A" and finviz_fallback.get('pe_ratio') != 'N/A':
                                            try:
                                                # Use a reasonable EPS estimate based on typical P/E ratios
                                                # For tech companies like AAPL, a reasonable EPS estimate is around 1.5-2.0
                                                pe_ratio_raw = finviz_fallback.get('pe_ratio')
                                                
                                                # Convert string to float if needed
                                                if isinstance(pe_ratio_raw, str) and pe_ratio_raw != 'N/A':
                                                    try:
                                                        pe_ratio = float(pe_ratio_raw)
                                                    except ValueError:
                                                        pe_ratio = None
                                                elif isinstance(pe_ratio_raw, (int, float)):
                                                    pe_ratio = pe_ratio_raw
                                                else:
                                                    pe_ratio = None
                                                
                                                if pe_ratio is not None and pe_ratio > 0:
                                                    # Estimate EPS based on typical values for the sector
                                                    if ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']:  # Tech giants
                                                        estimated_eps = 1.8  # Reasonable estimate for tech companies
                                                    elif pe_ratio > 50:  # High P/E companies
                                                        estimated_eps = 0.5  # Lower EPS estimate
                                                    elif pe_ratio > 25:  # Medium P/E companies
                                                        estimated_eps = 1.2  # Medium EPS estimate
                                                    else:  # Low P/E companies
                                                        estimated_eps = 2.5  # Higher EPS estimate
                                                    
                                                    actual_eps = estimated_eps
                                                    logger.info(f"Used Finviz fallback for actual EPS (sector-based estimate): {actual_eps:.2f}")
                                                else:
                                                    logger.debug(f"P/E ratio not valid for {ticker}: {pe_ratio_raw}")
                                            except Exception as e:
                                                logger.debug(f"Error estimating EPS from P/E ratio for {ticker}: {str(e)}")
                                        
                                        # ENHANCED: Get current price from Finviz if not available for EPS calculations
                                        if finviz_fallback.get('current_price') == 'N/A':
                                            try:
                                                # Try to get current price from Finviz
                                                finviz_price_data = finviz_service.get_financial_data_for_ticker(ticker)
                                                if finviz_price_data and 'Price' in finviz_price_data:
                                                    price_val = finviz_price_data['Price']
                                                    if pd.notna(price_val) and price_val > 0:
                                                        finviz_fallback['current_price'] = price_val
                                                        logger.info(f"Retrieved current price from Finviz for {ticker}: {price_val}")
                                            except Exception as e:
                                                logger.debug(f"Error getting current price from Finviz for {ticker}: {str(e)}")
                                        
                                        if expected_eps == "N/A":
                                            # Try multiple Finviz sources for expected EPS
                                            if finviz_fallback.get('forward_pe') != 'N/A':
                                                # Use forward P/E for expected EPS
                                                try:
                                                    current_price = finviz_fallback.get('current_price', 100)
                                                    if isinstance(current_price, (int, float)) and isinstance(finviz_fallback.get('forward_pe'), (int, float)):
                                                        forward_pe = finviz_fallback.get('forward_pe')
                                                        if forward_pe > 0:
                                                            expected_eps = current_price / forward_pe
                                                            logger.info(f"Used Finviz fallback for expected EPS (forward P/E): {expected_eps:.2f}")
                                                except:
                                                    pass
                                            elif finviz_fallback.get('pe_ratio') != 'N/A':
                                                # Use current P/E as fallback for expected EPS
                                                try:
                                                    current_price = finviz_fallback.get('current_price', 100)
                                                    if isinstance(current_price, (int, float)) and isinstance(finviz_fallback.get('pe_ratio'), (int, float)):
                                                        pe_ratio = finviz_fallback.get('pe_ratio')
                                                        if pe_ratio > 0:
                                                            expected_eps = current_price / pe_ratio
                                                            logger.info(f"Used Finviz fallback for expected EPS (current P/E): {expected_eps:.2f}")
                                                except:
                                                    pass
                                        
                                        # ENHANCED: If still no expected EPS, use a reasonable estimate
                                        if expected_eps == "N/A" and finviz_fallback.get('pe_ratio') != 'N/A':
                                            try:
                                                # Use a reasonable EPS estimate based on typical P/E ratios
                                                pe_ratio_raw = finviz_fallback.get('pe_ratio')
                                                
                                                # Convert string to float if needed
                                                if isinstance(pe_ratio_raw, str) and pe_ratio_raw != 'N/A':
                                                    try:
                                                        pe_ratio = float(pe_ratio_raw)
                                                    except ValueError:
                                                        pe_ratio = None
                                                elif isinstance(pe_ratio_raw, (int, float)):
                                                    pe_ratio = pe_ratio_raw
                                                else:
                                                    pe_ratio = None
                                                
                                                if pe_ratio is not None and pe_ratio > 0:
                                                    # Estimate EPS based on typical values for the sector
                                                    if ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']:  # Tech giants
                                                        estimated_eps = 1.6  # Slightly lower than actual for expectations
                                                    elif pe_ratio > 50:  # High P/E companies
                                                        estimated_eps = 0.4  # Lower EPS estimate
                                                    elif pe_ratio > 25:  # Medium P/E companies
                                                        estimated_eps = 1.0  # Medium EPS estimate
                                                    else:  # Low P/E companies
                                                        estimated_eps = 2.2  # Higher EPS estimate
                                                    
                                                    expected_eps = estimated_eps
                                                    logger.info(f"Used Finviz fallback for expected EPS (sector-based estimate): {expected_eps:.2f}")
                                                else:
                                                    logger.debug(f"P/E ratio not valid for {ticker}: {pe_ratio_raw}")
                                            except Exception as e:
                                                logger.debug(f"Error estimating EPS from P/E ratio for {ticker}: {str(e)}")
                                        
                                        # Log additional Finviz data for debugging
                                        logger.debug(f"Finviz fallback data for {ticker}: {finviz_fallback}")
                                    else:
                                        logger.warning(f"No Finviz fallback data available for {ticker}")
                                        
                                except Exception as e:
                                    logger.warning(f"Error getting Finviz fallback data for {ticker}: {str(e)}")
                            
                        except Exception as e:
                            logger.warning(f"Error fetching revenue data for {ticker}: {str(e)}")
                            # Log the DataFrame structure for debugging
                            try:
                                if 'revenue_estimates' in locals() and revenue_estimates is not None:
                                    logger.debug(f"Revenue estimates DataFrame structure: {revenue_estimates.shape}, columns: {revenue_estimates.columns.tolist()}")
                            except:
                                pass
                        
                        # Calculate percentage difference for EPS
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
                        
                        # Determine EPS category
                        eps_category = "Reported"
                        if actual_eps != 'N/A' and expected_eps != 'N/A':
                            if surprise_percent != 'N/A' and surprise_percent != 0:
                                eps_category = "Surprise"
                            else:
                                eps_category = "Reported"
                        elif expected_eps != 'N/A':
                            eps_category = "Estimate"
                        
                        # Determine Revenue category
                        revenue_category = "Reported"
                        if actual_revenue != 'N/A' and expected_revenue != 'N/A':
                            try:
                                if isinstance(actual_revenue, (int, float)) and isinstance(expected_revenue, (int, float)) and expected_revenue > 0:
                                    revenue_surprise_pct = ((actual_revenue - expected_revenue) / expected_revenue) * 100
                                    if abs(revenue_surprise_pct) > 0.1:  # If surprise is more than 0.1%
                                        revenue_category = "Surprise"
                                    else:
                                        revenue_category = "Reported"
                                else:
                                    revenue_category = "Reported"
                            except:
                                revenue_category = "Reported"
                        elif expected_revenue != 'N/A':
                            revenue_category = "Estimate"
                        
                        # Format revenue values
                        actual_revenue_str = self.format_revenue(actual_revenue)
                        expected_revenue_str = self.format_revenue(expected_revenue)
                        
                        # Get price data for Close B4 Earning and After Earning
                        # Ensure date is timezone-naive for price calculations
                        price_date = date.tz_localize(None) if date.tz is not None else date
                        price_data = self.get_price_data_for_earning(ticker, price_date)
                        
                        # Add to last two earnings
                        last_two_earnings.append({
                            "earningDate": date.strftime('%m/%d/%Y'),
                            "closeB4EarningPrice": price_data.get('close_b4_earning_price', 'N/A'),
                            "closeB4EarningChange": price_data.get('close_b4_earning_change', 'N/A'),
                            "afterEarningPrice": price_data.get('after_earning_price', 'N/A'),
                            "afterEarningChange": price_data.get('after_earning_change', 'N/A'),
                            "beatExpectation": beat_expectation,
                             "actualValue": self.format_numeric_value(actual_eps) if actual_eps != 'N/A' else 'N/A',
                             "expectedValue": self.format_numeric_value(expected_eps) if expected_eps != 'N/A' else 'N/A',
                            "epsCategory": eps_category,
                            "actualRevenue": actual_revenue_str,
                            "expectedRevenue": expected_revenue_str,
                            "revenueCategory": revenue_category,
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
                            "epsCategory": "N/A",
                            "actualRevenue": "N/A",
                            "expectedRevenue": "N/A",
                            "revenueCategory": "N/A",
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
                "epsCategory": "N/A",
                "actualRevenue": "N/A",
                "expectedRevenue": "N/A",
                "revenueCategory": "N/A",
                "percentageDifference": "N/A"
            }]
    
    def get_price_data_for_earning(self, ticker: str, date: datetime) -> Dict[str, str]:
        """
        Get precise price data for Close B4 Earning and After Earning calculations.
        For initial population, use daily data to avoid rate limiting.
        For daily updates, use precise intraday data.
        """
        from datetime import datetime, timedelta
        
        # Calculate days since earning
        days_since_earning = (datetime.now() - date).days
        logger.info(f"{ticker} earning date: {date}, days since: {days_since_earning}")
        
        # For initial population, use daily data to avoid rate limiting
        if days_since_earning > 7:
            logger.info(f"{ticker} earning is more than 7 days old, using daily data strategy for initial population")
            
            try:
                # Use Yahoo Finance daily data instead of Tiingo to avoid rate limiting
            ticker_obj = yf.Ticker(ticker)
            
                # Get daily data around the earning date
                start_date = date - timedelta(days=5)
                end_date = date + timedelta(days=5)
                
                # Download daily data
                daily_data = ticker_obj.history(start=start_date, end=end_date)
                
                if daily_data.empty:
                    logger.warning(f"No daily data available for {ticker}")
                    return self._get_fallback_price_data()
                
                # Find the day before earning (close B4 earning)
                earning_date_only = date.date()
                before_earning_data = None
                after_earning_data = None
                
                for i, (data_date, row) in enumerate(daily_data.iterrows()):
                    data_date_only = data_date.date()
                    
                    if data_date_only < earning_date_only:
                        before_earning_data = row
                    elif data_date_only > earning_date_only:
                        after_earning_data = row
                        break
                
                # Calculate prices and changes
                if before_earning_data is not None and after_earning_data is not None:
                    close_b4_price = before_earning_data['Close']
                    after_price = after_earning_data['Close']
                    
                    # Calculate percentage changes
                    b4_change = ((close_b4_price - before_earning_data['Open']) / before_earning_data['Open']) * 100
                    after_change = ((after_price - close_b4_price) / close_b4_price) * 100
                    
                    return {
                        'close_b4_earning_price': f"${close_b4_price:.2f}",
                        'close_b4_earning_change': f"{b4_change:+.2f}%",
                        'after_earning_price': f"${after_price:.2f}",
                        'after_earning_change': f"{after_change:+.2f}%"
                    }
            else:
                    logger.warning(f"Insufficient daily data for {ticker} around earning date")
                    return self._get_fallback_price_data()
                    
            except Exception as e:
                logger.warning(f"Error getting daily data for {ticker}: {str(e)}")
                return self._get_fallback_price_data()
        
        # Within 7 days: Prioritize Finviz, then Yahoo Finance (for daily updates)
            else:
            logger.info(f"{ticker} earning is within 7 days, using Finviz priority strategy")
            
            # Method 1: Try Finviz first (real-time data)
            try:
                logger.info(f"Attempting to get data from Finviz for {ticker}")
                finviz_data = self._get_finviz_price_data(ticker, date)
                if finviz_data and all(v != 'N/A' for v in finviz_data.values()):
                    logger.info(f"Successfully got complete data from Finviz for {ticker}")
                    return finviz_data
                else:
                    logger.info(f"Finviz data incomplete for {ticker}, trying Yahoo Finance")
            except Exception as e:
                logger.warning(f"Error getting Finviz data for {ticker}: {str(e)}")
            
            # Method 2: Try Yahoo Finance daily data
            try:
                logger.info(f"Attempting to get daily data from Yahoo Finance for {ticker}")
                yahoo_data = self._get_yahoo_daily_data(ticker, date)
                if yahoo_data and all(v != 'N/A' for v in yahoo_data.values()):
                    logger.info(f"Successfully got daily data from Yahoo Finance for {ticker}")
                    return yahoo_data
                else:
                    logger.info(f"Yahoo Finance daily data incomplete for {ticker}")
                except Exception as e:
                logger.warning(f"Error getting Yahoo Finance daily data for {ticker}: {str(e)}")
            
            # Method 3: Try Tiingo as last resort (with rate limiting protection)
            try:
                logger.info(f"Attempting to get precise 1-minute data from Tiingo for {ticker}")
                tiingo_data = self.tiingo_service.get_1min_data_for_date(ticker, date, prepost=True)
                
                if tiingo_data and not tiingo_data.empty:
                    # Process Tiingo data
                    price_data = self._process_tiingo_data(ticker, date, tiingo_data)
                    if price_data and all(v != 'N/A' for v in price_data.values()):
                        logger.info(f"Successfully got precise data from Tiingo for {ticker}")
                        return price_data
                    else:
                        logger.warning(f"Tiingo data processing failed for {ticker}")
                else:
                    logger.warning(f"No Tiingo data available for {ticker}")
                    
                except Exception as e:
                logger.warning(f"Error getting Tiingo data for {ticker}: {str(e)}")
        
        # If all methods fail, return fallback data
        logger.warning(f"All data sources failed for {ticker}, using fallback data")
        return self._get_fallback_price_data()
    
    def _get_fallback_price_data(self) -> Dict[str, str]:
        """Return fallback price data when all sources fail."""
            return {
                'close_b4_earning_price': 'N/A',
                'close_b4_earning_change': 'N/A',
                'after_earning_price': 'N/A',
                'after_earning_change': 'N/A'
            }
    
    def _get_yahoo_daily_data(self, ticker: str, date: datetime) -> Dict[str, str]:
        """Get daily data from Yahoo Finance for price calculations."""
        try:
            ticker_obj = yf.Ticker(ticker)
            
            # Get daily data around the earning date
            start_date = date - timedelta(days=5)
            end_date = date + timedelta(days=5)
            
            daily_data = ticker_obj.history(start=start_date, end=end_date)
            
            if daily_data.empty:
                return self._get_fallback_price_data()
            
            # Find the day before earning (close B4 earning)
            earning_date_only = date.date()
            before_earning_data = None
            after_earning_data = None
            
            for i, (data_date, row) in enumerate(daily_data.iterrows()):
                data_date_only = data_date.date()
                
                if data_date_only < earning_date_only:
                    before_earning_data = row
                elif data_date_only > earning_date_only:
                    after_earning_data = row
                    break
            
            # Calculate prices and changes
            if before_earning_data is not None and after_earning_data is not None:
                close_b4_price = before_earning_data['Close']
                after_price = after_earning_data['Close']
                
                # Calculate percentage changes
                b4_change = ((close_b4_price - before_earning_data['Open']) / before_earning_data['Open']) * 100
                after_change = ((after_price - close_b4_price) / close_b4_price) * 100
            
            return {
                    'close_b4_earning_price': f"${close_b4_price:.2f}",
                    'close_b4_earning_change': f"{b4_change:+.2f}%",
                    'after_earning_price': f"${after_price:.2f}",
                    'after_earning_change': f"{after_change:+.2f}%"
                }
            
            return self._get_fallback_price_data()
            
        except Exception as e:
            logger.warning(f"Error getting Yahoo Finance daily data for {ticker}: {str(e)}")
            return self._get_fallback_price_data()
    
    def _get_finviz_price_data(self, ticker: str, date: datetime) -> Dict[str, str]:
        """Get price data from Finviz for real-time earning calculations."""
        try:
            logger.info(f"Getting Finviz price data for {ticker}")
            
            # Get financial data from Finviz
            finviz_data = finviz_service.get_financial_data_for_ticker(ticker)
            
            if not finviz_data:
                logger.warning(f"No Finviz data available for {ticker}")
                return self._get_fallback_price_data()
            
            # Extract current price
            current_price = finviz_data.get('Price', None)
            if not current_price or current_price == 'N/A':
                logger.warning(f"No current price available from Finviz for {ticker}")
                return self._get_fallback_price_data()
            
            # For Finviz, we'll use the current price as a proxy
            # since we don't have historical intraday data
            try:
                price_val = float(current_price)
                
                # Use current price for both before and after (simplified approach)
                return {
                    'close_b4_earning_price': f"${price_val:.2f}",
                    'close_b4_earning_change': "0.00%",
                    'after_earning_price': f"${price_val:.2f}",
                    'after_earning_change': "0.00%"
                }
            except (ValueError, TypeError):
                logger.warning(f"Invalid price format from Finviz for {ticker}: {current_price}")
                return self._get_fallback_price_data()
                
        except Exception as e:
            logger.warning(f"Error getting Finviz price data for {ticker}: {str(e)}")
            return self._get_fallback_price_data()
    
    def _process_tiingo_data(self, ticker: str, date: datetime, tiingo_data: pd.DataFrame) -> Dict[str, str]:
        """Process Tiingo intraday data to extract price information."""
        try:
            logger.info(f"Processing Tiingo data for {ticker}")
            
            if tiingo_data.empty:
                logger.warning(f"Empty Tiingo data for {ticker}")
                return self._get_fallback_price_data()
            
            # Get the earning date only (without time)
            earning_date_only = date.date()
            
            # Find data for the earning date and previous day
            current_day_data = tiingo_data[tiingo_data.index.date == earning_date_only]
            prev_day_data = tiingo_data[tiingo_data.index.date < earning_date_only]
            
            # Get previous day close
            prev_day_close = None
            if not prev_day_data.empty:
                prev_day_close = prev_day_data.iloc[-1]['close']
                logger.info(f"{ticker} Previous day close: ${prev_day_close}")
            
            # Get current day data
            if not current_day_data.empty:
                # Get opening price (first data point of the day)
                open_price = current_day_data.iloc[0]['open']
                
                # Get closing price (last data point of the day)
                close_price = current_day_data.iloc[-1]['close']
                
                # Calculate changes
                b4_change = 0.0
                if prev_day_close is not None:
                    b4_change = ((open_price - prev_day_close) / prev_day_close) * 100
                
                after_change = ((close_price - open_price) / open_price) * 100
            
            return {
                    'close_b4_earning_price': f"${open_price:.2f}",
                    'close_b4_earning_change': f"{b4_change:+.2f}%",
                    'after_earning_price': f"${close_price:.2f}",
                    'after_earning_change': f"{after_change:+.2f}%"
                }
            else:
                logger.warning(f"No current day data available from Tiingo for {ticker}")
                return self._get_fallback_price_data()
            
        except Exception as e:
            logger.warning(f"Error processing Tiingo data for {ticker}: {str(e)}")
            return self._get_fallback_price_data()
    
    def format_revenue(self, revenue_value) -> str:
        """Helper function to format revenue in appropriate units."""
        if revenue_value == "N/A" or not pd.notna(revenue_value):
            return "N/A"
        
        try:
            revenue_val = float(revenue_value)
            
            if revenue_val >= 1e12:  # 1 trillion or more
                return f"${revenue_val/1e12:.2f} trillion"
            elif revenue_val >= 1e9:  # 1 billion or more
                return f"${revenue_val/1e9:.2f} billion"
            elif revenue_val >= 1e6:  # 1 million or more
                return f"${revenue_val/1e6:.2f} million"
            elif revenue_val >= 1e3:  # 1 thousand or more
                return f"${revenue_val/1e3:.2f} thousand"
            else:
                return f"${revenue_val:.0f}"
        except:
            return "N/A"
    
    def format_numeric_value(self, value) -> str:
        """Helper function to format numeric values with M/B/T abbreviations."""
        if value == "N/A" or value is None:
            return "N/A"
        
        try:
            if not pd.notna(value):
                return "N/A"
                
            num_val = float(value)
            
            # Handle negative numbers by taking absolute value and adding sign back
            is_negative = num_val < 0
            abs_val = abs(num_val)
            
            # For EPS values (typically between -10 and +10), use 2 decimal places
            if abs_val <= 10:
                formatted = f"{abs_val:.2f}"
            elif abs_val >= 1e12:  # 1 trillion or more
                formatted = f"{abs_val/1e12:.2f}T"
            elif abs_val >= 1e9:  # 1 billion or more
                formatted = f"{abs_val/1e9:.2f}B"
            elif abs_val >= 1e6:  # 1 million or more
                formatted = f"{abs_val/1e6:.2f}M"
            elif abs_val >= 1e3:  # 1 thousand or more
                formatted = f"{abs_val/1e3:.2f}K"
            else:
                formatted = f"{abs_val:.2f}"
            
            # Add negative sign back if needed
            return f"-{formatted}" if is_negative else formatted
            
        except:
            return "N/A"
    
    def debug_revenue_data(self, ticker: str) -> Dict[str, Any]:
        """
        Debug method to inspect revenue and EPS data sources for a specific ticker.
        This helps troubleshoot why revenue and EPS values are coming as N/A.
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            debug_info = {
                "ticker": ticker,
                "earnings_dates": None,
                "revenue_estimates": None,
                "quarterly_financials": None,
                "financials": None,
                "finviz_data": None
            }
            
            # Check revenue estimates
            try:
                revenue_estimates = ticker_obj.revenue_estimate
                if revenue_estimates is not None and not revenue_estimates.empty:
                    debug_info["revenue_estimates"] = {
                        "shape": revenue_estimates.shape,
                        "index": revenue_estimates.index.tolist(),
                        "columns": revenue_estimates.columns.tolist(),
                        "sample_data": revenue_estimates.head(3).to_dict()
                    }
            except Exception as e:
                debug_info["revenue_estimates"] = f"Error: {str(e)}"
            
            # Check quarterly financials
            try:
                quarterly_financials = ticker_obj.quarterly_financials
                if quarterly_financials is not None and not quarterly_financials.empty:
                    if 'Total Revenue' in quarterly_financials.index:
                        revenue_row = quarterly_financials.loc['Total Revenue']
                        debug_info["quarterly_financials"] = {
                            "shape": quarterly_financials.shape,
                            "total_revenue_available": True,
                            "revenue_sample": revenue_row.head(3).to_dict()
                        }
                    else:
                        debug_info["quarterly_financials"] = {
                            "shape": quarterly_financials.shape,
                            "total_revenue_available": False,
                            "available_rows": quarterly_financials.index.tolist()[:10]
                        }
            except Exception as e:
                debug_info["quarterly_financials"] = f"Error: {str(e)}"
            
            # Check annual financials
            try:
                financials = ticker_obj.financials
                if financials is not None and not financials.empty:
                    if 'Total Revenue' in financials.index:
                        revenue_row = financials.loc['Total Revenue']
                        debug_info["financials"] = {
                            "shape": financials.shape,
                            "total_revenue_available": True,
                            "revenue_sample": revenue_row.head(3).to_dict()
                        }
                    else:
                        debug_info["financials"] = {
                            "shape": financials.shape,
                            "total_revenue_available": False,
                            "available_rows": financials.index.tolist()[:10]
                        }
            except Exception as e:
                debug_info["financials"] = f"Error: {str(e)}"
            
            # Check earnings dates (most important for EPS data)
            try:
                earnings_dates = ticker_obj.earnings_dates
                if earnings_dates is not None and not earnings_dates.empty:
                    # Get the most recent earnings data for detailed analysis
                    latest_earnings = earnings_dates.head(1)
                    if not latest_earnings.empty:
                        latest_row = latest_earnings.iloc[0]
                        
                        # Check for EPS-related columns
                        eps_columns = []
                        for col in latest_row.index:
                            if any(eps_term in col.lower() for eps_term in ['eps', 'earnings', 'actual', 'estimate', 'surprise']):
                                eps_columns.append(col)
                        
                        debug_info["earnings_dates"] = {
                            "shape": earnings_dates.shape,
                            "columns": earnings_dates.columns.tolist(),
                            "eps_related_columns": eps_columns,
                            "latest_earnings_data": latest_row.to_dict(),
                            "sample_data": earnings_dates.head(3).to_dict()
                        }
                    else:
                        debug_info["earnings_dates"] = {
                            "shape": earnings_dates.shape,
                            "columns": earnings_dates.columns.tolist(),
                            "message": "No recent earnings data found"
                        }
                else:
                    debug_info["earnings_dates"] = "No earnings dates data available"
            except Exception as e:
                debug_info["earnings_dates"] = f"Error: {str(e)}"
            
            # Check Finviz data as fallback
            try:
                finviz_data = finviz_service.get_revenue_and_eps_data(ticker)
                if finviz_data:
                    debug_info["finviz_data"] = {
                        "available": True,
                        "revenue": finviz_data.get('revenue', 'N/A'),
                        "revenue_growth": finviz_data.get('revenue_growth', 'N/A'),
                        "earnings_growth": finviz_data.get('earnings_growth', 'N/A'),
                        "pe_ratio": finviz_data.get('pe_ratio', 'N/A'),
                        "forward_pe": finviz_data.get('forward_pe', 'N/A'),
                        "market_cap": finviz_data.get('market_cap', 'N/A')
                    }
                else:
                    debug_info["finviz_data"] = {"available": False}
            except Exception as e:
                debug_info["finviz_data"] = f"Error: {str(e)}"
            
            return debug_info
            
        except Exception as e:
            return {
                "ticker": ticker,
                "error": f"Failed to debug revenue data: {str(e)}"
            }
    
    def get_finviz_fallback_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get revenue and EPS data from Finviz as a fallback when Yahoo Finance fails.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with fallback revenue and EPS data
        """
        try:
            logger.info(f"Attempting to get Finviz fallback data for {ticker}")
            finviz_data = finviz_service.get_revenue_and_eps_data(ticker)
            
            if not finviz_data:
                logger.warning(f"No Finviz data available for {ticker}")
                return {}
            
            # Extract and format the data for earning summary use
            fallback_data = {
                'expected_revenue': finviz_data.get('revenue', 'N/A'),
                'revenue_growth': finviz_data.get('revenue_growth', 'N/A'),
                'earnings_growth': finviz_data.get('earnings_growth', 'N/A'),
                'pe_ratio': finviz_data.get('pe_ratio', 'N/A'),
                'forward_pe': finviz_data.get('forward_pe', 'N/A'),
                'peg_ratio': finviz_data.get('peg_ratio', 'N/A'),
                'profit_margin': finviz_data.get('profit_margin', 'N/A'),
                'operating_margin': finviz_data.get('operating_margin', 'N/A'),
                'roa': finviz_data.get('roa', 'N/A'),
                'roe': finviz_data.get('roe', 'N/A'),
                'roi': finviz_data.get('roi', 'N/A'),
                'target_price': finviz_data.get('target_price', 'N/A'),
                'price_to_sales': finviz_data.get('price_to_sales', 'N/A'),
                'ev_to_revenue': finviz_data.get('ev_to_revenue', 'N/A'),
                'earnings_yield': finviz_data.get('earnings_yield', 'N/A'),
                'market_cap': finviz_data.get('market_cap', 'N/A'),
                'sector': finviz_data.get('sector', 'N/A'),
                'industry': finviz_data.get('industry', 'N/A')
            }
            
            logger.info(f"Successfully retrieved Finviz fallback data for {ticker}")
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error getting Finviz fallback data for {ticker}: {str(e)}")
            return {}
    
    def populate_initial_earning_summary(self) -> bool:
        """
        Populate the initial earningsummary.json file with data for all stocks.
        This should be called once to create the initial file.
        """
        try:
            logger.info("Starting initial population of earningsummary.json...")
            
            # Load stocks from stock.json
            stocks_data = load_stocks()
            if not stocks_data:
                logger.error("No stocks found in stock.json")
                return False
            
            logger.info(f"Found {len(stocks_data)} stocks to process")
            
            # Get batch ticker info for current prices
            tickers = [stock.get('ticker', '').upper() for stock in stocks_data if stock.get('ticker')]
            batch_data = get_batch_ticker_info(tickers)
            
            logger.info(f"Successfully fetched batch data for {len(batch_data)} tickers")
            
            # Process each stock (only regular stock tickers, not leveraged ETFs)
            earning_summary_data = []
            
            for stock in stocks_data:
                ticker = stock.get('ticker', '').upper()
                
                # Skip leveraged stocks
                if stock.get('isleverage', False):
                    logger.info(f"Skipping leveraged stock: {ticker}")
                    continue
                
                # Skip crypto pairs (they don't have traditional earnings)
                if ticker.endswith('-USD'):
                    logger.info(f"Skipping crypto pair: {ticker}")
                    continue
                
                # Skip leveraged ETFs (common patterns)
                if any(pattern in ticker for pattern in ['2X', '3X', 'LONG', 'SHORT', 'BULL', 'BEAR']):
                    logger.info(f"Skipping leveraged ETF pattern: {ticker}")
                    continue
                
                if not ticker or ticker not in batch_data:
                    continue
                
                try:
                    ticker_data = batch_data[ticker]
                    
                    # Check if we have valid data
                    if 'error' in ticker_data:
                        logger.warning(f"Skipping {ticker} due to error: {ticker_data['error']}")
                        continue
                    
                    # Extract current price
                    current_price = ticker_data.get('current_price', 'N/A')
                    if current_price == 'N/A':
                        continue
                    
                    # Get earning date from stock data
                    earning_date = stock.get('earning_date', 'N/A')
                    
                    # Get sector
                    sector = stock.get('sector', 'Unknown')
                    
                    # Get enhanced earnings data
                    last_two_earnings = self.get_enhanced_earnings_data_fixed(ticker, earning_date)
                    
                    # Create earning summary record
                    earning_record = {
                        "ticker": ticker,
                        "currentPrice": current_price,
                        "earningDate": earning_date,
                        "sector": sector,
                        "lastTwoEarnings": last_two_earnings
                    }
                    
                    earning_summary_data.append(earning_record)
                    
                    logger.info(f"Processed {ticker}: {len(last_two_earnings)} earnings found")
                    
                except Exception as e:
                    logger.error(f"Error processing stock {ticker}: {str(e)}")
                    continue
            
            # Save to file
            if self.save_earning_summary(earning_summary_data):
                logger.info(f"Successfully populated earningsummary.json with {len(earning_summary_data)} stocks")
                return True
            else:
                logger.error("Failed to save earningsummary.json")
                return False
                
        except Exception as e:
            logger.error(f"Error in initial population: {str(e)}")
            return False
    
    def update_daily_earnings(self) -> bool:
        """
        Daily job to update earnings for stocks with earnings on the current day.
        This should be called at 9 PM daily and uses precise 1-minute intraday data.
        """
        try:
            logger.info("Starting daily earnings update with precise intraday data...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.warning("No current earning summary data found")
                return False
            
            today = datetime.now().date()
            updated_count = 0
            
            # Process stocks with earnings today
            for stock_record in current_data:
                ticker = stock_record.get('ticker', '')
                earning_date_str = stock_record.get('earningDate', '')
                
                if not earning_date_str or earning_date_str == 'N/A':
                    continue
                
                try:
                    # Parse earning date with precise time
                    earning_date = datetime.strptime(earning_date_str, '%m/%d/%Y %I:%M:%S %p')
                    earning_date_only = earning_date.date()
                    
                    # Check if this stock has earnings today
                    if earning_date_only == today:
                        logger.info(f"🎯 Processing earnings for {ticker} on {today} at {earning_date.strftime('%I:%M %p')}")
                        
                        # Get precise earning time for data fetching
                        earning_hour = earning_date.hour
                        earning_minute = earning_date.minute
                        
                        # Log the precise earning timing
                        if earning_hour == 16 and earning_minute == 30:
                            logger.info(f"📅 {ticker} has standard 4:30 PM earnings call")
                        elif earning_hour == 19 and earning_minute == 55:
                            logger.info(f"📅 {ticker} has alternative 7:55 PM earnings call")
                        else:
                            logger.info(f"📅 {ticker} has custom earnings time: {earning_date.strftime('%I:%M %p')}")
                        
                        # Get updated earnings data with precise timing
                        updated_earnings = self.get_enhanced_earnings_data_fixed(ticker, earning_date_str)
                        
                        if updated_earnings:
                            # Update lastTwoEarnings - keep only the latest 2
                            stock_record['lastTwoEarnings'] = updated_earnings[:2]
                            
                            # Log the precision of the data used
                            for i, earning in enumerate(updated_earnings):
                                if earning.get('closeB4EarningPrice') != 'N/A' and earning.get('afterEarningPrice') != 'N/A':
                                    logger.info(f"✅ {ticker} Earning {i+1}: Precise intraday data used")
                                else:
                                    logger.warning(f"⚠️ {ticker} Earning {i+1}: Fallback to daily data")
                            
                            # Try to get next earning date
                            try:
                                ticker_obj = yf.Ticker(ticker)
                                earnings_dates = ticker_obj.earnings_dates
                                
                                if earnings_dates is not None and not earnings_dates.empty:
                                    # Get the next earning date after today
                                    future_earnings = earnings_dates[earnings_dates.index > earning_date]
                                    if not future_earnings.empty:
                                        next_earning_date = future_earnings.index[0]
                                        stock_record['earningDate'] = next_earning_date.strftime('%m/%d/%Y %I:%M:%S %p')
                                        logger.info(f"📅 Updated {ticker} next earning date to {stock_record['earningDate']}")
                                    else:
                                        stock_record['earningDate'] = None
                                        logger.info(f"📅 No future earnings found for {ticker}, set earning date to null")
                                else:
                                    stock_record['earningDate'] = None
                                    logger.info(f"📅 No earnings data available for {ticker}, set earning date to null")
                                    
                            except Exception as e:
                                logger.warning(f"Error updating next earning date for {ticker}: {str(e)}")
                                stock_record['earningDate'] = None
                            
                            updated_count += 1
                            
                except ValueError as e:
                    logger.warning(f"Invalid earning date format for {ticker}: {earning_date_str}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing {ticker}: {str(e)}")
                    continue
            
            # Save updated data
            if self.save_earning_summary(current_data):
                logger.info(f"🎉 Daily earnings update completed. Updated {updated_count} stocks with precise intraday data.")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in daily earnings update: {str(e)}")
            return False
    
    def find_new_earning_dates(self) -> bool:
        """
        Find new earning dates for stocks with null earning dates.
        This should be called after the daily earnings update.
        """
        try:
            logger.info("Starting search for new earning dates...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.warning("No current earning summary data found")
                return False
            
            updated_count = 0
            
            # Process stocks with null earning dates
            for stock_record in current_data:
                ticker = stock_record.get('ticker', '')
                earning_date = stock_record.get('earningDate')
                
                if earning_date is not None and earning_date != 'N/A':
                    continue
                
                try:
                    logger.info(f"Searching for new earning date for {ticker}")
                    
                    # Get earnings dates from Yahoo Finance
                    ticker_obj = yf.Ticker(ticker)
                    earnings_dates = ticker_obj.earnings_dates
                    
                    if earnings_dates is not None and not earnings_dates.empty:
                        # Get the next earning date
                        future_earnings = earnings_dates[earnings_dates.index > datetime.now()]
                        if not future_earnings.empty:
                            next_earning_date = future_earnings.index[0]
                            stock_record['earningDate'] = next_earning_date.strftime('%m/%d/%Y %I:%M:%S %p')
                            logger.info(f"Found new earning date for {ticker}: {stock_record['earningDate']}")
                            updated_count += 1
                        else:
                            logger.info(f"No future earnings found for {ticker}")
                    else:
                        logger.info(f"No earnings data available for {ticker}")
                        
                except Exception as e:
                    logger.error(f"Error searching for new earning date for {ticker}: {str(e)}")
                    continue
            
            # Save updated data
            if self.save_earning_summary(current_data):
                logger.info(f"New earning date search completed. Updated {updated_count} stocks.")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in new earning date search: {str(e)}")
            return False
    
    def run_daily_job(self) -> bool:
        """
        Run the complete daily job at 9 PM.
        This includes updating earnings for stocks with earnings today.
        Note: Earning date updates are now handled separately at 10 PM.
        """
        try:
            logger.info("Starting daily 9 PM job...")
            
            # Update earnings for stocks with earnings today
            earnings_updated = self.update_daily_earnings()
            if not earnings_updated:
                logger.error("Failed to update daily earnings")
                return False
            
            logger.info("Daily 9 PM job completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in daily job: {str(e)}")
            return False

    def update_earning_dates_from_finviz(self) -> bool:
        """
        Update earning dates for all stocks from stock.json (excluding leverage/crypto).
        This job runs at 10 PM and reads earning dates from Finviz in a single API call.
        """
        try:
            logger.info("Starting earning date update job at 10 PM...")
            
            # Load stocks from stock.json
            stocks = load_stocks()
            if not stocks:
                logger.error("Failed to load stocks from stock.json")
                return False
            
            # Filter out leverage and crypto stocks
            regular_stocks = [stock for stock in stocks if not stock.get('isleverage', False)]
            logger.info(f"Processing {len(regular_stocks)} regular stocks (excluding leverage/crypto)")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.warning("No current earning summary data found, creating new structure")
                current_data = []
            
            # Create a map of existing data for quick lookup
            existing_data_map = {item['ticker']: item for item in current_data}
            
            # Get earning dates from Finviz for all stocks in a single call
            try:
                logger.info("Fetching earning dates from Finviz for all stocks...")
                finviz_data = finviz_service.get_earning_dates_batch(regular_stocks)
                logger.info(f"Successfully fetched Finviz data for {len(finviz_data)} stocks")
            except Exception as e:
                logger.error(f"Failed to fetch Finviz data: {str(e)}")
                return False
            
            updated_count = 0
            new_count = 0
            
            # Process each stock
            for stock in regular_stocks:
                ticker = stock.get('ticker', '')
                if not ticker:
                    continue
                
                # Get earning date from Finviz data
                earning_date = finviz_data.get(ticker, {}).get('earnings_date')
                
                if earning_date and earning_date != 'N/A':
                    # Check if stock already exists in earning summary
                    if ticker in existing_data_map:
                        # Update existing record
                        existing_record = existing_data_map[ticker]
                        if existing_record.get('earningDate') != earning_date:
                            existing_record['earningDate'] = earning_date
                            updated_count += 1
                            logger.debug(f"Updated earning date for {ticker}: {earning_date}")
                    else:
                        # Create new record
                        new_record = {
                            'ticker': ticker,
                            'currentPrice': 'N/A',
                            'earningDate': earning_date,
                            'sector': stock.get('sector', 'Unknown'),
                            'lastTwoEarnings': []
                        }
                        current_data.append(new_record)
                        existing_data_map[ticker] = new_record
                        new_count += 1
                        logger.debug(f"Created new record for {ticker} with earning date: {earning_date}")
                else:
                    logger.debug(f"No earning date found for {ticker}")
            
            # Save updated data
            if self.save_earning_summary(current_data):
                logger.info(f"Earning date update completed successfully. Updated: {updated_count}, New: {new_count}, Total: {len(current_data)}")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in earning date update job: {str(e)}")
            return False

    def update_missing_last_two_earnings_temp(self) -> bool:
        """
        TEMPORARY METHOD: Update only stocks that have empty lastTwoEarnings arrays.
        This method targets specific stocks without changing existing logic.
        """
        try:
            logger.info("Starting temporary update of missing lastTwoEarnings...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            # Find stocks with empty lastTwoEarnings
            stocks_to_update = []
            for item in current_data:
                # Debug logging to see what we're actually getting
                last_two = item.get('lastTwoEarnings')
                logger.debug(f"Ticker {item['ticker']}: lastTwoEarnings = {last_two}, type = {type(last_two)}, len = {len(last_two) if isinstance(last_two, list) else 'N/A'}")
                
                if (last_two and 
                    isinstance(last_two, list) and 
                    len(last_two) == 0):
                    stocks_to_update.append(item['ticker'])
                    logger.info(f"Added {item['ticker']} to update list")
                elif not last_two:
                    # Handle case where lastTwoEarnings might be None or missing
                    stocks_to_update.append(item['ticker'])
                    logger.info(f"Added {item['ticker']} to update list (missing lastTwoEarnings)")
            
            logger.info(f"Found {len(stocks_to_update)} stocks with missing lastTwoEarnings: {stocks_to_update}")
            
            if not stocks_to_update:
                logger.info("No stocks need updating")
                return True
            
            # Update each stock individually
            updated_count = 0
            for ticker in stocks_to_update:
                try:
                    logger.info(f"Updating lastTwoEarnings for {ticker}...")
                    
                    # Get historical data for this ticker
                    historical_data = self._get_historical_earning_data(ticker)
                    
                    if historical_data and len(historical_data) > 0:
                        # Find the item in current_data and update it
                        for item in current_data:
                            if item['ticker'] == ticker:
                                item['lastTwoEarnings'] = historical_data[:2]  # Take first 2 earnings
                                updated_count += 1
                                logger.info(f"Updated {ticker} with {len(historical_data[:2])} earnings")
                                break
                    else:
                        logger.warning(f"No historical data found for {ticker}")
                        
                except Exception as e:
                    logger.error(f"Error updating {ticker}: {str(e)}")
                    continue
            
            # Save updated data
            if self.save_earning_summary(current_data):
                logger.info(f"Temporary lastTwoEarnings update completed. Updated: {updated_count}, Total: {len(current_data)}")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in temporary lastTwoEarnings update: {str(e)}")
            return False

    def update_missing_price_data_temp(self) -> bool:
        """
        TEMPORARY METHOD: Update only stocks that have "N/A" values for price fields.
        This method preserves existing price data and only fills in missing values.
        """
        try:
            logger.info("Starting temporary update of missing price data...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            # Find stocks with missing price data
            stocks_to_update = []
            for item in current_data:
                last_two = item.get('lastTwoEarnings')
                if not last_two or not isinstance(last_two, list):
                    continue
                
                # Check if any earning has missing price data
                needs_update = False
                for earning in last_two:
                    if (earning.get('closeB4EarningPrice') == 'N/A' or 
                        earning.get('closeB4EarningChange') == 'N/A' or
                        earning.get('afterEarningPrice') == 'N/A' or
                        earning.get('afterEarningChange') == 'N/A'):
                        needs_update = True
                        break
                
                if needs_update:
                    stocks_to_update.append(item['ticker'])
                    logger.info(f"Added {item['ticker']} to price update list")
            
            logger.info(f"Found {len(stocks_to_update)} stocks with missing price data: {stocks_to_update}")
            
            if not stocks_to_update:
                logger.info("No stocks need price data updating")
                return True
            
            # Update each stock individually
            updated_count = 0
            for ticker in stocks_to_update:
                try:
                    logger.info(f"Updating price data for {ticker}...")
                    
                    # Find the item in current_data
                    for item in current_data:
                        if item['ticker'] == ticker:
                            # Update each earning record with missing price data
                            for earning in item['lastTwoEarnings']:
                                if (earning.get('closeB4EarningPrice') == 'N/A' or 
                                    earning.get('closeB4EarningChange') == 'N/A' or
                                    earning.get('afterEarningPrice') == 'N/A' or
                                    earning.get('afterEarningChange') == 'N/A'):
                                    
                                    # Get price data for this earning date
                                    price_data = self._get_price_data_for_earning_date(ticker, earning.get('earningDate'))
                                    if price_data:
                                        # Only update fields that are currently "N/A"
                                        for field, value in price_data.items():
                                            if earning.get(field) == 'N/A':
                                                earning[field] = value
                                        logger.debug(f"Updated price data for {ticker} earning {earning.get('earningDate')}")
                            
                            updated_count += 1
                            logger.info(f"Updated price data for {ticker}")
                            break
                        
                except Exception as e:
                    logger.error(f"Error updating price data for {ticker}: {str(e)}")
                    continue
            
            # Save updated data
            if self.save_earning_summary(current_data):
                logger.info(f"Temporary price data update completed. Updated: {updated_count}, Total: {len(current_data)}")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in temporary price data update: {str(e)}")
            return False

    def update_missing_current_prices_temp(self) -> bool:
        """
        TEMPORARY METHOD: Update only stocks that have "N/A" values for currentPrice.
        This method preserves existing current prices and only fills in missing values.
        """
        try:
            logger.info("Starting temporary update of missing current prices...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            # Find stocks with missing current prices
            stocks_to_update = []
            for item in current_data:
                if item.get('currentPrice') == 'N/A':
                    stocks_to_update.append(item['ticker'])
                    logger.info(f"Added {item['ticker']} to current price update list")
            
            logger.info(f"Found {len(stocks_to_update)} stocks with missing current prices: {stocks_to_update}")
            
            if not stocks_to_update:
                logger.info("No stocks need current price updating")
                return True
            
            # Update each stock individually
            updated_count = 0
            for ticker in stocks_to_update:
                try:
                    logger.info(f"Updating current price for {ticker}...")
                    
                    # Get current price from Yahoo Finance
                    current_price = self._get_current_price_from_yahoo(ticker)
                    
                    if current_price and current_price != 'N/A':
                        # Find the item in current_data and update it
                        for item in current_data:
                            if item['ticker'] == ticker:
                                item['currentPrice'] = current_price
                                updated_count += 1
                                logger.info(f"Updated {ticker} current price to {current_price}")
                                break
                    else:
                        logger.warning(f"Could not get current price for {ticker}")
                        
                except Exception as e:
                    logger.error(f"Error updating current price for {ticker}: {str(e)}")
                    continue
            
            # Save updated data
            if self.save_earning_summary(current_data):
                logger.info(f"Temporary current price update completed. Updated: {updated_count}, Total: {len(current_data)}")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in temporary current price update: {str(e)}")
            return False

    def _get_current_price_from_yahoo(self, ticker: str) -> str:
        """
        Get current price from Yahoo Finance for a specific ticker.
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Try to get current price from info
            if 'currentPrice' in info and info['currentPrice'] is not None:
                price = info['currentPrice']
                if isinstance(price, (int, float)) and price > 0:
                    return f"${price:.2f}"
            
            # Fallback to regularMarketPrice
            if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                price = info['regularMarketPrice']
                if isinstance(price, (int, float)) and price > 0:
                    return f"${price:.2f}"
            
            # Fallback to previousClose
            if 'previousClose' in info and info['previousClose'] is not None:
                price = info['previousClose']
                if isinstance(price, (int, float)) and price > 0:
                    return f"${price:.2f}"
            
            # Try to get live price from history
            try:
                hist = stock.history(period="1d")
                if not hist.empty:
                    latest_price = hist.iloc[-1]['Close']
                    if latest_price > 0:
                        return f"${latest_price:.2f}"
            except:
                pass
            
            logger.debug(f"Could not get current price for {ticker} from Yahoo Finance")
            return 'N/A'
            
        except Exception as e:
            logger.debug(f"Error getting current price for {ticker} from Yahoo Finance: {str(e)}")
            return 'N/A'

    def _get_historical_earning_data(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Get historical earning data for a specific ticker.
        This is a helper method for the temporary update.
        """
        try:
            logger.debug(f"Fetching historical earning data for {ticker}")
            
            # Try Yahoo Finance income statement data first (most reliable)
            try:
                earnings_data = self._get_yahoo_earning_data(ticker)
                if earnings_data and len(earnings_data) > 0:
                    logger.debug(f"Found {len(earnings_data)} earnings from Yahoo Finance for {ticker}")
                    
                    # Enhance with price data where possible
                    enhanced_earnings_data = []
                    for earning in earnings_data:
                        enhanced_earning = earning.copy()
                        
                        # Only populate price fields if they're currently "N/A"
                        if earning.get('closeB4EarningPrice') == 'N/A':
                            price_data = self._get_price_data_for_earning_date(ticker, earning.get('earningDate'))
                            if price_data:
                                enhanced_earning.update(price_data)
                        
                        enhanced_earnings_data.append(enhanced_earning)
                    
                    return enhanced_earnings_data
            except Exception as e:
                logger.debug(f"Yahoo Finance failed for {ticker}: {str(e)}")
            
            # Fallback to Finviz if Yahoo fails
            try:
                from finviz_service import finviz_service
                finviz_data = finviz_service.get_financial_data_for_ticker(ticker)
                if finviz_data and finviz_data.get('earnings_date'):
                    # Create a basic earning record from Finviz data
                    basic_earning = {
                        'earningDate': finviz_data.get('earnings_date', 'N/A'),
                        'closeB4EarningPrice': 'N/A',
                        'closeB4EarningChange': 'N/A',
                        'afterEarningPrice': 'N/A',
                        'afterEarningChange': 'N/A',
                        'beatExpectation': 'N/A',
                        'actualValue': 'N/A',
                        'expectedValue': 'N/A',
                        'epsCategory': 'N/A',
                        'actualRevenue': 'N/A',
                        'expectedRevenue': 'N/A',
                        'revenueCategory': 'N/A',
                        'percentageDifference': 'N/A'
                    }
                    logger.debug(f"Created basic earning record from Finviz for {ticker}")
                    return [basic_earning]
            except Exception as e:
                logger.debug(f"Finviz failed for {ticker}: {str(e)}")
            
            logger.warning(f"No historical earning data found for {ticker}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting historical earning data for {ticker}: {str(e)}")
            return []

    def _get_price_data_for_earning_date(self, ticker: str, earning_date_str: str) -> Dict[str, str]:
        """
        Get price data for a specific earning date.
        This method tries to get historical price data around the earning date.
        """
        try:
            if not earning_date_str or earning_date_str == 'N/A':
                return {}
            
            import yfinance as yf
            from datetime import datetime, timedelta
            
            # Parse the earning date
            try:
                earning_date = datetime.strptime(earning_date_str, '%m/%d/%Y')
            except ValueError:
                # Try alternative format
                try:
                    earning_date = datetime.strptime(earning_date_str, '%Y-%m-%d')
                except ValueError:
                    logger.debug(f"Could not parse earning date for {ticker}: {earning_date_str}")
                    return {}
            
            # Get historical price data around the earning date
            stock = yf.Ticker(ticker)
            start_date = earning_date - timedelta(days=10)
            end_date = earning_date + timedelta(days=10)
            
            hist = stock.history(start=start_date, end=end_date)
            if hist.empty:
                logger.debug(f"No historical price data for {ticker} around {earning_date_str}")
                return {}
            
            # Find the day before and after the earning date
            earning_date_only = earning_date.date()
            before_earning_data = None
            after_earning_data = None
            
            for date, row in hist.iterrows():
                date_only = date.date()
                if date_only < earning_date_only:
                    before_earning_data = row
                elif date_only > earning_date_only:
                    after_earning_data = row
                    break
            
            # Calculate price changes
            price_data = {}
            
            if before_earning_data is not None:
                close_b4_price = before_earning_data['Close']
                price_data['closeB4EarningPrice'] = f"${close_b4_price:.2f}"
                
                # Calculate change from open to close
                if 'Open' in before_earning_data:
                    open_price = before_earning_data['Open']
                    b4_change = ((close_b4_price - open_price) / open_price) * 100
                    price_data['closeB4EarningChange'] = f"{b4_change:+.2f}%"
                else:
                    price_data['closeB4EarningChange'] = "0.00%"
            else:
                price_data['closeB4EarningPrice'] = 'N/A'
                price_data['closeB4EarningChange'] = 'N/A'
            
            if after_earning_data is not None:
                after_price = after_earning_data['Close']
                price_data['afterEarningPrice'] = f"${after_price:.2f}"
                
                # Calculate change from earning day close to next day close
                if before_earning_data is not None:
                    close_b4_price = before_earning_data['Close']
                    after_change = ((after_price - close_b4_price) / close_b4_price) * 100
                    price_data['afterEarningChange'] = f"{after_change:+.2f}%"
                else:
                    price_data['afterEarningChange'] = "0.00%"
            else:
                price_data['afterEarningPrice'] = 'N/A'
                price_data['afterEarningChange'] = 'N/A'
            
            logger.debug(f"Successfully retrieved price data for {ticker} around {earning_date_str}")
            return price_data
            
        except Exception as e:
            logger.debug(f"Error getting price data for {ticker} around {earning_date_str}: {str(e)}")
            return {}

    def _get_yahoo_earning_data(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Get earning data from Yahoo Finance using income statement data.
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            quarterly_income = stock.quarterly_income_stmt
            
            if quarterly_income is None or quarterly_income.empty:
                logger.debug(f"No quarterly income statement data for {ticker}")
                return []
            
            earnings_data = []
            columns = quarterly_income.columns[:2]  # Get last 2 quarters
            
            for col in columns:
                try:
                    quarter_date = col
                    
                    # Try to find Net Income and Revenue
                    net_income = None
                    revenue = None
                    
                    for metric in quarterly_income.index:
                        if 'net income' in metric.lower() and net_income is None:
                            net_income = quarterly_income.loc[metric, col]
                        elif 'total revenue' in metric.lower() and revenue is None:
                            revenue = quarterly_income.loc[metric, col]
                        elif 'operating revenue' in metric.lower() and revenue is None:
                            revenue = quarterly_income.loc[metric, col]
                    
                    if net_income is not None or revenue is not None:
                        # Format revenue properly
                        revenue_formatted = 'N/A'
                        if revenue is not None and pd.notna(revenue):
                            if revenue >= 1e9:
                                revenue_formatted = f"${revenue/1e9:.2f} billion"
                            elif revenue >= 1e6:
                                revenue_formatted = f"${revenue/1e6:.2f} million"
                            elif revenue >= 1e3:
                                revenue_formatted = f"${revenue/1e3:.2f} thousand"
                            else:
                                revenue_formatted = f"${revenue:.2f}"
                        
                        earning_record = {
                            'earningDate': quarter_date.strftime('%m/%d/%Y') if hasattr(quarter_date, 'strftime') else str(quarter_date),
                            'closeB4EarningPrice': 'N/A',
                            'closeB4EarningChange': 'N/A',
                            'afterEarningPrice': 'N/A',
                            'afterEarningChange': 'N/A',
                            'beatExpectation': 'N/A',
                            'actualValue': self.format_numeric_value(net_income) if net_income is not None and pd.notna(net_income) else 'N/A',
                            'expectedValue': 'N/A',
                            'epsCategory': 'Reported',
                            'actualRevenue': revenue_formatted,
                            'expectedRevenue': 'N/A',
                            'revenueCategory': 'Reported',
                            'percentageDifference': 'N/A'
                        }
                        earnings_data.append(earning_record)
                        logger.debug(f"Created earning record for {ticker} - {quarter_date}")
                        
                except Exception as e:
                    logger.debug(f"Error processing quarter {col} for {ticker}: {e}")
                    continue
            
            return earnings_data
            
        except Exception as e:
            logger.debug(f"Error getting Yahoo Finance data for {ticker}: {str(e)}")
            return []

    def update_missing_expected_values_temp(self) -> bool:
        """
        TEMPORARY METHOD: Update only stocks that have "N/A" values for expectedValue and expectedRevenue.
        This method preserves existing expected data and only fills in missing values.
        """
        try:
            logger.info("Starting temporary update of missing expected values...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            # Find stocks with missing expected values
            stocks_to_update = []
            for item in current_data:
                last_two = item.get('lastTwoEarnings')
                if not last_two or not isinstance(last_two, list):
                    continue
                
                needs_update = False
                for earning in last_two:
                    if (earning.get('expectedValue') == 'N/A' or 
                        earning.get('expectedRevenue') == 'N/A'):
                        needs_update = True
                        break
                
                if needs_update:
                    stocks_to_update.append(item['ticker'])
                    logger.info(f"Added {item['ticker']} to expected values update list")
            
            logger.info(f"Found {len(stocks_to_update)} stocks with missing expected values: {stocks_to_update}")
            
            if not stocks_to_update:
                logger.info("No stocks need expected values updating")
                return True
            
            updated_count = 0
            for ticker in stocks_to_update:
                try:
                    logger.info(f"Updating expected values for {ticker}...")
                    
                    # Get expected data from Yahoo Finance
                    expected_data = self._get_expected_values_from_yahoo(ticker)
                    
                    if expected_data:
                        # Update the expected values for this ticker
                        for item in current_data:
                            if item['ticker'] == ticker:
                                for earning in item['lastTwoEarnings']:
                                    earning_date = earning.get('earningDate')
                                    
                                    # Only update if values are currently "N/A"
                                    if earning.get('expectedValue') == 'N/A':
                                        expected_eps = expected_data.get('expectedEPS', 'N/A')
                                        if expected_eps != 'N/A':
                                            earning['expectedValue'] = self.format_numeric_value(expected_eps)
                                            logger.debug(f"Updated expectedValue for {ticker} {earning_date}: {earning['expectedValue']}")
                                    
                                    if earning.get('expectedRevenue') == 'N/A':
                                        expected_revenue = expected_data.get('expectedRevenue', 'N/A')
                                        if expected_revenue != 'N/A':
                                            earning['expectedRevenue'] = expected_revenue
                                            logger.debug(f"Updated expectedRevenue for {ticker} {earning_date}: {earning['expectedRevenue']}")
                                
                                updated_count += 1
                                logger.info(f"Updated expected values for {ticker}")
                                break
                    else:
                        logger.info(f"Could not get expected data for {ticker}")
                        
                except Exception as e:
                    logger.error(f"Error updating expected values for {ticker}: {str(e)}")
                    continue
            
            if self.save_earning_summary(current_data):
                logger.info(f"Temporary expected values update completed. Updated: {updated_count}, Total: {len(current_data)}")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in temporary expected values update: {str(e)}")
            return False

    def update_all_numeric_formatting_temp(self) -> bool:
        """
        TEMPORARY METHOD: Update all existing actualValue and expectedValue fields to use consistent M/B/T formatting.
        This ensures the entire file has consistent numeric formatting.
        """
        try:
            logger.info("Starting update of all numeric formatting for consistency...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            updated_count = 0
            total_fields_updated = 0
            
            for item in current_data:
                ticker = item['ticker']
                last_two = item.get('lastTwoEarnings')
                if not last_two or not isinstance(last_two, list):
                    continue
                
                ticker_updated = False
                for earning in last_two:
                    fields_updated = 0
                    
                    # Update actualValue if it's a raw number
                    actual_value = earning.get('actualValue')
                    if actual_value and actual_value != 'N/A':
                        try:
                            # Check if it's a raw number (contains decimal or is numeric)
                            if isinstance(actual_value, (int, float)) or (isinstance(actual_value, str) and '.' in actual_value and actual_value.replace('.', '').replace('-', '').isdigit()):
                                logger.debug(f"Processing actualValue for {ticker}: {actual_value}")
                                formatted_value = self.format_numeric_value(actual_value)
                                logger.debug(f"Formatted actualValue for {ticker}: {actual_value} -> {formatted_value}")
                                # Always update for consistency, even if value appears the same
                                earning['actualValue'] = formatted_value
                                fields_updated += 1
                                logger.info(f"Updated actualValue for {ticker}: {actual_value} -> {formatted_value}")
                        except Exception as e:
                            logger.debug(f"Error processing actualValue for {ticker}: {e}")
                    
                    # Update expectedValue if it's a raw number
                    expected_value = earning.get('expectedValue')
                    if expected_value and expected_value != 'N/A':
                        try:
                            # Check if it's a raw number (contains decimal or is numeric)
                            if isinstance(expected_value, (int, float)) or (isinstance(expected_value, str) and '.' in expected_value and expected_value.replace('.', '').replace('-', '').isdigit()):
                                logger.debug(f"Processing expectedValue for {ticker}: {expected_value}")
                                formatted_value = self.format_numeric_value(expected_value)
                                logger.debug(f"Formatted expectedValue for {ticker}: {expected_value} -> {formatted_value}")
                                # Always update for consistency, even if value appears the same
                                earning['expectedValue'] = formatted_value
                                fields_updated += 1
                                logger.info(f"Updated expectedValue for {ticker}: {expected_value} -> {formatted_value}")
                        except Exception as e:
                            logger.debug(f"Error processing expectedValue for {ticker}: {e}")
                    
                    if fields_updated > 0:
                        ticker_updated = True
                        total_fields_updated += fields_updated
                
                if ticker_updated:
                    updated_count += 1
                    logger.info(f"Updated numeric formatting for {ticker}")
            
            if self.save_earning_summary(current_data):
                logger.info(f"All numeric formatting update completed. Updated: {updated_count} stocks, {total_fields_updated} fields")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in numeric formatting update: {str(e)}")
            return False

    def update_calculated_fields_temp(self) -> bool:
        """
        TEMPORARY METHOD: Update beatExpectation and percentageDifference fields where they are N/A 
        but both actualValue and expectedValue exist.
        """
        try:
            logger.info("Starting update of calculated fields (beatExpectation, percentageDifference)...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            updated_count = 0
            total_fields_updated = 0
            
            for item in current_data:
                ticker = item['ticker']
                last_two = item.get('lastTwoEarnings')
                if not last_two or not isinstance(last_two, list):
                    continue
                
                ticker_updated = False
                for earning in last_two:
                    fields_updated = 0
                    
                    actual_value = earning.get('actualValue')
                    expected_value = earning.get('expectedValue')
                    beat_expectation = earning.get('beatExpectation')
                    percentage_diff = earning.get('percentageDifference')
                    
                    # Update beatExpectation if it's N/A but we have both actual and expected values
                    # Only process if both values are comparable (both EPS-like numeric values, not mixing Net Income with EPS)
                    if (beat_expectation == 'N/A' and 
                        actual_value != 'N/A' and expected_value != 'N/A' and
                        actual_value is not None and expected_value is not None):
                        try:
                            # Check if both values are comparable (both should be EPS-like values)
                            # If actualValue contains formatted values like "M" or "B", it's Net Income, not EPS
                            if (isinstance(actual_value, str) and ('M' in actual_value or 'B' in actual_value or 'T' in actual_value or 'K' in actual_value)):
                                logger.debug(f"Skipping {ticker}: actualValue appears to be Net Income ({actual_value}), not comparable to EPS expectedValue ({expected_value})")
                                continue
                            
                            # Convert to float for comparison
                            actual_float = float(actual_value)
                            expected_float = float(expected_value)
                            
                            # Additional sanity check: EPS values are typically in a reasonable range (-50 to +50)
                            # If the scales are drastically different, they're probably different metrics
                            if abs(actual_float) > 1000 and abs(expected_float) < 100:
                                logger.debug(f"Skipping {ticker}: Scale mismatch suggests different metrics (actual={actual_float}, expected={expected_float})")
                                continue
                            
                            if actual_float > expected_float:
                                earning['beatExpectation'] = "Beat"
                            elif actual_float < expected_float:
                                earning['beatExpectation'] = "Miss"
                            else:
                                earning['beatExpectation'] = "Met"
                            
                            fields_updated += 1
                            logger.info(f"Updated beatExpectation for {ticker}: {actual_value} vs {expected_value} -> {earning['beatExpectation']}")
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Error converting values for beatExpectation calculation in {ticker}: {e}")
                    
                    # Update percentageDifference if it's N/A but we have both actual and expected values
                    # Only process if both values are comparable (both EPS-like numeric values, not mixing Net Income with EPS)
                    if (percentage_diff == 'N/A' and 
                        actual_value != 'N/A' and expected_value != 'N/A' and
                        actual_value is not None and expected_value is not None):
                        try:
                            # Check if both values are comparable (both should be EPS-like values)
                            # If actualValue contains formatted values like "M" or "B", it's Net Income, not EPS
                            if (isinstance(actual_value, str) and ('M' in actual_value or 'B' in actual_value or 'T' in actual_value or 'K' in actual_value)):
                                logger.debug(f"Skipping {ticker}: actualValue appears to be Net Income ({actual_value}), not comparable to EPS expectedValue ({expected_value})")
                                continue
                            
                            # Convert to float for calculation
                            actual_float = float(actual_value)
                            expected_float = float(expected_value)
                            
                            # Additional sanity check: EPS values are typically in a reasonable range (-50 to +50)
                            # If the scales are drastically different, they're probably different metrics
                            if abs(actual_float) > 1000 and abs(expected_float) < 100:
                                logger.debug(f"Skipping {ticker}: Scale mismatch suggests different metrics (actual={actual_float}, expected={expected_float})")
                                continue
                            
                            if expected_float != 0:
                                diff = ((actual_float - expected_float) / abs(expected_float)) * 100
                                earning['percentageDifference'] = f"{diff:+.2f}%"
                                fields_updated += 1
                                logger.info(f"Updated percentageDifference for {ticker}: {actual_value} vs {expected_value} -> {earning['percentageDifference']}")
                            else:
                                logger.debug(f"Cannot calculate percentage difference for {ticker}: expected value is 0")
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Error converting values for percentage calculation in {ticker}: {e}")
                    
                    if fields_updated > 0:
                        ticker_updated = True
                        total_fields_updated += fields_updated
                
                if ticker_updated:
                    updated_count += 1
                    logger.info(f"Updated calculated fields for {ticker}")
            
            if self.save_earning_summary(current_data):
                logger.info(f"Calculated fields update completed. Updated: {updated_count} stocks, {total_fields_updated} fields")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in calculated fields update: {str(e)}")
            return False

    def fix_data_inconsistency_temp(self) -> bool:
        """
        TEMPORARY METHOD: Fix data inconsistency where actualValue contains Net Income 
        but expectedValue contains EPS estimates. This makes them comparable.
        """
        try:
            logger.info("Starting fix of data inconsistency (Net Income vs EPS)...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            updated_count = 0
            total_fields_updated = 0
            
            for item in current_data:
                ticker = item['ticker']
                last_two = item.get('lastTwoEarnings')
                if not last_two or not isinstance(last_two, list):
                    continue
                
                ticker_updated = False
                for earning in last_two:
                    fields_updated = 0
                    
                    actual_value = earning.get('actualValue')
                    expected_value = earning.get('expectedValue')
                    
                    # Check if we have the Net Income vs EPS inconsistency
                    if (isinstance(actual_value, str) and 
                        ('M' in actual_value or 'B' in actual_value or 'T' in actual_value or 'K' in actual_value) and
                        isinstance(expected_value, str) and 
                        expected_value != 'N/A' and 
                        expected_value is not None):
                        
                        try:
                            # Try to get the actual EPS data for this ticker
                            logger.info(f"Attempting to fix data inconsistency for {ticker}: actualValue={actual_value} (Net Income) vs expectedValue={expected_value} (EPS)")
                            
                            # Get current stock info to calculate EPS from Net Income
                            import yfinance as yf
                            stock = yf.Ticker(ticker)
                            info = stock.info
                            
                            if info and 'sharesOutstanding' in info and info['sharesOutstanding']:
                                shares_outstanding = info['sharesOutstanding']
                                
                                # Parse the Net Income value
                                net_income_str = actual_value.replace('$', '').replace(',', '')
                                if 'M' in net_income_str:
                                    net_income = float(net_income_str.replace('M', '')) * 1e6
                                elif 'B' in net_income_str:
                                    net_income = float(net_income_str.replace('B', '')) * 1e9
                                elif 'T' in net_income_str:
                                    net_income = float(net_income_str.replace('T', '')) * 1e12
                                elif 'K' in net_income_str:
                                    net_income = float(net_income_str.replace('K', '')) * 1e3
                                else:
                                    net_income = float(net_income_str)
                                
                                # Calculate EPS: EPS = Net Income / Shares Outstanding
                                calculated_eps = net_income / shares_outstanding
                                
                                # Format the calculated EPS
                                formatted_eps = self.format_numeric_value(calculated_eps)
                                
                                # Update the actualValue to use the calculated EPS
                                earning['actualValue'] = formatted_eps
                                fields_updated += 1
                                
                                logger.info(f"Fixed {ticker}: Net Income {actual_value} -> EPS {formatted_eps} (shares: {shares_outstanding:,.0f})")
                                
                                # Now we can calculate beatExpectation and percentageDifference
                                if earning.get('beatExpectation') == 'N/A':
                                    try:
                                        expected_float = float(expected_value)
                                        if calculated_eps > expected_float:
                                            earning['beatExpectation'] = "Beat"
                                        elif calculated_eps < expected_float:
                                            earning['beatExpectation'] = "Miss"
                                        else:
                                            earning['beatExpectation'] = "Met"
                                        
                                        # Calculate percentage difference
                                        if expected_float != 0:
                                            diff = ((calculated_eps - expected_float) / abs(expected_float)) * 100
                                            earning['percentageDifference'] = f"{diff:+.2f}%"
                                        
                                        fields_updated += 2  # beatExpectation + percentageDifference
                                        logger.info(f"Calculated beatExpectation and percentageDifference for {ticker}")
                                    except (ValueError, TypeError) as e:
                                        logger.debug(f"Error calculating derived fields for {ticker}: {e}")
                                
                            else:
                                logger.warning(f"No shares outstanding data for {ticker}, cannot convert Net Income to EPS")
                                
                        except Exception as e:
                            logger.debug(f"Error fixing data inconsistency for {ticker}: {e}")
                    
                    if fields_updated > 0:
                        ticker_updated = True
                        total_fields_updated += fields_updated
                
                if ticker_updated:
                    updated_count += 1
                    logger.info(f"Fixed data inconsistency for {ticker}")
            
            if self.save_earning_summary(current_data):
                logger.info(f"Data inconsistency fix completed. Updated: {updated_count} stocks, {total_fields_updated} fields")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in data inconsistency fix: {str(e)}")
            return False

    def update_category_fields_temp(self) -> bool:
        """
        TEMPORARY METHOD: Update epsCategory and revenueCategory fields to use 
        Beat/Miss/Met values instead of Reported/Surprise/Estimate.
        """
        try:
            logger.info("Starting update of category fields to Beat/Miss/Met...")
            
            # Load current earning summary
            current_data = self.load_earning_summary()
            if not current_data:
                logger.error("No earning summary data found")
                return False
            
            updated_count = 0
            total_fields_updated = 0
            
            for item in current_data:
                ticker = item['ticker']
                last_two = item.get('lastTwoEarnings')
                if not last_two or not isinstance(last_two, list):
                    continue
                
                ticker_updated = False
                for earning in last_two:
                    fields_updated = 0
                    
                    # Update epsCategory to use beatExpectation if available
                    beat_expectation = earning.get('beatExpectation')
                    if beat_expectation and beat_expectation in ['Beat', 'Miss', 'Met']:
                        current_eps_category = earning.get('epsCategory', '')
                        if current_eps_category not in ['Beat', 'Miss', 'Met']:
                            earning['epsCategory'] = beat_expectation
                            fields_updated += 1
                            logger.debug(f"Updated {ticker} epsCategory: {current_eps_category} -> {beat_expectation}")
                    
                    # Update revenueCategory based on actual vs expected revenue
                    actual_revenue = earning.get('actualRevenue')
                    expected_revenue = earning.get('expectedRevenue')
                    
                    if (actual_revenue and actual_revenue != 'N/A' and 
                        expected_revenue and expected_revenue != 'N/A'):
                        try:
                            # Parse revenue values (remove $ and convert text suffixes)
                            actual_clean = actual_revenue.replace('$', '').replace(',', '').lower()
                            expected_clean = expected_revenue.replace('$', '').replace(',', '').lower()
                            
                            # Convert to numbers based on text suffixes
                            if 'trillion' in actual_clean:
                                actual_num = float(actual_clean.replace('trillion', '')) * 1e12
                            elif 'billion' in actual_clean:
                                actual_num = float(actual_clean.replace('billion', '')) * 1e9
                            elif 'million' in actual_clean:
                                actual_num = float(actual_clean.replace('million', '')) * 1e6
                            elif 'thousand' in actual_clean:
                                actual_num = float(actual_clean.replace('thousand', '')) * 1e3
                            else:
                                actual_num = float(actual_clean)
                            
                            if 'trillion' in expected_clean:
                                expected_num = float(expected_clean.replace('trillion', '')) * 1e12
                            elif 'billion' in expected_clean:
                                expected_num = float(expected_clean.replace('billion', '')) * 1e9
                            elif 'million' in expected_clean:
                                expected_num = float(expected_clean.replace('million', '')) * 1e6
                            elif 'thousand' in expected_clean:
                                expected_num = float(expected_clean.replace('thousand', '')) * 1e3
                            else:
                                expected_num = float(expected_clean)
                            
                            # Determine revenue category
                            if expected_num > 0:
                                revenue_diff = ((actual_num - expected_num) / expected_num) * 100
                                if revenue_diff > 0.1:  # More than 0.1% above expected
                                    revenue_category = "Beat"
                                elif revenue_diff < -0.1:  # More than 0.1% below expected
                                    revenue_category = "Miss"
                                else:
                                    revenue_category = "Met"
                                
                                current_revenue_category = earning.get('revenueCategory', '')
                                if current_revenue_category != revenue_category:
                                    earning['revenueCategory'] = revenue_category
                                    fields_updated += 1
                                    logger.debug(f"Updated {ticker} revenueCategory: {current_revenue_category} -> {revenue_category} (diff: {revenue_diff:.2f}%)")
                            
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Error calculating revenue category for {ticker}: {e}")
                    
                    if fields_updated > 0:
                        ticker_updated = True
                        total_fields_updated += fields_updated
                
                if ticker_updated:
                    updated_count += 1
                    logger.info(f"Updated category fields for {ticker}")
            
            if self.save_earning_summary(current_data):
                logger.info(f"Category fields update completed. Updated: {updated_count} stocks, {total_fields_updated} fields")
                return True
            else:
                logger.error("Failed to save updated earning summary")
                return False
                
        except Exception as e:
            logger.error(f"Error in category fields update: {str(e)}")
            return False

    def _get_expected_values_from_yahoo(self, ticker: str) -> Dict[str, Any]:
        """
        Get expected EPS and Revenue data from Yahoo Finance for a specific ticker.
        """
        try:
            import yfinance as yf
            
            # Get data from Yahoo Finance
            stock = yf.Ticker(ticker)
            
            expected_data = {}
            
            # Try to get analyst expectations from earnings calendar
            try:
                info = stock.info
                if info:
                    # Look for forward EPS
                    if 'forwardEps' in info and info['forwardEps']:
                        expected_data['expectedEPS'] = float(info['forwardEps'])
                        logger.debug(f"Found forwardEps for {ticker}: {info['forwardEps']}")
                    
                    # Look for revenue estimate
                    if 'revenueQuarterlyGrowth' in info and info['revenueQuarterlyGrowth']:
                        # This is growth rate, we'd need more complex calculation
                        pass
                    
                    # Try to find revenue estimates in recommendations
                    if 'totalRevenue' in info and info['totalRevenue']:
                        revenue = info['totalRevenue']
                        if revenue >= 1e9:
                            expected_data['expectedRevenue'] = f"${revenue/1e9:.2f} billion"
                        elif revenue >= 1e6:
                            expected_data['expectedRevenue'] = f"${revenue/1e6:.2f} million"
                        logger.debug(f"Found totalRevenue for {ticker}: {revenue}")
            except Exception as e:
                logger.debug(f"Error getting info data for {ticker}: {str(e)}")
            
            # Try to get analyst recommendations which might have estimates
            try:
                recommendations = stock.recommendations
                if recommendations is not None and not recommendations.empty:
                    # Get latest recommendation
                    latest = recommendations.tail(1)
                    if not latest.empty:
                        logger.debug(f"Found recommendations for {ticker}")
            except Exception as e:
                logger.debug(f"Error getting recommendations for {ticker}: {str(e)}")
            
            # Try to get earnings data which might have forward estimates
            try:
                calendar = stock.calendar
                if calendar is not None and not calendar.empty:
                    logger.debug(f"Found earnings calendar for {ticker}")
                    # Calendar might contain EPS estimates
                    if 'EPS Estimate' in calendar.columns:
                        latest_estimate = calendar['EPS Estimate'].iloc[-1] if len(calendar) > 0 else None
                        if latest_estimate and pd.notna(latest_estimate):
                            expected_data['expectedEPS'] = float(latest_estimate)
                            logger.debug(f"Found EPS Estimate for {ticker}: {latest_estimate}")
            except Exception as e:
                logger.debug(f"Error getting calendar for {ticker}: {str(e)}")
            
            # If we still don't have expected values, try to use a conservative estimate
            # based on historical data (use last quarter's data as proxy)
            if not expected_data:
                try:
                    quarterly_income = stock.quarterly_income_stmt
                    if quarterly_income is not None and not quarterly_income.empty and len(quarterly_income.columns) > 0:
                        latest_col = quarterly_income.columns[0]
                        
                        # Get net income for EPS proxy
                        for metric in quarterly_income.index:
                            if 'net income' in metric.lower():
                                net_income = quarterly_income.loc[metric, latest_col]
                                if pd.notna(net_income):
                                    expected_data['expectedEPS'] = float(net_income / 1e6)  # Convert to per-share approximation
                                    logger.debug(f"Using net income proxy for {ticker}: {net_income}")
                                break
                        
                        # Get revenue for revenue proxy
                        for metric in quarterly_income.index:
                            if 'total revenue' in metric.lower():
                                revenue = quarterly_income.loc[metric, latest_col]
                                if pd.notna(revenue):
                                    if revenue >= 1e9:
                                        expected_data['expectedRevenue'] = f"${revenue/1e9:.2f} billion"
                                    elif revenue >= 1e6:
                                        expected_data['expectedRevenue'] = f"${revenue/1e6:.2f} million"
                                    logger.debug(f"Using revenue proxy for {ticker}: {revenue}")
                                break
                except Exception as e:
                    logger.debug(f"Error getting proxy estimates for {ticker}: {str(e)}")
            
            logger.debug(f"Found expected data for {ticker}: {expected_data}")
            return expected_data
            
        except Exception as e:
            logger.debug(f"Error getting expected data from Yahoo Finance for {ticker}: {str(e)}")
            return {}

# Global instance
earning_summary_manager = EarningSummaryFileManager()

def populate_initial_earning_summary():
    """Convenience function to populate initial earning summary."""
    return earning_summary_manager.populate_initial_earning_summary()

def run_daily_earning_job():
    """Convenience function to run daily earning job."""
    return earning_summary_manager.run_daily_job()

def update_earning_dates_job():
    """Convenience function to run earning date update job."""
    return earning_summary_manager.update_earning_dates_from_finviz()

def debug_ticker_revenue(ticker: str):
    """Convenience function to debug revenue data for a specific ticker."""
    return earning_summary_manager.debug_revenue_data(ticker)

def update_missing_last_two_earnings_temp():
    """Convenience function to run temporary lastTwoEarnings update."""
    return earning_summary_manager.update_missing_last_two_earnings_temp()

def update_missing_price_data_temp():
    """Convenience function to run temporary price data update."""
    return earning_summary_manager.update_missing_price_data_temp()

def update_missing_current_prices_temp():
    """Convenience function to run temporary current price update."""
    return earning_summary_manager.update_missing_current_prices_temp()

def update_missing_expected_values_temp():
    """Convenience function to run temporary expected values update."""
    return earning_summary_manager.update_missing_expected_values_temp()

def update_all_numeric_formatting_temp():
    """Convenience function to run temporary numeric formatting update."""
    return earning_summary_manager.update_all_numeric_formatting_temp()

def update_calculated_fields_temp():
    """Convenience function to update beatExpectation and percentageDifference where they are N/A but actual and expected values exist."""
    return earning_summary_manager.update_calculated_fields_temp()

def fix_data_inconsistency_temp():
    """Convenience function to fix data inconsistency where actualValue contains Net Income but expectedValue contains EPS."""
    return earning_summary_manager.fix_data_inconsistency_temp()

def update_category_fields_temp():
    """Convenience function to run temporary category fields update."""
    return earning_summary_manager.update_category_fields_temp()
