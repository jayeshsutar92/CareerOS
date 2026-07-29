from __future__ import annotations

from typing import Any

from app.workers.base import WorkerTask


class CleanupTask(WorkerTask):
    name = "cleanup"

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "skipped",
            "reason": "cleanup worker is registered but not implemented yet",
            "input": kwargs,
        }
