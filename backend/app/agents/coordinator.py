from __future__ import annotations

import asyncio
import logging

from app.agents.base import AgentExecutionResult, AgentRequest, AgentResult, AgentStatus
from app.agents.context import AgentContext
from app.agents.exceptions import AgentExecutionError, AgentValidationError
from app.agents.registry import AgentRegistry, agent_registry
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AgentCoordinator:
    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self.registry = registry or agent_registry

    async def execute(
        self,
        agent_name: str,
        *,
        payload: dict | None = None,
        context: AgentContext | None = None,
        max_retries: int | None = None,
    ) -> AgentExecutionResult:
        agent = self.registry.get(agent_name)
        request = AgentRequest(payload=payload or {}, context=context or AgentContext())
        settings = get_settings()
        retry_limit = max_retries
        if retry_limit is None:
            retry_limit = (
                agent.max_retries if agent.max_retries is not None else settings.agent_max_retries
            )

        last_error: Exception | None = None
        results: list[AgentResult] = []

        for attempt in range(retry_limit + 1):
            log_extra = {
                "agent_name": agent.name,
                "agent_run_id": request.context.run_id,
                "agent_attempt": attempt + 1,
            }
            logger.info("Agent execution started", extra={**log_extra, "agent_status": "running"})

            try:
                result = await agent.execute(request)
            except AgentValidationError:
                logger.exception(
                    "Agent validation failed", extra={**log_extra, "agent_status": "failed"}
                )
                raise
            except Exception as exc:
                last_error = exc
                failed_result = AgentResult(
                    agent_name=agent.name,
                    status=AgentStatus.FAILED,
                    error=str(exc),
                )
                results.append(failed_result)
                if attempt < retry_limit:
                    logger.warning(
                        "Agent execution scheduled for retry",
                        extra={**log_extra, "agent_status": "retrying"},
                    )
                    await asyncio.sleep(settings.agent_retry_delay_seconds)
                    continue

                logger.exception(
                    "Agent execution failed", extra={**log_extra, "agent_status": "failed"}
                )
                raise AgentExecutionError(f"Agent execution failed: {agent.name}") from last_error

            results.append(result)
            logger.info(
                "Agent execution succeeded", extra={**log_extra, "agent_status": "succeeded"}
            )
            return AgentExecutionResult(
                run_id=request.context.run_id,
                status=AgentStatus.SUCCEEDED,
                results=results,
                context=request.context,
                attempts=attempt + 1,
            )

        raise AgentExecutionError(f"Agent execution failed: {agent.name}") from last_error

    async def execute_many(
        self,
        agent_names: list[str],
        *,
        payload: dict | None = None,
        context: AgentContext | None = None,
        stop_on_error: bool = True,
    ) -> AgentExecutionResult:
        shared_context = context or AgentContext()
        results: list[AgentResult] = []

        for agent_name in agent_names:
            try:
                execution = await self.execute(
                    agent_name,
                    payload=payload,
                    context=shared_context,
                )
            except Exception:
                if stop_on_error:
                    raise
                results.append(
                    AgentResult(
                        agent_name=agent_name,
                        status=AgentStatus.FAILED,
                        error="Agent execution failed",
                    )
                )
                continue

            results.extend(execution.results[-1:])
            shared_context.set_state(f"agents.{agent_name}.output", execution.results[-1].output)

        status = AgentStatus.SUCCEEDED
        if any(result.status == AgentStatus.FAILED for result in results):
            status = AgentStatus.FAILED

        return AgentExecutionResult(
            run_id=shared_context.run_id,
            status=status,
            results=results,
            context=shared_context,
        )


async def run_agent(
    agent_name: str,
    *,
    payload: dict | None = None,
    context: AgentContext | None = None,
) -> AgentExecutionResult:
    return await AgentCoordinator().execute(agent_name, payload=payload, context=context)
