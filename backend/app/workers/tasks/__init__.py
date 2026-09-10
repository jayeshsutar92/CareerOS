from app.workers.registry import task_registry
from app.workers.tasks.agent_execution import AgentExecutionTask
from app.workers.tasks.analysis import AnalysisTask
from app.workers.tasks.business_sync import BusinessSyncTask
from app.workers.tasks.cleanup import CleanupTask
from app.workers.tasks.bulk_email import BulkEmailWorker

_TASKS_REGISTERED = False


def register_tasks() -> None:
    global _TASKS_REGISTERED
    if _TASKS_REGISTERED:
        return

    task_registry.register(AgentExecutionTask())
    task_registry.register(BusinessSyncTask())
    task_registry.register(AnalysisTask())
    task_registry.register(CleanupTask())
    task_registry.register(BulkEmailWorker())
    _TASKS_REGISTERED = True
