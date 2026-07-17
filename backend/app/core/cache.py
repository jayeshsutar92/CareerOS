import json
from typing import Any

from app.core.config import get_settings
from app.core.redis import build_redis_key, get_redis_client


def build_cache_key(key: str) -> str:
    return build_redis_key("cache", key)


async def cache_get(key: str) -> Any | None:
    value = await get_redis_client().get(build_cache_key(key))
    if value is None:
        return None
    return json.loads(value)


async def cache_set(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    settings = get_settings()
    await get_redis_client().set(
        build_cache_key(key),
        json.dumps(value, default=str),
        ex=ttl_seconds or settings.cache_default_ttl_seconds,
    )


async def cache_delete(key: str) -> None:
    await get_redis_client().delete(build_cache_key(key))
