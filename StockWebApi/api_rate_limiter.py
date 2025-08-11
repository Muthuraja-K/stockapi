"""
Advanced API Rate Limiter for Yahoo Finance and other external APIs
This module provides a centralized rate limiting system to prevent 429 errors
"""

import time
import logging
import threading
from typing import Callable, Any, Dict
from functools import wraps
from queue import Queue
import asyncio

logger = logging.getLogger(__name__)

class APIRateLimiter:
    """Centralized rate limiter for all external API calls"""
    
    def __init__(self, calls_per_second: float = 0.3):
        """
        Initialize rate limiter
        
        Args:
            calls_per_second: Maximum API calls per second (default: 0.3 = 1 call every 3+ seconds)
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        self.request_queue = Queue()
        self.lock = threading.Lock()
        self.consecutive_429_errors = 0
        self.max_retries = 5
        self.circuit_breaker_threshold = 5  # Open circuit after 5 consecutive 429s
        self.circuit_breaker_timeout = 60   # Keep circuit open for 60 seconds
        self.circuit_breaker_opened_at = None
        self._start_worker()
    
    def _start_worker(self):
        """Start background worker to process queued requests"""
        def worker():
            while True:
                try:
                    # Get request from queue
                    request_data = self.request_queue.get()
                    if request_data is None:  # Shutdown signal
                        break
                    
                    func, args, kwargs, future = request_data
                    
                    # Execute the function
                    try:
                        result = func(*args, **kwargs)
                        future.set_result(result)
                    except Exception as e:
                        future.set_exception(e)
                    finally:
                        self.request_queue.task_done()
                        
                except Exception as e:
                    logger.error(f"Error in rate limiter worker: {e}")
                    time.sleep(0.1)
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()
    
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.circuit_breaker_opened_at is None:
            return False
        
        # Check if timeout has passed
        if time.time() - self.circuit_breaker_opened_at > self.circuit_breaker_timeout:
            # Reset circuit breaker
            with self.lock:
                self.circuit_breaker_opened_at = None
                self.consecutive_429_errors = 0
                logger.info("Circuit breaker timeout expired, resetting")
            return False
        
        return True
    
    def enforce_rate_limit(self):
        """Enforce rate limiting by sleeping if necessary"""
        # Check circuit breaker first
        if self.is_circuit_open():
            remaining_time = self.circuit_breaker_timeout - (time.time() - self.circuit_breaker_opened_at)
            logger.error(f"Circuit breaker is OPEN. All API calls blocked for {remaining_time:.1f}s")
            raise Exception("Circuit breaker is open - too many 429 errors")
        
        with self.lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time
            
            # Add exponential backoff if we've had consecutive 429 errors
            if self.consecutive_429_errors > 0:
                backoff_multiplier = min(2 ** self.consecutive_429_errors, 10)  # Cap at 10x
                adjusted_interval = self.min_interval * backoff_multiplier
                logger.warning(f"Rate limiting with backoff: {adjusted_interval:.2f}s (429 count: {self.consecutive_429_errors})")
            else:
                adjusted_interval = self.min_interval
            
            if time_since_last_call < adjusted_interval:
                sleep_time = adjusted_interval - time_since_last_call
                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
            
            self.last_call_time = time.time()
    
    def handle_429_error(self):
        """Handle a 429 error by increasing backoff and potentially opening circuit breaker"""
        with self.lock:
            self.consecutive_429_errors += 1
            logger.warning(f"429 error detected. Consecutive count: {self.consecutive_429_errors}")
            
            # Open circuit breaker if threshold exceeded
            if self.consecutive_429_errors >= self.circuit_breaker_threshold:
                self.circuit_breaker_opened_at = time.time()
                logger.error(f"Circuit breaker OPENED after {self.consecutive_429_errors} consecutive 429 errors")
    
    def handle_successful_call(self):
        """Handle a successful call by reducing backoff"""
        with self.lock:
            if self.consecutive_429_errors > 0:
                self.consecutive_429_errors = max(0, self.consecutive_429_errors - 1)
                logger.info(f"Successful call. Reduced 429 count to: {self.consecutive_429_errors}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the rate limiter"""
        return {
            'consecutive_429_errors': self.consecutive_429_errors,
            'circuit_breaker_open': self.is_circuit_open(),
            'circuit_breaker_opened_at': self.circuit_breaker_opened_at,
            'calls_per_second': self.calls_per_second,
            'min_interval': self.min_interval
        }
    
    def rate_limited(self, func: Callable) -> Callable:
        """Decorator to apply rate limiting to a function"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.enforce_rate_limit()
            return func(*args, **kwargs)
        return wrapper
    
    def queue_request(self, func: Callable, *args, **kwargs):
        """Queue a request for execution with rate limiting"""
        import concurrent.futures
        
        future = concurrent.futures.Future()
        self.request_queue.put((func, args, kwargs, future))
        return future.result()  # This will block until the request is processed
    
    def shutdown(self):
        """Shutdown the rate limiter"""
        self.request_queue.put(None)  # Send shutdown signal
        if hasattr(self, 'worker_thread'):
            self.worker_thread.join(timeout=5)

# Global instance with more conservative rate limiting
_rate_limiter = APIRateLimiter(calls_per_second=0.3)

def enforce_rate_limit():
    """Global function to enforce rate limiting"""
    _rate_limiter.enforce_rate_limit()

def handle_429_error():
    """Global function to handle 429 errors"""
    _rate_limiter.handle_429_error()

def handle_successful_call():
    """Global function to handle successful calls"""
    _rate_limiter.handle_successful_call()

def rate_limited(func: Callable) -> Callable:
    """Global decorator to apply rate limiting"""
    return _rate_limiter.rate_limited(func)

def get_rate_limiter() -> APIRateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter

def retry_on_429(max_retries: int = 3, base_delay: float = 2.0):
    """Decorator to retry functions on 429 errors with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    enforce_rate_limit()
                    result = func(*args, **kwargs)
                    handle_successful_call()
                    return result
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries:
                        handle_429_error()
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"429 error on attempt {attempt + 1}, retrying in {delay:.1f}s...")
                        time.sleep(delay)
                        continue
                    else:
                        raise
            return None
        return wrapper
    return decorator

# Convenience functions for common operations
@retry_on_429(max_retries=3, base_delay=3.0)
def safe_yfinance_call(ticker_symbol: str, operation: str = "info"):
    """
    Safely make a yfinance call with rate limiting and retry logic
    
    Args:
        ticker_symbol: Stock ticker symbol
        operation: Operation to perform ('info', 'history', 'earnings', etc.)
    
    Returns:
        Rate-limited yfinance call result
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(ticker_symbol)
        
        if operation == "info":
            return ticker.info
        elif operation == "history":
            return ticker.history(period="1d", interval="1m", prepost=True)
        elif operation == "earnings":
            return ticker.earnings
        elif operation == "financials":
            return ticker.financials
        else:
            return ticker.info
            
    except Exception as e:
        logger.error(f"Error in safe_yfinance_call for {ticker_symbol}: {e}")
        raise

@retry_on_429(max_retries=3, base_delay=3.0)
def safe_finviz_call(ticker_symbol: str):
    """
    Safely make a Finviz call with rate limiting and retry logic
    
    Args:
        ticker_symbol: Stock ticker symbol
    
    Returns:
        Rate-limited Finviz call result
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        url = f"https://finviz.com/quote.ashx?t={ticker_symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract data (simplified version)
        data = {}
        
        # Extract current price
        price_element = soup.select_one('span.fvz-price, span[class*="price"], td[class*="price"]')
        if price_element:
            data['current_price'] = price_element.text.strip()
        
        # Extract today's change
        change_element = soup.select_one('span.fvz-change, span[class*="change"], td[class*="change"]')
        if change_element:
            data['today_change'] = change_element.text.strip()
        
        return data
        
    except Exception as e:
        logger.error(f"Error in safe_finviz_call for {ticker_symbol}: {e}")
        raise
