from __future__ import annotations

from typing import Any

from app.workers.base import WorkerTask


class BusinessSyncTask(WorkerTask):
    name = "business_sync"

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "skipped",
            "reason": "business sync worker is registered but not implemented yet",
            "input": kwargs,
        }
