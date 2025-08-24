#!/usr/bin/env python3
"""
Test script to debug stock prediction service issues
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all required packages can be imported"""
    try:
        logger.info("Testing imports...")
        
        # Test basic imports
        import fastapi
        logger.info("✓ FastAPI imported successfully")
        
        import yfinance as yf
        logger.info("✓ yfinance imported successfully")
        
        import pandas as pd
        logger.info("✓ pandas imported successfully")
        
        import numpy as np
        logger.info("✓ numpy imported successfully")
        
        import sklearn
        logger.info("✓ scikit-learn imported successfully")
        
        # Test OpenAI import
        try:
            import openai
            logger.info("✓ openai imported successfully")
        except ImportError as e:
            logger.error(f"✗ openai import failed: {e}")
            return False
        
        # Test config
        try:
            from config import config, OPENAI_API_KEY
            logger.info("✓ config imported successfully")
            logger.info(f"OpenAI API Key present: {'Yes' if OPENAI_API_KEY else 'No'}")
        except Exception as e:
            logger.error(f"✗ config import failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Import test failed: {e}")
        return False

def test_stock_prediction_service():
    """Test if stock prediction service can be instantiated"""
    try:
        logger.info("Testing stock prediction service...")
        
        from stock_prediction_service import StockPredictionService
        
        service = StockPredictionService()
        logger.info("✓ StockPredictionService instantiated successfully")
        
        # Test historical data fetch
        logger.info("Testing historical data fetch...")
        data = service._get_historical_data("AAPL", 30)
        
        if data is not None and not data.empty:
            logger.info(f"✓ Historical data fetched successfully: {len(data)} rows")
            logger.info(f"Latest price: ${data['Close'].iloc[-1]:.2f}")
        else:
            logger.warning("⚠ Historical data fetch returned empty data")
        
        return True
        
    except Exception as e:
        logger.error(f"Stock prediction service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment():
    """Test environment variables and configuration"""
    try:
        logger.info("Testing environment...")
        
        # Check if .env file exists
        env_file = ".env"
        if os.path.exists(env_file):
            logger.info(f"✓ .env file found: {env_file}")
        else:
            logger.warning(f"⚠ .env file not found: {env_file}")
        
        # Check models directory
        models_dir = "models"
        if os.path.exists(models_dir):
            logger.info(f"✓ models directory found: {models_dir}")
        else:
            logger.warning(f"⚠ models directory not found: {models_dir}")
        
        # Check required files
        required_files = [
            "stock_prediction_service.py",
            "config.py",
            "main.py"
        ]
        
        for file in required_files:
            if os.path.exists(file):
                logger.info(f"✓ {file} found")
            else:
                logger.error(f"✗ {file} not found")
        
        return True
        
    except Exception as e:
        logger.error(f"Environment test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting stock prediction service tests...")
    
    tests = [
        ("Environment", test_environment),
        ("Imports", test_imports),
        ("Stock Prediction Service", test_stock_prediction_service)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            logger.info(f"{test_name} test: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            logger.error(f"{test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! The service should work correctly.")
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
