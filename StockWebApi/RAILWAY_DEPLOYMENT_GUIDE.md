# Railway Deployment Guide - Rate Limiting System

## Overview
This guide explains how to deploy the updated StockWebApi with the comprehensive rate limiting system to Railway to resolve the persistent "429 Client Error: Too Many Requests" errors.

## What We've Implemented

### 1. Centralized Rate Limiting System
- **File**: `api_rate_limiter.py`
- **Purpose**: Single point of control for all external API calls
- **Rate**: 0.5 calls per second (1 call every 2 seconds) - Railway-optimized
- **Features**: Exponential backoff, circuit breaker, retry logic

### 2. Updated All API Call Modules
- ✅ `enhanced_stock_operations.py` - Uses `safe_yfinance_call()` and `safe_finviz_call()`
- ✅ `stock_summary.py` - Uses centralized rate limiting
- ✅ `history_cache.py` - Uses centralized rate limiting  
- ✅ `earning_summary.py` - Uses centralized rate limiting
- ✅ `sentiment_analysis.py` - Uses centralized rate limiting

### 3. New API Endpoints
- **GET** `/api/rate-limiter-status` - Monitor rate limiter status
- **POST** `/api/rate-limiter-reset` - Manually reset circuit breaker (admin only)

### 4. Enhanced Logging
- Better error detection for 429 errors
- Detailed logging of API calls and responses
- Circuit breaker status monitoring

## Deployment Steps

### Step 1: Commit and Push Changes
```bash
git add .
git commit -m "Implement comprehensive rate limiting system for Railway deployment"
git push origin main
```

### Step 2: Railway Dashboard Configuration
1. Go to your Railway project dashboard
2. Navigate to the **Variables** tab
3. Ensure these environment variables are set:
   ```
   PYTHON_VERSION=3.11.7
   PORT=8000
   ```

### Step 3: Railway Build Settings
1. Go to **Settings** tab
2. Verify these configurations:
   - **Build Command**: (leave empty - Railway auto-detects)
   - **Start Command**: `python start_simple.py`
   - **Builder**: `nixpacks`

### Step 4: Deploy
1. Railway will automatically detect the changes
2. Click **Deploy** or wait for auto-deployment
3. Monitor the build logs for any errors

## Verification

### Option 1: Use the Verification Script
After deployment, you can run the verification script on Railway:
```bash
python verify_railway_deployment.py
```

### Option 2: Test API Endpoints
1. **Check Rate Limiter Status**:
   ```bash
   curl https://your-railway-app.railway.app/api/rate-limiter-status
   ```

2. **Test Stock Data Endpoint**:
   ```bash
   curl https://your-railway-app.railway.app/api/stocks
   ```

### Option 3: Monitor Logs
1. In Railway dashboard, go to **Deployments** tab
2. Click on the latest deployment
3. Check **Logs** for rate limiting activity

## Expected Behavior

### Normal Operation
- API calls spaced 2+ seconds apart
- No 429 errors
- Circuit breaker remains closed
- Response times: 2-4 seconds for single calls

### After 429 Errors
- Delays increase exponentially (2s → 4s → 8s → 16s)
- After 5 consecutive 429s, circuit breaker opens
- All API calls blocked for 60 seconds
- Automatic recovery after timeout

### Recovery
- Delays decrease after successful calls
- Circuit breaker closes automatically
- Normal operation resumes

## Troubleshooting

### Still Getting 429 Errors?
1. **Check Rate Limiter Status**:
   ```bash
   curl https://your-app.railway.app/api/rate-limiter-status
   ```

2. **Reset Circuit Breaker** (if stuck open):
   ```bash
   curl -X POST https://your-app.railway.app/api/rate-limiter-reset \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
   ```

3. **Check Logs**: Look for rate limiting messages in Railway logs

### Performance Issues?
1. **Reduce Rate Limiting**: Edit `api_rate_limiter.py` line 162:
   ```python
   _rate_limiter = APIRateLimiter(calls_per_second=0.8)  # 1 call every 1.25s
   ```

2. **Increase Circuit Breaker Timeout**: Edit line 32:
   ```python
   self.circuit_breaker_timeout = 120   # 2 minutes instead of 1
   ```

### Deployment Issues?
1. **Check Build Logs**: Ensure all dependencies are installed
2. **Verify Python Version**: Must be 3.11.7
3. **Check Start Command**: Must be `python start_simple.py`

## Monitoring

### Key Metrics to Watch
- **Rate Limiter Status**: Circuit breaker state, consecutive 429 count
- **API Response Times**: Should be 2-4 seconds for rate-limited calls
- **Error Rates**: 429 errors should be eliminated
- **Circuit Breaker Events**: Should be rare

### Log Analysis
Look for these log patterns:
```
INFO - Rate limiting: sleeping for 2.00s
INFO - Successfully got info for AAPL
WARNING - 429 error detected for MSFT, will trigger retry logic
ERROR - Circuit breaker OPENED after 5 consecutive 429 errors
```

## Success Indicators

✅ **No more 429 errors** in Railway logs  
✅ **Consistent API response times** (2-4 seconds)  
✅ **Circuit breaker rarely opens**  
✅ **All stock data endpoints working**  
✅ **Rate limiter status endpoint accessible**  

## Next Steps

1. **Deploy to Railway** using the steps above
2. **Monitor the deployment** for any build errors
3. **Test the API endpoints** to verify rate limiting is working
4. **Check logs** for rate limiting activity
5. **Verify no more 429 errors** are occurring

## Support

If you continue to experience issues:
1. Check Railway deployment logs
2. Run the verification script locally
3. Test the rate limiter status endpoint
4. Review the troubleshooting section above

The comprehensive rate limiting system should resolve the persistent 429 errors by coordinating all API calls through a single, intelligent rate limiter with automatic recovery mechanisms.
