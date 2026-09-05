from __future__ import annotations

from app.workers.base import WorkerTask
from app.workers.tasks.agent_execution import AgentExecutionTask
from app.workers.tasks.analysis import CompanyAnalysisTask
from app.workers.tasks.business_sync import BusinessSyncTask
from app.workers.tasks.cleanup import CleanupTask
from app.workers.tasks.bulk_email import BulkEmailWorker


class TaskRegistry:
    def __init__(self) -> None:
        self._tasks: dict[str, WorkerTask] = {}

    def register(self, task: WorkerTask) -> WorkerTask:
        if not task.name:
            raise ValueError("Worker task name is required")
        if task.name in self._tasks:
            raise ValueError(f"Worker task already registered: {task.name}")
        self._tasks[task.name] = task
        return task

    def get(self, name: str) -> WorkerTask:
        try:
            return self._tasks[name]
        except KeyError as exc:
            raise KeyError(f"Worker task is not registered: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._tasks)


task_registry = TaskRegistry()
task_registry.register(AgentExecutionTask())
task_registry.register(CompanyAnalysisTask())
task_registry.register(CleanupTask())
task_registry.register(BusinessSyncTask())
task_registry.register(BulkEmailWorker())
