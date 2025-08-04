"""Redis-based caching service for API responses."""

import json
import asyncio
from typing import Any, Callable, Optional
from functools import wraps
import hashlib

import redis.asyncio as aioredis
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Service for caching API responses in Redis."""
    
    def __init__(self):
        self.redis = None
        self.default_ttl = 3600  # 1 hour
        self.cache_prefix = "sota:"
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Connected to Redis for caching")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Continue without caching if Redis is unavailable
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
    
    def _make_key(self, namespace: str, key: str) -> str:
        """Create a cache key with namespace."""
        return f"{self.cache_prefix}{namespace}:{key}"
    
    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            return None
        
        try:
            cache_key = self._make_key(namespace, key)
            value = await self.redis.get(cache_key)
            
            if value:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(value)
            
            logger.debug(f"Cache miss: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with TTL."""
        if not self.redis:
            return False
        
        try:
            cache_key = self._make_key(namespace, key)
            ttl = ttl or self.default_ttl
            
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(value, default=str)
            )
            
            logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete value from cache."""
        if not self.redis:
            return False
        
        try:
            cache_key = self._make_key(namespace, key)
            await self.redis.delete(cache_key)
            logger.debug(f"Cache delete: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        if not self.redis:
            return 0
        
        try:
            pattern = self._make_key(namespace, "*")
            keys = await self.redis.keys(pattern)
            
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Cleared {deleted} keys from namespace: {namespace}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0
    
    async def get_or_set(
        self,
        namespace: str,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """Get from cache or compute and cache."""
        # Try to get from cache
        cached = await self.get(namespace, key)
        if cached is not None:
            return cached
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Cache the result
        await self.set(namespace, key, value, ttl)
        
        return value
    
    def cached(
        self,
        namespace: str,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = hashlib.md5(
                        ":".join(key_parts).encode()
                    ).hexdigest()
                
                # Use get_or_set
                return await self.get_or_set(
                    namespace=namespace,
                    key=cache_key,
                    factory=lambda: func(*args, **kwargs),
                    ttl=ttl
                )
            
            return wrapper
        return decorator


# Global cache instance
cache_service = CacheService()


# Cache configuration for different types of data
CACHE_CONFIG = {
    "model_practices": {
        "ttl": 3600,  # 1 hour
        "namespace": "practices"
    },
    "model_list": {
        "ttl": 300,  # 5 minutes
        "namespace": "models"
    },
    "search_results": {
        "ttl": 900,  # 15 minutes
        "namespace": "search"
    },
    "usage_patterns": {
        "ttl": 7200,  # 2 hours
        "namespace": "usage"
    },
    "scraper_status": {
        "ttl": 60,  # 1 minute
        "namespace": "status"
    },
}


async def init_cache():
    """Initialize cache service."""
    await cache_service.connect()


async def close_cache():
    """Close cache service."""
    await cache_service.disconnect()


# Utility functions for specific cache operations
async def invalidate_model_cache(model_id: str, category: str):
    """Invalidate all cache entries for a specific model."""
    # Clear specific model practices
    await cache_service.delete(
        "practices",
        f"{category}/{model_id}"
    )
    
    # Clear model list cache as counts may have changed
    await cache_service.clear_namespace("models")
    
    # Clear search results that might include this model
    await cache_service.clear_namespace("search")
    
    logger.info(f"Invalidated cache for model: {category}/{model_id}")


async def invalidate_all_cache():
    """Invalidate all cached data."""
    namespaces = set(config["namespace"] for config in CACHE_CONFIG.values())
    
    for namespace in namespaces:
        await cache_service.clear_namespace(namespace)
    
    logger.info("Invalidated all cache")


async def warm_cache():
    """Pre-populate cache with frequently accessed data."""
    from src.services.model_service import ModelService
    from src.services.usage_service import UsageService
    
    model_service = ModelService()
    usage_service = UsageService()
    
    logger.info("Starting cache warming...")
    
    # Cache all model lists
    await model_service.list_models()
    
    # Cache usage patterns
    await usage_service.get_usage_patterns()
    
    # Cache popular models
    popular_models = [
        ("text", "gpt-4"),
        ("text", "claude-3"),
        ("image", "stable-diffusion"),
        ("image", "midjourney"),
    ]
    
    for category, model_id in popular_models:
        try:
            await model_service.get_model_practices(category, model_id)
        except:
            pass
    
    logger.info("Cache warming completed")