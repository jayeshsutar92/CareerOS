from typing import Any

import pytest
from app.core import cache, rate_limit, redis, sessions
from app.core.config import get_settings
from fastapi import HTTPException
from starlette.datastructures import Headers


class FakeRequest:
    def __init__(self, headers: dict[str, str] | None = None, host: str = "127.0.0.1") -> None:
        self.headers = Headers(headers or {})
        self.client = type("Client", (), {"host": host})()


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}
        self.counters: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds

    async def ttl(self, key: str) -> int:
        return self.expirations.get(key, -1)


def reset_settings(monkeypatch: pytest.MonkeyPatch, **env: Any) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    get_settings.cache_clear()


def test_build_redis_key_uses_configured_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings(monkeypatch, REDIS_KEY_PREFIX="test")

    assert redis.build_redis_key("cache", "companies") == "test:cache:companies"


@pytest.mark.asyncio
async def test_cache_utilities_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    reset_settings(monkeypatch, REDIS_KEY_PREFIX="test", CACHE_DEFAULT_TTL_SECONDS=42)
    monkeypatch.setattr(cache, "get_redis_client", lambda: fake_redis)

    await cache.cache_set("key", {"value": 1})

    assert await cache.cache_get("key") == {"value": 1}
    assert fake_redis.expirations["test:cache:key"] == 42

    await cache.cache_delete("key")
    assert await cache.cache_get("key") is None


@pytest.mark.asyncio
async def test_session_storage_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    reset_settings(monkeypatch, REDIS_KEY_PREFIX="test", SESSION_TTL_SECONDS=99)
    monkeypatch.setattr(sessions, "get_redis_client", lambda: fake_redis)

    await sessions.session_set("session-id", {"user_id": "user-1"})

    assert await sessions.session_get("session-id") == {"user_id": "user-1"}
    assert fake_redis.expirations["test:session:session-id"] == 99

    await sessions.session_delete("session-id")
    assert await sessions.session_get("session-id") is None


@pytest.mark.asyncio
async def test_rate_limit_disabled_does_not_touch_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings(monkeypatch, RATE_LIMIT_ENABLED="false", RATE_LIMIT_REQUESTS=10)

    result = await rate_limit.check_rate_limit("127.0.0.1")

    assert result.limit == 10
    assert result.remaining == 10


@pytest.mark.asyncio
async def test_rate_limit_raises_after_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    reset_settings(
        monkeypatch,
        REDIS_KEY_PREFIX="test",
        RATE_LIMIT_ENABLED="true",
        RATE_LIMIT_REQUESTS=1,
        RATE_LIMIT_WINDOW_SECONDS=60,
    )
    monkeypatch.setattr(rate_limit, "get_redis_client", lambda: fake_redis)

    await rate_limit.check_rate_limit("127.0.0.1")

    with pytest.raises(HTTPException) as exc_info:
        await rate_limit.check_rate_limit("127.0.0.1")

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "60"}


def test_rate_limit_identifier_prefers_forwarded_for() -> None:
    request = FakeRequest(headers={"x-forwarded-for": "203.0.113.10, 10.0.0.1"})

    assert rate_limit.get_rate_limit_identifier(request) == "203.0.113.10"
