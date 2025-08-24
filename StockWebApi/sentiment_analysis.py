import yfinance as yf
import random
from datetime import datetime, timedelta
import json
import time
from api_rate_limiter import enforce_rate_limit, safe_yfinance_call
import logging

# Remove old rate limiting variables and functions - now using centralized rate limiter

def get_sentiment_analysis(ticker):
    """
    Get comprehensive sentiment analysis for a given ticker
    This is a mock implementation that generates realistic sentiment data
    """
    try:
        # Use centralized rate limiting
        enforce_rate_limit()
        
        # Get stock info from yfinance using safe call
        stock_info = safe_yfinance_call(ticker, "info")
        
        # Generate realistic sentiment data based on stock performance
        current_price = stock_info.get('currentPrice', 100)
        previous_close = stock_info.get('previousClose', 100)
        
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
        technical_indicators = generate_technical_indicators(ticker, current_price)
        
        # Generate institutional holdings data
        institutional_holdings = generate_institutional_holdings(ticker, overall_sentiment)
        
        # Generate individual holdings data
        individual_holdings = generate_individual_holdings(ticker, overall_sentiment)
        
        # Generate major holders data
        major_holders = generate_major_holders(ticker, overall_sentiment)
        
        # Generate top institutional holders with dates
        top_institutional_holders = generate_top_institutional_holders(ticker, overall_sentiment)
        
        # Generate top mutual fund holders
        top_mutual_fund_holders = generate_top_mutual_fund_holders(ticker, overall_sentiment)
        
        # Get option chain data from Yahoo Finance
        option_data = get_option_chain_data(ticker, current_price)
        
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
            "technical_indicators": technical_indicators,
            "institutional_holdings": institutional_holdings,
            "individual_holdings": individual_holdings,
            "major_holders": major_holders,
            "top_institutional_holders": top_institutional_holders,
            "top_mutual_fund_holders": top_mutual_fund_holders,
            "option_data": option_data
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

def generate_technical_indicators(ticker, current_price):
    """Generate technical indicators based on stock data"""
    try:
        # Get historical data for technical analysis using safe call
        hist = safe_yfinance_call(ticker, "history")
        
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

def generate_institutional_holdings(ticker, overall_sentiment):
    """Generate mock institutional holdings data"""
    # List of major financial institutions
    institutions = [
        "BlackRock Inc.",
        "Vanguard Group Inc.",
        "State Street Corp.",
        "Fidelity Management & Research Co.",
        "T. Rowe Price Associates Inc.",
        "Capital Research & Management Co.",
        "Wellington Management Co. LLP",
        "Invesco Ltd.",
        "Northern Trust Corp.",
        "Goldman Sachs Asset Management",
        "Morgan Stanley Investment Management",
        "JPMorgan Chase & Co.",
        "Bank of America Corp.",
        "Wells Fargo & Co.",
        "Charles Schwab Corp.",
        "Ameriprise Financial Inc.",
        "Franklin Resources Inc.",
        "Eaton Vance Corp.",
        "Allianz Global Investors",
        "PIMCO LLC"
    ]
    
    # Generate holdings based on sentiment
    if overall_sentiment == "Positive":
        # More institutions likely to hold positive sentiment stocks
        num_institutions = random.randint(8, 15)
        base_percentage = random.uniform(0.5, 2.5)
    elif overall_sentiment == "Negative":
        # Fewer institutions likely to hold negative sentiment stocks
        num_institutions = random.randint(4, 10)
        base_percentage = random.uniform(0.2, 1.5)
    else:
        # Neutral sentiment - moderate holdings
        num_institutions = random.randint(6, 12)
        base_percentage = random.uniform(0.3, 2.0)
    
    # Select random institutions
    selected_institutions = random.sample(institutions, min(num_institutions, len(institutions)))
    
    holdings = []
    total_percentage = 0
    
    for i, institution in enumerate(selected_institutions):
        if i == 0:
            # First institution gets the highest percentage
            percentage = base_percentage + random.uniform(0.5, 2.0)
        elif i < 3:
            # Top 3 institutions get significant percentages
            percentage = base_percentage + random.uniform(0.2, 1.5)
        else:
            # Other institutions get smaller percentages
            percentage = base_percentage * random.uniform(0.1, 0.8)
        
        # Ensure percentage is reasonable
        percentage = max(0.1, min(5.0, percentage))
        
        holdings.append({
            "institution_name": institution,
            "percentage_held": round(percentage, 2),
            "shares_held": random.randint(100000, 5000000),
            "market_value": round(percentage * random.uniform(1000000, 50000000), 2)
        })
        
        total_percentage += percentage
    
    # Sort by percentage held (descending)
    holdings.sort(key=lambda x: x["percentage_held"], reverse=True)
    
    return {
        "total_institutions": len(holdings),
        "total_percentage_held": round(total_percentage, 2),
        "holdings": holdings
    }

def generate_individual_holdings(ticker, overall_sentiment):
    """Generate mock individual holdings data"""
    # List of individual investor names (fictional)
    individual_investors = [
        "John Smith",
        "Sarah Johnson",
        "Michael Brown",
        "Emily Davis",
        "David Wilson",
        "Lisa Anderson",
        "Robert Taylor",
        "Jennifer Martinez",
        "William Garcia",
        "Amanda Rodriguez",
        "James Lopez",
        "Michelle White",
        "Christopher Lee",
        "Jessica Hall",
        "Daniel Allen",
        "Ashley Young",
        "Matthew King",
        "Nicole Wright",
        "Joshua Green",
        "Stephanie Baker"
    ]
    
    # Generate holdings based on sentiment
    if overall_sentiment == "Positive":
        # More individuals likely to hold positive sentiment stocks
        num_individuals = random.randint(6, 12)
        base_percentage = random.uniform(0.1, 1.0)
    elif overall_sentiment == "Negative":
        # Fewer individuals likely to hold negative sentiment stocks
        num_individuals = random.randint(3, 8)
        base_percentage = random.uniform(0.05, 0.5)
    else:
        # Neutral sentiment - moderate holdings
        num_individuals = random.randint(4, 10)
        base_percentage = random.uniform(0.08, 0.8)
    
    # Select random individuals
    selected_individuals = random.sample(individual_investors, min(num_individuals, len(individual_investors)))
    
    holdings = []
    total_percentage = 0
    
    for i, individual in enumerate(selected_individuals):
        if i == 0:
            # First individual gets the highest percentage
            percentage = base_percentage + random.uniform(0.2, 0.8)
        elif i < 3:
            # Top 3 individuals get significant percentages
            percentage = base_percentage + random.uniform(0.1, 0.5)
        else:
            # Other individuals get smaller percentages
            percentage = base_percentage * random.uniform(0.05, 0.4)
        
        # Ensure percentage is reasonable for individual holdings
        percentage = max(0.01, min(2.0, percentage))
        
        holdings.append({
            "investor_name": individual,
            "percentage_held": round(percentage, 2),
            "shares_held": random.randint(1000, 100000),
            "market_value": round(percentage * random.uniform(100000, 5000000), 2)
        })
        
        total_percentage += percentage
    
    # Sort by percentage held (descending)
    holdings.sort(key=lambda x: x["percentage_held"], reverse=True)
    
    return {
        "total_individuals": len(holdings),
        "total_percentage_held": round(total_percentage, 2),
        "holdings": holdings
    }

def generate_major_holders(ticker, overall_sentiment):
    """Generate mock major holders data showing percentage held by different categories"""
    # Generate realistic percentages based on sentiment
    if overall_sentiment == "Positive":
        insider_percentage = random.uniform(1.5, 4.0)
        institutional_percentage = random.uniform(55.0, 75.0)
        retail_percentage = random.uniform(15.0, 35.0)
    elif overall_sentiment == "Negative":
        insider_percentage = random.uniform(0.5, 2.5)
        institutional_percentage = random.uniform(40.0, 60.0)
        retail_percentage = random.uniform(25.0, 45.0)
    else:
        insider_percentage = random.uniform(1.0, 3.0)
        institutional_percentage = random.uniform(50.0, 70.0)
        retail_percentage = random.uniform(20.0, 40.0)
    
    # Ensure percentages add up to approximately 100%
    total = insider_percentage + institutional_percentage + retail_percentage
    if total > 100:
        # Scale down proportionally
        scale_factor = 100 / total
        insider_percentage *= scale_factor
        institutional_percentage *= scale_factor
        retail_percentage *= scale_factor
    
    return {
        "insider_percentage": round(insider_percentage, 2),
        "institutional_percentage": round(institutional_percentage, 2),
        "retail_percentage": round(retail_percentage, 2),
        "total_percentage": round(insider_percentage + institutional_percentage + retail_percentage, 2)
    }

def generate_top_institutional_holders(ticker, overall_sentiment):
    """Generate mock top institutional holders data with dates"""
    # List of major financial institutions
    institutions = [
        "BlackRock Inc.",
        "Vanguard Group Inc.",
        "State Street Corp.",
        "Fidelity Management & Research Co.",
        "T. Rowe Price Associates Inc.",
        "Capital Research & Management Co.",
        "Wellington Management Co. LLP",
        "Invesco Ltd.",
        "Northern Trust Corp.",
        "Goldman Sachs Asset Management",
        "Morgan Stanley Investment Management",
        "JPMorgan Chase & Co.",
        "Bank of America Corp.",
        "Wells Fargo & Co.",
        "Charles Schwab Corp."
    ]
    
    # Generate holdings based on sentiment
    if overall_sentiment == "Positive":
        num_institutions = random.randint(8, 12)
        base_percentage = random.uniform(0.8, 3.0)
    elif overall_sentiment == "Negative":
        num_institutions = random.randint(5, 9)
        base_percentage = random.uniform(0.3, 2.0)
    else:
        num_institutions = random.randint(6, 11)
        base_percentage = random.uniform(0.5, 2.5)
    
    # Select random institutions
    selected_institutions = random.sample(institutions, min(num_institutions, len(institutions)))
    
    holdings = []
    total_percentage = 0
    
    for i, institution in enumerate(selected_institutions):
        if i == 0:
            # First institution gets the highest percentage
            percentage = base_percentage + random.uniform(0.8, 2.5)
        elif i < 3:
            # Top 3 institutions get significant percentages
            percentage = base_percentage + random.uniform(0.3, 1.8)
        else:
            # Other institutions get smaller percentages
            percentage = base_percentage * random.uniform(0.15, 0.9)
        
        # Ensure percentage is reasonable
        percentage = max(0.1, min(6.0, percentage))
        
        # Generate random date within last 6 months
        days_ago = random.randint(30, 180)
        date_reported = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        # Calculate shares and value
        shares_held = random.randint(100000, 8000000)
        market_value = round(percentage * random.uniform(2000000, 100000000), 2)
        
        holdings.append({
            "holder": institution,
            "shares": shares_held,
            "date_reported": date_reported,
            "percentage_out": round(percentage, 2),
            "value": market_value
        })
        
        total_percentage += percentage
    
    # Sort by percentage held (descending)
    holdings.sort(key=lambda x: x["percentage_out"], reverse=True)
    
    return {
        "total_institutions": len(holdings),
        "total_percentage_held": round(total_percentage, 2),
        "holdings": holdings
    }

def generate_top_mutual_fund_holders(ticker, overall_sentiment):
    """Generate mock top mutual fund holders data"""
    # List of major mutual fund companies
    mutual_funds = [
        "Vanguard 500 Index Fund",
        "Fidelity 500 Index Fund",
        "SPDR S&P 500 ETF Trust",
        "iShares Core S&P 500 ETF",
        "Vanguard Total Stock Market Index Fund",
        "Fidelity Total Market Index Fund",
        "T. Rowe Price Blue Chip Growth Fund",
        "American Funds Growth Fund of America",
        "Dodge & Cox Stock Fund",
        "Fidelity Contrafund",
        "Vanguard Growth Index Fund",
        "Fidelity Growth Company Fund",
        "T. Rowe Price Growth Stock Fund",
        "American Funds Investment Company of America",
        "Vanguard Value Index Fund"
    ]
    
    # Generate holdings based on sentiment
    if overall_sentiment == "Positive":
        num_funds = random.randint(6, 10)
        base_percentage = random.uniform(0.5, 2.0)
    elif overall_sentiment == "Negative":
        num_funds = random.randint(3, 7)
        base_percentage = random.uniform(0.2, 1.2)
    else:
        num_funds = random.randint(4, 9)
        base_percentage = random.uniform(0.3, 1.6)
    
    # Select random mutual funds
    selected_funds = random.sample(mutual_funds, min(num_funds, len(mutual_funds)))
    
    holdings = []
    total_percentage = 0
    
    for i, fund in enumerate(selected_funds):
        if i == 0:
            # First fund gets the highest percentage
            percentage = base_percentage + random.uniform(0.5, 1.8)
        elif i < 3:
            # Top 3 funds get significant percentages
            percentage = base_percentage + random.uniform(0.2, 1.2)
        else:
            # Other funds get smaller percentages
            percentage = base_percentage * random.uniform(0.1, 0.7)
        
        # Ensure percentage is reasonable
        percentage = max(0.05, min(4.0, percentage))
        
        # Generate random date within last 3 months
        days_ago = random.randint(15, 90)
        date_reported = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        # Calculate shares and value
        shares_held = random.randint(50000, 3000000)
        market_value = round(percentage * random.uniform(1000000, 50000000), 2)
        
        holdings.append({
            "holder": fund,
            "shares": shares_held,
            "date_reported": date_reported,
            "percentage_out": round(percentage, 2),
            "value": market_value
        })
        
        total_percentage += percentage
    
    # Sort by percentage held (descending)
    holdings.sort(key=lambda x: x["percentage_out"], reverse=True)
    
    return {
        "total_funds": len(holdings),
        "total_percentage_held": round(total_percentage, 2),
        "holdings": holdings
    }

def get_option_chain_data(ticker, current_price):
    """Fetch real option chain data from Yahoo Finance"""
    try:
        logging.info(f"Starting to fetch option chain data for {ticker}")
        
        # Get available option expiration dates
        options = safe_yfinance_call(ticker, "options")
        logging.info(f"Retrieved options for {ticker}: {options}")
        
        if not options:
            logging.warning(f"No options available for {ticker}")
            return {
                "expiration_dates": [],
                "calls": [],
                "puts": [],
                "message": "No options available for this stock",
                "current_price": current_price
            }
        
        # Get the first few expiration dates (limit to avoid too many API calls)
        expiration_dates = options[:4]  # Limit to 4 expiration dates
        logging.info(f"Processing {len(expiration_dates)} expiration dates for {ticker}: {expiration_dates}")
        
        all_calls = []
        all_puts = []
        
        # Get the ticker object for option chain calls
        ticker_obj = safe_yfinance_call(ticker, "option_chain")
        logging.info(f"Got ticker object for {ticker}")
        
        # Fetch options data for each expiration date
        for exp_date in expiration_dates:
            try:
                logging.info(f"Fetching options for {ticker} at {exp_date}")
                # Enforce rate limiting between option chain calls
                enforce_rate_limit()
                
                opt = ticker_obj.option_chain(exp_date)
                logging.info(f"Retrieved option chain for {ticker} at {exp_date}")
                
                # Process calls
                if opt.calls is not None and not opt.calls.empty:
                    logging.info(f"Processing {len(opt.calls)} calls for {ticker} at {exp_date}")
                    for _, call in opt.calls.head(10).iterrows():  # Limit to 10 calls per expiration
                        call_data = {
                            "ticker": ticker,
                            "expiration_date": exp_date,
                            "strike_price": float(call['strike']),
                            "option_type": "call",
                            "last_price": float(call['lastPrice']) if call['lastPrice'] > 0 else 0,
                            "bid": float(call['bid']) if call['bid'] > 0 else 0,
                            "ask": float(call['ask']) if call['ask'] > 0 else 0,
                            "volume": int(call['volume']) if call['volume'] > 0 else 0,
                            "open_interest": int(call['openInterest']) if call['openInterest'] > 0 else 0,
                            "implied_volatility": float(call['impliedVolatility']) if call['impliedVolatility'] > 0 else 0,
                            "delta": 0,  # Not available in Yahoo Finance API
                            "gamma": 0,  # Not available in Yahoo Finance API
                            "theta": 0,  # Not available in Yahoo Finance API
                            "vega": 0,   # Not available in Yahoo Finance API
                            "in_the_money": call['inTheMoney'] if 'inTheMoney' in call else False
                        }
                        all_calls.append(call_data)
                
                # Process puts
                if opt.puts is not None and not opt.puts.empty:
                    logging.info(f"Processing {len(opt.puts)} puts for {ticker} at {exp_date}")
                    for _, put in opt.puts.head(10).iterrows():  # Limit to 10 puts per expiration
                        put_data = {
                            "ticker": ticker,
                            "expiration_date": exp_date,
                            "strike_price": float(put['strike']),
                            "option_type": "put",
                            "last_price": float(put['lastPrice']) if put['lastPrice'] > 0 else 0,
                            "bid": float(put['bid']) if put['bid'] > 0 else 0,
                            "ask": float(put['ask']) if put['ask'] > 0 else 0,
                            "volume": int(put['volume']) if put['volume'] > 0 else 0,
                            "open_interest": int(put['openInterest']) if put['openInterest'] > 0 else 0,
                            "implied_volatility": float(put['impliedVolatility']) if put['impliedVolatility'] > 0 else 0,
                            "delta": 0,  # Not available in Yahoo Finance API
                            "gamma": 0,  # Not available in Yahoo Finance API
                            "theta": 0,  # Not available in Yahoo Finance API
                            "vega": 0,   # Not available in Yahoo Finance API
                            "in_the_money": put['inTheMoney'] if 'inTheMoney' in put else False
                        }
                        all_puts.append(put_data)
                        
            except Exception as e:
                logging.warning(f"Failed to fetch options for {ticker} at {exp_date}: {str(e)}")
                continue
        
        logging.info(f"Successfully processed options for {ticker}: {len(all_calls)} calls, {len(all_puts)} puts")
        
        return {
            "expiration_dates": expiration_dates,
            "calls": all_calls,
            "puts": all_puts,
            "last_updated": datetime.now().isoformat(),
            "current_price": current_price
        }
        
    except Exception as e:
        logging.error(f"Failed to fetch option chain for {ticker}: {str(e)}")
        return {
            "expiration_dates": [],
            "calls": [],
            "puts": [],
            "error": f"Failed to fetch options: {str(e)}",
            "current_price": current_price
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
        },
        "institutional_holdings": {
            "total_institutions": 10,
            "total_percentage_held": 100.0,
            "holdings": [
                {"institution_name": "BlackRock Inc.", "percentage_held": 25.0, "shares_held": 1000000, "market_value": 100000000.0},
                {"institution_name": "Vanguard Group Inc.", "percentage_held": 15.0, "shares_held": 500000, "market_value": 50000000.0},
                {"institution_name": "State Street Corp.", "percentage_held": 10.0, "shares_held": 300000, "market_value": 30000000.0},
                {"institution_name": "Fidelity Management & Research Co.", "percentage_held": 8.0, "shares_held": 200000, "market_value": 20000000.0},
                {"institution_name": "T. Rowe Price Associates Inc.", "percentage_held": 7.0, "shares_held": 150000, "market_value": 15000000.0},
                {"institution_name": "Capital Research & Management Co.", "percentage_held": 6.0, "shares_held": 120000, "market_value": 12000000.0},
                {"institution_name": "Wellington Management Co. LLP", "percentage_held": 5.0, "shares_held": 100000, "market_value": 10000000.0},
                {"institution_name": "Invesco Ltd.", "percentage_held": 4.0, "shares_held": 80000, "market_value": 8000000.0},
                {"institution_name": "Northern Trust Corp.", "percentage_held": 3.0, "shares_held": 60000, "market_value": 6000000.0},
                {"institution_name": "Goldman Sachs Asset Management", "percentage_held": 2.0, "shares_held": 40000, "market_value": 4000000.0}
            ]
        },
        "individual_holdings": {
            "total_individuals": 8,
            "total_percentage_held": 15.0,
            "holdings": [
                {"investor_name": "John Smith", "percentage_held": 3.5, "shares_held": 50000, "market_value": 5000000.0},
                {"investor_name": "Sarah Johnson", "percentage_held": 2.8, "shares_held": 40000, "market_value": 4000000.0},
                {"investor_name": "Michael Brown", "percentage_held": 2.2, "shares_held": 30000, "market_value": 3000000.0},
                {"investor_name": "Emily Davis", "percentage_held": 1.8, "shares_held": 25000, "market_value": 2500000.0},
                {"investor_name": "David Wilson", "percentage_held": 1.5, "shares_held": 20000, "market_value": 2000000.0},
                {"investor_name": "Lisa Anderson", "percentage_held": 1.2, "shares_held": 15000, "market_value": 1500000.0},
                {"investor_name": "Robert Taylor", "percentage_held": 1.0, "shares_held": 12000, "market_value": 1200000.0},
                {"investor_name": "Jennifer Martinez", "percentage_held": 1.0, "shares_held": 10000, "market_value": 1000000.0}
            ]
        },
        "major_holders": {
            "insider_percentage": 2.5,
            "institutional_percentage": 65.0,
            "retail_percentage": 32.5,
            "total_percentage": 100.0
        },
        "top_institutional_holders": {
            "total_institutions": 10,
            "total_percentage_held": 100.0,
            "holdings": [
                {"holder": "BlackRock Inc.", "shares": 1000000, "date_reported": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"), "percentage_out": 25.0, "value": 100000000.0},
                {"holder": "Vanguard Group Inc.", "shares": 500000, "date_reported": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"), "percentage_out": 15.0, "value": 50000000.0},
                {"holder": "State Street Corp.", "shares": 300000, "date_reported": (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"), "percentage_out": 10.0, "value": 30000000.0},
                {"holder": "Fidelity Management & Research Co.", "shares": 200000, "date_reported": (datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d"), "percentage_out": 8.0, "value": 20000000.0},
                {"holder": "T. Rowe Price Associates Inc.", "shares": 150000, "date_reported": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"), "percentage_out": 7.0, "value": 15000000.0},
                {"holder": "Capital Research & Management Co.", "shares": 120000, "date_reported": (datetime.now() - timedelta(days=210)).strftime("%Y-%m-%d"), "percentage_out": 6.0, "value": 12000000.0},
                {"holder": "Wellington Management Co. LLP", "shares": 100000, "date_reported": (datetime.now() - timedelta(days=240)).strftime("%Y-%m-%d"), "percentage_out": 5.0, "value": 10000000.0},
                {"holder": "Invesco Ltd.", "shares": 80000, "date_reported": (datetime.now() - timedelta(days=270)).strftime("%Y-%m-%d"), "percentage_out": 4.0, "value": 8000000.0},
                {"holder": "Northern Trust Corp.", "shares": 60000, "date_reported": (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d"), "percentage_out": 3.0, "value": 6000000.0},
                {"holder": "Goldman Sachs Asset Management", "shares": 40000, "date_reported": (datetime.now() - timedelta(days=330)).strftime("%Y-%m-%d"), "percentage_out": 2.0, "value": 4000000.0}
            ]
        },
        "top_mutual_fund_holders": {
            "total_funds": 10,
            "total_percentage_held": 100.0,
            "holdings": [
                {"holder": "Vanguard 500 Index Fund", "shares": 1000000, "date_reported": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"), "percentage_out": 20.0, "value": 20000000.0},
                {"holder": "Fidelity 500 Index Fund", "shares": 800000, "date_reported": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"), "percentage_out": 16.0, "value": 16000000.0},
                {"holder": "SPDR S&P 500 ETF Trust", "shares": 700000, "date_reported": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"), "percentage_out": 14.0, "value": 14000000.0},
                {"holder": "iShares Core S&P 500 ETF", "shares": 600000, "date_reported": (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"), "percentage_out": 12.0, "value": 12000000.0},
                {"holder": "Vanguard Total Stock Market Index Fund", "shares": 500000, "date_reported": (datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d"), "percentage_out": 10.0, "value": 10000000.0},
                {"holder": "Fidelity Total Market Index Fund", "shares": 400000, "date_reported": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d"), "percentage_out": 8.0, "value": 8000000.0},
                {"holder": "T. Rowe Price Blue Chip Growth Fund", "shares": 300000, "date_reported": (datetime.now() - timedelta(days=210)).strftime("%Y-%m-%d"), "percentage_out": 6.0, "value": 6000000.0},
                {"holder": "American Funds Growth Fund of America", "shares": 250000, "date_reported": (datetime.now() - timedelta(days=240)).strftime("%Y-%m-%d"), "percentage_out": 5.0, "value": 50000000.0},
                {"holder": "Dodge & Cox Stock Fund", "shares": 200000, "date_reported": (datetime.now() - timedelta(days=270)).strftime("%Y-%m-%d"), "percentage_out": 4.0, "value": 4000000.0},
                {"holder": "Fidelity Contrafund", "shares": 150000, "date_reported": (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d"), "percentage_out": 3.0, "value": 3000000.0}
            ]
        },
        "option_data": {
            "expiration_dates": [],
            "calls": [],
            "puts": [],
            "last_updated": datetime.now().isoformat(),
            "current_price": 0,
            "message": "No options available in fallback mode"
        }
    } 