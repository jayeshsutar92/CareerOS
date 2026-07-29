from __future__ import annotations

import json
from typing import Any

import pytest
from app.core.config import get_settings
from app.workers import queue
from app.workers.base import TaskPayload, TaskResult, TaskStatus, WorkerTask
from app.workers.registry import TaskRegistry, task_registry
from app.workers.runner import WorkerRunner
from app.workers.tasks import register_tasks


class FakeRedis:
    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}
        self.sorted_sets: dict[str, dict[str, float]] = {}
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    async def lpush(self, key: str, value: str) -> int:
        self.lists.setdefault(key, []).insert(0, value)
        return len(self.lists[key])

    async def brpop(self, key: str, timeout: int = 1) -> tuple[str, str] | None:
        values = self.lists.get(key, [])
        if not values:
            return None
        return key, values.pop()

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        self.sorted_sets.setdefault(key, {}).update(mapping)
        return len(mapping)

    async def zrangebyscore(
        self,
        key: str,
        min: float,
        max: float,
        start: int = 0,
        num: int | None = None,
    ) -> list[str]:
        items = [
            value for value, score in self.sorted_sets.get(key, {}).items() if min <= score <= max
        ]
        return items[start : start + num if num is not None else None]

    async def zrem(self, key: str, value: str) -> int:
        if value in self.sorted_sets.get(key, {}):
            del self.sorted_sets[key][value]
            return 1
        return 0

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    async def get(self, key: str) -> str | None:
        return self.values.get(key)


class SuccessfulTask(WorkerTask):
    name = "success"

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        return {"received": kwargs}


class FailingTask(WorkerTask):
    name = "failure"
    max_retries = 1
    retry_delay_seconds = 10

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("task failed")


def reset_settings(monkeypatch: pytest.MonkeyPatch, **env: Any) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    get_settings.cache_clear()


def test_task_payload_round_trip() -> None:
    payload = TaskPayload(id="task-1", name="analysis", args={"company_id": "company-1"})

    parsed = TaskPayload.from_json(payload.to_json())

    assert parsed.id == "task-1"
    assert parsed.name == "analysis"
    assert parsed.args == {"company_id": "company-1"}


def test_example_tasks_are_registered() -> None:
    register_tasks()

    assert {"analysis", "business_sync", "cleanup"}.issubset(task_registry.names())


@pytest.mark.asyncio
async def test_enqueue_task_uses_immediate_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    reset_settings(monkeypatch, REDIS_KEY_PREFIX="test", WORKER_QUEUE_NAME="default")
    monkeypatch.setattr(queue, "get_redis_client", lambda: fake_redis)

    payload = await queue.enqueue_task("analysis", {"company_id": "company-1"}, task_id="task-1")

    assert payload.id == "task-1"
    queued_payload = fake_redis.lists["test:workers:default:queue"][0]
    assert json.loads(queued_payload)["name"] == "analysis"


@pytest.mark.asyncio
async def test_scheduled_tasks_move_to_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    reset_settings(monkeypatch, REDIS_KEY_PREFIX="test", WORKER_QUEUE_NAME="default")
    monkeypatch.setattr(queue, "get_redis_client", lambda: fake_redis)

    await queue.enqueue_task("cleanup", task_id="task-1", delay_seconds=1)
    scheduled_payload = next(iter(fake_redis.sorted_sets["test:workers:default:scheduled"]))
    fake_redis.sorted_sets["test:workers:default:scheduled"][scheduled_payload] = 0

    moved = await queue.move_due_scheduled_tasks()

    assert moved == 1
    assert len(fake_redis.lists["test:workers:default:queue"]) == 1


@pytest.mark.asyncio
async def test_worker_runner_stores_success_result(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    registry = TaskRegistry()
    registry.register(SuccessfulTask())
    reset_settings(monkeypatch, REDIS_KEY_PREFIX="test", WORKER_QUEUE_NAME="default")
    monkeypatch.setattr(queue, "get_redis_client", lambda: fake_redis)

    await queue.enqueue_task("success", {"value": 1}, task_id="task-1")
    await WorkerRunner(registry=registry).run_once()

    result = TaskResult.from_json(fake_redis.values["test:workers:result:task-1"])
    assert result.status == TaskStatus.SUCCEEDED
    assert result.result == {"received": {"value": 1}}


@pytest.mark.asyncio
async def test_worker_runner_schedules_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = FakeRedis()
    registry = TaskRegistry()
    registry.register(FailingTask())
    reset_settings(monkeypatch, REDIS_KEY_PREFIX="test", WORKER_QUEUE_NAME="default")
    monkeypatch.setattr(queue, "get_redis_client", lambda: fake_redis)

    await queue.enqueue_task("failure", task_id="task-1")
    await WorkerRunner(registry=registry).run_once()

    assert len(fake_redis.sorted_sets["test:workers:default:scheduled"]) == 1
    result = TaskResult.from_json(fake_redis.values["test:workers:result:task-1"])
    assert result.status == TaskStatus.RETRYING
    assert result.attempts == 1
