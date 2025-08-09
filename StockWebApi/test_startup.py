#!/usr/bin/env python3
"""
Test script to verify that the application can start properly
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import fastapi
        print(f"✓ FastAPI {fastapi.__version__}")
    except ImportError as e:
        print(f"✗ FastAPI import failed: {e}")
        return False
    
    try:
        import uvicorn
        print(f"✓ Uvicorn {uvicorn.__version__}")
    except ImportError as e:
        print(f"✗ Uvicorn import failed: {e}")
        return False
    
    try:
        from main import app
        print("✓ Main app imported successfully")
    except ImportError as e:
        print(f"✗ Main app import failed: {e}")
        return False
    
    return True

def test_static_files():
    """Test if static files directory exists"""
    print("\nTesting static files...")
    
    if os.path.exists("static"):
        print("✓ Static directory exists")
        if os.path.exists("static/index.html"):
            print("✓ index.html exists")
            return True
        else:
            print("✗ index.html not found")
            return False
    else:
        print("✗ Static directory not found")
        return False

def main():
    """Main test function"""
    print("Stock Prediction API - Startup Test")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        sys.exit(1)
    
    # Test static files
    if not test_static_files():
        print("\n❌ Static files test failed")
        sys.exit(1)
    
    print("\n✅ All tests passed! Application should start successfully.")
    print("\nTo start the application, run:")
    print("uvicorn main:app --host 0.0.0.0 --port $PORT")

if __name__ == "__main__":
    main()
