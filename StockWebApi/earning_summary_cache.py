"""
Earning Summary Cache Manager
This module provides caching for earning summaries to improve performance and reduce API calls.
The cache automatically refreshes when the date changes.
"""

import json
import os
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
from earning_summary_optimized import get_earning_summary_optimized

logger = logging.getLogger(__name__)

class EarningSummaryCache:
    """Cache manager for earning summaries with automatic date-based refresh."""
    
    def __init__(self, cache_file: str = 'earning_summary_cache.json'):
        self.cache_file = cache_file
        self.cache_data = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file or create new cache structure."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    logger.info(f"Loaded earning summary cache from {self.cache_file}")
                    return cache
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading cache file: {e}, creating new cache")
        
        # Create new cache structure - only cache 1M data, filter others from it
        return {
            'last_updated': None,
            'cache_date': None,
            'periods': {
                '1M': {'data': None, 'last_updated': None}  # Only cache 1M, filter 1D/1W from it
            },
            'sector_cache': {}  # Cache for sector-specific queries
        }
    
    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache_data, f, indent=2, default=str)
            logger.info(f"Saved earning summary cache to {self.cache_file}")
        except IOError as e:
            logger.error(f"Error saving cache file: {e}")
    
    def _is_cache_valid(self, period: str, sectors: str = None) -> bool:
        """Check if cache is valid for the given period and sectors."""
        today = date.today()
        cache_date = self.cache_data.get('cache_date')
        
        # If no cache date, cache is invalid
        if not cache_date:
            return False
        
        # Parse cache date
        try:
            if isinstance(cache_date, str):
                cached_date = datetime.strptime(cache_date, '%Y-%m-%d').date()
            else:
                cached_date = cache_date
        except ValueError:
            return False
        
        # Cache is invalid if date has changed
        if cached_date != today:
            logger.info(f"Cache invalid: cached date {cached_date} != today {today}")
            return False
        
        # Check if 1M cache exists and is valid (all periods filter from 1M data)
        period_1m_cache = self.cache_data['periods'].get('1M')
        if not period_1m_cache or not period_1m_cache.get('data'):
            logger.info(f"1M cache missing or empty (required for all periods)")
            return False
        
        # Check sector-specific cache if sectors are specified
        if sectors:
            sector_key = f"{period}_{sectors}"
            sector_cache = self.cache_data['sector_cache'].get(sector_key)
            if not sector_cache or not sector_cache.get('data'):
                logger.info(f"Sector cache for {sector_key} missing or empty")
                return False
        
        logger.info(f"Cache valid for period {period}, sectors: {sectors}")
        return True
    
    def _get_cache_key(self, period: str, sectors: str = None) -> str:
        """Generate cache key for the given period and sectors."""
        if sectors:
            return f"{period}_{sectors}"
        return period
    
    def get_cached_summary(self, period: str, sectors: str = None, page: int = 1, per_page: int = 10) -> Optional[Dict[str, Any]]:
        """Get cached earning summary if available and valid."""
        if period not in ['1D', '1W', '1M']:
            logger.info(f"Period {period} not cached (only 1D, 1W, and 1M are cached), fetching fresh data")
            return None
        
        if not self._is_cache_valid(period, sectors):
            logger.info(f"Cache invalid for period {period}, will fetch fresh data")
            return None
        
        # Get cached data - all periods filter from 1M data
        if sectors:
            sector_key = self._get_cache_key(period, sectors)
            cached_data = self.cache_data['sector_cache'].get(sector_key, {}).get('data')
        else:
            # For 1D, 1W, and 1M, all use the same 1M cached data
            cached_data = self.cache_data['periods']['1M'].get('data')
        
        if not cached_data:
            logger.info(f"No cached data found for period {period}")
            return None
        
        # Apply pagination to cached data
        total = cached_data.get('total', 0)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        
        # Ensure we don't go out of bounds
        if start_index >= total:
            return {
                "page": page,
                "per_page": per_page,
                "total": total,
                "results": []
            }
        
        # Get paginated results
        results = cached_data.get('results', [])
        paginated_results = results[start_index:end_index]
        
        logger.info(f"Returning cached data for period {period}, page {page}: {len(paginated_results)} results")
        
        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "results": paginated_results
        }
    
    def cache_summary(self, period: str, data: Dict[str, Any], sectors: str = None):
        """Cache earning summary data for the given period."""
        if period not in ['1D', '1W', '1M']:
            logger.warning(f"Cannot cache period {period} (only 1D, 1W, and 1M are cached)")
            return
        
        today = date.today()
        
        # Update main cache
        self.cache_data['last_updated'] = datetime.now().isoformat()
        self.cache_data['cache_date'] = today.isoformat()
        
        # Cache period data (store full dataset for pagination)
        if sectors:
            sector_key = self._get_cache_key(period, sectors)
            self.cache_data['sector_cache'][sector_key] = {
                'data': data,
                'last_updated': datetime.now().isoformat(),
                'period': period,
                'sectors': sectors
            }
            logger.info(f"Cached sector-specific data for {sector_key}")
        else:
            # For 1D, 1W, and 1M, all store in the 1M slot since they share the same data
            self.cache_data['periods']['1M'] = {
                'data': data,
                'last_updated': datetime.now().isoformat()
            }
            logger.info(f"Cached data for period {period} (stored in 1M slot)")
        
        # Save cache to file
        self._save_cache()
    
    def get_or_fetch_summary(self, period: str, sectors: str = None, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Get cached summary or fetch and cache new data."""
        # Try to get from cache first
        cached_result = self.get_cached_summary(period, sectors, page, per_page)
        if cached_result:
            return cached_result
        
        # Cache miss, fetch fresh data
        logger.info(f"Cache miss for period {period}, fetching fresh data")
        
        try:
            # Fetch data from the main function
            fresh_data = get_earning_summary_optimized(
                sectors_param=sectors,
                period_param=period,
                page=1,  # Get all data for caching
                per_page=1000  # Large number to get all results
            )
            
            # Cache the full dataset
            self.cache_summary(period, fresh_data, sectors)
            
            # Return paginated result
            return self.get_cached_summary(period, sectors, page, per_page)
            
        except Exception as e:
            logger.error(f"Error fetching fresh data for period {period}: {e}")
            # Return empty result on error
            return {
                "page": page,
                "per_page": per_page,
                "total": 0,
                "results": []
            }
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache_data = {
            'last_updated': None,
            'cache_date': None,
            'periods': {
                '1M': {'data': None, 'last_updated': None}  # Only 1M is cached, others filter from it
            },
            'sector_cache': {}
        }
        self._save_cache()
        logger.info("Earning summary cache cleared (1M only, 1D/1W filter from it)")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status information."""
        today = date.today()
        cache_date = self.cache_data.get('cache_date')
        
        status = {
            'cache_file': self.cache_file,
            'last_updated': self.cache_data.get('last_updated'),
            'cache_date': cache_date,
            'is_valid': cache_date == today.isoformat() if cache_date else False,
            'periods': {},
            'sector_cache_count': len(self.cache_data.get('sector_cache', {}))
        }
        
        # Add period status - all periods share the same 1M data
        for period in ['1D', '1W', '1M']:
            period_1m_data = self.cache_data['periods'].get('1M', {})
            status['periods'][period] = {
                'has_data': period_1m_data.get('data') is not None,
                'last_updated': period_1m_data.get('last_updated'),
                'result_count': len(period_1m_data.get('data', {}).get('results', [])) if period_1m_data.get('data') else 0,
                'source': '1M cache' if period != '1M' else 'direct'
            }
        
        return status

# Global cache instance
earning_cache = EarningSummaryCache()

def get_cached_earning_summary(period: str, sectors: str = None, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """Convenience function to get cached earning summary."""
    return earning_cache.get_or_fetch_summary(period, sectors, page, per_page)

def clear_earning_cache():
    """Convenience function to clear earning cache."""
    earning_cache.clear_cache()

def get_earning_cache_status() -> Dict[str, Any]:
    """Convenience function to get cache status."""
    return earning_cache.get_cache_status()

def pre_warm_cache():
    """Pre-warm the cache by fetching 1M period and common sector combinations."""
    logger.info("Pre-warming earning summary cache (1M only, 1D/1W filter from it)...")
    
    try:
        # Pre-warm 1M period (1D and 1W will filter from this)
        try:
            earning_cache.get_or_fetch_summary('1M')
            logger.info("Pre-warmed cache for period 1M (1D and 1W will filter from this)")
        except Exception as e:
            logger.error(f"Error pre-warming cache for period 1M: {e}")
        
        # Pre-warm common sector combinations (all periods)
        common_sectors = [
            "Technology",
            "Healthcare", 
            "Financial Services",
            "Energy",
            "Consumer Cyclical"
        ]
        
        for sector in common_sectors:
            try:
                # Cache 1M for each sector, 1D and 1W will filter from it
                earning_cache.get_or_fetch_summary('1M', sector)
                logger.info(f"Pre-warmed cache for period 1M, sector {sector} (1D and 1W will filter from this)")
            except Exception as e:
                logger.error(f"Error pre-warming cache for sector {sector}: {e}")
        
        logger.info("Earning summary cache pre-warming completed (1M only, 1D/1W filter from it)")
        
    except Exception as e:
        logger.error(f"Error in pre-warming cache: {e}")

def get_cache_performance_metrics() -> Dict[str, Any]:
    """Get cache performance metrics."""
    try:
        from datetime import datetime, date
        
        # Get cache status
        status = get_earning_cache_status()
        
        # Calculate cache hit rate (this would need to be implemented with counters)
        metrics = {
            'cache_status': status,
            'cache_age_hours': 0,
            'estimated_savings': {
                'api_calls_saved': 0,
                'time_saved_seconds': 0
            }
        }
        
        # Calculate cache age
        if status.get('last_updated'):
            try:
                last_updated = datetime.fromisoformat(status['last_updated'].replace('Z', '+00:00'))
                age_hours = (datetime.now() - last_updated).total_seconds() / 3600
                metrics['cache_age_hours'] = round(age_hours, 2)
            except:
                pass
        
        # Estimate savings based on cache validity
        if status.get('is_valid'):
            # Rough estimate: each period fetch takes ~5-15 seconds
            # With 3 periods (1D, 1W, 1M) sharing the same cache, that's potentially 15-45 seconds saved per day
            metrics['estimated_savings']['api_calls_saved'] = 3  # 1D, 1W, 1M all use same cache
            metrics['estimated_savings']['time_saved_seconds'] = 30  # Rough estimate
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting cache performance metrics: {e}")
        return {'error': str(e)}
