from __future__ import annotations

from typing import Any

import pytest
from app.agents.base import AgentRequest, AgentStatus, BaseAgent
from app.agents.context import AgentContext
from app.agents.coordinator import AgentCoordinator
from app.agents.exceptions import AgentExecutionError, AgentRegistrationError
from app.agents.registry import AgentRegistry, agent_registry
from app.core.config import get_settings
from app.workers.tasks.agent_execution import AgentExecutionTask


class EchoAgent(BaseAgent):
    name = "echo"
    description = "Echoes payload into shared state."

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        request.context.set_state("echo.payload", request.payload)
        return {"payload": request.payload}


class StateReaderAgent(BaseAgent):
    name = "state_reader"

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        return {"seen": request.context.get_state("echo.payload")}


class FlakyAgent(BaseAgent):
    name = "flaky"
    max_retries = 1

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary failure")
        return {"calls": self.calls}


class FailingAgent(BaseAgent):
    name = "failing"
    max_retries = 0

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        raise RuntimeError("permanent failure")


def reset_settings(monkeypatch: pytest.MonkeyPatch, **env: Any) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    get_settings.cache_clear()


def test_agent_registry_registers_and_discovers_agents() -> None:
    registry = AgentRegistry()
    registry.register(EchoAgent())

    assert registry.names() == ["echo"]
    assert registry.discover() == [
        {"name": "echo", "description": "Echoes payload into shared state."}
    ]


def test_agent_registry_rejects_duplicate_names() -> None:
    registry = AgentRegistry()
    registry.register(EchoAgent())

    with pytest.raises(AgentRegistrationError):
        registry.register(EchoAgent())


@pytest.mark.asyncio
async def test_coordinator_executes_agent_lifecycle() -> None:
    registry = AgentRegistry()
    registry.register(EchoAgent())
    context = AgentContext()

    result = await AgentCoordinator(registry).execute(
        "echo",
        payload={"value": 1},
        context=context,
    )

    assert result.status == AgentStatus.SUCCEEDED
    assert result.results[0].output == {"payload": {"value": 1}}
    assert result.context.get_state("echo.payload") == {"value": 1}
    assert [event.event for event in result.context.events] == ["before_run", "after_run"]


@pytest.mark.asyncio
async def test_coordinator_shares_context_between_agents() -> None:
    registry = AgentRegistry()
    registry.register(EchoAgent())
    registry.register(StateReaderAgent())

    result = await AgentCoordinator(registry).execute_many(
        ["echo", "state_reader"],
        payload={"value": 1},
    )

    assert result.status == AgentStatus.SUCCEEDED
    assert result.results[1].output == {"seen": {"value": 1}}
    assert result.context.get_state("agents.echo.output") == {"payload": {"value": 1}}


@pytest.mark.asyncio
async def test_coordinator_retries_agent_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings(monkeypatch, AGENT_RETRY_DELAY_SECONDS=0)
    registry = AgentRegistry()
    flaky = FlakyAgent()
    registry.register(flaky)

    result = await AgentCoordinator(registry).execute("flaky")

    assert result.status == AgentStatus.SUCCEEDED
    assert result.attempts == 2
    assert flaky.calls == 2
    assert result.results[0].status == AgentStatus.FAILED
    assert result.results[1].status == AgentStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_coordinator_raises_after_retry_exhaustion(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings(monkeypatch, AGENT_RETRY_DELAY_SECONDS=0)
    registry = AgentRegistry()
    registry.register(FailingAgent())

    with pytest.raises(AgentExecutionError):
        await AgentCoordinator(registry).execute("failing")


@pytest.mark.asyncio
async def test_agent_execution_worker_runs_registered_agent() -> None:
    agent_registry.clear()
    agent_registry.register(EchoAgent())

    try:
        result = await AgentExecutionTask().run(
            agent_name="echo",
            payload={"value": 1},
            context=AgentContext().model_dump(mode="json"),
        )
    finally:
        agent_registry.clear()

    assert result["status"] == "succeeded"
    assert result["results"][0]["output"] == {"payload": {"value": 1}}
