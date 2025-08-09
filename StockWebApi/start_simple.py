#!/usr/bin/env python3
"""
Simple startup script for Railway debugging
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    try:
        logger.info("Starting simple startup script...")
        
        # Check environment
        port = os.environ.get("PORT", "8000")
        logger.info(f"PORT environment variable: {port}")
        
        # Try to import the app
        logger.info("Importing main app...")
        from main import app
        logger.info("App imported successfully")
        
        # Try to import uvicorn
        logger.info("Importing uvicorn...")
        import uvicorn
        logger.info(f"Uvicorn version: {uvicorn.__version__}")
        
        # Start the server
        logger.info(f"Starting server on port {port}...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(port),
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
