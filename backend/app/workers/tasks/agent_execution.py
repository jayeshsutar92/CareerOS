from __future__ import annotations

from typing import Any

from app.agents.context import AgentContext
from app.agents.coordinator import AgentCoordinator
from app.workers.base import WorkerTask


class AgentExecutionTask(WorkerTask):
    name = "agent_execution"

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        agent_name = kwargs.get("agent_name")
        if not isinstance(agent_name, str) or not agent_name:
            raise ValueError("agent_name is required")

        payload = kwargs.get("payload")
        if payload is not None and not isinstance(payload, dict):
            raise ValueError("payload must be an object")

        context_data = kwargs.get("context")
        context = AgentContext.model_validate(context_data) if context_data else None
        result = await AgentCoordinator().execute(agent_name, payload=payload, context=context)
        return result.model_dump(mode="json")
