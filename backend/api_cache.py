"""
API Cache & Rate Limiting
Implements response caching and rate limiting for Flask API endpoints
"""
import time
import hashlib
import json
from functools import wraps
from typing import Optional, Dict, Any, Callable
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple in-memory cache with TTL (Time To Live)
    """
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, ttl: int = 60) -> Optional[Any]:
        """
        Get value from cache if not expired
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            Cached value or None if expired/missing
        """
        if key in self._cache:
            timestamp = self._timestamps.get(key, 0)
            if time.time() - timestamp < ttl:
                logger.debug(f"✅ Cache HIT: {key}")
                return self._cache[key]
            else:
                # Expired - remove
                logger.debug(f"⏰ Cache EXPIRED: {key}")
                del self._cache[key]
                del self._timestamps[key]
        
        logger.debug(f"❌ Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value
        self._timestamps[key] = time.time()
        logger.debug(f"💾 Cache SET: {key}")
    
    def delete(self, key: str):
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            logger.debug(f"🗑️  Cache DELETE: {key}")
    
    def clear(self):
        """Clear entire cache"""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("🗑️  Cache CLEARED")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'total_keys': len(self._cache),
            'memory_size_kb': len(str(self._cache)) / 1024
        }


class RateLimiter:
    """
    Simple rate limiter
    Limits requests per IP address
    """
    
    def __init__(self):
        self._requests = {}  # {ip: [timestamps]}
    
    def is_allowed(self, identifier: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request is allowed
        
        Args:
            identifier: Client identifier (e.g., IP address)
            max_requests: Max requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        
        # Get request timestamps for this identifier
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        timestamps = self._requests[identifier]
        
        # Remove old timestamps outside window
        timestamps = [ts for ts in timestamps if now - ts < window_seconds]
        self._requests[identifier] = timestamps
        
        # Check if limit exceeded
        if len(timestamps) >= max_requests:
            logger.warning(f"⚠️  Rate limit exceeded for {identifier}")
            return False
        
        # Add current timestamp
        timestamps.append(now)
        return True
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            'tracked_clients': len(self._requests),
            'total_requests': sum(len(ts) for ts in self._requests.values())
        }


# Global instances
_cache = SimpleCache()
_rate_limiter = RateLimiter()


def cached(ttl: int = 60, key_prefix: str = ''):
    """
    Decorator to cache Flask route responses
    
    Args:
        ttl: Cache time to live in seconds (default: 60)
        key_prefix: Prefix for cache key (default: '')
        
    Usage:
        @app.route('/api/articles')
        @cached(ttl=120, key_prefix='articles')
        def get_articles():
            return jsonify(articles)
    """
    def decorator(f: Callable):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Create cache key from route + args + query params
            route = request.path
            query = request.query_string.decode('utf-8')
            cache_key = f"{key_prefix}:{route}:{query}"
            cache_key_hash = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Try to get from cache
            cached_response = _cache.get(cache_key_hash, ttl)
            if cached_response is not None:
                return jsonify(cached_response)
            
            # Execute function
            response = f(*args, **kwargs)
            
            # Cache the response data (if it's a dict or list)
            if hasattr(response, 'get_json'):
                data = response.get_json()
                if data is not None:
                    _cache.set(cache_key_hash, data)
            
            return response
        
        return wrapper
    return decorator


def rate_limited(max_requests: int = 60, window_seconds: int = 60):
    """
    Decorator to rate limit Flask routes
    
    Args:
        max_requests: Max requests allowed (default: 60)
        window_seconds: Time window in seconds (default: 60)
        
    Usage:
        @app.route('/api/search')
        @rate_limited(max_requests=30, window_seconds=60)
        def search():
            return jsonify(results)
    """
    def decorator(f: Callable):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get client identifier (IP address)
            identifier = request.remote_addr or 'unknown'
            
            # Check rate limit
            if not _rate_limiter.is_allowed(identifier, max_requests, window_seconds):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Max {max_requests} requests per {window_seconds} seconds'
                }), 429  # Too Many Requests
            
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


def invalidate_cache(key_prefix: str = ''):
    """
    Invalidate all cache entries with given prefix
    
    Args:
        key_prefix: Cache key prefix to invalidate
    """
    # For simplicity, clear entire cache
    # In production, use Redis with pattern matching
    _cache.clear()
    logger.info(f"🗑️  Invalidated cache for prefix: {key_prefix}")


def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return {
        'cache': _cache.get_stats(),
        'rate_limiter': _rate_limiter.get_stats()
    }


def clear_cache():
    """Clear entire cache"""
    _cache.clear()


# Health check endpoint helper
def create_health_endpoint(app):
    """
    Add health check endpoint to Flask app
    
    Args:
        app: Flask app instance
        
    Usage:
        from api_cache import create_health_endpoint
        create_health_endpoint(app)
    """
    @app.route('/api/health')
    def health():
        stats = get_cache_stats()
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'cache_stats': stats['cache'],
            'rate_limiter_stats': stats['rate_limiter']
        })
    
    @app.route('/api/cache/clear', methods=['POST'])
    def clear_cache_endpoint():
        clear_cache()
        return jsonify({'message': 'Cache cleared successfully'})


# Example usage
if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/api/test')
    @cached(ttl=30, key_prefix='test')
    @rate_limited(max_requests=10, window_seconds=60)
    def test_endpoint():
        return jsonify({
            'message': 'This response is cached for 30 seconds',
            'timestamp': time.time()
        })
    
    create_health_endpoint(app)
    
    print("Test endpoints created:")
    print("  GET  /api/test     - Cached & rate limited")
    print("  GET  /api/health   - Health check")
    print("  POST /api/cache/clear - Clear cache")
