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

# Import the proxy system
try:
    from yahoo_finance_proxy import initialize_yahoo_finance_proxy, get_proxy_status
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False
    logging.warning("Yahoo Finance proxy system not available")

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
            
            # Remove sleep to avoid delays - just log the rate limiting
            if time_since_last_call < adjusted_interval:
                logger.info(f"Rate limiting: would sleep for {adjusted_interval - time_since_last_call:.2f}s (skipped)")
            
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
        status = {
            'consecutive_429_errors': self.consecutive_429_errors,
            'circuit_breaker_open': self.is_circuit_open(),
            'circuit_breaker_opened_at': self.circuit_breaker_opened_at,
            'calls_per_second': self.calls_per_second,
            'min_interval': self.min_interval
        }
        
        # Add proxy status if available
        if PROXY_AVAILABLE:
            try:
                proxy_status = get_proxy_status()
                status['proxy_status'] = proxy_status
            except Exception as e:
                status['proxy_status'] = {'error': str(e)}
        
        return status
    
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

# Global instance with Railway-friendly rate limiting
_rate_limiter = APIRateLimiter(calls_per_second=0.5)  # Increased from 0.3 to 0.5 (1 call every 2 seconds)

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
    """Decorator to retry functions on various errors with exponential backoff"""
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
                    error_msg = str(e)
                    
                    # Check if this is a retryable error
                    is_retryable = any(keyword in error_msg for keyword in [
                        "429", "Too Many Requests", "Connection Timeout", 
                        "DNS Resolution", "Connection Failed", "timeout"
                    ])
                    
                    if is_retryable and attempt < max_retries:
                        # Determine delay based on error type
                        if "Connection Timeout" in error_msg:
                            # Longer delays for timeout errors
                            delay = base_delay * (3 ** attempt)  # More aggressive backoff
                            logger.warning(f"Connection timeout on attempt {attempt + 1}, retrying in {delay:.1f}s...")
                        elif "429" in error_msg:
                            # Standard backoff for rate limiting
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"429 error on attempt {attempt + 1}, retrying in {delay:.1f}s...")
                            handle_429_error()
                        else:
                            # Standard backoff for other connection errors
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Connection error on attempt {attempt + 1}, retrying in {delay:.1f}s...")
                        
                        time.sleep(delay)
                        continue
                    else:
                        # Either not retryable or max retries reached
                        raise
            return None
        return wrapper
    return decorator

# Convenience functions for common operations
@retry_on_429(max_retries=5, base_delay=5.0)
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
        logger.info(f"Making yfinance call for {ticker_symbol} operation: {operation}")
        
        ticker = yf.Ticker(ticker_symbol)
        
        if operation == "info":
            # Add timeout handling for info operations
            try:
                result = ticker.info
                logger.info(f"Successfully got info for {ticker_symbol}")
                return result
            except Exception as e:
                if "timeout" in str(e).lower() or "curl: (28)" in str(e):
                    logger.warning(f"Timeout getting info for {ticker_symbol}, will retry with backoff")
                    raise Exception(f"Connection Timeout Error for {ticker_symbol}")
                else:
                    raise
        elif operation == "history":
            result = ticker.history(period="1d", interval="1m", prepost=True)
            logger.info(f"Successfully got history for {ticker_symbol} with {len(result)} data points")
            return result
        elif operation == "history_1y":
            # Get 1 year of daily data for calculating 1D, 5D, 1M, 6M, 1Y metrics
            # OPTIMIZATION: Use 6mo instead of 1y to reduce data size and API load
            # Add timeout handling for long-running operations
            try:
                result = ticker.history(period="6mo", interval="1d", prepost=False)
                logger.info(f"Successfully got 6-month history for {ticker_symbol} with {len(result)} data points")
                return result
            except Exception as e:
                if "timeout" in str(e).lower() or "curl: (28)" in str(e):
                    logger.warning(f"Timeout getting 6-month history for {ticker_symbol}, trying shorter period")
                    # Fallback to 1 month if 6 months times out
                    result = ticker.history(period="1mo", interval="1d", prepost=False)
                    logger.info(f"Successfully got 1-month history for {ticker_symbol} with {len(result)} data points")
                    return result
                else:
                    raise
        elif operation == "history_6m":
            # Get 6 months of daily data
            result = ticker.history(period="6mo", interval="1d", prepost=False)
            logger.info(f"Successfully got 6-month history for {ticker_symbol} with {len(result)} data points")
            return result
        elif operation == "history_1m":
            # Get 1 month of daily data
            result = ticker.history(period="1mo", interval="1d", prepost=False)
            logger.info(f"Successfully got 1-month history for {ticker_symbol} with {len(result)} data points")
            return result
        elif operation == "history_5d":
            # Get 5 days of daily data
            result = ticker.history(period="5d", interval="1d", prepost=False)
            logger.info(f"Successfully got 5-day history for {ticker_symbol} with {len(result)} data points")
            return result
        elif operation == "earnings":
            result = ticker.earnings
            logger.info(f"Successfully got earnings for {ticker_symbol}")
            return result
        elif operation == "financials":
            result = ticker.financials
            logger.info(f"Successfully got financials for {ticker_symbol}")
            return result
        elif operation == "income_stmt":
            result = ticker.income_stmt
            logger.info(f"Successfully got income statement for {ticker_symbol}")
            return result
        elif operation == "earnings_dates":
            result = ticker.earnings_dates
            logger.info(f"Successfully got earnings dates for {ticker_symbol}")
            return result
        else:
            result = ticker.info
            logger.info(f"Successfully got default info for {ticker_symbol}")
            return result
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in safe_yfinance_call for {ticker_symbol} operation {operation}: {error_msg}")
        
        # Enhanced error handling for different types of errors
        if "429" in error_msg or "Too Many Requests" in error_msg:
            logger.warning(f"429 error detected for {ticker_symbol}, will trigger retry logic")
            # Re-raise to trigger retry decorator
            raise Exception(f"429 Client Error: Too Many Requests for {ticker_symbol}")
        elif "curl: (28)" in error_msg or "Connection timed out" in error_msg or "timeout" in error_msg.lower():
            logger.warning(f"Connection timeout detected for {ticker_symbol}, will trigger retry logic")
            # Re-raise to trigger retry decorator with longer delays
            raise Exception(f"Connection Timeout Error for {ticker_symbol}")
        elif "curl: (6)" in error_msg or "Could not resolve host" in error_msg:
            logger.warning(f"DNS resolution error for {ticker_symbol}, will trigger retry logic")
            # Re-raise to trigger retry decorator
            raise Exception(f"DNS Resolution Error for {ticker_symbol}")
        elif "curl: (7)" in error_msg or "Failed to connect" in error_msg:
            logger.warning(f"Connection failed for {ticker_symbol}, will trigger retry logic")
            # Re-raise to trigger retry decorator
            raise Exception(f"Connection Failed Error for {ticker_symbol}")
        else:
            # For other errors, log and re-raise
            logger.error(f"Unhandled error type for {ticker_symbol}: {error_msg}")
            raise

# Finviz function removed - no longer needed
