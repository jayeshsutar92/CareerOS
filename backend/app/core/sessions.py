import json
from typing import Any

from app.core.config import get_settings
from app.core.redis import build_redis_key, get_redis_client


def build_session_key(session_id: str) -> str:
    return build_redis_key("session", session_id)


async def session_get(session_id: str) -> dict[str, Any] | None:
    value = await get_redis_client().get(build_session_key(session_id))
    if value is None:
        return None
    return json.loads(value)


async def session_set(
    session_id: str, data: dict[str, Any], ttl_seconds: int | None = None
) -> None:
    settings = get_settings()
    await get_redis_client().set(
        build_session_key(session_id),
        json.dumps(data, default=str),
        ex=ttl_seconds or settings.session_ttl_seconds,
    )


async def session_delete(session_id: str) -> None:
    await get_redis_client().delete(build_session_key(session_id))
