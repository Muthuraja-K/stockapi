"""
Centralized Cache Manager for Stock Data
This module provides intelligent caching to minimize Yahoo Finance API calls
"""

import time
import logging
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from functools import wraps
import threading

logger = logging.getLogger(__name__)

class StockDataCache:
    """Centralized cache for stock data with intelligent invalidation"""
    
    def __init__(self, cache_file: str = "stock_cache.json"):
        self.cache_file = cache_file
        self.cache_data = {}
        self.cache_metadata = {}
        self.lock = threading.RLock()
        self.load_cache()
        
        # Cache TTL settings (in seconds)
        self.ttl_settings = {
            'realtime': 60,        # 1 minute for real-time data
            'daily': 300,          # 5 minutes for daily data
            'historical': 3600,    # 1 hour for historical data
            'info': 1800,          # 30 minutes for company info
            'batch': 120,          # 2 minutes for batch data
            'sentiment': 7200,     # 2 hours for sentiment data
            'earnings': 86400      # 24 hours for earnings data
        }
        
        # Maximum cache sizes
        self.max_cache_sizes = {
            'realtime': 1000,
            'daily': 500,
            'historical': 200,
            'info': 300,
            'batch': 100,
            'sentiment': 100,
            'earnings': 50
        }
    
    def load_cache(self):
        """Load cached data from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.cache_data = data.get('cache', {})
                    self.cache_metadata = data.get('metadata', {})
                    logger.info(f"Loaded cache with {len(self.cache_data)} entries")
            else:
                logger.info("No cache file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.cache_data = {}
            self.cache_metadata = {}
    
    def save_cache(self):
        """Save cache data to file"""
        try:
            data = {
                'cache': self.cache_data,
                'metadata': self.cache_metadata,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved cache with {len(self.cache_data)} entries")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def _get_cache_key(self, data_type: str, identifier: str, **kwargs) -> str:
        """Generate a cache key based on data type and identifier"""
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items()) if kwargs else []
        kwargs_str = "_".join([f"{k}_{v}" for k, v in sorted_kwargs])
        
        if kwargs_str:
            return f"{data_type}_{identifier}_{kwargs_str}"
        return f"{data_type}_{identifier}"
    
    def get(self, data_type: str, identifier: str, **kwargs) -> Optional[Any]:
        """Get cached data if it's still valid"""
        with self.lock:
            cache_key = self._get_cache_key(data_type, identifier, **kwargs)
            
            if cache_key in self.cache_data:
                cached_item = self.cache_data[cache_key]
                metadata = self.cache_metadata.get(cache_key, {})
                
                # Check if cache is still valid
                if self._is_cache_valid(cache_key, metadata):
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_item['data']
                else:
                    # Remove expired cache entry
                    logger.debug(f"Cache expired for {cache_key}")
                    del self.cache_data[cache_key]
                    if cache_key in self.cache_metadata:
                        del self.cache_metadata[cache_key]
            
            logger.debug(f"Cache miss for {cache_key}")
            return None
    
    def set(self, data_type: str, identifier: str, data: Any, **kwargs):
        """Cache data with appropriate TTL"""
        with self.lock:
            cache_key = self._get_cache_key(data_type, identifier, **kwargs)
            
            # Clean up cache if it's too large
            self._cleanup_cache(data_type)
            
            # Store data and metadata
            self.cache_data[cache_key] = {
                'data': data,
                'timestamp': time.time(),
                'data_type': data_type
            }
            
            self.cache_metadata[cache_key] = {
                'created_at': time.time(),
                'data_type': data_type,
                'size': len(str(data)) if data else 0
            }
            
            logger.debug(f"Cached data for {cache_key}")
            
            # Periodically save cache to disk
            if len(self.cache_data) % 100 == 0:
                self.save_cache()
    
    def _is_cache_valid(self, cache_key: str, metadata: Dict) -> bool:
        """Check if cached data is still valid based on TTL"""
        if cache_key not in self.cache_data:
            return False
        
        cached_item = self.cache_data[cache_key]
        data_type = cached_item.get('data_type', 'daily')
        ttl = self.ttl_settings.get(data_type, 300)  # Default to 5 minutes
        
        age = time.time() - cached_item['timestamp']
        return age < ttl
    
    def _cleanup_cache(self, data_type: str):
        """Clean up cache for a specific data type"""
        max_size = self.max_cache_sizes.get(data_type, 100)
        
        # Get all keys for this data type
        type_keys = [k for k, v in self.cache_data.items() 
                    if v.get('data_type') == data_type]
        
        if len(type_keys) >= max_size:
            # Remove oldest entries
            type_keys_with_timestamps = [
                (k, self.cache_data[k]['timestamp']) for k in type_keys
            ]
            type_keys_with_timestamps.sort(key=lambda x: x[1])
            
            # Remove oldest entries
            keys_to_remove = type_keys_with_timestamps[:len(type_keys) - max_size + 1]
            for key, _ in keys_to_remove:
                del self.cache_data[key]
                if key in self.cache_metadata:
                    del self.cache_metadata[key]
            
            logger.debug(f"Cleaned up {len(keys_to_remove)} old {data_type} cache entries")
    
    def invalidate(self, data_type: str = None, identifier: str = None):
        """Invalidate cache entries based on criteria"""
        with self.lock:
            keys_to_remove = []
            
            for key in self.cache_data.keys():
                should_remove = False
                
                if data_type and identifier:
                    # Remove specific entry
                    if key == f"{data_type}_{identifier}":
                        should_remove = True
                elif data_type:
                    # Remove all entries of a specific type
                    if key.startswith(f"{data_type}_"):
                        should_remove = True
                elif identifier:
                    # Remove all entries for a specific identifier
                    if f"_{identifier}" in key or key.endswith(f"_{identifier}"):
                        should_remove = True
                
                if should_remove:
                    keys_to_remove.append(key)
            
            # Remove invalidated entries
            for key in keys_to_remove:
                del self.cache_data[key]
                if key in self.cache_metadata:
                    del self.cache_metadata[key]
            
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            stats = {
                'total_entries': len(self.cache_data),
                'total_size': sum(meta.get('size', 0) for meta in self.cache_metadata.values()),
                'by_type': {},
                'oldest_entry': None,
                'newest_entry': None
            }
            
            # Count by data type
            for item in self.cache_data.values():
                data_type = item.get('data_type', 'unknown')
                if data_type not in stats['by_type']:
                    stats['by_type'][data_type] = 0
                stats['by_type'][data_type] += 1
            
            # Find oldest and newest entries
            if self.cache_data:
                timestamps = [item['timestamp'] for item in self.cache_data.values()]
                stats['oldest_entry'] = datetime.fromtimestamp(min(timestamps)).isoformat()
                stats['newest_entry'] = datetime.fromtimestamp(max(timestamps)).isoformat()
            
            return stats
    
    def clear_cache(self, data_type: str = None):
        """Clear all cache or cache for a specific type"""
        with self.lock:
            if data_type:
                keys_to_remove = [k for k in self.cache_data.keys() 
                                if self.cache_data[k].get('data_type') == data_type]
                for key in keys_to_remove:
                    del self.cache_data[key]
                    if key in self.cache_metadata:
                        del self.cache_metadata[key]
                logger.info(f"Cleared {len(keys_to_remove)} {data_type} cache entries")
            else:
                self.cache_data.clear()
                self.cache_metadata.clear()
                logger.info("Cleared all cache")

# Global cache instance
_stock_cache = StockDataCache()

def get_cache() -> StockDataCache:
    """Get the global cache instance"""
    return _stock_cache

def cache_result(data_type: str, ttl_override: int = None):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Check cache first
            cached_result = _stock_cache.get(data_type, cache_key, **kwargs)
            if cached_result is not None:
                return cached_result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            _stock_cache.set(data_type, cache_key, result, **kwargs)
            
            return result
        return wrapper
    return decorator

def invalidate_cache(data_type: str = None, identifier: str = None):
    """Invalidate cache entries"""
    _stock_cache.invalidate(data_type, identifier)

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return _stock_cache.get_cache_stats()

def clear_cache(data_type: str = None):
    """Clear cache"""
    _stock_cache.clear_cache(data_type)
