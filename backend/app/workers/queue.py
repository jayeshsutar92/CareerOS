from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.core.redis import build_redis_key, get_redis_client
from app.workers.base import TaskPayload, TaskResult


def _queue_key(queue_name: str | None = None) -> str:
    settings = get_settings()
    return build_redis_key("workers", queue_name or settings.worker_queue_name, "queue")


def _scheduled_key(queue_name: str | None = None) -> str:
    settings = get_settings()
    return build_redis_key("workers", queue_name or settings.worker_queue_name, "scheduled")


def _result_key(task_id: str) -> str:
    return build_redis_key("workers", "result", task_id)


def _dead_letter_key(queue_name: str | None = None) -> str:
    settings = get_settings()
    return build_redis_key("workers", queue_name or settings.worker_queue_name, "dead-letter")


async def enqueue_task(
    name: str,
    args: dict[str, Any] | None = None,
    *,
    task_id: str | None = None,
    queue_name: str | None = None,
    delay_seconds: int = 0,
    max_retries: int | None = None,
) -> TaskPayload:
    run_at = datetime.now(UTC) + timedelta(seconds=delay_seconds) if delay_seconds > 0 else None
    payload = TaskPayload(
        id=task_id or str(uuid4()),
        name=name,
        args=args or {},
        max_retries=max_retries,
        run_at=run_at,
    )
    redis = get_redis_client()

    if run_at is not None:
        await redis.zadd(_scheduled_key(queue_name), {payload.to_json(): run_at.timestamp()})
        return payload

    await redis.lpush(_queue_key(queue_name), payload.to_json())
    return payload


async def dequeue_task(
    queue_name: str | None = None, timeout_seconds: int = 1
) -> TaskPayload | None:
    item = await get_redis_client().brpop(_queue_key(queue_name), timeout=timeout_seconds)
    if item is None:
        return None
    _, payload = item
    return TaskPayload.from_json(payload)


async def move_due_scheduled_tasks(queue_name: str | None = None, limit: int = 100) -> int:
    now = datetime.now(UTC).timestamp()
    redis = get_redis_client()
    key = _scheduled_key(queue_name)
    due_payloads = await redis.zrangebyscore(key, min=0, max=now, start=0, num=limit)
    moved = 0

    for payload in due_payloads:
        removed = await redis.zrem(key, payload)
        if removed:
            await redis.lpush(_queue_key(queue_name), payload)
            moved += 1

    return moved


async def schedule_retry(
    payload: TaskPayload,
    *,
    delay_seconds: int,
    queue_name: str | None = None,
) -> TaskPayload:
    retry_payload = TaskPayload(
        id=payload.id,
        name=payload.name,
        args=payload.args,
        attempt=payload.attempt + 1,
        max_retries=payload.max_retries,
        run_at=datetime.now(UTC) + timedelta(seconds=delay_seconds),
        created_at=payload.created_at,
    )
    await get_redis_client().zadd(
        _scheduled_key(queue_name),
        {retry_payload.to_json(): retry_payload.run_at.timestamp()},
    )
    return retry_payload


async def store_task_result(result: TaskResult, ttl_seconds: int | None = None) -> None:
    settings = get_settings()
    ttl = ttl_seconds if ttl_seconds is not None else settings.worker_result_ttl_seconds
    await get_redis_client().set(_result_key(result.task_id), result.to_json(), ex=ttl)


async def get_task_result(task_id: str) -> TaskResult | None:
    value = await get_redis_client().get(_result_key(task_id))
    return TaskResult.from_json(value) if value else None


async def send_to_dead_letter(
    payload: TaskPayload,
    error: str,
    *,
    queue_name: str | None = None,
) -> None:
    dead_letter_payload = {
        "task": json.loads(payload.to_json()),
        "error": error,
        "failed_at": datetime.now(UTC).isoformat(),
    }
    await get_redis_client().lpush(_dead_letter_key(queue_name), json.dumps(dead_letter_payload))
