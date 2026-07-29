from __future__ import annotations

from typing import Any

from app.workers.base import WorkerTask


class AnalysisTask(WorkerTask):
    name = "analysis"

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "skipped",
            "reason": "analysis worker is registered but not implemented yet",
            "input": kwargs,
        }
