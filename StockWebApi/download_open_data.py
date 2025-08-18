import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_open_stock_data():
    """Download 1 year of OPEN stock data and save as CSV"""
    try:
        logger.info("Starting download of OPEN stock data...")
        
        # Download 1 year of data for OPEN stock
        # Using period="1y" to get exactly 1 year of data
        open_data = yf.download("OPEN", period="1y", interval="1d", progress=True)
        
        if open_data.empty:
            logger.error("No data received for OPEN stock")
            return False
        
        logger.info(f"Downloaded {len(open_data)} days of data for OPEN stock")
        logger.info(f"Date range: {open_data.index[0].date()} to {open_data.index[-1].date()}")
        
        # Display data info
        logger.info(f"Columns available: {list(open_data.columns)}")
        logger.info(f"Data shape: {open_data.shape}")
        
        # Show first few rows
        logger.info("\nFirst 5 rows of data:")
        logger.info(open_data.head())
        
        # Show last few rows
        logger.info("\nLast 5 rows of data:")
        logger.info(open_data.tail())
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"OPEN_stock_data_1year_{timestamp}.csv"
        
        # Save to CSV
        open_data.to_csv(csv_filename)
        logger.info(f"Data saved to {csv_filename}")
        
        # Also save to Excel format
        excel_filename = f"OPEN_stock_data_1year_{timestamp}.xlsx"
        open_data.to_excel(excel_filename, engine='openpyxl')
        logger.info(f"Data also saved to {excel_filename}")
        
        # Display summary statistics
        logger.info("\nSummary Statistics:")
        logger.info(open_data.describe())
        
        # Show data types
        logger.info("\nData Types:")
        logger.info(open_data.dtypes)
        
        # Check for missing values
        logger.info("\nMissing Values:")
        logger.info(open_data.isnull().sum())
        
        return True
        
    except Exception as e:
        logger.error(f"Error downloading OPEN stock data: {e}")
        return False

if __name__ == "__main__":
    success = download_open_stock_data()
    if success:
        print("\n✅ OPEN stock data downloaded successfully!")
        print("Check the current directory for CSV and Excel files.")
    else:
        print("\n❌ Failed to download OPEN stock data.")
