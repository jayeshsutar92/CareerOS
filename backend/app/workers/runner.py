from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import get_settings
from app.workers.base import TaskPayload, TaskResult, TaskStatus
from app.workers.queue import (
    dequeue_task,
    move_due_scheduled_tasks,
    schedule_retry,
    send_to_dead_letter,
    store_task_result,
)
from app.workers.registry import TaskRegistry, task_registry

logger = logging.getLogger(__name__)


class WorkerRunner:
    def __init__(self, registry: TaskRegistry | None = None, queue_name: str | None = None) -> None:
        settings = get_settings()
        self.registry = registry or task_registry
        self.queue_name = queue_name or settings.worker_queue_name
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def run_forever(self) -> None:
        settings = get_settings()
        logger.info("Worker started", extra={"queue": self.queue_name})

        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception:
                logger.exception("Worker loop error")
                await asyncio.sleep(settings.worker_poll_interval_seconds)

        logger.info("Worker stopped", extra={"queue": self.queue_name})

    async def run_once(self) -> bool:
        settings = get_settings()
        await move_due_scheduled_tasks(self.queue_name)
        payload = await dequeue_task(self.queue_name, timeout_seconds=1)
        if payload is None:
            await asyncio.sleep(settings.worker_poll_interval_seconds)
            return False

        await self._execute(payload)
        return True

    async def _execute(self, payload: TaskPayload) -> None:
        settings = get_settings()
        task = self.registry.get(payload.name)
        max_retries = payload.max_retries
        if max_retries is None:
            max_retries = (
                task.max_retries if task.max_retries is not None else settings.worker_max_retries
            )
        retry_delay = task.retry_delay_seconds or settings.worker_retry_delay_seconds

        logger.info(
            "Worker task started",
            extra={"task_id": payload.id, "task_name": payload.name, "attempt": payload.attempt},
        )

        try:
            result = await task.run(**payload.args)
        except Exception as exc:
            await self._handle_failure(
                payload, exc, max_retries=max_retries, retry_delay=retry_delay
            )
            return

        await store_task_result(
            TaskResult(
                task_id=payload.id,
                task_name=payload.name,
                status=TaskStatus.SUCCEEDED,
                attempts=payload.attempt + 1,
                result=result,
            )
        )
        logger.info(
            "Worker task succeeded", extra={"task_id": payload.id, "task_name": payload.name}
        )

    async def _handle_failure(
        self,
        payload: TaskPayload,
        exc: Exception,
        *,
        max_retries: int,
        retry_delay: int,
    ) -> None:
        error = str(exc)
        if payload.attempt < max_retries:
            retry_payload = await schedule_retry(
                payload,
                delay_seconds=retry_delay,
                queue_name=self.queue_name,
            )
            await store_task_result(
                TaskResult(
                    task_id=payload.id,
                    task_name=payload.name,
                    status=TaskStatus.RETRYING,
                    attempts=retry_payload.attempt,
                    error=error,
                )
            )
            logger.warning(
                "Worker task scheduled for retry",
                extra={
                    "task_id": payload.id,
                    "task_name": payload.name,
                    "attempt": retry_payload.attempt,
                },
            )
            return

        await send_to_dead_letter(payload, error, queue_name=self.queue_name)
        await store_task_result(
            TaskResult(
                task_id=payload.id,
                task_name=payload.name,
                status=TaskStatus.FAILED,
                attempts=payload.attempt + 1,
                error=error,
            )
        )
        logger.exception(
            "Worker task failed permanently",
            extra={"task_id": payload.id, "task_name": payload.name},
            exc_info=True,
        )


async def run_worker(**kwargs: Any) -> None:
    await WorkerRunner(**kwargs).run_forever()
