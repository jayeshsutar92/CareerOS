from redis.asyncio import Redis

from app.core.config import get_settings

_redis_client: Redis | None = None


def build_redis_key(*parts: object) -> str:
    settings = get_settings()
    normalized_parts = [str(part).strip(":") for part in parts if part is not None]
    return ":".join([settings.redis_key_prefix, *normalized_parts])


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
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
        await _redis_client.aclose()
        _redis_client = None


async def ping_redis() -> bool:
    return bool(await get_redis_client().ping())
