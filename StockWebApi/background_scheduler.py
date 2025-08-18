import asyncio
import threading
import time
import logging
from datetime import datetime
from stock_history_operations import stock_history_ops

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundScheduler:
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        self.history_populated_today = False
        
    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.info("Scheduler is already running")
            return
            
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Background scheduler started")
        
    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Background scheduler stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check if we need to populate history data (once per day)
                if not self.history_populated_today or stock_history_ops.should_populate_history():
                    logger.info("Populating stock history data...")
                    if stock_history_ops.populate_stock_history():
                        self.history_populated_today = True
                        logger.info("Stock history data populated successfully")
                    else:
                        logger.error("Failed to populate stock history data")
                
                # Check if we need to populate market data (every minute)
                if stock_history_ops.should_populate_market_data():
                    logger.info(f"Populating stock market data at {current_time.strftime('%H:%M:%S')}...")
                    if stock_history_ops.populate_stock_market_data():
                        logger.info(f"Stock market data populated successfully at {current_time.strftime('%H:%M:%S')}")
                    else:
                        logger.error(f"Failed to populate stock market data at {current_time.strftime('%H:%M:%S')}")
                else:
                    logger.debug(f"Market data is up-to-date, skipping update at {current_time.strftime('%H:%M:%S')}")
                
                # Reset history populated flag at midnight
                if current_time.hour == 0 and current_time.minute == 0:
                    self.history_populated_today = False
                
                # Refresh earning summary cache at 6 AM (market open preparation)
                if current_time.hour == 6 and current_time.minute == 0:
                    try:
                        logger.info("Refreshing earning summary cache...")
                        from earning_summary_cache import earning_cache, pre_warm_cache
                        
                        # Refresh 1M period (1D and 1W will filter from this)
                        try:
                            earning_cache.get_or_fetch_summary('1M')
                            logger.info("Refreshed earning summary cache for period 1M (1D and 1W will filter from this)")
                        except Exception as e:
                            logger.error(f"Error refreshing cache for period 1M: {e}")
                        
                        # Pre-warm cache with common sector combinations (1M only, 1D/1W filter from it)
                        try:
                            pre_warm_cache()
                        except Exception as e:
                            logger.error(f"Error pre-warming cache: {e}")
                        
                        logger.info("Earning summary cache refresh and pre-warming completed (1M only, 1D/1W filter from it)")
                    except Exception as e:
                        logger.error(f"Error in earning summary cache refresh: {e}")
                
                # Wait for 30 seconds before next check for more responsive market data updates
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait before retrying
                
    def get_status(self):
        """Get scheduler status"""
        return {
            "running": self.running,
            "history_populated_today": self.history_populated_today,
            "last_check": datetime.now().isoformat()
        }

# Global scheduler instance
background_scheduler = BackgroundScheduler()

def start_background_scheduler():
    """Start the background scheduler"""
    background_scheduler.start()

def stop_background_scheduler():
    """Stop the background scheduler"""
    background_scheduler.stop()

def get_scheduler_status():
    """Get the scheduler status"""
    return background_scheduler.get_status()
