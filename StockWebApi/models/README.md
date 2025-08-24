# Stock Prediction Models

This directory contains the machine learning models for stock prediction.

## Expected Files

- `lstm_stock_predictor.h5` - LSTM neural network model (Keras format)
- `regression_stock_predictor.pkl` - Linear regression model (Pickle format)

## Current Status

**Note**: These model files are currently **NOT IMPLEMENTED**. The stock prediction service uses placeholder implementations that work without these files.

## Implementation Details

The stock prediction service currently uses:
1. **LSTM Prediction**: Simple trend-based prediction (placeholder)
2. **Regression Prediction**: Linear regression trained on historical data
3. **ChatGPT Analysis**: Disabled (requires OpenAI API key)

## Future Enhancement

To implement actual ML models:
1. Train LSTM model using historical stock data
2. Save as `lstm_stock_predictor.h5`
3. Train regression model and save as `regression_stock_predictor.pkl`
4. Update `stock_prediction_service.py` to load and use these models

## Current Behavior

Without model files, the service:
- ✅ Works correctly using placeholder implementations
- ✅ Provides reasonable predictions based on historical trends
- ✅ Handles missing models gracefully
- ✅ No 500 errors due to missing model files
