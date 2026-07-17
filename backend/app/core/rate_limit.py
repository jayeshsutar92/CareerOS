from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.redis import build_redis_key, get_redis_client


@dataclass(frozen=True)
class RateLimitResult:
    limit: int
    remaining: int
    reset_seconds: int


async def check_rate_limit(identifier: str, scope: str = "api") -> RateLimitResult:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return RateLimitResult(
            limit=settings.rate_limit_requests,
            remaining=settings.rate_limit_requests,
            reset_seconds=settings.rate_limit_window_seconds,
        )

    redis = get_redis_client()
    key = build_redis_key("rate_limit", scope, identifier)
    try:
        current_count = await redis.incr(key)
        if current_count == 1:
            await redis.expire(key, settings.rate_limit_window_seconds)

        ttl = await redis.ttl(key)
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiting is temporarily unavailable",
        ) from exc
    reset_seconds = ttl if ttl > 0 else settings.rate_limit_window_seconds
    remaining = max(settings.rate_limit_requests - current_count, 0)

    if current_count > settings.rate_limit_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(reset_seconds)},
        )

    return RateLimitResult(
        limit=settings.rate_limit_requests,
        remaining=remaining,
        reset_seconds=reset_seconds,
    )


def get_rate_limit_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"
