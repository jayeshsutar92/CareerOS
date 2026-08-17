from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskStatus(StrEnum):
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class TaskPayload:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    attempt: int = 0
    max_retries: int | None = None
    run_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_json(self) -> str:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["run_at"] = self.run_at.isoformat() if self.run_at else None
        return json.dumps(payload, default=str)

    @classmethod
    def from_json(cls, value: str) -> TaskPayload:
        payload = json.loads(value)
        created_at = payload.get("created_at")
        run_at = payload.get("run_at")
        payload["created_at"] = (
            datetime.fromisoformat(created_at) if created_at else datetime.now(UTC)
        )
        payload["run_at"] = datetime.fromisoformat(run_at) if run_at else None
        return cls(**payload)


@dataclass(slots=True)
class TaskResult:
    task_id: str
    task_name: str
    user_id: str | None = None
    status: TaskStatus
    attempts: int
    result: dict[str, Any] | None = None
    error: str | None = None
    finished_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_json(self) -> str:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["finished_at"] = self.finished_at.isoformat()
        return json.dumps(payload, default=str)

    @classmethod
    def from_json(cls, value: str) -> TaskResult:
        payload = json.loads(value)
        payload["status"] = TaskStatus(payload["status"])
        payload["finished_at"] = datetime.fromisoformat(payload["finished_at"])
        return cls(**payload)


class WorkerTask(ABC):
    name: str
    max_retries: int | None = None
    retry_delay_seconds: int | None = None

    @abstractmethod
    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the task and return a JSON-serializable result."""
