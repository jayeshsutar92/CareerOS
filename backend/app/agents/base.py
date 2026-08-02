from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.agents.context import AgentContext
from app.agents.exceptions import AgentValidationError


class AgentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AgentRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    context: AgentContext = Field(default_factory=AgentContext)


class AgentResult(BaseModel):
    agent_name: str
    status: AgentStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class AgentExecutionResult(BaseModel):
    run_id: str
    status: AgentStatus
    results: list[AgentResult] = Field(default_factory=list)
    context: AgentContext
    attempts: int = 1


class BaseAgent(ABC):
    name: str
    description: str = ""
    max_retries: int | None = None

    async def validate(self, request: AgentRequest) -> None:
        if not self.name:
            raise AgentValidationError("Agent name is required")
        if request.payload is None:
            raise AgentValidationError("Agent payload must be an object")

    async def before_run(self, request: AgentRequest) -> None:
        request.context.add_event(self.name, "before_run")

    @abstractmethod
    async def run(self, request: AgentRequest) -> dict[str, Any]:
        """Execute the agent and return a JSON-serializable result."""

    async def after_run(self, request: AgentRequest, result: AgentResult) -> None:
        request.context.add_event(self.name, "after_run", status=result.status.value)

    async def on_error(self, request: AgentRequest, exc: Exception) -> None:
        request.context.add_event(self.name, "error", error=str(exc))

    async def execute(self, request: AgentRequest) -> AgentResult:
        await self.validate(request)
        await self.before_run(request)
        result = AgentResult(agent_name=self.name, status=AgentStatus.RUNNING)

        try:
            result.output = await self.run(request)
            result.status = AgentStatus.SUCCEEDED
            return result
        except Exception as exc:
            result.status = AgentStatus.FAILED
            result.error = str(exc)
            await self.on_error(request, exc)
            raise
        finally:
            result.finished_at = datetime.now(UTC)
            await self.after_run(request, result)
