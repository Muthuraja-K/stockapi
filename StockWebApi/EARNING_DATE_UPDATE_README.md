# Earning Date Update Job - 10 PM Background Job

## Overview

The earning date update job has been reorganized to run as a separate background job at 10 PM, after the main daily earning job completes at 9 PM. This separation provides better performance and reliability.

## Job Schedule

### 9:00 PM - Daily Earning Job
- **Purpose**: Update earnings for stocks with earnings today
- **Function**: `run_daily_earning_job()`
- **Scope**: Only stocks that have earnings on the current day
- **Performance**: Fast execution, focused scope

### 10:00 PM - Earning Date Update Job
- **Purpose**: Update earning dates for all stocks from stock.json
- **Function**: `update_earning_dates_from_finviz()`
- **Scope**: All regular stocks (excluding leverage/crypto)
- **Performance**: Single Finviz API call for all stocks

## Key Features

### 1. Stock Filtering
- **Includes**: Regular stocks from `stock.json`
- **Excludes**: Stocks with `isleverage: true` (leveraged ETFs, crypto)
- **Source**: Reads directly from `stock.json` file

### 2. Single API Call Optimization
- **Finviz API**: Single batch request for all stocks
- **Columns**: Only ticker and earnings date (minimal data transfer)
- **Timeout**: 60 seconds for large batch requests
- **Efficiency**: Reduces API calls from N to 1

### 3. Smart Data Management
- **Existing Records**: Updates earning dates for existing stocks
- **New Records**: Creates new records for stocks not in earning summary
- **Preservation**: Maintains existing `lastTwoEarnings` data
- **Sector Mapping**: Preserves sector information from stock.json

## Implementation Details

### Background Scheduler
```python
# 9 PM - Daily earning job
if current_time.hour == 21 and current_time.minute == 0:
    run_daily_earning_job()

# 10 PM - Earning date update job
if current_time.hour == 22 and current_time.minute == 0:
    update_earning_dates_job()
```

### Finviz Service Integration
```python
def get_earning_dates_batch(self, stocks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Get earning dates for multiple stocks in a single API call.
    Optimized for the 10 PM earning date update job.
    """
    # Single API call with minimal columns
    params = {
        'v': '152',  # View 152
        't': ','.join(tickers),  # Multiple tickers
        'c': '1,11',  # Ticker and Earnings Date only
        'auth': self.auth_id
    }
```

### Data Structure
```json
{
  "ticker": "AAPL",
  "currentPrice": "N/A",
  "earningDate": "7/31/2025 4:30:00 PM",
  "sector": "Technology",
  "lastTwoEarnings": []
}
```

## API Endpoints

### Manual Execution (Admin Only)

#### 1. Daily Earning Job
```http
POST /api/admin/run-daily-earning-job
Authorization: Bearer {token}
```

#### 2. Earning Date Update Job
```http
POST /api/admin/update-earning-dates
Authorization: Bearer {token}
```

## Testing

### Test Script
```bash
python test_earning_date_update.py
```

### Manual Testing
1. **Start Background Scheduler**: The jobs run automatically
2. **Monitor Logs**: Check for 9 PM and 10 PM job execution
3. **Verify Data**: Check `earningsummary.json` for updated earning dates
4. **API Testing**: Use admin endpoints for manual execution

## Benefits of New Structure

### 1. **Performance**
- 9 PM job: Fast execution for daily earnings
- 10 PM job: Single API call for all earning dates

### 2. **Reliability**
- Separated concerns reduce failure impact
- Independent execution and error handling
- Better logging and monitoring

### 3. **Maintainability**
- Clear separation of responsibilities
- Easier debugging and troubleshooting
- Modular design for future enhancements

### 4. **Resource Management**
- Reduced API rate limiting impact
- Better memory management
- Optimized database/file operations

## Configuration

### Required Environment Variables
```bash
FINVIZ_AUTH_ID=your_finviz_auth_id
```

### File Dependencies
- `stock.json`: Source of stock information
- `earningsummary.json`: Target file for updates
- `finviz_service.py`: API integration service

## Monitoring and Logging

### Job Execution Logs
```
INFO: Running daily earning summary job at 9 PM...
INFO: Daily earning summary job completed successfully
INFO: Running earning date update job at 10 PM...
INFO: Earning date update job completed successfully
```

### Performance Metrics
- **9 PM Job**: Execution time, success rate
- **10 PM Job**: Stocks processed, API response time
- **Overall**: Data consistency, file update success

## Troubleshooting

### Common Issues

#### 1. **Finviz API Failures**
- Check `FINVIZ_AUTH_ID` configuration
- Verify API rate limits
- Check network connectivity

#### 2. **File Access Issues**
- Ensure write permissions for `earningsummary.json`
- Check disk space availability
- Verify file path configuration

#### 3. **Stock Data Issues**
- Validate `stock.json` format
- Check for missing ticker symbols
- Verify sector mapping

### Debug Commands
```bash
# Test earning date update
python test_earning_date_update.py

# Check background scheduler status
curl -H "Authorization: Bearer {token}" http://localhost:8000/api/admin/cache/status

# Manual job execution
curl -X POST -H "Authorization: Bearer {token}" http://localhost:8000/api/admin/update-earning-dates
```

## Future Enhancements

### 1. **Incremental Updates**
- Only update stocks with changed earning dates
- Reduce unnecessary API calls

### 2. **Retry Logic**
- Implement exponential backoff for API failures
- Queue failed updates for retry

### 3. **Performance Monitoring**
- Track API response times
- Monitor job execution metrics
- Alert on job failures

### 4. **Data Validation**
- Validate earning date formats
- Check for data consistency
- Implement data quality metrics
