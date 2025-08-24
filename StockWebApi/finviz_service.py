"""
Finviz Service for fetching financial data including revenue and EPS information.

This service provides an alternative data source when Yahoo Finance fails to provide
revenue and EPS data. It uses Finviz's CSV export API to fetch comprehensive financial metrics.
"""

import requests
import logging
from typing import Dict, Any, Optional, List
from config import config

# Configure logging
logger = logging.getLogger(__name__)

class FinvizService:
    """Service for fetching financial data from Finviz API"""
    
    def __init__(self):
        self.base_url = "https://elite.finviz.com/export.ashx"
        self.auth_id = config.FINVIZ_AUTH_ID
        
    def get_financial_data_for_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive financial data for a single ticker including revenue and EPS.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary containing financial data or empty dict if failed
        """
        try:
            if not self.auth_id:
                logger.warning("FINVIZ_AUTH_ID not configured, skipping Finviz data fetch")
                return {}
            
            # Use view 152 with comprehensive columns for financial data
            # Columns include: Ticker, Market Cap, P/E, Price, Change, Volume, 
            # Earnings Date, Revenue, EPS, Forward P/E, PEG, Debt/Eq, Profit Margin
            params = {
                'v': '152',  # View 152
                't': ticker,
                'c': '1,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,199,200',
                'auth': self.auth_id
            }
            
            logger.info(f"Fetching Finviz financial data for {ticker}")
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Finviz API request failed for {ticker} with status {response.status_code}")
                return {}
            
            # Parse CSV response
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                logger.warning(f"Finviz API returned insufficient data for {ticker}")
                return {}
            
            # Parse header to get column indices
            header = lines[0].split(',')
            column_map = {}
            for i, col in enumerate(header):
                column_map[col.strip()] = i
            
            # Parse data row
            values = lines[1].split(',')
            if len(values) < len(header):
                logger.warning(f"Data row too short for {ticker}")
                return {}
            
            # Extract financial data using column mapping
            financial_data = {
                'ticker': ticker,
                'price': self._extract_value(values, column_map, '"Price"'),
                'change': self._extract_value(values, column_map, '"Change"'),
                'market_cap': self._extract_value(values, column_map, '"Market Cap"'),
                'pe_ratio': self._extract_value(values, column_map, '"P/E"'),
                'forward_pe': self._extract_value(values, column_map, '"Forward P/E"'),
                'peg_ratio': self._extract_value(values, column_map, '"PEG"'),
                'debt_to_equity': self._extract_value(values, column_map, '"Debt/Eq"'),
                'profit_margin': self._extract_value(values, column_map, '"Profit M"'),
                'operating_margin': self._extract_value(values, column_map, '"Oper. Margin"'),
                'roa': self._extract_value(values, column_map, '"ROA"'),
                'roe': self._extract_value(values, column_map, '"ROE"'),
                'roi': self._extract_value(values, column_map, '"ROI"'),
                'revenue': self._extract_value(values, column_map, '"Sales Q/Q"'),
                'revenue_growth': self._extract_value(values, column_map, '"Sales Q/Q"'),
                'earnings_growth': self._extract_value(values, column_map, '"Earnings Q/Q"'),
                'earnings_date': self._extract_value(values, column_map, '"Earnings"'),
                'volume': self._extract_value(values, column_map, '"Volume"'),
                'avg_volume': self._extract_value(values, column_map, '"Avg Volume"'),
                'shares_outstanding': self._extract_value(values, column_map, '"Shs Outstand"'),
                'shares_float': self._extract_value(values, column_map, '"Shs Float"'),
                'insider_ownership': self._extract_value(values, column_map, '"Insider Own"'),
                'institutional_ownership': self._extract_value(values, column_map, '"Inst Own"'),
                'short_ratio': self._extract_value(values, column_map, '"Short Ratio"'),
                'current_ratio': self._extract_value(values, column_map, '"Current Ratio"'),
                'quick_ratio': self._extract_value(values, column_map, '"Quick Ratio"'),
                'debt_to_equity': self._extract_value(values, column_map, '"Debt/Eq"'),
                'lt_debt_to_equity': self._extract_value(values, column_map, '"LT Debt/Eq"'),
                'beta': self._extract_value(values, column_map, '"Beta"'),
                'atr': self._extract_value(values, column_map, '"ATR"'),
                'rsi': self._extract_value(values, column_map, '"RSI (14)"'),
                'gap': self._extract_value(values, column_map, '"Gap"'),
                'recom': self._extract_value(values, column_map, '"Recom"'),
                'target_price': self._extract_value(values, column_map, '"Target Price"'),
                'price_to_book': self._extract_value(values, column_map, '"P/B"'),
                'price_to_sales': self._extract_value(values, column_map, '"P/S"'),
                'price_to_cash': self._extract_value(values, column_map, '"P/C"'),
                'price_to_free_cash': self._extract_value(values, column_map, '"P/FCF"'),
                'ev_to_ebitda': self._extract_value(values, column_map, '"EV/EBITDA"'),
                'ev_to_revenue': self._extract_value(values, column_map, '"EV/Revenue"'),
                'ev_to_ebit': self._extract_value(values, column_map, '"EV/EBIT"'),
                'earnings_yield': self._extract_value(values, column_map, '"Earnings Y"'),
                'dividend': self._extract_value(values, column_map, '"Dividend"'),
                'dividend_yield': self._extract_value(values, column_map, '"Dividend %"'),
                'payout_ratio': self._extract_value(values, column_map, '"Payout"'),
                'sector': self._extract_value(values, column_map, '"Sector"'),
                'industry': self._extract_value(values, column_map, '"Industry"'),
                'country': self._extract_value(values, column_map, '"Country"'),
                'exchange': self._extract_value(values, column_map, '"Exchange"'),
                'ipo_date': self._extract_value(values, column_map, '"IPO Date"'),
                'employees': self._extract_value(values, column_map, '"Employees"'),
                'shares_short': self._extract_value(values, column_map, '"Shs Short"'),
                'short_interest': self._extract_value(values, column_map, '"Short Interest"'),
                'short_interest_ratio': self._extract_value(values, column_map, '"Short Interest Ratio"'),
                'float_short': self._extract_value(values, column_map, '"Float Short"'),
                'avg_true_range': self._extract_value(values, column_map, '"Avg True Range"'),
                'volatility': self._extract_value(values, column_map, '"Volatility"'),
                'prev_close': self._extract_value(values, column_map, '"Prev Close"'),
                'open': self._extract_value(values, column_map, '"Open"'),
                'high': self._extract_value(values, column_map, '"High"'),
                'low': self._extract_value(values, column_map, '"Low"'),
                'after_hours_close': self._extract_value(values, column_map, '"After-Hours Close"'),
                'after_hours_change': self._extract_value(values, column_map, '"After-Hours Change"')
            }
            
            logger.info(f"Successfully fetched Finviz data for {ticker}")
            return financial_data
            
        except Exception as e:
            logger.error(f"Error fetching Finviz data for {ticker}: {str(e)}")
            return {}
    
    def get_financial_data_for_tickers(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get financial data for multiple tickers.
        
        Args:
            tickers: List of stock ticker symbols
            
        Returns:
            Dictionary mapping ticker to financial data
        """
        try:
            if not self.auth_id:
                logger.warning("FINVIZ_AUTH_ID not configured, skipping Finviz data fetch")
                return {}
            
            # Use view 152 with comprehensive columns
            params = {
                'v': '152',
                't': ','.join(tickers),
                'c': '1,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,199,200',
                'auth': self.auth_id
            }
            
            logger.info(f"Fetching Finviz data for {len(tickers)} tickers")
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Finviz API request failed with status {response.status_code}")
                return {}
            
            # Parse CSV response
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                logger.warning("Finviz API returned insufficient data")
                return {}
            
            # Parse header
            header = lines[0].split(',')
            column_map = {}
            for i, col in enumerate(header):
                column_map[col.strip()] = i
            
            # Parse data rows
            finviz_data = {}
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                values = line.split(',')
                if len(values) < len(header):
                    continue
                
                ticker = self._extract_value(values, column_map, '"Ticker"')
                if not ticker:
                    continue
                
                # Extract comprehensive financial data
                finviz_data[ticker] = {
                    'ticker': ticker,
                    'price': self._extract_value(values, column_map, '"Price"'),
                    'change': self._extract_value(values, column_map, '"Change"'),
                    'market_cap': self._extract_value(values, column_map, '"Market Cap"'),
                    'pe_ratio': self._extract_value(values, column_map, '"P/E"'),
                    'forward_pe': self._extract_value(values, column_map, '"Forward P/E"'),
                    'peg_ratio': self._extract_value(values, column_map, '"PEG"'),
                    'debt_to_equity': self._extract_value(values, column_map, '"Debt/Eq"'),
                    'profit_margin': self._extract_value(values, column_map, '"Profit M"'),
                    'operating_margin': self._extract_value(values, column_map, '"Oper. Margin"'),
                    'roa': self._extract_value(values, column_map, '"ROA"'),
                    'roe': self._extract_value(values, column_map, '"ROE"'),
                    'roi': self._extract_value(values, column_map, '"ROI"'),
                    'revenue': self._extract_value(values, column_map, '"Sales Q/Q"'),
                    'revenue_growth': self._extract_value(values, column_map, '"Sales Q/Q"'),
                    'earnings_growth': self._extract_value(values, column_map, '"Earnings Q/Q"'),
                    'earnings_date': self._extract_value(values, column_map, '"Earnings"'),
                    'volume': self._extract_value(values, column_map, '"Volume"'),
                    'avg_volume': self._extract_value(values, column_map, '"Avg Volume"'),
                    'shares_outstanding': self._extract_value(values, column_map, '"Shs Outstand"'),
                    'shares_float': self._extract_value(values, column_map, '"Shs Float"'),
                    'insider_ownership': self._extract_value(values, column_map, '"Insider Own"'),
                    'institutional_ownership': self._extract_value(values, column_map, '"Inst Own"'),
                    'short_ratio': self._extract_value(values, column_map, '"Short Ratio"'),
                    'current_ratio': self._extract_value(values, column_map, '"Current Ratio"'),
                    'quick_ratio': self._extract_value(values, column_map, '"Quick Ratio"'),
                    'debt_to_equity': self._extract_value(values, column_map, '"Debt/Eq"'),
                    'lt_debt_to_equity': self._extract_value(values, column_map, '"LT Debt/Eq"'),
                    'beta': self._extract_value(values, column_map, '"Beta"'),
                    'atr': self._extract_value(values, column_map, '"ATR"'),
                    'rsi': self._extract_value(values, column_map, '"RSI (14)"'),
                    'gap': self._extract_value(values, column_map, '"Gap"'),
                    'recom': self._extract_value(values, column_map, '"Recom"'),
                    'target_price': self._extract_value(values, column_map, '"Target Price"'),
                    'price_to_book': self._extract_value(values, column_map, '"P/B"'),
                    'price_to_sales': self._extract_value(values, column_map, '"P/S"'),
                    'price_to_cash': self._extract_value(values, column_map, '"P/C"'),
                    'price_to_free_cash': self._extract_value(values, column_map, '"P/FCF"'),
                    'ev_to_ebitda': self._extract_value(values, column_map, '"EV/EBITDA"'),
                    'ev_to_revenue': self._extract_value(values, column_map, '"EV/Revenue"'),
                    'ev_to_ebit': self._extract_value(values, column_map, '"EV/EBIT"'),
                    'earnings_yield': self._extract_value(values, column_map, '"Earnings Y"'),
                    'dividend': self._extract_value(values, column_map, '"Dividend"'),
                    'dividend_yield': self._extract_value(values, column_map, '"Dividend %"'),
                    'payout_ratio': self._extract_value(values, column_map, '"Payout"'),
                    'sector': self._extract_value(values, column_map, '"Sector"'),
                    'industry': self._extract_value(values, column_map, '"Industry"'),
                    'country': self._extract_value(values, column_map, '"Country"'),
                    'exchange': self._extract_value(values, column_map, '"Exchange"'),
                    'ipo_date': self._extract_value(values, column_map, '"IPO Date"'),
                    'employees': self._extract_value(values, column_map, '"Employees"'),
                    'shares_short': self._extract_value(values, column_map, '"Shs Short"'),
                    'short_interest': self._extract_value(values, column_map, '"Short Interest"'),
                    'short_interest_ratio': self._extract_value(values, column_map, '"Short Interest Ratio"'),
                    'float_short': self._extract_value(values, column_map, '"Float Short"'),
                    'avg_true_range': self._extract_value(values, column_map, '"Avg True Range"'),
                    'volatility': self._extract_value(values, column_map, '"Volatility"'),
                    'prev_close': self._extract_value(values, column_map, '"Prev Close"'),
                    'open': self._extract_value(values, column_map, '"Open"'),
                    'high': self._extract_value(values, column_map, '"High"'),
                    'low': self._extract_value(values, column_map, '"Low"'),
                    'after_hours_close': self._extract_value(values, column_map, '"After-Hours Close"'),
                    'after_hours_change': self._extract_value(values, column_map, '"After-Hours Change"')
                }
            
            logger.info(f"Successfully fetched Finviz data for {len(finviz_data)} tickers")
            return finviz_data
            
        except Exception as e:
            logger.error(f"Error fetching Finviz data: {str(e)}")
            return {}
    
    def get_revenue_and_eps_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get revenue and EPS data specifically for a ticker.
        This is optimized for the earning summary use case.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with revenue and EPS data
        """
        try:
            financial_data = self.get_financial_data_for_ticker(ticker)
            if not financial_data:
                return {}
            
            # Extract relevant revenue and EPS data
            revenue_eps_data = {
                'ticker': ticker,
                'revenue': financial_data.get('revenue', 'N/A'),
                'revenue_growth': financial_data.get('revenue_growth', 'N/A'),
                'earnings_growth': financial_data.get('earnings_growth', 'N/A'),
                'pe_ratio': financial_data.get('pe_ratio', 'N/A'),
                'forward_pe': financial_data.get('forward_pe', 'N/A'),
                'peg_ratio': financial_data.get('peg_ratio', 'N/A'),
                'profit_margin': financial_data.get('profit_margin', 'N/A'),
                'operating_margin': financial_data.get('operating_margin', 'N/A'),
                'roa': financial_data.get('roa', 'N/A'),
                'roe': financial_data.get('roe', 'N/A'),
                'roi': financial_data.get('roi', 'N/A'),
                'earnings_date': financial_data.get('earnings_date', 'N/A'),
                'target_price': financial_data.get('target_price', 'N/A'),
                'price_to_sales': financial_data.get('price_to_sales', 'N/A'),
                'ev_to_revenue': financial_data.get('ev_to_revenue', 'N/A'),
                'earnings_yield': financial_data.get('earnings_yield', 'N/A'),
                'market_cap': financial_data.get('market_cap', 'N/A'),
                'sector': financial_data.get('sector', 'N/A'),
                'industry': financial_data.get('industry', 'N/A')
            }
            
            return revenue_eps_data
            
        except Exception as e:
            logger.error(f"Error getting revenue and EPS data for {ticker}: {str(e)}")
            return {}
    
    def _extract_value(self, values: List[str], column_map: Dict[str, int], column_name: str) -> str:
        """
        Extract value from CSV row using column mapping.
        
        Args:
            values: List of values from CSV row
            column_map: Mapping of column names to indices
            column_name: Name of the column to extract
            
        Returns:
            Extracted value or 'N/A' if not found
        """
        try:
            if column_name in column_map:
                index = column_map[column_name]
                if index < len(values):
                    value = values[index].strip().strip('"')
                    return value if value else 'N/A'
            return 'N/A'
        except:
            return 'N/A'

    def get_earning_dates_batch(self, stocks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Get earning dates for multiple stocks in a single API call.
        This is optimized for the 10 PM earning date update job.
        
        Args:
            stocks: List of stock dictionaries with 'ticker' key
            
        Returns:
            Dictionary mapping ticker to earning date data
        """
        try:
            if not self.auth_id:
                logger.warning("FINVIZ_AUTH_ID not configured, skipping batch earning date fetch")
                return {}
            
            # Extract tickers
            tickers = [stock.get('ticker', '') for stock in stocks if stock.get('ticker')]
            if not tickers:
                logger.warning("No valid tickers provided for batch earning date fetch")
                return {}
            
            logger.info(f"Fetching earning dates for {len(tickers)} stocks from Finviz...")
            
            # Use view 161 which is specifically designed for earnings data
            # This view should include earning dates
            params = {
                'v': '161',  # View 161 - Earnings
                't': ','.join(tickers),  # Multiple tickers
                'auth': self.auth_id
            }
            
            response = requests.get(self.base_url, params=params, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"Finviz batch API request failed with status {response.status_code}")
                return {}
            
            # Parse CSV response
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                logger.warning("Finviz API returned insufficient data for batch request")
                return {}
            
            # Parse header to get column indices
            header = lines[0].split(',')
            column_map = {}
            for i, col in enumerate(header):
                column_map[col.strip()] = i
            
            # Parse data rows
            result = {}
            logger.debug(f"Parsing {len(lines)-1} data rows...")
            logger.debug(f"Column map: {column_map}")
            
            for i, line in enumerate(lines[1:], 1):
                values = line.split(',')
                if len(values) < len(header):
                    logger.warning(f"Row {i} too short: {len(values)} < {len(header)}")
                    continue
                
                ticker = self._extract_value(values, column_map, '"Ticker"')
                earnings_date = self._extract_value(values, column_map, '"Earnings Date"')
                
                logger.debug(f"Row {i}: Ticker={ticker}, Earnings Date={earnings_date}")
                
                if ticker and ticker != 'N/A':
                    result[ticker] = {
                        'earnings_date': earnings_date
                    }
            
            logger.info(f"Successfully fetched earning dates for {len(result)} stocks from Finviz")
            return result
            
        except Exception as e:
            logger.error(f"Error in batch earning date fetch: {str(e)}")
            return {}

# Global instance
finviz_service = FinvizService()
