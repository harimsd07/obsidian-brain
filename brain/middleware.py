"""
Rate limiting and caching middleware for web UI.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from collections import defaultdict
import logging

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Rate Limiting (Simple Token Bucket)
# ──────────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""
    
    def __init__(self):
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            "tokens": 0,
            "last_refill": datetime.now()
        })
    
    def is_allowed(self, client_ip: str, endpoint: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if a request is allowed for the client/endpoint.
        
        Args:
            client_ip: Client IP address
            endpoint: API endpoint name
            max_requests: Max requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            True if request is allowed, False if rate limited
        """
        key = f"{client_ip}:{endpoint}"
        bucket = self.buckets[key]
        
        now = datetime.now()
        time_passed = (now - bucket["last_refill"]).total_seconds()
        
        # Refill tokens based on time passed
        refill_rate = max_requests / window_seconds
        bucket["tokens"] = min(max_requests, bucket["tokens"] + refill_rate * time_passed)
        bucket["last_refill"] = now
        
        # Check if we have tokens
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        
        return False
    
    def get_retry_after(self, client_ip: str, endpoint: str, refill_rate: float) -> int:
        """Get retry-after time in seconds."""
        key = f"{client_ip}:{endpoint}"
        bucket = self.buckets[key]
        # Time to get 1 token back
        return max(1, int(1.0 / refill_rate + 1))


# Global rate limiter instance
rate_limiter = RateLimiter()

# Rate limiting strategies
LIMITS = {
    "search": {"max_requests": 100, "window_seconds": 3600},     # 100/hour
    "ask": {"max_requests": 50, "window_seconds": 3600},         # 50/hour
    "stats": {"max_requests": 1000, "window_seconds": 3600},     # 1000/hour
}


# ──────────────────────────────────────────────────────────────────────────────
# Query Caching
# ──────────────────────────────────────────────────────────────────────────────

class QueryCache:
    """Simple in-memory cache for search and ask queries with TTL."""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            maxsize: Maximum number of cached items
            ttl: Time to live in seconds (default: 1 hour)
        """
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
    
    @staticmethod
    def _make_key(query: str, n: int, hybrid: bool, endpoint: str) -> str:
        """Generate cache key from query parameters."""
        cache_input = f"{endpoint}:{query}:{n}:{hybrid}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def get(self, query: str, n: int, hybrid: bool, endpoint: str) -> Optional[Any]:
        """Get cached result if available."""
        key = self._make_key(query, n, hybrid, endpoint)
        result = self._cache.get(key)
        if result:
            logger.debug(f"Cache hit for {endpoint}: {query[:30]}")
            return result
        return None
    
    def set(self, query: str, n: int, hybrid: bool, endpoint: str, result: Any) -> None:
        """Cache a result."""
        key = self._make_key(query, n, hybrid, endpoint)
        self._cache[key] = result
        logger.debug(f"Cache set for {endpoint}: {query[:30]}")
    
    def clear(self) -> None:
        """Clear all cached items."""
        self._cache.clear()
        logger.info("Query cache cleared")
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "maxsize": self._cache.maxsize,
            "ttl": self._cache.ttl
        }


# Global cache instance
query_cache = QueryCache(maxsize=1000, ttl=3600)  # 1000 items, 1 hour TTL


# ──────────────────────────────────────────────────────────────────────────────
# Monitoring/Metrics
# ──────────────────────────────────────────────────────────────────────────────

class RequestMetrics:
    """Track basic request metrics."""
    
    def __init__(self):
        self.search_requests = 0
        self.ask_requests = 0
        self.stats_requests = 0
        self.total_requests = 0
        self.start_time = datetime.now()
    
    def record_search(self) -> None:
        self.search_requests += 1
        self.total_requests += 1
    
    def record_ask(self) -> None:
        self.ask_requests += 1
        self.total_requests += 1
    
    def record_stats(self) -> None:
        self.stats_requests += 1
        self.total_requests += 1
    
    def get_stats(self) -> dict:
        """Get aggregated metrics."""
        uptime = datetime.now() - self.start_time
        return {
            "uptime_seconds": round(uptime.total_seconds()),
            "total_requests": self.total_requests,
            "search_requests": self.search_requests,
            "ask_requests": self.ask_requests,
            "stats_requests": self.stats_requests,
            "cache_stats": query_cache.stats()
        }


# Global metrics instance
metrics = RequestMetrics()
