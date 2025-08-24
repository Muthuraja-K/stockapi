# Earning Summary File System

This document describes the new earning summary system that stores data in `earningsummary.json` instead of dynamically fetching from APIs.

## Overview

The earning summary system has been redesigned to:
1. **Store data persistently** in `earningsummary.json` file
2. **Update automatically** via daily jobs at 9 PM
3. **Provide faster UI response** by reading from file instead of API calls
4. **Maintain data consistency** with proper Before/After Earning calculations

## File Structure

The `earningsummary.json` file contains an array of stock objects:

```json
[
  {
    "ticker": "AAPL",
    "currentPrice": "$150.00",
    "earningDate": "7/31/2025 4:30:00 PM",
    "sector": "Technology",
    "companyName": "Apple Inc.",
    "marketCap": "$2.5T",
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
```

## Key Components

### 1. EarningSummaryFileManager (`earning_summary_file_manager.py`)

Main class that manages the `earningsummary.json` file:

- **`populate_initial_earning_summary()`** - Creates initial file with all stocks
- **`update_daily_earnings()`** - Updates earnings for stocks with earnings today
- **`find_new_earning_dates()`** - Finds new earning dates for stocks with null dates
- **`run_daily_job()`** - Runs the complete daily job

### 2. Background Scheduler Integration

The background scheduler now runs the earning summary job at **9 PM daily**:

```python
# Run earning summary daily job at 9 PM
if current_time.hour == 21 and current_time.minute == 0:
    from earning_summary_file_manager import run_daily_earning_job
    success = run_daily_earning_job()
```

### 3. API Endpoint Changes

The `/api/earning-summary` endpoint now:
- Reads from `earningsummary.json` instead of dynamic API calls
- Applies period filtering (1D, 1W, 1M, custom)
- Applies sector filtering
- Provides pagination
- **No changes to UI required** - same response format

## Setup Instructions

### Step 1: Initial Population

Run the initial population script to create the `earningsummary.json` file:

```bash
cd StockWebApi
python populate_earning_summary.py
```

This will:
- Read all stocks from `stock.json`
- Fetch current prices and earning data
- Calculate Before/After Earning prices
- Save everything to `earningsummary.json`

### Step 2: Verify File Creation

Check that `earningsummary.json` was created in the StockWebApi directory:

```bash
ls -la earningsummary.json
```

### Step 3: Test the API

The API endpoint `/api/earning-summary` should now return data from the file instead of making external API calls.

## Daily Job Process

Every day at 9 PM, the system automatically:

1. **Updates earnings for stocks with earnings today:**
   - **Identifies stocks with earnings on the current day**
   - **Uses precise 1-minute intraday data** for accurate calculations
   - **Recognizes earning times:** 4:30 PM, 7:55 PM, or custom times
   - **Calculates precise Before/After Earning prices:**
     - Close B4 Earning: Previous day close vs 4:00 PM
     - After Earning: 4:00 PM vs 7:55 PM
   - Updates `lastTwoEarnings` (keeps only latest 2)
   - Updates `earningDate` with next earning date

2. **Finds new earning dates:**
   - Searches for stocks with null earning dates
   - Updates with newly announced earning dates

**Data Quality:** The 9 PM job prioritizes intraday data for maximum accuracy, falling back to daily data only when necessary.

## Admin Endpoints

New admin endpoints for managing the system:

### Populate Initial File
```
POST /api/admin/populate-earning-summary-file
```
Creates the initial `earningsummary.json` file.

### Run Daily Job Manually
```
POST /api/admin/run-daily-earning-job
```
Manually triggers the daily earning job.

## Data Quality Improvements

### Fixed Revenue/EPS Fetching

The new system includes improved data fetching:

- **Multiple revenue sources:** Estimates, financials, quarterly data
- **Better EPS handling:** Proper NaN value handling
- **Revenue formatting:** Automatic unit conversion (M, B, T)
- **Category determination:** Smart detection of Reported/Estimate/Surprise
- **Finviz fallback:** Alternative data source when Yahoo Finance fails

### Enhanced Before/After Earning Logic

**Precise 1-minute intraday data calculations:**

- **Close B4 Earning:** Previous day close vs 4:00 PM (or earning time)
- **After Earning:** 4:00 PM vs 7:55 PM (or 3h25m after earning)
- **Data sources priority:**
  1. **Tiingo 1-minute data** (most accurate)
  2. **Yahoo Finance 1-minute data** (fallback)
  3. **Daily data** (final fallback)
- **Earning time recognition:**
  - Standard: 4:30 PM earnings call
  - Alternative: 7:55 PM earnings call
  - Custom: Any other earning time
- **Precise timing:** Finds closest available 1-minute data points

## Troubleshooting

### Common Issues

1. **File not found:**
   - Run `python populate_earning_summary.py`
   - Check file permissions

2. **Daily job not running:**
   - Verify background scheduler is running
   - Check logs for 9 PM job execution

3. **Data not updating:**
   - Check earning dates in `earningsummary.json`
   - Verify Yahoo Finance API access

4. **Revenue/EPS showing as N/A:**
   - Run `python debug_revenue.py <TICKER>` to diagnose
   - Check if Finviz fallback is working
   - Verify `FINVIZ_AUTH_ID` environment variable is set

5. **Percentage Difference showing as N/A:**
   - Run `python debug_eps_data.py <TICKER>` to diagnose EPS data
   - Check if both actual and expected EPS values are available
   - Verify EPS column names in Yahoo Finance data
   - Check if Finviz fallback provides EPS data

### Logs

Check the application logs for:
- Initial population progress
- Daily job execution
- Data update counts
- Error messages

## Migration Notes

### What Changed

- **Data source:** File-based instead of API-based
- **Update frequency:** Daily at 9 PM instead of on-demand
- **Performance:** Faster UI response (no external API calls)
- **Reliability:** Consistent data structure

### What Stayed the Same

- **UI component:** No changes required
- **API response format:** Identical structure
- **Filtering:** Same period and sector filters
- **Pagination:** Same pagination logic

## Enhanced Intraday Data Benefits

The new system provides significant improvements in earning data accuracy:

### 🎯 **Precise Timing Recognition**
- **4:30 PM earnings:** Standard market close earnings calls
- **7:55 PM earnings:** Alternative after-hours earnings calls  
- **Custom times:** Any other earning announcement time

### 📊 **Accurate Price Calculations**
- **Before Earning:** Previous day close → 4:00 PM (or earning time)
- **After Earning:** 4:00 PM → 7:55 PM (or 3h25m after earning)
- **Percentage changes:** Calculated from exact intraday prices

### 🔄 **Data Source Priority**
1. **Tiingo 1-minute data** - Highest accuracy, includes pre/post market
2. **Yahoo Finance 1-minute data** - Reliable fallback option
3. **Daily data** - Final fallback when intraday unavailable

### 💡 **Trading Benefits**
- **Better surprise detection:** Accurate revenue/EPS vs expectations
- **Reliable signals:** Precise Before/After Earning movements
- **Risk management:** Exact price levels for stop losses
- **Timing optimization:** Know when to enter/exit positions

## Future Enhancements

Potential improvements:

1. **Real-time updates:** WebSocket notifications for earning announcements
2. **Data validation:** Schema validation for file integrity
3. **Backup system:** Automatic backup of earning data
4. **Performance monitoring:** Track file read/write performance
5. **Data compression:** Compress historical earning data
6. **Machine learning:** Predict earning surprises based on intraday patterns

## Support

For issues or questions:

1. Check the application logs
2. Verify file permissions and existence
3. Test admin endpoints manually
4. Review this documentation
5. Use debug tools:
   - `python debug_revenue.py <TICKER>` - Debug revenue/EPS issues
   - `python debug_eps_data.py <TICKER>` - Debug EPS data and percentage difference issues
   - `python test_finviz_integration.py <TICKER>` - Test Finviz integration
   - `python test_intraday_earning_data.py <TICKER>` - Test enhanced intraday data functionality

The system is designed to be self-maintaining once properly set up, with daily automatic updates ensuring data freshness.
