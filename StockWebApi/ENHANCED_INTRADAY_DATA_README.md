# Enhanced Intraday Data for Earning Calculations

This document explains the enhanced intraday data system that provides precise Before/After Earning price calculations using 1-minute data instead of daily data.

## 🎯 Overview

The enhanced system automatically fetches **1-minute intraday data** for stocks with earnings on the current day, providing much more accurate calculations for:

- **Close B4 Earning Price & Change**
- **After Earning Price & Change**
- **Precise percentage movements**
- **Better earning surprise detection**

## 🕐 Earning Time Recognition

The system automatically recognizes and handles different earning call times:

### Standard 4:30 PM Earnings
- **Before Earning:** Previous day close → 4:00 PM
- **After Earning:** 4:00 PM → 7:55 PM
- **Calculation:** Uses exact 4:00 PM and 7:55 PM prices

### Alternative 7:55 PM Earnings  
- **Before Earning:** Previous day close → 4:00 PM
- **After Earning:** 4:00 PM → 7:55 PM
- **Calculation:** Same timing, different earning call time

### Custom Earning Times
- **Before Earning:** Previous day close → Earning time
- **After Earning:** Earning time → 3h25m after earning
- **Calculation:** Adapts to any earning announcement time

## 📊 Data Source Priority

The system tries multiple data sources in order of accuracy:

### 1. Tiingo 1-Minute Data (Highest Priority)
```python
# Automatically tries Tiingo first
if tiingo_service.is_available():
    tiingo_data = tiingo_service.get_1min_data_for_date(ticker, date, prepost=True)
    if tiingo_data is not None and not tiingo_data.empty:
        return calculate_precise_prices_from_intraday(ticker, date, tiingo_data, "Tiingo")
```

**Benefits:**
- Includes pre/post market data
- Highest data quality
- Most reliable API

### 2. Yahoo Finance 1-Minute Data (Fallback)
```python
# Falls back to Yahoo Finance if Tiingo fails
yahoo_data = get_yahoo_1min_data(ticker, date)
if yahoo_data is not None and not yahoo_data.empty:
    return calculate_precise_prices_from_intraday(ticker, date, yahoo_data, "Yahoo Finance")
```

**Benefits:**
- Widely available
- Good data coverage
- Reliable fallback

### 3. Daily Data (Final Fallback)
```python
# Uses daily data only when intraday data is unavailable
return get_daily_data_fallback(ticker, date)
```

**Benefits:**
- Always available
- Consistent data
- Basic calculations

## 🔄 Daily 9 PM Job Process

The enhanced daily job now follows this precise process:

### Step 1: Identify Stocks with Earnings Today
```python
# Check if stock has earnings on current day
if earning_date_only == today:
    logger.info(f"🎯 Processing earnings for {ticker} on {today} at {earning_date.strftime('%I:%M %p')}")
```

### Step 2: Recognize Earning Time
```python
# Determine earning call timing
earning_hour = earning_date.hour
earning_minute = earning_date.minute

if earning_hour == 16 and earning_minute == 30:
    logger.info(f"📅 {ticker} has standard 4:30 PM earnings call")
elif earning_hour == 19 and earning_minute == 55:
    logger.info(f"📅 {ticker} has alternative 7:55 PM earnings call")
else:
    logger.info(f"📅 {ticker} has custom earnings time: {earning_date.strftime('%I:%M %p')}")
```

### Step 3: Fetch Precise Intraday Data
```python
# Try Tiingo first, then Yahoo Finance, then daily fallback
price_data = get_price_data_for_earning(ticker, earning_date)
```

### Step 4: Calculate Precise Prices
```python
# Calculate from 1-minute data when available
if intraday_data_available:
    # Close B4 Earning: Previous day close vs 4:00 PM
    # After Earning: 4:00 PM vs 7:55 PM
    logger.info(f"✅ {ticker} Earning: Precise intraday data used")
else:
    logger.warning(f"⚠️ {ticker} Earning: Fallback to daily data")
```

## 📈 Price Calculation Examples

### Example 1: AAPL with 4:30 PM Earnings
```
Earning Date: 7/31/2025 4:30:00 PM

Previous Day Close: $148.50
4:00 PM Price: $149.25  
7:55 PM Price: $152.00

Close B4 Earning: $148.50 → $149.25 (+0.51%)
After Earning: $149.25 → $152.00 (+1.84%)
```

### Example 2: MSFT with 7:55 PM Earnings
```
Earning Date: 7/31/2025 7:55:00 PM

Previous Day Close: $420.00
4:00 PM Price: $421.50
7:55 PM Price: $425.00

Close B4 Earning: $420.00 → $421.50 (+0.36%)
After Earning: $421.50 → $425.00 (+0.83%)
```

## 🧪 Testing the Enhanced System

### Test Script
Use the dedicated test script to verify functionality:

```bash
python test_intraday_earning_data.py AAPL
python test_intraday_earning_data.py MSFT
```

### Test Results
The test script provides detailed analysis:

```
📊 Test 1: Standard 4:30 PM Earning Time
✅ 4:30 PM Test: Precise intraday data available

📊 Test 2: Alternative 7:55 PM Earning Time  
✅ 7:55 PM Test: Precise intraday data available

📊 Test 3: Custom Earning Time (2:00 PM)
✅ Custom Time Test: Precise intraday data available

🎉 EXCELLENT: 100% precision rate - All tests used precise intraday data!
```

## 🔧 Configuration Requirements

### Tiingo Service
```python
# Ensure Tiingo API key is configured
TIINGO_API_KEY = "your_api_key_here"

# Check availability
if tiingo_service.is_available():
    print("✅ Tiingo service available")
else:
    print("❌ Tiingo service not available")
```

### Yahoo Finance
```python
# Yahoo Finance is automatically available
# No additional configuration required
```

### Finviz Fallback
```python
# Optional: Configure Finviz for additional data
FINVIZ_AUTH_ID = "your_auth_id_here"
```

## 📊 Performance Benefits

### Data Accuracy
- **Before:** Daily data (previous close vs current open)
- **After:** Daily data (current open vs current close)
- **Enhanced:** 1-minute data (exact 4:00 PM vs 7:55 PM)

### Trading Signals
- **More reliable:** Precise price levels
- **Better timing:** Exact earning call reactions
- **Risk management:** Accurate stop loss levels

### Earning Analysis
- **Surprise detection:** Accurate revenue/EPS vs expectations
- **Market reaction:** Precise price movements
- **Pattern recognition:** Better historical analysis

## 🚨 Troubleshooting

### Common Issues

#### 1. Intraday Data Not Available
```python
# Check Tiingo availability
if not tiingo_service.is_available():
    logger.warning("Tiingo not available, using Yahoo Finance fallback")

# Check Yahoo Finance data
yahoo_data = get_yahoo_1min_data(ticker, date)
if yahoo_data is None or yahoo_data.empty:
    logger.warning("Yahoo Finance 1-minute data not available, using daily fallback")
```

#### 2. Earning Time Recognition Issues
```python
# Verify earning date format
earning_date = datetime.strptime(earning_date_str, '%m/%d/%Y %I:%M:%S %p')
logger.info(f"Parsed earning time: {earning_date.strftime('%I:%M %p')}")
```

#### 3. Data Source Priority
```python
# Check data source availability
logger.info(f"Tiingo available: {tiingo_service.is_available()}")
logger.info(f"Yahoo Finance 1-min data: {len(yahoo_data) if yahoo_data is not None else 0} points")
```

### Debug Commands
```bash
# Test intraday functionality
python test_intraday_earning_data.py <TICKER>

# Debug revenue data
python debug_revenue.py <TICKER>

# Test Finviz integration
python test_finviz_integration.py <TICKER>
```

## 🔮 Future Enhancements

### Planned Improvements
1. **Real-time alerts:** WebSocket notifications for earning announcements
2. **Machine learning:** Predict earning surprises from intraday patterns
3. **Advanced timing:** Support for international market hours
4. **Data validation:** Schema validation for intraday data integrity

### Potential Features
1. **Custom time windows:** User-defined Before/After Earning periods
2. **Multi-timeframe analysis:** 1-min, 5-min, and daily comparisons
3. **Earning calendar integration:** Automatic earning date detection
4. **Performance metrics:** Track calculation accuracy over time

## 📚 Related Documentation

- [Earning Summary File System](EARNING_SUMMARY_FILE_SYSTEM_README.md)
- [Finviz Integration](test_finviz_integration.py)
- [Revenue Debugging](debug_revenue.py)
- [Main API Documentation](README.md)

## 🎉 Summary

The enhanced intraday data system provides:

✅ **Precise timing recognition** for all earning call times  
✅ **1-minute data priority** for maximum accuracy  
✅ **Intelligent fallbacks** when high-quality data unavailable  
✅ **Better trading signals** from accurate price calculations  
✅ **Automatic daily updates** at 9 PM with precise data  
✅ **Comprehensive testing** tools for verification  

This system ensures that your earning summary data is as accurate as possible, using the best available data sources to provide precise Before/After Earning calculations.
