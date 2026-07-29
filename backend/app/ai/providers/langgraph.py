from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.ai.costs import calculate_cost
from app.ai.exceptions import AIConfigurationError, AIProviderError
from app.ai.models import AIRequest, AIResponse, TokenUsage
from app.ai.providers.base import AIProvider
from app.core.config import get_settings

LangGraphRunner = Callable[[AIRequest], Awaitable[dict[str, Any]]]


class LangGraphProvider(AIProvider):
    name = "langgraph"

    def __init__(self, runner: LangGraphRunner | None = None) -> None:
        self.runner = runner

    async def complete(self, request: AIRequest) -> AIResponse:
        if self.runner is None:
            raise AIConfigurationError("LangGraph provider requires an injected graph runner")

        settings = get_settings()
        try:
            result = await self.runner(request)
        except Exception as exc:
            raise AIProviderError("LangGraph request failed") from exc

        usage = TokenUsage.model_validate(result.get("usage", {}))
        return AIResponse(
            content=str(result.get("content", "")),
            provider=self.name,
            model=str(result.get("model") or request.model or settings.ai_model),
            usage=usage,
            cost=calculate_cost(usage),
            raw={key: value for key, value in result.items() if key not in {"content", "usage"}},
            request_id=request.request_id,
        )
