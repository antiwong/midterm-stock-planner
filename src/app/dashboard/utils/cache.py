"""
Query Caching Utilities
========================
Cache frequently accessed database queries and data with compression support.
"""

import functools
import hashlib
import json
import time
import gzip
import pickle
from typing import Any, Callable, Optional, Dict
from datetime import datetime, timedelta


class QueryCache:
    """Simple in-memory cache for query results."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() < entry['expires_at']:
                value = entry['value']
                # Decompress if needed
                if entry.get('compressed', False):
                    try:
                        decompressed = gzip.decompress(value)
                        value = pickle.loads(decompressed)
                    except Exception:
                        # If decompression fails, return None
                        del self.cache[key]
                        return None
                return value
            else:
                # Expired, remove it
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, compress: bool = True):
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            compress: Whether to compress large values (default: True)
        """
        ttl = ttl or self.default_ttl
        
        # Compress large values (dicts, lists, DataFrames)
        if compress and isinstance(value, (dict, list)):
            try:
                # Serialize and compress
                serialized = pickle.dumps(value)
                if len(serialized) > 1024:  # Compress if > 1KB
                    compressed = gzip.compress(serialized)
                    if len(compressed) < len(serialized) * 0.8:  # Only use if 20%+ savings
                        self.cache[key] = {
                            'value': compressed,
                            'compressed': True,
                            'expires_at': time.time() + ttl,
                            'created_at': time.time()
                        }
                        return
            except Exception:
                # If compression fails, store uncompressed
                pass
        
        # Store uncompressed
        self.cache[key] = {
            'value': value,
            'compressed': False,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
    
    def clear(self, pattern: Optional[str] = None):
        """Clear cache entries. If pattern provided, only clear matching keys."""
        if pattern:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = len(self.cache)
        expired = sum(1 for entry in self.cache.values() if time.time() >= entry['expires_at'])
        active = total_size - expired
        
        return {
            'total_entries': total_size,
            'active_entries': active,
            'expired_entries': expired,
            'default_ttl': self.default_ttl
        }


# Global cache instance
_global_cache = QueryCache()


def cached_query(ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key from arguments
    
    Usage:
        @cached_query(ttl=600)
        def expensive_query(param1, param2):
            # ... expensive operation ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name + args + kwargs
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_str = "|".join(key_parts)
                cache_key = hashlib.md5(key_str.encode()).hexdigest()
            
            # Check cache
            cached_result = _global_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            _global_cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_key_for_run(run_id: str, query_type: str) -> str:
    """Generate cache key for run-specific queries."""
    return f"run:{run_id}:{query_type}"


def cache_key_for_watchlist(watchlist: str, query_type: str) -> str:
    """Generate cache key for watchlist-specific queries."""
    return f"watchlist:{watchlist}:{query_type}"


def clear_cache(pattern: Optional[str] = None):
    """Clear cache entries matching pattern."""
    _global_cache.clear(pattern)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return _global_cache.get_stats()
