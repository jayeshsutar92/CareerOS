import functools
import logging
import pickle
import zlib
import asyncio
from typing import Callable, Any

from app.core.redis import get_redis_client, build_redis_key
from app.lead_discovery.metrics import DiscoveryMetrics

logger = logging.getLogger(__name__)

# Global dictionary to track in-flight requests for deduplication
_in_flight_requests = {}

def cached(prefix: str, ttl_seconds: int = 86400, key_func: Callable[..., str] | None = None):
    """
    An asynchronous caching decorator backed by Redis.
    Supports in-flight request deduplication.
    """
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract metrics tracker if passed in kwargs
            metrics: DiscoveryMetrics | None = kwargs.get("metrics")
            
            # Generate cache key
            if key_func:
                cache_key_suffix = key_func(*args, **kwargs)
            else:
                # Default to string representation of args/kwargs (excluding self/metrics)
                clean_args = [a for a in args if not hasattr(a, "__dict__")]
                clean_kwargs = {k: v for k, v in kwargs.items() if k != "metrics"}
                cache_key_suffix = f"{clean_args}:{clean_kwargs}"
                
            redis_key = build_redis_key("cache", prefix, cache_key_suffix)
            redis = get_redis_client()
            
            # In-flight deduplication
            if redis_key in _in_flight_requests:
                logger.debug(f"In-flight deduplication for {redis_key}")
                return await _in_flight_requests[redis_key].wait()

            # Create future for this request
            future = asyncio.Future()
            _in_flight_requests[redis_key] = future

            try:
                # Check Redis cache
                if redis:
                    try:
                        # Attempt to get raw bytes since we use pickle/zlib
                        # Redis client might be configured with decode_responses=True in app.core.redis
                        # We need to bypass it or store as base64 string
                        cached_data_str = await redis.get(redis_key)
                        if cached_data_str:
                            import base64
                            cached_bytes = base64.b64decode(cached_data_str.encode('utf-8'))
                            decompressed = zlib.decompress(cached_bytes)
                            result = pickle.loads(decompressed)
                            if metrics:
                                metrics.record_cache_hit()
                            
                            future.set_result(result)
                            return result
                    except Exception as e:
                        logger.warning(f"Failed to read from cache {redis_key}: {e}")

                if metrics:
                    metrics.record_cache_miss()

                # Execute original function
                result = await func(*args, **kwargs)

                # Save to Redis
                if redis:
                    try:
                        import base64
                        serialized = pickle.dumps(result)
                        compressed = zlib.compress(serialized)
                        b64_str = base64.b64encode(compressed).decode('utf-8')
                        await redis.setex(redis_key, ttl_seconds, b64_str)
                    except Exception as e:
                        logger.warning(f"Failed to write to cache {redis_key}: {e}")

                future.set_result(result)
                return result
                
            except Exception as e:
                future.set_exception(e)
                raise
            finally:
                _in_flight_requests.pop(redis_key, None)

        return wrapper
    return decorator
