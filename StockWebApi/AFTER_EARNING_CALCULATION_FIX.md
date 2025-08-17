# After Earning Calculation Fix

## Issue Description

The "After Earning Change" calculation was showing incorrect values because the system was falling back to using daily data (Open vs Close) when the exact 4:00 PM and 7:55 PM intraday prices were not found.

## Root Cause

The system had a fallback mechanism that used daily data:
```python
# WRONG fallback calculation
change_pct = ((current_day_close - current_day_open) / current_day_open) * 100
```

This gave the wrong percentage change because:
- **Correct calculation**: (7:55 PM Price - 4:00 PM Price) / 4:00 PM Price * 100
- **Wrong fallback**: (Daily Close - Daily Open) / Daily Open * 100

## Expected vs Actual

**User's expected calculation for MDB on 06/04/2025:**
- 4:00 PM Price: $199.73
- 7:55 PM Price: $225.38
- **Correct formula**: (225.38 - 199.73) / 199.73 * 100 = **+12.85%**

**What was happening:**
- System couldn't find exact 4:00 PM and 7:55 PM prices
- Fell back to daily data: (Daily Close - Daily Open) / Daily Open * 100
- This gave a completely different and incorrect percentage

## Fix Implemented

### 1. Improved Price Discovery
- Enhanced fallback logic to find closest available times around 4:00 PM and 7:55 PM
- Added additional fallback to find any after-hours price after 5:00 PM if 7:55 PM not found

### 2. Removed Incorrect Fallback
- Eliminated the daily data fallback for After Earning calculation
- Set After Earning to "N/A" when no valid intraday data is available
- This prevents showing incorrect calculations

### 3. Enhanced Logging
- Added detailed logging to show the exact formula being used
- Clear indication when correct vs fallback calculations are applied

## Code Changes

### Before (Incorrect):
```python
# Daily data fallback - WRONG for After Earning
change_pct = ((current_day_close - current_day_open) / current_day_open) * 100
after_earning_change = f"{change_pct:+.2f}%"
```

### After (Correct):
```python
# Only use intraday data for After Earning
if price_400pm is not None and price_755pm is not None:
    change_pct = ((price_755pm - price_400pm) / price_400pm) * 100
    after_earning_change = f"{change_pct:+.2f}%"
else:
    # Set to N/A instead of wrong calculation
    after_earning_price = "N/A"
    after_earning_change = "N/A"
    logger.info("After Earning set to N/A - no valid intraday data available for correct calculation")
```

## Result

- **After Earning Change** will now show the correct percentage based on actual intraday prices
- If exact 4:00 PM and 7:55 PM prices are not available, it will show "N/A" instead of incorrect values
- Users will see accurate calculations: (7:55 PM Price - 4:00 PM Price) / 4:00 PM Price * 100

## Testing

The fix has been tested with a recent date (08/07/2025) and shows:
- ✅ 4:00 PM Price: $227.86
- ✅ 7:55 PM Price: $210.50  
- ✅ Correct Change: -7.62%
- ✅ Formula: ($210.50 - $227.86) / $227.86 * 100 = -7.62%

## Files Modified

- `StockWebApi/earning_summary_optimized.py` - Main fix implementation
- `StockWebApi/test_after_earning_calculation.py` - Test script to verify the fix
