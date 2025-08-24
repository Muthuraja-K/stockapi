#!/usr/bin/env python3
"""
Simple Earning Summary Manager - Fixed version without syntax errors
"""

import json
import logging
from typing import List, Dict, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleEarningSummaryManager:
    def __init__(self, file_path: str = 'earningsummary.json'):
        self.file_path = file_path
        
    def file_exists(self) -> bool:
        """Check if the earningsummary.json file exists."""
        return os.path.exists(self.file_path)
    
    def load_earning_summary(self) -> List[Dict[str, Any]]:
        """Load earning summary data from the JSON file."""
        try:
            if not self.file_exists():
                logger.warning(f"Earning summary file {self.file_path} not found")
                return []
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.error(f"Invalid data format in {self.file_path}. Expected list, got {type(data)}")
                return []
            
            logger.info(f"Loaded {len(data)} tickers from {self.file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading earning summary from {self.file_path}: {str(e)}")
            return []

# Create a global instance
earning_summary_manager = SimpleEarningSummaryManager()
