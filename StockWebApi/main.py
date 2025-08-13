from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import logging
import os
import json
from typing import Optional, List, Dict, Any
# Removed unused asyncio import
import time
from datetime import datetime

# Import models and operations
from models import *
from auth_operations import get_current_user, require_auth, require_admin, login_user, verify_token
from stock_operations import get_stock_details, get_stock_with_filters, add_stock_to_file, update_stock_in_file, delete_stock_from_file

from stock_summary_optimized import get_stock_summary, get_stock_summary_today
from sector_operations import get_sectors_with_filters, add_sector_to_file, update_sector_in_file, delete_sector_from_file
from user_operations import get_users_with_filters, add_user_to_file, update_user_in_file, delete_user_from_file
from earning_summary_optimized import get_earning_summary
from sentiment_analysis import get_sentiment_analysis
from api_rate_limiter import get_rate_limiter
from cache_manager import get_cache_stats, clear_cache, invalidate_cache
from yahoo_finance_proxy import initialize_yahoo_finance_proxy, clear_expired_cache
from stock_history_operations import stock_history_ops
from background_scheduler import start_background_scheduler, get_scheduler_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with performance optimizations
app = FastAPI(
    title="Stock Prediction API",
    description="A FastAPI-based stock prediction and analysis API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with optimized settings
from config import config

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


# Global performance tracking
_request_times = {}

@app.middleware("http")
async def performance_middleware(request, call_next):
    """Middleware to track and optimize request performance"""
    start_time = time.time()
    
    # Add performance headers
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 2.0:  # Log requests taking more than 2 seconds
        logger.warning(f"Slow request: {request.url.path} took {process_time:.2f}s")
    
    return response

# Note: Removed complex session management to avoid conflicts with yfinance
# yfinance will handle its own connections internally

# Application startup event
@app.on_event("startup")
async def startup_event():
    # Initialize Yahoo Finance proxy system
    try:
        initialize_yahoo_finance_proxy()
        logger.info("Yahoo Finance proxy system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Yahoo Finance proxy system: {e}")
        # Continue startup even if proxy initialization fails
    
    # Start background scheduler for stock history data
    try:
        start_background_scheduler()
        logger.info("Background scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start background scheduler: {e}")
        # Continue startup even if scheduler fails

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway monitoring"""
    return {
        "status": "healthy", 
        "message": "Stock Prediction API is running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Authentication endpoints
@app.post('/api/login')
async def login_route(request: LoginRequest):
    result = login_user(request.username, request.password)
    
    if result['success']:
        return result
    else:
        raise HTTPException(status_code=401, detail=result)

@app.post('/api/verify-token')
async def verify_token_route(request: TokenRequest):
    payload = verify_token(request.token)
    if payload:
        return {
            'valid': True,
            'username': payload['username'],
            'role': payload['role'],
            'firstname': payload.get('firstname', ''),
            'lastname': payload.get('lastname', '')
        }
    else:
        raise HTTPException(status_code=401, detail={'valid': False})

# Protected routes - require authentication
@app.get('/api/getstock')
async def get_stock_route(
    sector: str = "",
    ticker: str = "",
    isleverage: Optional[bool] = None,
    page: int = 1,
    per_page: int = 10,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    sector_param = sector.strip().lower()
    ticker_param = ticker.strip().lower()
    
    result = get_stock_with_filters(sector_param, ticker_param, isleverage, page, per_page)
    
    # Always include isleverage in results
    for s in result['results']:
        if 'isleverage' not in s:
            s['isleverage'] = False
    
    return result

@app.get('/api/getstockdetails')
async def get_stockdetails_route(
    ticker: str = "",
    sector: str = "",
    isleverage: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    tickers_param = ticker.strip()
    sector_param = sector.strip().lower()
    
    result = get_stock_details(tickers_param, sector_param, isleverage, sort_by, sort_order)
    
    return result











# Admin-only routes
@app.post('/api/stocks')
async def add_stock_route(
    request: StockRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = add_stock_to_file(request.ticker, request.sector, request.isleverage)
    
    if success:
        return {
            'message': message, 
            'stock': {
                'ticker': request.ticker, 
                'sector': request.sector, 
                'isleverage': request.isleverage
            }
        }
    else:
        raise HTTPException(status_code=400, detail={'error': message})

@app.put('/api/stocks/update')
async def update_stock_route(
    request: StockUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    new_ticker = request.ticker if request.ticker else request.oldTicker
    
    success, message = update_stock_in_file(request.oldTicker, request.sector, request.isleverage, new_ticker)
    
    if success:
        return {
            'message': message, 
            'stock': {
                'ticker': new_ticker, 
                'sector': request.sector, 
                'isleverage': request.isleverage
            }
        }
    else:
        raise HTTPException(status_code=404, detail={'error': message})

@app.post('/api/stocks/delete')
async def delete_stock_route(
    request: StockDeleteRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = delete_stock_from_file(request.ticker)
    
    if success:
        return {'message': message, 'ticker': request.ticker}
    else:
        raise HTTPException(status_code=404, detail={'error': message})

@app.get('/api/sectors')
async def get_sectors_route(
    filter: str = "",
    page: int = 1,
    per_page: int = 10,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    filter_param = filter.strip().lower()
    result = get_sectors_with_filters(filter_param, page, per_page)
    return result

@app.get('/api/sectors/public')
async def get_sectors_public_route(
    filter: str = "",
    page: int = 1,
    per_page: int = 10
):
    """Get sectors with filtering and pagination (Public access - no authentication required)"""
    filter_param = filter.strip().lower()
    result = get_sectors_with_filters(filter_param, page, per_page)
    return result

@app.post('/api/sectors')
async def add_sector_route(
    request: SectorRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = add_sector_to_file(request.sector)
    
    if success:
        return {'message': message, 'sector': request.sector}
    else:
        raise HTTPException(status_code=400, detail={'error': message})

@app.put('/api/sectors/update')
async def update_sector_route(
    request: SectorUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = update_sector_in_file(request.oldSector, request.newSector)
    
    if success:
        return {'message': message, 'sector': request.newSector}
    else:
        raise HTTPException(status_code=404, detail={'error': message})

@app.post('/api/sectors/delete')
async def delete_sector_route(
    request: SectorDeleteRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = delete_sector_from_file(request.sector)
    
    if success:
        return {'message': message, 'sector': request.sector}
    else:
        raise HTTPException(status_code=404, detail={'error': message})

# User management endpoints
@app.get('/api/users')
async def get_users_route(
    filter: str = "",
    page: int = 1,
    per_page: int = 10,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    username_param = filter.strip().lower()
    result = get_users_with_filters(username_param, page, per_page)
    return result

@app.post('/api/users')
async def add_user_route(
    request: UserRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = add_user_to_file(
        request.username, 
        request.password, 
        request.role, 
        request.firstname, 
        request.lastname
    )
    
    if success:
        return {
            'message': message, 
            'user': {
                'username': request.username, 
                'role': request.role, 
                'firstname': request.firstname, 
                'lastname': request.lastname
            }
        }
    else:
        raise HTTPException(status_code=400, detail={'error': message})

@app.put('/api/users/update')
async def update_user_route(
    request: UserUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = update_user_in_file(
        request.oldUsername, 
        request.username, 
        request.password, 
        request.role, 
        request.firstname, 
        request.lastname
    )
    
    if success:
        return {
            'message': message, 
            'user': {
                'username': request.username, 
                'role': request.role, 
                'firstname': request.firstname, 
                'lastname': request.lastname
            }
        }
    else:
        raise HTTPException(status_code=404, detail={'error': message})

@app.post('/api/users/delete')
async def delete_user_route(
    request: UserDeleteRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = delete_user_from_file(request.username)
    
    if success:
        return {'message': message, 'username': request.username}
    else:
        raise HTTPException(status_code=404, detail={'error': message})

# User-accessible routes
@app.get('/api/stock-summary')
async def get_stock_summary_route(
    sectors: str = "",
    isleverage: Optional[bool] = None,
    date_from: str = "",
    date_to: str = "",
    today: Optional[bool] = None,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    sectors_param = sectors.strip()
    date_from_param = date_from.strip()
    date_to_param = date_to.strip()
    
    # Check if this is a "today" request
    if today:
        logger.info("Today filter requested for stock summary - using Finviz API")
        results = get_stock_summary_today(sectors_param, isleverage)
    else:
        results = get_stock_summary(sectors_param, isleverage, date_from_param, date_to_param)
    
    return {'groups': results}

@app.get('/api/earning-summary')
async def get_earning_summary_route(
    sectors: str = "",
    period: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    per_page: int = 10,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    sectors_param = sectors.strip()
    period_param = period.strip()
    date_from_param = date_from.strip()
    date_to_param = date_to.strip()
    
    # Cache validation and automatic caching for 1D, 1W, and 1M periods (all share 1M cache)
    if period_param in ['1D', '1W', '1M']:
        try:
            from earning_summary_cache import earning_cache, get_cache_status
            from datetime import date
            
            # Check if cache is available and valid for current date
            cache_status = get_cache_status()
            today = date.today()
            is_cache_valid = cache_status.get('is_valid', False)
            
            logger.info(f"Cache validation for period {period_param}: valid={is_cache_valid}, date={today}")
            
            if is_cache_valid:
                # Cache is valid, try to get from cache
                try:
                    cached_result = earning_cache.get_cached_summary(period_param, sectors_param, page, per_page)
                    if cached_result:
                        logger.info(f"Returning cached earning summary for period {period_param}, sectors: {sectors_param}")
                        return cached_result
                except Exception as e:
                    logger.warning(f"Error getting cached data: {e}, will fetch fresh data")
            
            # Cache is invalid or missing, fetch fresh data and cache it
            logger.info(f"Cache invalid or missing for period {period_param}, fetching fresh data and caching")
            
            # Fetch fresh data
            fresh_result = get_earning_summary(sectors_param, period_param, date_from_param, date_to_param, page, per_page)
            
            # Cache the full dataset for future use (always cache as 1M since all periods share it)
            try:
                # Get all data for caching (not just the current page)
                # Always cache as 1M since 1D and 1W will filter from it
                full_data = get_earning_summary(sectors_param, '1M', date_from_param, date_to_param, page=1, per_page=1000)
                earning_cache.cache_summary('1M', full_data, sectors_param)
                logger.info(f"Successfully cached fresh data for period 1M (used by {period_param}), sectors: {sectors_param}")
            except Exception as e:
                logger.error(f"Error caching data for period 1M: {e}")
            
            return fresh_result
            
        except Exception as e:
            logger.error(f"Error in cache validation for period {period_param}: {e}, falling back to direct call")
            # Fall back to direct call if cache operations fail
            result = get_earning_summary(sectors_param, period_param, date_from_param, date_to_param, page, per_page)
            return result
    
    else:
        # For custom periods or other cases, use direct call without caching
        logger.info(f"Direct call for period {period_param} (not cached)")
        result = get_earning_summary(sectors_param, period_param, date_from_param, date_to_param, page, per_page)
        return result

@app.get('/api/market-status')
async def get_market_status_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get current market status information including working day status and period calculations."""
    try:
        from earning_summary_optimized import get_market_status_info
        return get_market_status_info()
    except Exception as e:
        logger.error(f"Error getting market status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get market status: {str(e)}")

@app.get('/api/earning-cache/status')
async def get_earning_cache_status_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get earning summary cache status information."""
    try:
        from earning_summary_cache import get_earning_cache_status
        return get_earning_cache_status()
    except Exception as e:
        logger.error(f"Error getting earning cache status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get earning cache status: {str(e)}")

@app.get('/api/earning-cache/metrics')
async def get_earning_cache_metrics_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get earning summary cache performance metrics."""
    try:
        from earning_summary_cache import get_cache_performance_metrics
        return get_cache_performance_metrics()
    except Exception as e:
        logger.error(f"Error getting earning cache metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get earning cache metrics: {str(e)}")

@app.post('/api/earning-cache/clear')
async def clear_earning_cache_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Clear earning summary cache - Admin only."""
    try:
        # Only admin can clear cache
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail={'error': 'Admin access required'})
        
        from earning_summary_cache import clear_earning_cache
        clear_earning_cache()
        return {"message": "Earning summary cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing earning cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear earning cache: {str(e)}")

@app.post('/api/earning-cache/refresh')
async def refresh_earning_cache_route(
    period: str = Query(..., description="Period to refresh ('1D', '1W', '1M', or 'all')"),
    sectors: str = Query("", description="Sectors to refresh (optional)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Refresh earning summary cache for specific period - Admin only."""
    try:
        # Only admin can refresh cache
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail={'error': 'Admin access required'})
        
        from earning_summary_cache import earning_cache
        
        if period == 'all':
            # Refresh all periods
            for p in ['1D', '1W', '1M']:
                earning_cache.get_or_fetch_summary(p, sectors if sectors else None)
            return {"message": f"All earning summary cache refreshed for sectors: {sectors if sectors else 'all'}"}
        elif period in ['1D', '1W', '1M']:
            # Refresh specific period
            earning_cache.get_or_fetch_summary(period, sectors if sectors else None)
            return {"message": f"Earning summary cache refreshed for period {period}, sectors: {sectors if sectors else 'all'}"}
        else:
            raise HTTPException(status_code=400, detail="Invalid period. Must be '1D', '1W', '1M', or 'all'")
            
    except Exception as e:
        logger.error(f"Error refreshing earning cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh earning cache: {str(e)}")

# Today filter cache management endpoints
@app.get('/api/today-cache/status')
async def get_today_cache_status_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get the current status of the Today filter cache."""
    try:
        from stock_summary_optimized import get_today_cache_status
        return get_today_cache_status()
    except Exception as e:
        logger.error(f"Error getting today cache status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get today cache status: {str(e)}")

@app.post('/api/today-cache/clear')
async def clear_today_cache_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Clear Today filter cache - Admin only."""
    try:
        # Only admin can clear cache
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail={'error': 'Admin access required'})
        
        from stock_summary_optimized import clear_today_cache
        result = clear_today_cache()
        return result
    except Exception as e:
        logger.error(f"Error clearing today cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear today cache: {str(e)}")

@app.post('/api/today-cache/refresh')
async def refresh_today_cache_route(
    sectors: str = Query("", description="Sectors to refresh (optional)"),
    isleverage: Optional[bool] = Query(None, description="Leverage filter (optional)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Refresh Today filter cache - Admin only."""
    try:
        # Only admin can refresh cache
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail={'error': 'Admin access required'})
        
        from stock_summary_optimized import refresh_today_cache
        result = refresh_today_cache(sectors, isleverage)
        return result
        
    except Exception as e:
        logger.error(f"Error refreshing today cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh today cache: {str(e)}")

# Test endpoint for historical price data
@app.get('/api/test-historical-price')
async def test_historical_price_route(
    ticker: str = Query(..., description="Stock ticker symbol"),
    date: str = Query(..., description="Date in MM/DD/YYYY or YYYY-MM-DD format"),
    interval: str = Query('1h', description="Data interval"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Test endpoint for historical price data"""
    try:
        logger.info(f"Test endpoint called with ticker={ticker}, date={date}, interval={interval}")
        
        # Import and call the function directly
        from earning_summary_optimized import get_historical_price_data
        logger.info("Import successful")
        
        result = get_historical_price_data(ticker, date, interval)
        logger.info(f"Function result: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Test endpoint error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Test endpoint error: {str(e)}")

@app.get('/api/historical-price')
async def get_historical_price_route(
    ticker: str = Query(..., description="Stock ticker symbol"),
    date: str = Query(..., description="Date in MM/DD/YYYY or YYYY-MM-DD format"),
    interval: str = Query('1m', description="Data interval: '1m' for intraday, '1h' for hourly, '1d' for daily"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get historical price data for a specific ticker and date.
    
    Args:
        ticker: Stock ticker symbol
        date: Date in MM/DD/YYYY or YYYY-MM-DD format
        interval: Data interval ('1m' for intraday, '1h' for hourly, '1d' for daily)
    
    Returns:
        Historical price data including intraday points and after-hours data
    """
    try:
        logger.info(f"Attempting to import get_historical_price_data for {ticker} on {date}")
        from earning_summary_optimized import get_historical_price_data
        logger.info(f"Import successful, calling function with ticker={ticker}, date={date}, interval={interval}")
        result = get_historical_price_data(ticker, date, interval)
        logger.info(f"Function call successful, result type: {type(result)}")
        
        if "error" in result:
            logger.warning(f"Function returned error: {result['error']}")
            raise HTTPException(status_code=404, detail=result["error"])
        
        logger.info(f"Returning successful result with {len(result.get('data', []))} data points")
        return result
    except Exception as e:
        logger.error(f"Error getting historical price data for {ticker} on {date}: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get historical price data: {str(e)}")






# Download endpoints
@app.get('/api/download/{file_type}')
async def download_file_route(
    file_type: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Download JSON files based on file type - Admin only"""
    try:
        # Only admin can download any files
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail={'error': 'Admin access required'})
        
        if file_type == 'users':
            with open('user.json', 'r') as file:
                data = json.load(file)
            
            # Remove password hashes for security
            for user in data:
                if 'password' in user:
                    del user['password']
            
            return data
            
        elif file_type == 'stocks':
            # Load stocks data
            from stock_operations import load_stocks
            stocks = load_stocks()
            return stocks
            
        elif file_type == 'sectors':
            # Load sectors data
            from sector_operations import load_sectors
            sectors = load_sectors()
            return sectors
            
        else:
            raise HTTPException(status_code=400, detail={'error': 'Invalid file type'})
            
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail={'error': 'File not found'})
    except Exception as e:
        raise HTTPException(status_code=500, detail={'error': str(e)})

# Sentiment Analysis endpoint
@app.get('/api/sentiment/{ticker}')
async def get_sentiment_route(
    ticker: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get sentiment analysis for a specific ticker"""
    try:
        if not ticker or ticker.strip() == '':
            raise HTTPException(status_code=400, detail={'error': 'Ticker is required'})
        
        ticker = ticker.strip().upper()
        sentiment_data = get_sentiment_analysis(ticker)
        
        return sentiment_data
        
    except Exception as e:
        logging.error(f"Error getting sentiment for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail={'error': 'Failed to get sentiment data'})

# Test Earnings Data endpoint
# Test earnings endpoint removed during cleanup - was using removed history_cache module

@app.get('/api/rate-limiter-status')
async def get_rate_limiter_status():
    """Get the current status of the API rate limiter"""
    try:
        rate_limiter = get_rate_limiter()
        status = rate_limiter.get_status()
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting rate limiter status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting rate limiter status: {str(e)}")

@app.post('/api/rate-limiter-reset')
async def reset_rate_limiter(current_user: Dict[str, Any] = Depends(require_admin)):
    """Manually reset the rate limiter circuit breaker (admin only)"""
    try:
        rate_limiter = get_rate_limiter()
        
        # Reset the circuit breaker
        with rate_limiter.lock:
            rate_limiter.consecutive_429_errors = 0
            rate_limiter.circuit_breaker_opened_at = None
        
        logger.info("Rate limiter manually reset by admin")
        return {
            "status": "success",
            "message": "Rate limiter circuit breaker reset successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error resetting rate limiter: {e}")
        raise HTTPException(status_code=500, detail=f"Error resetting rate limiter: {str(e)}")

# Cache management endpoints (consolidated)

@app.post('/api/clear-cache')
async def clear_cache_route(current_user: Dict[str, Any] = Depends(require_admin)):
    """Clear the entire cache"""
    try:
        clear_cache()
        return {
            "status": "success",
            "message": "Cache cleared successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@app.post('/api/invalidate-cache')
async def invalidate_cache_route(current_user: Dict[str, Any] = Depends(require_admin)):
    """Invalidate specific cache entries"""
    try:
        invalidate_cache()
        return {
            "status": "success",
            "message": "Cache invalidated successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error invalidating cache: {str(e)}")

@app.get("/api/cache/stats")
async def get_cache_stats_route(current_user: Dict[str, Any] = Depends(require_auth)):
    """Get smart cache statistics"""
    try:
        stats = get_cache_stats()
        return {
            "success": True,
            "data": stats,
            "message": "Cache statistics retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@app.post("/api/cache/clear-expired")
async def clear_expired_cache_route(current_user: Dict[str, Any] = Depends(require_auth)):
    """Clear expired cache entries"""
    try:
        clear_expired_cache()
        return {
            "success": True,
            "message": "Expired cache entries cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing expired cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear expired cache: {str(e)}")

@app.get("/api/cache/status")
async def get_cache_status_route(current_user: Dict[str, Any] = Depends(require_auth)):
    """Get comprehensive cache status including both old and new cache systems"""
    try:
        # Get old cache stats
        old_cache_stats = get_cache_stats()
        
        # Get new smart cache stats
        smart_cache_stats = get_cache_stats()
        
        # Get rate limiter status
        rate_limiter = get_rate_limiter()
        rate_limiter_status = {
            "current_delay": rate_limiter.current_delay,
            "consecutive_failures": rate_limiter.consecutive_failures,
            "consecutive_successes": rate_limiter.consecutive_successes
        }
        
        return {
            "success": True,
            "data": {
                "old_cache": old_cache_stats,
                "smart_cache": smart_cache_stats,
                "rate_limiter": rate_limiter_status
            },
            "message": "Cache status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache status: {str(e)}")

# Stock History endpoints
@app.get("/api/stock-history")
async def get_stock_history_route(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    leverage_filter: Optional[str] = Query(None, description="Filter by leverage (true/false)"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get combined stock history data from both history and market data files"""
    try:
        
        # Check if stock history data is empty and populate if needed
        history_data = stock_history_ops.load_stock_history()
        if not history_data or len(history_data) == 0:
            logger.info("Stock history data is empty, populating now...")
            if stock_history_ops.populate_stock_history():
                logger.info("Stock history data populated successfully")
            else:
                logger.error("Failed to populate stock history data")
        elif stock_history_ops.should_populate_history():
            logger.info("Populating stock history data (cache-based update)...")
            stock_history_ops.populate_stock_history()
        
        # Check if market data is empty and populate if needed
        market_data = stock_history_ops.load_stock_market_data()
        if not market_data or len(market_data) == 0:
            logger.info("Market data is empty, populating now...")
            if stock_history_ops.populate_stock_market_data():
                logger.info("Market data populated successfully")
            else:
                logger.error("Failed to populate market data")
        elif stock_history_ops.should_populate_market_data():
            logger.info("Populating stock market data (cache-based update)...")
            stock_history_ops.populate_stock_market_data()
        
        # Get combined data after ensuring both files are populated
        data = stock_history_ops.get_combined_stock_data()
        
        # Apply filters if provided
        if ticker or sector or leverage_filter:
            filtered_results = []
            for item in data["results"]:
                # Ticker filter
                if ticker and ticker.lower() not in item["ticker"].lower():
                    continue
                
                # Sector filter
                if sector and sector.lower() not in item["sector"].lower():
                    continue
                
                # Leverage filter
                if leverage_filter is not None:
                    if leverage_filter.lower() == "true" and not item["isleverage"]:
                        continue
                    if leverage_filter.lower() == "false" and item["isleverage"]:
                        continue
                
                filtered_results.append(item)
            
            data["results"] = filtered_results
            data["total"] = len(filtered_results)
        
        return data
        
    except Exception as e:
        logger.error(f"Error getting stock history: {e}")
        # Return empty data structure on error instead of throwing exception
        return {
            "results": [],
            "total": 0
        }



@app.get("/api/stock-history/status")
async def get_stock_history_status_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get the current status of stock history and market data files"""
    try:
        # Check current status of both files
        history_data = stock_history_ops.load_stock_history()
        market_data = stock_history_ops.load_stock_market_data()
        
        # Check if files need population
        needs_history_population = not history_data or len(history_data) == 0
        needs_market_population = not market_data or len(market_data) == 0
        
        # Check if cache-based updates are needed
        should_update_history = stock_history_ops.should_populate_history()
        should_update_market = stock_history_ops.should_populate_market_data()
        
        # Get cache status
        cache_status = stock_history_ops.get_cache_status()
        
        return {
            "success": True,
            "message": "Stock history status retrieved successfully",
            "data": {
                "history": {
                    "records": len(history_data),
                    "needs_population": needs_history_population,
                    "should_update": should_update_history,
                    "file_exists": len(history_data) > 0
                },
                "market": {
                    "records": len(market_data),
                    "needs_population": needs_market_population,
                    "should_update": should_update_market,
                    "file_exists": len(market_data) > 0
                },
                "overall": {
                    "total_records": len(history_data) + len(market_data),
                    "needs_any_population": needs_history_population or needs_market_population,
                    "needs_any_update": should_update_history or should_update_market
                },
                "cache_status": cache_status
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stock history status: {e}")
        return {
            "success": False,
            "message": f"Error retrieving status: {str(e)}",
            "data": {}
        }

@app.get("/api/stock-history/cache-status")
async def get_stock_history_cache_status_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get detailed cache status for stock history and market data"""
    try:
        cache_status = stock_history_ops.get_cache_status()
        
        return {
            "success": True,
            "message": "Cache status retrieved successfully",
            "data": cache_status
        }
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return {
            "success": False,
            "message": f"Error retrieving cache status: {str(e)}",
            "data": {}
        }

@app.post("/api/stock-history/populate")
async def populate_stock_history_data_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Manually populate both stock history and market data files"""
    try:
        results = {}
        
        # Populate stock history data
        logger.info("Manually populating stock history data...")
        if stock_history_ops.populate_stock_history():
            logger.info("Stock history data populated successfully")
            results["history"] = {"success": True, "message": "Stock history data populated successfully"}
        else:
            logger.error("Failed to populate stock history data")
            results["history"] = {"success": False, "message": "Failed to populate stock history data"}
        
        # Populate market data
        logger.info("Manually populating market data...")
        if stock_history_ops.populate_stock_market_data():
            logger.info("Market data populated successfully")
            results["market"] = {"success": True, "message": "Market data populated successfully"}
        else:
            logger.error("Failed to populate market data")
            results["market"] = {"success": False, "message": "Failed to populate market data"}
        
        # Check final status
        history_data = stock_history_ops.load_stock_history()
        market_data = stock_history_ops.load_stock_market_data()
        
        return {
            "success": True,
            "message": "Population process completed",
            "results": results,
            "summary": {
                "history_records": len(history_data),
                "market_records": len(market_data),
                "total_records": len(history_data) + len(market_data)
            }
        }
        
    except Exception as e:
        logger.error(f"Error populating stock history data: {e}")
        return {
            "success": False,
            "message": f"Error during population: {str(e)}",
            "results": {},
            "summary": {}
        }

@app.get("/api/scheduler/status")
async def get_scheduler_status_route(current_user: Dict[str, Any] = Depends(require_auth)):
    """Get background scheduler status"""
    try:
        status = get_scheduler_status()
        return {
            "success": True,
            "data": status,
            "message": "Scheduler status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")

# Catch-all route for static files - must be at the end
@app.get("/{path:path}")
async def serve_static(path: str):
    # Skip API routes - let them be handled by their specific endpoints
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    try:
        file_path = os.path.join("static", path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        else:
            # Fallback to index.html for SPA routing
            index_path = os.path.join("static", "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            else:
                raise HTTPException(status_code=404, detail="Static files not found")
    except Exception as e:
        logging.error(f"Error serving static file {path}: {e}")
        raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    # uvicorn already imported at the top
    # os already imported at the top
    
    # Get port from environment variable
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        reload=False,  # Disable auto-reload
        log_level="info"
    ) 