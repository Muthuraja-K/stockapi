# Admin Cache Management System

## Overview

The Admin Cache Management System provides a comprehensive interface for administrators to manage and refresh all system caches and data files. This is essential when adding new stocks, making changes to existing stocks, or when you need to ensure all data is up-to-date.

## Access

**URL**: `/admin/cache`  
**Access**: Admin users only  
**Authentication**: Required (Bearer token)

## Features

### 🔄 Quick Actions

#### 1. Refresh All Caches
- **Purpose**: Clears and refreshes all system caches simultaneously
- **What it does**:
  - Clears earning summary cache
  - Clears today filter cache
  - Clears general cache
  - Refreshes stock history data
  - Refreshes market data
- **When to use**: After major system changes or when you want to ensure all data is fresh

#### 2. Refresh Stock History
- **Purpose**: Refreshes only stock history and market data
- **What it does**:
  - Populates `stockhistory.json`
  - Populates `stockhistorymarketdata.json`
  - Updates cache timestamps
- **When to use**: After adding/removing stocks or when stock history data seems outdated

#### 3. Force Populate History
- **Purpose**: Forces population of stock history data regardless of cache status
- **What it does**:
  - Bypasses cache validation
  - Downloads fresh data from Yahoo Finance
  - Updates all stock history files
- **When to use**: When cache validation is preventing updates or you need immediate data refresh

#### 4. Get Cache Overview
- **Purpose**: Displays current status of all system caches
- **What it shows**:
  - Earning cache status
  - Today filter cache status
  - Stock history cache status
  - General cache statistics
  - Rate limiter status

### 📊 Cache Status Overview

The system displays real-time status of:
- **Earning Summary Cache**: Status of 1M, 1W, 1D period caches
- **Today Filter Cache**: Status of real-time stock data cache
- **Stock History Cache**: Status of historical data files
- **General Cache**: Overall system cache statistics
- **Rate Limiter**: API rate limiting status

### 📈 System Statistics

Real-time display of:
- Total stocks in system
- Cache entries count
- Last refresh timestamp
- Overall system status

## API Endpoints

### Admin-Only Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/refresh-all-caches` | POST | Refresh all system caches |
| `/api/admin/refresh-stock-history` | POST | Refresh stock history data |
| `/api/admin/force-populate-history` | POST | Force populate history data |
| `/api/admin/cache-overview` | GET | Get comprehensive cache status |

### Authentication

All admin endpoints require:
- Valid authentication token
- Admin role privileges
- Bearer token in Authorization header

## When to Use

### 🆕 Adding New Stocks
1. Add new stock to `stock.json`
2. Navigate to `/admin/cache`
3. Click **"Refresh Stock History"**
4. Verify new stock appears in system

### 🔄 Updating Existing Stocks
1. Modify stock data in `stock.json`
2. Navigate to `/admin/cache`
3. Click **"Refresh Stock History"**
4. Verify changes are reflected

### 🧹 System Maintenance
1. Navigate to `/admin/cache`
2. Click **"Get Cache Overview"**
3. Review cache status
4. Click **"Refresh All Caches"** if needed

### 🚨 Troubleshooting
1. Navigate to `/admin/cache`
2. Click **"Get Cache Overview"**
3. Identify problematic caches
4. Use specific refresh buttons as needed

## File Management

### Stock History Files
- **`stockhistory.json`**: Historical price data for all stocks
- **`stockhistorymarketdata.json`**: Real-time market data from Finviz

### Cache Files
- **Earning Summary Cache**: Cached earning data for 1M, 1W, 1D periods
- **Today Filter Cache**: Real-time stock data cache (1-minute TTL)
- **General Cache**: System-wide cache with 5-minute TTL

## Security Features

- **Admin-only access**: Requires admin role
- **Authentication required**: Valid JWT token needed
- **Audit logging**: All admin actions are logged
- **Rate limiting**: API calls are rate-limited to prevent abuse

## Error Handling

The system provides:
- **Real-time alerts**: Success/error messages for all actions
- **Detailed logging**: Comprehensive error logging for debugging
- **Graceful fallbacks**: System continues operating even if some caches fail
- **Status monitoring**: Real-time status of all cache operations

## Best Practices

### ✅ Do's
- Use specific refresh buttons when possible
- Monitor cache status regularly
- Refresh caches after stock changes
- Use "Get Cache Overview" before major operations

### ❌ Don'ts
- Don't refresh all caches unnecessarily
- Don't ignore error messages
- Don't bypass authentication
- Don't perform operations during peak usage

## Troubleshooting

### Common Issues

#### Cache Not Updating
1. Check authentication status
2. Verify admin privileges
3. Review error messages
4. Try force populate option

#### Slow Performance
1. Check cache overview
2. Clear expired caches
3. Monitor rate limiter status
4. Review system logs

#### Data Not Appearing
1. Verify stock exists in `stock.json`
2. Check cache status
3. Refresh specific caches
4. Review API responses

### Support

For technical issues:
1. Check system logs
2. Review cache overview
3. Verify API endpoints
4. Contact system administrator

## Technical Details

### Cache TTL (Time To Live)
- **Earning Summary**: 24 hours
- **Today Filter**: 1 minute
- **General Cache**: 5 minutes
- **Stock History**: Daily refresh

### Data Sources
- **Stock History**: Yahoo Finance (yfinance)
- **Market Data**: Finviz API
- **Earning Data**: Tiingo API + Yahoo Finance fallback

### Refresh Triggers
- **Automatic**: Daily scheduled refresh
- **Manual**: Admin-initiated refresh
- **Conditional**: Cache validation failures
- **Emergency**: Force populate option

---

**Note**: This system is designed for administrative use only. Regular users should not have access to these functions. Always ensure proper authentication and authorization before performing cache operations.
