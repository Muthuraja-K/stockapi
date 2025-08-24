"""
Stock Prediction Service

This service provides comprehensive stock prediction using:
1. LSTM Neural Network for price prediction
2. Linear Regression for trend analysis
3. ChatGPT integration for fundamental and technical analysis (Currently Disabled)
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import requests
import openai
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
import yfinance as yf
from config import OPENAI_API_KEY, LSTM_MODEL_PATH, REGRESSION_MODEL_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockPredictionService:
    def __init__(self):
        self.openai_api_key = OPENAI_API_KEY
        if not self.openai_api_key:
            logger.error("OpenAI API key not found! Please check your .env file.")
            logger.error("ChatGPT analysis will not work without a valid API key.")
        else:
            logger.info("OpenAI API key loaded successfully")
            # Configure OpenAI client
            openai.api_key = self.openai_api_key
            
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        # Initialize models (placeholder - you'll need to train these)
        self.lstm_model = None
        self.regression_model = None
        self.scaler = MinMaxScaler()
        
        # Cache for predictions
        self.prediction_cache = {}
        
    def get_stock_prediction(self, ticker: str, model_type: str = "both", days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive stock prediction using specified model types.
        
        Args:
            ticker: Stock ticker symbol
            model_type: "chatgpt", "lstm", "regression", or "both" (ChatGPT currently disabled)
            days: Number of days to predict
            
        Returns:
            Dictionary containing prediction results
        """
        try:
            logger.info(f"Starting stock prediction for {ticker} using {model_type}")
            
            # Prevent ChatGPT calls - redirect to other models
            if model_type == "chatgpt":
                model_type = "both"  # Automatically switch to both models instead
                logger.info(f"ChatGPT disabled for {ticker} - switching to combined models")
            
            # Get historical data
            historical_data = self._get_historical_data(ticker)
            if historical_data is None or historical_data.empty:
                return {"error": f"No historical data available for {ticker}"}
            
            result = {
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "model_type": model_type,
                "prediction_days": days,
                "current_price": float(historical_data['Close'].iloc[-1]),
                "current_date": datetime.now().strftime('%Y-%m-%d')
            }
            
            # Run predictions based on model type
            if model_type in ["lstm", "both"]:
                lstm_result = self._run_lstm_prediction(ticker, historical_data, days)
                result["lstm_prediction"] = lstm_result
                
            if model_type in ["regression", "both"]:
                regression_result = self._run_regression_prediction(ticker, historical_data, days)
                result["regression_prediction"] = regression_result
                
            # ChatGPT is currently disabled
            # if model_type in ["chatgpt", "both"]:
            #     chatgpt_result = self._run_chatgpt_analysis(ticker, historical_data)
            #     result["chatgpt_analysis"] = chatgpt_result
                
            # Calculate combined prediction if both models are used
            if model_type == "both" and "lstm_prediction" in result and "regression_prediction" in result:
                combined_result = self._combine_predictions(
                    result["lstm_prediction"], 
                    result["regression_prediction"]
                )
                result["combined_prediction"] = combined_result
                
            logger.info(f"Successfully completed prediction for {ticker}")
            return result
            
        except Exception as e:
            logger.error(f"Error in stock prediction for {ticker}: {str(e)}")
            return {"error": f"Prediction failed: {str(e)}"}
    
    def _get_historical_data(self, ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Get historical stock data from Yahoo Finance."""
        try:
            ticker_obj = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = ticker_obj.history(start=start_date, end=end_date)
            
            if data.empty:
                logger.warning(f"No historical data found for {ticker}")
                return None
                
            logger.info(f"Retrieved {len(data)} days of historical data for {ticker}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {str(e)}")
            return None
    
    def _run_lstm_prediction(self, ticker: str, data: pd.DataFrame, days: int) -> Dict[str, Any]:
        """Run LSTM prediction (placeholder - needs trained model)."""
        try:
            # This is a placeholder - you'll need to implement actual LSTM prediction
            # For now, we'll create a simple trend-based prediction
            
            close_prices = data['Close'].values
            dates = data.index
            
            # Simple trend calculation
            if len(close_prices) >= 20:
                # Calculate 20-day moving average trend
                ma_20 = np.convolve(close_prices, np.ones(20)/20, mode='valid')
                trend = (ma_20[-1] - ma_20[0]) / ma_20[0] if ma_20[0] != 0 else 0
                
                # Generate future predictions based on trend
                current_price = close_prices[-1]
                predictions = []
                prediction_dates = []
                
                for i in range(1, days + 1):
                    # Apply trend with some randomness
                    daily_change = trend / 252  # Daily trend
                    random_factor = np.random.normal(0, 0.01)  # Small random variation
                    predicted_price = current_price * (1 + daily_change + random_factor)
                    
                    predictions.append(max(predicted_price, 0))  # Ensure non-negative
                    prediction_dates.append((datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'))
                    current_price = predicted_price
                
                return {
                    "status": "success",
                    "predictions": predictions,
                    "prediction_dates": prediction_dates,
                    "trend": trend,
                    "confidence": 0.7,
                    "method": "trend_based_placeholder"
                }
            else:
                return {
                    "status": "insufficient_data",
                    "error": "Need at least 20 days of data for LSTM prediction"
                }
                
        except Exception as e:
            logger.error(f"Error in LSTM prediction for {ticker}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _run_regression_prediction(self, ticker: str, data: pd.DataFrame, days: int) -> Dict[str, Any]:
        """Run linear regression prediction."""
        try:
            # Prepare data for regression
            close_prices = data['Close'].values
            volumes = data['Volume'].values
            
            # Create features (you can add more sophisticated features)
            X = []
            y = []
            
            for i in range(20, len(close_prices)):
                # Features: last 20 days of prices and volumes
                price_features = close_prices[i-20:i]
                volume_features = volumes[i-20:i]
                
                # Normalize features
                price_features_norm = (price_features - np.mean(price_features)) / np.std(price_features)
                volume_features_norm = (volume_features - np.mean(volume_features)) / np.std(volume_features)
                
                features = np.concatenate([price_features_norm, volume_features_norm])
                X.append(features)
                y.append(close_prices[i])
            
            if len(X) < 10:
                return {
                    "status": "insufficient_data",
                    "error": "Need more data for regression analysis"
                }
            
            # Train regression model
            X = np.array(X)
            y = np.array(y)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Make predictions
            current_price = close_prices[-1]
            predictions = []
            prediction_dates = []
            
            # Use the last feature set to predict future values
            last_features = X[-1]
            
            for i in range(1, days + 1):
                # Simple linear extrapolation with some noise
                trend = model.coef_.mean() if len(model.coef_) > 0 else 0
                predicted_price = current_price + trend * i + np.random.normal(0, current_price * 0.01)
                
                predictions.append(max(predicted_price, 0))
                prediction_dates.append((datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'))
                current_price = predicted_price
            
            return {
                "status": "success",
                "predictions": predictions,
                "prediction_dates": prediction_dates,
                "model_score": model.score(X, y),
                "trend_coefficient": float(trend),
                "confidence": min(0.8, model.score(X, y)),
                "method": "linear_regression"
            }
            
        except Exception as e:
            logger.error(f"Error in regression prediction for {ticker}: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    # def _run_chatgpt_analysis(self, ticker: str, data: pd.DataFrame) -> Dict[str, Any]:
    #     """Run ChatGPT analysis for fundamental and technical analysis."""
    #     try:
    #         # Prepare stock data summary for ChatGPT
    #         current_price = float(data['Close'].iloc[-1])
    #         price_change = float(data['Close'].iloc[-1] - data['Close'].iloc[-2])
    #         price_change_percent = (price_change / data['Close'].iloc[-2]) * 100
    #         
    #         # Calculate moving averages
    #         ma_20 = data['Close'].rolling(window=20).mean().iloc[-1]
    #         ma_50 = data['Close'].rolling(window=50).mean().iloc[-1]
    #         ma_200 = data['Close'].rolling(window=200).mean().iloc[-1]
    #         
    #         # Volume analysis
    #         avg_volume = data['Volume'].mean()
    #         current_volume = data['Volume'].iloc[-1]
    #         volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    #         
    #         # Prepare context for ChatGPT
    #         context = {
    #             "current_price": current_price,
    #             "price_change": price_change,
    #             "price_change_percent": price_change_percent,
    #             "moving_averages": {
    #                 "ma_20": ma_20,
    #                 "ma_50": ma_50,
    #                 "ma_200": ma_200
    #             },
    #             "volume_analysis": {
    #                 "current_volume": current_volume,
    #                 "avg_volume": avg_volume,
    #                 "volume_ratio": volume_ratio
    #             }
    #         }
    #         
    #         # Create analysis prompt
    #         prompt = self._create_analysis_prompt(ticker, context)
    #         
    #         # Call ChatGPT API
    #         response = self._call_chatgpt_api(prompt)
    #         
    #         if response:
    #             return {
    #                 "status": "success",
    #                 "analysis": response,
    #                 "context": context,
    #                 "method": "chatgpt_analysis"
    #             }
    #         else:
    #             return {
    #                 "status": "error",
    #                 "error": "Failed to get ChatGPT analysis"
    #             }
    #             
    #     except Exception as e:
    #         logger.error(f"Error in ChatGPT analysis for {ticker}: {str(e)}")
    #         return {
    #             "status": "error",
    #             "error": str(e)
    #         }
    
    # def _create_analysis_prompt(self, ticker: str, context: Dict[str, Any]) -> str:
    #     """Create comprehensive analysis prompt for ChatGPT."""
    #     prompt = f"""You are a world-class equity research analyst, technical analyst, and financial news summarizer combined. Perform a complete 360° analysis of {ticker} listed on USA stock market NYSE or NASDAQ using the latest available data.
    #     
    #     Current Market Data:
    #     - Current Price: ${context['current_price']:.2f}
    #     - Price Change: ${context['price_change']:.2f} ({context['price_change_percent']:.2f}%)
    #     - 20-Day MA: ${context['moving_averages']['ma_20']:.2f}
    #     - 50-Day MA: ${context['moving_averages']['ma_50']:.2f}
    #     - 200-Day MA: ${context['moving_averages']['ma_200']:.2f}
    #     - Volume Ratio: {context['volume_analysis']['volume_ratio']:.2f}x average
    #     
    #     Your report must have 4 main sections:
    #     
    #     ⸻1) FUNDAMENTAL ANALYSIS
    #     • Company Overview (business model, core products/services)
    #     • Financial Health Table: Revenue Growth, Net Profit Growth, EPS trends, Margins, Debt ratios
    #     • Valuation vs Competitors: P/E, P/B, EV/EBITDA, Dividend Yield
    #     • Growth Potential: Industry trends, market size, competitive advantages
    #     • Risk Analysis: Macro, sector, and financial risks
    #     • Recent Catalysts: Earnings surprises, acquisitions, partnerships
    #     • Verdict: Bull Case, Bear Case, Short-term & Long-term outlook
    #     
    #     ⸻2) TECHNICAL ANALYSIS
    #     • Current Price & % change analysis
    #     • Key Support & Resistance levels
    #     • Moving Averages analysis (20, 50, 200-day)
    #     • RSI, MACD, Stochastic readings
    #     • Trend Direction & Chart Patterns
    #     • Volume analysis
    #     • Trading Plan with Entry, Target, Stop Loss
    #     
    #     ⸻3) NEWS & SENTIMENT
    #     • Latest market-wide news summary
    #     • Stock-specific news (5-10 items with sentiment scoring)
    #     • Overall sentiment score (0-10) with reasoning
    #     
    #     ⸻4) PEER & SCREENER INSIGHT
    #     • Top 3 competitors comparison
    #     • Alternative stock suggestions
    #     
    #     📌 OUTPUT STYLE
    #     • Use clear section headings
    #     • Include at least 1-2 tables
    #     • Be data-backed but easy to understand
    #     • End with "Key Takeaways" → 5 bullet points
    #     
    #     Focus on actionable insights and professional analysis."""
    #     
    #     return prompt
    
    # def _call_chatgpt_api(self, prompt: str) -> Optional[str]:
    #     """Call OpenAI ChatGPT API using official client."""
    #     try:
    #         logger.info(f"Calling ChatGPT API for ticker analysis")
    #         
    #         if not self.openai_api_key:
    #             logger.error("No OpenAI API key available")
    #             return None
    #         
    #         # Use the official OpenAI client
    #         client = openai.OpenAI(api_key=self.openai_api_key)
    #         
    #         response = client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[
    #                 {"role": "system", "content": "You are a professional financial analyst providing comprehensive stock analysis."},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             max_tokens=2000,
    #             temperature=0.3
    #         )
    #         
    #         if response.choices and response.choices[0].message:
    #             analysis = response.choices[0].message.content
    #             logger.info("Successfully received ChatGPT analysis")
    #             return analysis
    #         else:
    #             logger.error("No content in ChatGPT response")
    #             return None
    #             
    #     except openai.RateLimitError as e:
    #         logger.error(f"OpenAI rate limit exceeded: {str(e)}")
    #         return None
    #     except openai.AuthenticationError as e:
    #         logger.error(f"OpenAI authentication error: {str(e)}")
    #         return None
    #     except openai.APIError as e:
    #         logger.error(f"OpenAI API error: {str(e)}")
    #         return None
    #     except Exception as e:
    #         logger.error(f"Error calling ChatGPT API: {str(e)}")
    #         return None
    
    def _combine_predictions(self, lstm_result: Dict, regression_result: Dict) -> Dict[str, Any]:
        """Combine predictions from both models for better accuracy."""
        try:
            if (lstm_result.get("status") != "success" or 
                regression_result.get("status") != "success"):
                return {
                    "status": "error",
                    "error": "Both models must be successful to combine predictions"
                }
            
            # Weighted average of predictions
            lstm_weight = 0.6  # LSTM gets higher weight
            regression_weight = 0.4
            
            combined_predictions = []
            combined_dates = lstm_result.get("prediction_dates", [])
            
            lstm_preds = lstm_result.get("predictions", [])
            regression_preds = regression_result.get("predictions", [])
            
            for i in range(len(combined_dates)):
                if i < len(lstm_preds) and i < len(regression_preds):
                    combined_price = (lstm_preds[i] * lstm_weight + 
                                   regression_preds[i] * regression_weight)
                    combined_predictions.append(combined_price)
                else:
                    break
            
            # Calculate confidence as weighted average
            lstm_conf = lstm_result.get("confidence", 0.5)
            regression_conf = regression_result.get("confidence", 0.5)
            combined_confidence = (lstm_conf * lstm_weight + regression_conf * regression_weight)
            
            return {
                "status": "success",
                "predictions": combined_predictions,
                "prediction_dates": combined_dates[:len(combined_predictions)],
                "confidence": combined_confidence,
                "method": "weighted_combination",
                "weights": {
                    "lstm": lstm_weight,
                    "regression": regression_weight
                }
            }
            
        except Exception as e:
            logger.error(f"Error combining predictions: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_prediction_summary(self, ticker: str, model_type: str = "both") -> Dict[str, Any]:
        """Get a summary of predictions for quick analysis."""
        try:
            # Get full prediction
            full_prediction = self.get_stock_prediction(ticker, model_type, days=7)
            
            if "error" in full_prediction:
                return full_prediction
            
            # Extract key summary points
            summary = {
                "ticker": ticker,
                "current_price": full_prediction.get("current_price"),
                "prediction_summary": {},
                "recommendation": "HOLD"
            }
            
            # Add model-specific summaries
            if "lstm_prediction" in full_prediction:
                lstm_data = full_prediction["lstm_prediction"]
                if lstm_data.get("status") == "success":
                    predictions = lstm_data.get("predictions", [])
                    if len(predictions) >= 7:
                        week_prediction = predictions[6]  # 7-day prediction
                        current_price = full_prediction.get("current_price", 0)
                        if current_price > 0:
                            week_change = ((week_prediction - current_price) / current_price) * 100
                            summary["prediction_summary"]["lstm"] = {
                                "week_prediction": week_prediction,
                                "week_change_percent": week_change,
                                "confidence": lstm_data.get("confidence", 0)
                            }
            
            if "regression_prediction" in full_prediction:
                regression_data = full_prediction["regression_prediction"]
                if regression_data.get("status") == "success":
                    predictions = regression_data.get("predictions", [])
                    if len(predictions) >= 7:
                        week_prediction = predictions[6]
                        current_price = full_prediction.get("current_price", 0)
                        if current_price > 0:
                            week_change = ((week_prediction - current_price) / current_price) * 100
                            summary["prediction_summary"]["regression"] = {
                                "week_prediction": week_prediction,
                                "week_change_percent": week_change,
                                "confidence": regression_data.get("confidence", 0)
                            }
            
            # Generate recommendation based on predictions
            if "prediction_summary" in summary and summary["prediction_summary"]:
                avg_change = 0
                total_confidence = 0
                count = 0
                
                for model_data in summary["prediction_summary"].values():
                    if "week_change_percent" in model_data:
                        avg_change += model_data["week_change_percent"]
                        total_confidence += model_data.get("confidence", 0.5)
                        count += 1
                
                if count > 0:
                    avg_change /= count
                    avg_confidence = total_confidence / count
                    
                    # Simple recommendation logic
                    if avg_change > 5 and avg_confidence > 0.6:
                        summary["recommendation"] = "BUY"
                    elif avg_change < -5 and avg_confidence > 0.6:
                        summary["recommendation"] = "SELL"
                    else:
                        summary["recommendation"] = "HOLD"
                    
                    summary["average_predicted_change"] = avg_change
                    summary["average_confidence"] = avg_confidence
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting prediction summary for {ticker}: {str(e)}")
            return {"error": f"Summary generation failed: {str(e)}"}

    # def test_openai_api_connection(self) -> Dict[str, Any]:
    #     """Test OpenAI API connection and basic functionality."""
    #     try:
    #         logger.info("Testing OpenAI API connection...")
    #         
    #         test_results = {
    #             "connection_status": "unknown",
    #             "api_key_status": "unknown",
    #             "models_status": "unknown",
    #             "chat_status": "unknown",
    #             "usage_info": {},
    #             "diagnosis": [],
    #             "recommendations": []
    #         }
    #         
    #         # Check API key
    #         if not self.openai_api_key:
    #             test_results["api_key_status"] = "❌ No API Key"
    #             test_results["connection_status"] = "❌ Cannot Connect"
    #             test_results["diagnosis"].append("No API key found")
    #             test_results["recommendations"].append("Set OPENAI_API_KEY environment variable")
    #             return test_results
    #         
    #         test_results["api_key_status"] = "✅ API Key Present"
    #         
    #         try:
    #             import openai
    #             
    #             # Test basic chat completion
    #             client = openai.OpenAI(api_key=self.openai_api_key)
    #             
    #             response = client.chat.completions.create(
    #                 model="gpt-3.5-turbo",
    #                 messages=[{"role": "user", "content": "Hello!"}],
    #                 max_tokens=50
    #             )
    #             
    #             if response.choices and response.choices[0].message:
    #                 test_results["chat_status"] = "✅ Chat Working"
    #                 test_results["connection_status"] = "✅ Connected"
    #                 
    #                 # Get usage info
    #                 if hasattr(response, 'usage') and response.usage:
    #                     test_results["usage_info"] = {
    #                         "prompt_tokens": response.usage.prompt_tokens,
    #                         "completion_tokens": response.usage.completion_tokens,
    #                         "total_tokens": response.usage.total_tokens
    #                     }
    #                 
    #                 test_results["diagnosis"].append("API connection successful")
    #                 test_results["recommendations"].append("API is working correctly")
    #             else:
    #                 test_results["chat_status"] = "❌ Chat Failed"
    #                 test_results["connection_status"] = "❌ Connection Issues"
    #                 test_results["diagnosis"].append("Chat completion failed")
    #                 test_results["recommendations"].append("Check API response format")
    #                 
    #         except openai.RateLimitError as rate_error:
    #             test_results["chat_status"] = "⚠️ Rate Limited"
    #             test_results["connection_status"] = "⚠️ Limited Connection"
    #             test_results["diagnosis"].append(f"Rate limit exceeded: {str(rate_error)}")
    #             test_results["recommendations"].append("Check OpenAI billing and quota limits")
    #             
    #         except openai.AuthenticationError as auth_error:
    #             test_results["chat_status"] = "❌ Auth Error"
    #             test_results["connection_status"] = "❌ Auth Failed"
    #             test_results["diagnosis"].append(f"Authentication error: {str(auth_error)}")
    #             test_results["recommendations"].append("Check API key validity")
    #             
    #         except openai.APIError as api_error:
    #             test_results["chat_status"] = "❌ API Error"
    #             test_results["connection_status"] = "❌ API Failed"
    #             test_results["diagnosis"].append(f"OpenAI API error: {str(api_error)}")
    #             test_results["recommendations"].append("Check OpenAI service status")
    #             
    #         except Exception as general_error:
    #             test_results["chat_status"] = f"❌ Error: {str(general_error)}"
    #             test_results["connection_status"] = "❌ Connection Failed"
    #             test_results["diagnosis"].append(f"Unexpected error: {str(general_error)}")
    #             test_results["recommendations"].append("Check logs for details")
    #         
    #         return test_results
    #         
    #     except Exception as e:
    #         logger.error(f"Error in API connection test: {str(e)}")
    #         return {
    #             "connection_status": "❌ Test Error",
    #             "error": f"Test failed: {str(e)}",
    #             "diagnosis": [f"Test method failed: {str(e)}"]
    #         }
    
    # def test_openai_latest_format(self) -> Dict[str, Any]:
    #     """Test OpenAI API using the latest format (openai>=1.0.0)."""
    #     try:
    #         logger.info("Testing OpenAI API using latest format...")
    #         
    #         test_results = {
    #             "latest_test_status": "unknown",
    #             "usage_info": {},
    #             "response_content": "",
    #             "api_version": "",
    #             "diagnosis": [],
    #             "recommendations": []
    #         }
    #         
    #         if not self.openai_api_key:
    #             test_results["latest_test_status"] = "❌ No API Key"
    #             test_results["diagnosis"].append("No API key found")
    #             return test_results
    #         
    #         try:
    #             import openai
    #             
    #             test_results["api_version"] = openai.__version__
    #             test_results["diagnosis"].append(f"OpenAI library version: {openai.__version__}")
    #             
    #             print("=== Testing Latest OpenAI Format ===")
    #             print(f"API Key: {self.openai_api_key[:10]}...{self.openai_api_key[-4:]}")
    #             
    #             client = openai.OpenAI(api_key=self.openai_api_key)
    #             
    #             response = client.chat.completions.create(
    #                 model="gpt-3.5-turbo",
    #                 messages=[{"role": "user", "content": "Hello!"}],
    #                 max_tokens=50
    #             )
    #             
    #             usage_info = {
    #                 "prompt_tokens": response.usage.prompt_tokens,
    #                 "completion_tokens": response.usage.completion_tokens,
    #                 "total_tokens": response.usage.total_tokens
    #             } if response.usage else {}
    #             
    #             content = response.choices[0].message.content
    #             
    #             print("Response Usage:", usage_info)
    #             print("Response Content:", content)
    #             
    #             test_results["latest_test_status"] = "✅ Success"
    #             test_results["usage_info"] = usage_info
    #             test_results["response_content"] = content
    #             test_results["diagnosis"].append("Latest format working correctly")
    #             test_results["recommendations"].append("API is fully functional")
    #             
    #             logger.info(f"Latest API Response Usage: {usage_info}")
    #             logger.info(f"Latest API Response Content: {content}")
    #             
    #         except openai.RateLimitError as rate_error:
    #             test_results["latest_test_status"] = "⚠️ Rate Limited"
    #             test_results["diagnosis"].append(f"Rate limit exceeded: {str(rate_error)}")
    #             test_results["recommendations"].append("Check OpenAI billing and quota limits")
    #             print("Rate Limit Error:", str(rate_error))
    #             
    #         except openai.AuthenticationError as auth_error:
    #             test_results["latest_test_status"] = "❌ Auth Error"
    #             test_results["diagnosis"].append(f"Authentication error: {str(auth_error)}")
    #             test_results["recommendations"].append("Check API key validity")
    #             print("Authentication Error:", str(auth_error))
    #             
    #         except openai.APIError as api_error:
    #             test_results["latest_test_status"] = "❌ API Error"
    #             test_results["diagnosis"].append(f"OpenAI API error: {str(api_error)}")
    #             test_results["recommendations"].append("Check OpenAI service status")
    #             print("API Error:", str(api_error))
    #             
    #         except Exception as general_error:
    #             test_results["latest_test_status"] = f"❌ Error: {str(general_error)}"
    #             test_results["diagnosis"].append(f"Unexpected error: {str(general_error)}")
    #             test_results["recommendations"].append("Check logs for details")
    #             print("General Error:", str(general_error))
    #         
    #         return test_results
    #         
    #     except Exception as e:
    #         logger.error(f"Error in latest format test: {str(e)}")
    #         return {
    #             "latest_test_status": "❌ Test Error",
    #             "error": f"Test failed: {str(e)}",
    #             "diagnosis": [f"Test method failed: {str(e)}"]
    #         }

# Global instance
stock_prediction_service = StockPredictionService()
