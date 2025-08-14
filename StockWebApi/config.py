"""
Configuration file for environment variables and settings
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Finviz API Configuration
    FINVIZ_AUTH_ID = os.getenv('FINVIZ_AUTH_ID', '')
    
    # Tiingo API Configuration
    TIINGO_API_KEY = os.getenv('TIINGO_API_KEY', '')
    TIINGO_BASE_URL = 'https://api.tiingo.com'
    
    # API Configuration
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',') if os.getenv('ALLOWED_ORIGINS') else ['*']
    
    # Database Configuration (if needed in future)
    # DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./stock_prediction.db')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')
    
    # Rate Limiting Configuration
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration values"""
        if not cls.FINVIZ_AUTH_ID:
            raise ValueError("FINVIZ_AUTH_ID environment variable is required")
        
        return True

# Create global config instance
config = Config()
