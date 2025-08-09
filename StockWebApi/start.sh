#!/bin/bash

# Debug information
echo "Starting Stock Prediction API..."
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "ERROR: Python not found!"
    exit 1
fi

# Check if uvicorn is installed
echo "Checking uvicorn installation..."
python -c "import uvicorn; print('Uvicorn version:', uvicorn.__version__)" || {
    echo "ERROR: Uvicorn not found! Installing dependencies..."
    pip install -r requirements.txt
}

# Check if main.py exists
if [ -f "main.py" ]; then
    echo "main.py found"
else
    echo "ERROR: main.py not found!"
    exit 1
fi

# Start the application
echo "Starting application with uvicorn..."
exec python -m uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
