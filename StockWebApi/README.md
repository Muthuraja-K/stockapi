# Stock Prediction API

A FastAPI-based stock prediction and analysis API with enhanced stock details functionality.

## Features

- **Enhanced Stock Details**: Comprehensive stock data with time-based analysis (1D, 5D, 1M, 6M, 1Y)
- **Real-time Price Updates**: Live price and today's change updates with configurable intervals
- **Smart Caching**: Daily caching system with automatic updates
- **Advanced Filtering**: Filter by sector, ticker, and leverage type
- **Sorting**: Sort by any column with percentage-based sorting for time periods
- **Authentication**: JWT-based authentication with role-based access
- **Stock Management**: CRUD operations for stocks, sectors, and users
- **Sentiment Analysis**: Stock sentiment analysis with news and social media data
- **Earnings Summary**: Earnings data analysis and reporting
- **Stock Summary**: Historical stock performance summaries

## Project Structure

### Backend (StockWebApi/)

```
StockWebApi/
├── main.py                          # FastAPI application with all endpoints
├── models.py                        # Pydantic models for request/response
├── enhanced_stock_operations.py     # Enhanced stock data processing
├── stock_operations.py              # Basic stock CRUD operations
├── auth_operations.py               # Authentication and user management
├── sector_operations.py             # Sector management
├── user_operations.py               # User management
├── stock_summary.py                 # Stock summary functionality
├── earning_summary.py               # Earnings summary functionality
├── sentiment_analysis.py            # Sentiment analysis
├── history_cache.py                 # Historical data caching
├── utils.py                         # Utility functions
├── requirements.txt                 # Python dependencies
├── stock.json                       # Stock data storage
├── sector.json                      # Sector data storage
├── user.json                        # User data storage
├── Ticker_Today.json                # Enhanced stock data cache (auto-generated)
└── static/                          # Frontend build files
```

### Frontend (StockUI/)

```
StockUI/src/app/
├── stock-info/
│   ├── stocks.component.ts          # Stock management component
│   ├── stock-info.service.ts        # Stock data service
│   ├── sentiment.service.ts         # Sentiment service
│   └── models.ts                    # TypeScript interfaces
├── stockhistory/
│   ├── stock-history.component.ts   # Enhanced stock history component
│   ├── stock-history.component.html # Stock history template
│   └── stock-history.component.scss # Stock history styles
├── sector/
│   ├── sector.component.ts          # Sector management component
│   ├── sector.component.html        # Sector template
│   ├── sector.component.scss        # Sector styles
│   └── sector.service.ts            # Sector service
├── auth/                            # Authentication components
├── stock-summary/                   # Stock summary components
├── earning-summary/                 # Earnings summary components
├── download/                        # Download components
└── user/                            # User management components
```

## API Endpoints

### Enhanced Stock Details
- `GET /api/getenhancedstockdetails` - Get comprehensive stock data with time-based analysis
- `GET /api/realtime-prices` - Get real-time price and today's change updates
- `POST /api/update-ticker-data` - Manually trigger data update

### Basic Stock Operations
- `GET /api/getstock` - Get basic stock list with pagination
- `GET /api/getstockdetails` - Get detailed stock information (legacy)
- `POST /api/stocks` - Add new stock
- `PUT /api/stocks/update` - Update stock
- `POST /api/stocks/delete` - Delete stock

### Authentication
- `POST /api/login` - User login
- `POST /api/verify-token` - Verify JWT token

### Other Features
- `GET /api/sectors` - Get sectors
- `GET /api/users` - Get users (admin only)
- `GET /api/stock-summary` - Get stock summaries
- `GET /api/earning-summary` - Get earnings summaries
- `GET /api/sentiment/{ticker}` - Get sentiment analysis
- `GET /api/download/{file_type}` - Download data files

## Enhanced Stock Details Features

### Data Structure
Each stock record includes:
- **Basic Info**: Ticker, Sector, Market Cap, Earnings Date
- **Current Data**: Current Price, Today's Low/High/Change
- **Time-based Analysis**: 1D, 5D, 1M, 6M, 1Y with Low/High/Percentage Change

### Smart Refresh Logic
- **Current Price & Today's Data**: Updates at user-defined intervals (1M, 5M, 15M, 1H)
- **Historical Data**: Only updates when date changes or cache is invalid
- **Daily Cache**: `Ticker_Today.json` stores comprehensive data and updates daily

### Filtering Options
- **Sector**: Filter by specific sector
- **Ticker**: Filter by ticker symbols
- **Leverage**: 
  - "Ticker Only" - Regular stocks only
  - "Leverage Only" - Leveraged stocks only
  - "Both" - All stocks

### Sorting
- Sort by any column
- Time-based columns sort by percentage change, not low/high values
- Default sort: Today's percentage change (descending)

## Installation & Setup

### Backend Setup
```bash
cd StockWebApi
pip install -r requirements.txt
python main.py
```

### Frontend Setup
```bash
cd StockUI
npm install
ng serve
```

## Data Files

### stock.json
Contains basic stock information:
```json
{
  "ticker": "AAPL",
  "sector": "Technology",
  "isxticker": false
}
```

### Ticker_Today.json (Auto-generated)
Contains enhanced stock data with time-based analysis:
```json
{
  "ticker": "AAPL",
  "sector": "Technology",
  "isxticker": false,
  "market_cap": "$2.5T",
  "earning_date": "2024-01-25",
  "current_price": "$150.25",
  "today": {
    "low": "$149.50",
    "high": "$151.00",
    "percentage": "+2.5%"
  },
  "previous_day": { ... },
  "five_day": { ... },
  "one_month": { ... },
  "six_month": { ... },
  "one_year": { ... }
}
```

## Performance Optimizations

- **Parallel Processing**: Uses ThreadPoolExecutor for concurrent API calls
- **Smart Caching**: In-memory cache with TTL and file-based daily cache
- **Batch Processing**: Processes stocks in batches to avoid rate limiting
- **Connection Pooling**: Optimized HTTP session with retry strategy

## Security

- JWT-based authentication
- Role-based access control (admin/user)
- Input validation with Pydantic models
- CORS configuration for frontend integration

## Monitoring

- Comprehensive logging throughout the application
- Performance middleware for request tracking
- Error handling and fallback mechanisms

## Trading Disclaimer

**Trading involves significant risk and may not suit all investors. The information on this website serves educational and informational purposes only and is not trading or investment advice.** 