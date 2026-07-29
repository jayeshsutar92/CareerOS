from __future__ import annotations

from app.ai.costs import calculate_cost
from app.ai.exceptions import AIProviderError
from app.ai.models import AIRequest, AIResponse, TokenUsage
from app.ai.providers.base import AIProvider
from app.core.config import get_settings


class PydanticAIProvider(AIProvider):
    name = "pydantic_ai"

    async def complete(self, request: AIRequest) -> AIResponse:
        settings = get_settings()
        prompt = "\n".join(f"{message.role}: {message.content}" for message in request.messages)

        try:
            from pydantic_ai import Agent

            agent = Agent(request.model or settings.ai_model)
            result = await agent.run(prompt)
        except Exception as exc:
            raise AIProviderError("PydanticAI request failed") from exc

        usage = self._extract_usage(result)
        return AIResponse(
            content=str(getattr(result, "output", result)),
            provider=self.name,
            model=request.model or settings.ai_model,
            usage=usage,
            cost=calculate_cost(usage),
            raw={"result_type": type(result).__name__},
            request_id=request.request_id,
        )

    def _extract_usage(self, result: object) -> TokenUsage:
        usage_getter = getattr(result, "usage", None)
        usage = usage_getter() if callable(usage_getter) else usage_getter
        if usage is None:
            return TokenUsage()

        prompt_tokens = (
            getattr(usage, "request_tokens", None) or getattr(usage, "input_tokens", 0) or 0
        )
        completion_tokens = (
            getattr(usage, "response_tokens", None) or getattr(usage, "output_tokens", 0) or 0
        )
        total_tokens = getattr(usage, "total_tokens", None) or prompt_tokens + completion_tokens
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
