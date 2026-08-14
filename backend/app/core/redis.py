import logging
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Any = None
_redis_available: bool = True


class DummyRedis:
    def __getattr__(self, name: str) -> Any:
        async def dummy(*args: Any, **kwargs: Any) -> Any:
            if name == "ping":
                return True
            if name == "brpop":
                import asyncio
                await asyncio.sleep(5)
                return None
            return None
        return dummy


def build_redis_key(*parts: object) -> str:
    settings = get_settings()
    normalized_parts = [str(part).strip(":") for part in parts if part is not None]
    return ":".join([settings.redis_key_prefix, *normalized_parts])


def get_redis_client() -> Any:
    global _redis_client, _redis_available
    if _redis_client is None:
        settings = get_settings()
        if not _redis_available and settings.app_env != "production":
            _redis_client = DummyRedis()
        else:
            _redis_client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        if not isinstance(_redis_client, DummyRedis):
            await _redis_client.aclose()
        _redis_client = None


async def ping_redis() -> bool:
    global _redis_available, _redis_client
    settings = get_settings()
    try:
        client = get_redis_client()
        if isinstance(client, DummyRedis):
            return True
        return bool(await client.ping())
    except Exception as e:
        if settings.app_env == "production":
            raise
        logger.warning(f"Redis is unavailable: {e}. Falling back to DummyRedis for local development.")
        _redis_available = False
        _redis_client = DummyRedis()
        return False
