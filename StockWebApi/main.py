from fastapi import FastAPI, HTTPException, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import logging
import os
import json
from typing import Optional, List, Dict, Any
import asyncio
import time
from datetime import datetime

# Import models and operations
from models import *
from auth_operations import get_current_user, require_auth, require_admin, login_user, verify_token
from stock_operations import get_stock_details, add_stock_to_file, update_stock_in_file, delete_stock_from_file, get_stock_with_filters
from enhanced_stock_operations import get_enhanced_stock_details, get_realtime_price_updates, update_ticker_today_data, force_update_ticker_today_data, is_after_hours
from history_cache import history_cache
from stock_summary import get_stock_summary
from sector_operations import get_sectors_with_filters, add_sector_to_file, update_sector_in_file, delete_sector_from_file
from user_operations import get_users_with_filters, add_user_to_file, update_user_in_file, delete_user_from_file
from earning_summary import get_earning_summary, get_after_hours_data
from sentiment_analysis import get_sentiment_analysis

# Configure logging
logging.basicConfig(level=logging.WARNING)
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
# Get allowed origins from environment variable or use default
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",") if os.environ.get("ALLOWED_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Configure appropriately for production
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

# Optimize connection pooling for external APIs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure session with connection pooling and retries
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=0.1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=100,  # Increased connection pool
    pool_maxsize=100,      # Increased max connections
)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Application startup event
@app.on_event("startup")
async def startup_event():
    pass

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway monitoring"""
    import datetime
    return {
        "status": "healthy", 
        "message": "Stock Prediction API is running",
        "timestamp": datetime.datetime.now().isoformat(),
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
    isxticker: Optional[bool] = None,
    page: int = 1,
    per_page: int = 10,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    sector_param = sector.strip().lower()
    ticker_param = ticker.strip().lower()
    
    result = get_stock_with_filters(sector_param, ticker_param, isxticker, page, per_page)
    
    # Always include isxticker in results
    for s in result['results']:
        if 'isxticker' not in s:
            s['isxticker'] = False
    
    return result

@app.get('/api/getstockdetails')
async def get_stockdetails_route(
    ticker: str = "",
    sector: str = "",
    isxticker: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    tickers_param = ticker.strip()
    sector_param = sector.strip().lower()
    
    result = get_stock_details(tickers_param, sector_param, isxticker, sort_by, sort_order)
    
    return result

@app.get('/api/getenhancedstockdetails')
async def get_enhanced_stockdetails_route(
    ticker: str = "",
    sector: str = "",
    leverage_filter: str = "Ticker Only",
    sort_by: str = "today_percentage",
    sort_order: str = "desc",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    tickers_param = ticker.strip()
    sector_param = sector.strip().lower()
    
    result = get_enhanced_stock_details(tickers_param, sector_param, leverage_filter, sort_by, sort_order)
    
    return result

@app.get('/api/realtime-prices')
async def get_realtime_prices_route(
    tickers: str = "",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Get real-time price and today's data updates for specified tickers"""
    if not tickers:
        return {}
    
    ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
    updates = get_realtime_price_updates(ticker_list)
    
    return updates

@app.get('/api/is-after-hours')
async def is_after_hours_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Check if current time is after regular market hours"""
    return {'is_after_hours': is_after_hours()}

@app.post('/api/update-ticker-data')
async def update_ticker_data_route(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Manually trigger update of Ticker_Today.json"""
    try:
        result = update_ticker_today_data()
        return {
            'message': f'Successfully updated data for {len(result)} stocks',
            'count': len(result)
        }
    except Exception as e:
        logging.error(f"Error updating ticker data: {e}")
        raise HTTPException(status_code=500, detail={'error': str(e)})

@app.post('/api/force-update-ticker-data')
async def force_update_ticker_data_route(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """Force update Ticker_Today.json regardless of daily update check"""
    try:
        result = force_update_ticker_today_data()
        return {
            'message': f'Successfully force updated data for {len(result)} stocks',
            'count': len(result)
        }
    except Exception as e:
        logging.error(f"Error force updating ticker data: {e}")
        raise HTTPException(status_code=500, detail={'error': str(e)})

# Admin-only routes
@app.post('/api/stocks')
async def add_stock_route(
    request: StockRequest,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    success, message = add_stock_to_file(request.ticker, request.sector, request.isxticker)
    
    if success:
        return {
            'message': message, 
            'stock': {
                'ticker': request.ticker, 
                'sector': request.sector, 
                'isxticker': request.isxticker
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
    
    success, message = update_stock_in_file(request.oldTicker, request.sector, request.isxticker, new_ticker)
    
    if success:
        return {
            'message': message, 
            'stock': {
                'ticker': new_ticker, 
                'sector': request.sector, 
                'isxticker': request.isxticker
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
    current_user: Dict[str, Any] = Depends(require_admin)
):
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
    isxticker: Optional[bool] = None,
    date_from: str = "",
    date_to: str = "",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    sectors_param = sectors.strip()
    date_from_param = date_from.strip()
    date_to_param = date_to.strip()
    
    results = get_stock_summary(sectors_param, isxticker, date_from_param, date_to_param)
    
    return {'groups': results}

@app.get('/api/earning-summary')
async def get_earning_summary_route(
    sectors: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    per_page: int = 10,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    sectors_param = sectors.strip()
    date_from_param = date_from.strip()
    date_to_param = date_to.strip()
    
    result = get_earning_summary(sectors_param, date_from_param, date_to_param, page, per_page)
    return result

@app.get('/api/historical-price/{ticker}/{date}')
async def get_historical_price_route(
    ticker: str,
    date: str,
    interval: str = Query('1m', description="Data interval: '1m' for intraday, '1h' for hourly, '1d' for daily"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get historical price data for a specific ticker and date.
    
    Args:
        ticker: Stock ticker symbol
        date: Date in YYYY-MM-DD format
        interval: Data interval ('1m' for intraday, '1h' for hourly, '1d' for daily)
    
    Returns:
        Historical price data including intraday points and after-hours data
    """
    try:
        from earning_summary import get_historical_price_data
        result = get_historical_price_data(ticker, date, interval)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except Exception as e:
        logger.error(f"Error getting historical price data for {ticker} on {date}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get historical price data: {str(e)}")


@app.get('/api/after-hours/{ticker}/{date}')
async def get_after_hours_route(
    ticker: str,
    date: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get specifically after-hours and pre-market data for a ticker on a specific date.
    
    Args:
        ticker: Stock ticker symbol
        date: Date in YYYY-MM-DD format
    
    Returns:
        After-hours and pre-market data including price points and changes
    """
    try:
        # Validate ticker format
        if not ticker or not ticker.strip():
            raise HTTPException(status_code=400, detail="Ticker symbol is required")
        
        ticker = ticker.strip().upper()
        
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD format.")
        
        # Check if date is in the future
        current_date = datetime.now().date()
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        if target_date > current_date:
            raise HTTPException(
                status_code=400, 
                detail=f"Date {date} is in the future. Yahoo Finance only provides data for past dates."
            )
        
        # Check if date is too far in the past
        days_ago = (current_date - target_date).days
        if days_ago > 60:
            raise HTTPException(
                status_code=400,
                detail=f"Date {date} is too far in the past. Yahoo Finance only provides detailed data for the last 60 days."
            )
        
        result = get_after_hours_data(ticker, date)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error getting after-hours data for {ticker} on {date}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get after-hours data: {str(e)}")

# Test endpoint for after-hours validation (no auth required)
@app.get('/api/test-after-hours-validation/{ticker}/{date}')
async def test_after_hours_validation_route(ticker: str, date: str):
    """
    Test endpoint for after-hours date validation (no authentication required)
    """
    try:
        # Validate ticker format
        if not ticker or not ticker.strip():
            raise HTTPException(status_code=400, detail="Ticker symbol is required")
        
        ticker = ticker.strip().upper()
        
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD format.")
        
        # Check if date is in the future
        current_date = datetime.now().date()
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        if target_date > current_date:
            raise HTTPException(
                status_code=400, 
                detail=f"Date {date} is in the future. Yahoo Finance only provides data for past dates."
            )
        
        # Check if date is too far in the past
        days_ago = (current_date - target_date).days
        if days_ago > 60:
            raise HTTPException(
                status_code=400,
                detail=f"Date {date} is too far in the past. Yahoo Finance only provides detailed data for the last 60 days."
            )
        
        return {
            "message": "Date validation passed",
            "ticker": ticker,
            "date": date,
            "days_ago": days_ago,
            "is_valid": True
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error validating date for {ticker} on {date}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate date: {str(e)}")

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
@app.get('/api/test-earnings/{ticker}')
async def test_earnings_route(
    ticker: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """Test earnings data retrieval for debugging"""
    try:
        if not ticker or ticker.strip() == '':
            raise HTTPException(status_code=400, detail={'error': 'Ticker is required'})
        
        ticker = ticker.strip().upper()
        earnings_test = history_cache.test_earnings_data(ticker)
        
        return earnings_test
        
    except Exception as e:
        logging.error(f"Error testing earnings for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail={'error': 'Failed to test earnings data'})


# Catch-all route for static files - must be at the end
@app.get("/{path:path}")
async def serve_static(path: str):
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
    import uvicorn
    import os
    
    # Get port from environment variable
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        reload=False,  # Disable auto-reload
        log_level="info"
    ) 