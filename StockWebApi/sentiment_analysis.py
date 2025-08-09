import yfinance as yf
import random
from datetime import datetime, timedelta
import json

def get_sentiment_analysis(ticker):
    """
    Get comprehensive sentiment analysis for a given ticker
    This is a mock implementation that generates realistic sentiment data
    """
    try:
        # Get stock info from yfinance
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Generate realistic sentiment data based on stock performance
        current_price = info.get('currentPrice', 100)
        previous_close = info.get('previousClose', 100)
        
        # Calculate price change percentage
        if previous_close and previous_close > 0:
            price_change_pct = ((current_price - previous_close) / previous_close) * 100
        else:
            price_change_pct = 0
        
        # Determine overall sentiment based on price movement
        if price_change_pct > 2:
            overall_sentiment = "Positive"
            sentiment_score = 0.7 + (price_change_pct / 100) * 0.3
        elif price_change_pct < -2:
            overall_sentiment = "Negative"
            sentiment_score = 0.3 + (abs(price_change_pct) / 100) * 0.2
        else:
            overall_sentiment = "Neutral"
            sentiment_score = 0.4 + random.uniform(-0.1, 0.1)
        
        # Ensure sentiment score is between 0 and 1
        sentiment_score = max(0, min(1, sentiment_score))
        
        # Generate sentiment distribution
        if overall_sentiment == "Positive":
            positive_percentage = 45 + random.randint(10, 25)
            negative_percentage = 15 + random.randint(5, 20)
            neutral_percentage = 100 - positive_percentage - negative_percentage
        elif overall_sentiment == "Negative":
            positive_percentage = 15 + random.randint(5, 20)
            negative_percentage = 45 + random.randint(10, 25)
            neutral_percentage = 100 - positive_percentage - negative_percentage
        else:
            positive_percentage = 25 + random.randint(5, 15)
            negative_percentage = 25 + random.randint(5, 15)
            neutral_percentage = 100 - positive_percentage - negative_percentage
        
        # Generate recent news
        recent_news = generate_recent_news(ticker, overall_sentiment)
        
        # Generate social media sentiment
        social_sentiment = generate_social_sentiment(overall_sentiment)
        
        # Generate technical indicators
        technical_indicators = generate_technical_indicators(stock, current_price)
        
        return {
            "ticker": ticker,
            "overall_sentiment": overall_sentiment,
            "sentiment_score": round(sentiment_score, 3),
            "positive_percentage": positive_percentage,
            "negative_percentage": negative_percentage,
            "neutral_percentage": neutral_percentage,
            "news_count": len(recent_news),
            "recent_news": recent_news,
            "social_media_sentiment": social_sentiment,
            "technical_indicators": technical_indicators
        }
        
    except Exception as e:
        # Return fallback data if there's an error
        return get_fallback_sentiment(ticker)

def generate_recent_news(ticker, overall_sentiment):
    """Generate mock recent news articles"""
    news_templates = {
        "Positive": [
            f"{ticker} shows strong performance in recent trading session",
            f"Analysts upgrade {ticker} rating following positive earnings",
            f"{ticker} gains momentum on positive market sentiment",
            f"Strong fundamentals drive {ticker} stock higher",
            f"Investors bullish on {ticker} future prospects"
        ],
        "Negative": [
            f"{ticker} faces headwinds in challenging market conditions",
            f"Analysts downgrade {ticker} amid concerns",
            f"{ticker} underperforms market expectations",
            f"Volatility affects {ticker} trading patterns",
            f"Market uncertainty impacts {ticker} performance"
        ],
        "Neutral": [
            f"{ticker} maintains steady performance",
            f"Analysts maintain hold rating on {ticker}",
            f"{ticker} shows mixed signals in recent trading",
            f"Market conditions keep {ticker} stable",
            f"{ticker} trading within expected range"
        ]
    }
    
    sources = ["Financial News", "Market Analysis", "Trading Desk", "Investment Weekly", "Stock Report"]
    sentiments = ["Positive", "Neutral", "Negative"]
    
    news_articles = []
    for i in range(random.randint(3, 6)):
        # Mix sentiments for more realistic news
        if i == 0:
            sentiment = overall_sentiment
            templates = news_templates[overall_sentiment]
        else:
            sentiment = random.choice(sentiments)
            templates = news_templates[sentiment]
        
        title = random.choice(templates)
        source = random.choice(sources)
        date = (datetime.now() - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d")
        
        news_articles.append({
            "title": title,
            "sentiment": sentiment,
            "published_date": date,
            "source": source
        })
    
    return news_articles

def generate_social_sentiment(overall_sentiment):
    """Generate social media sentiment data"""
    sentiment_options = {
        "Positive": ["Positive", "Neutral"],
        "Negative": ["Negative", "Neutral"],
        "Neutral": ["Neutral", "Positive", "Negative"]
    }
    
    twitter_sentiment = random.choice(sentiment_options[overall_sentiment])
    reddit_sentiment = random.choice(sentiment_options[overall_sentiment])
    
    # Calculate overall social score
    sentiment_scores = {"Positive": 0.7, "Neutral": 0.5, "Negative": 0.3}
    overall_social_score = (sentiment_scores[twitter_sentiment] + sentiment_scores[reddit_sentiment]) / 2
    
    return {
        "twitter_sentiment": twitter_sentiment,
        "reddit_sentiment": reddit_sentiment,
        "overall_social_score": round(overall_social_score, 3)
    }

def generate_technical_indicators(stock, current_price):
    """Generate technical indicators based on stock data"""
    try:
        # Get historical data for technical analysis
        hist = stock.history(period="30d")
        
        if len(hist) > 0:
            # Calculate RSI (simplified)
            closes = hist['Close'].values
            if len(closes) >= 14:
                gains = [max(0, closes[i] - closes[i-1]) for i in range(1, len(closes))]
                losses = [max(0, closes[i-1] - closes[i]) for i in range(1, len(closes))]
                
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                
                if avg_loss > 0:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                else:
                    rsi = 100
            else:
                rsi = random.uniform(30, 70)
            
            # Determine MACD signal
            if current_price > closes[-1] if len(closes) > 0 else current_price:
                macd = "Bullish"
            elif current_price < closes[-1] if len(closes) > 0 else current_price:
                macd = "Bearish"
            else:
                macd = "Neutral"
            
            # Moving averages
            if len(closes) >= 20:
                sma_20 = sum(closes[-20:]) / 20
                if current_price > sma_20:
                    moving_averages = "Above 20-day SMA"
                else:
                    moving_averages = "Below 20-day SMA"
            else:
                moving_averages = "Mixed"
            
            # Support and resistance levels (simplified)
            if len(closes) > 0:
                support_level = round(min(closes[-10:]) * 0.95, 2)
                resistance_level = round(max(closes[-10:]) * 1.05, 2)
            else:
                support_level = round(current_price * 0.9, 2)
                resistance_level = round(current_price * 1.1, 2)
                
        else:
            # Fallback values
            rsi = random.uniform(30, 70)
            macd = random.choice(["Bullish", "Bearish", "Neutral"])
            moving_averages = "Mixed"
            support_level = round(current_price * 0.9, 2)
            resistance_level = round(current_price * 1.1, 2)
            
    except Exception:
        # Fallback values if technical analysis fails
        rsi = random.uniform(30, 70)
        macd = random.choice(["Bullish", "Bearish", "Neutral"])
        moving_averages = "Mixed"
        support_level = round(current_price * 0.9, 2)
        resistance_level = round(current_price * 1.1, 2)
    
    return {
        "rsi": round(rsi, 1),
        "macd": macd,
        "moving_averages": moving_averages,
        "support_level": support_level,
        "resistance_level": resistance_level
    }

def get_fallback_sentiment(ticker):
    """Return fallback sentiment data if API fails"""
    return {
        "ticker": ticker,
        "overall_sentiment": "Neutral",
        "sentiment_score": 0.5,
        "positive_percentage": 35,
        "negative_percentage": 30,
        "neutral_percentage": 35,
        "news_count": 5,
        "recent_news": [
            {
                "title": f"{ticker} shows mixed signals in recent trading",
                "sentiment": "Neutral",
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "source": "Financial News"
            },
            {
                "title": f"Analysts maintain hold rating on {ticker}",
                "sentiment": "Neutral",
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "source": "Market Analysis"
            }
        ],
        "social_media_sentiment": {
            "twitter_sentiment": "Neutral",
            "reddit_sentiment": "Neutral",
            "overall_social_score": 0.5
        },
        "technical_indicators": {
            "rsi": 55,
            "macd": "Neutral",
            "moving_averages": "Mixed",
            "support_level": 0,
            "resistance_level": 0
        }
    } 