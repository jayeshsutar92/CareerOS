from __future__ import annotations

from typing import Any

from app.ai.costs import calculate_cost
from app.ai.exceptions import AIConfigurationError, AIProviderError
from app.ai.models import AIRequest, AIResponse, TokenUsage
from app.ai.providers.base import AIProvider
from app.core.config import get_settings


class OpenAIProvider(AIProvider):
    name = "openai"

    async def complete(self, request: AIRequest) -> AIResponse:
        settings = get_settings()
        if not settings.openai_api_key:
            raise AIConfigurationError("OPENAI_API_KEY is required for the OpenAI provider")

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.ai_timeout_seconds,
                max_retries=settings.ai_max_retries,
            )
            response = await client.responses.create(
                model=request.model or settings.ai_model,
                input=[message.model_dump() for message in request.messages],
                temperature=request.temperature
                if request.temperature is not None
                else settings.ai_temperature,
                max_output_tokens=request.max_output_tokens or settings.ai_max_output_tokens,
                metadata=request.metadata or None,
            )
        except AIConfigurationError:
            raise
        except Exception as exc:
            raise AIProviderError("OpenAI request failed") from exc

        usage = self._extract_usage(response)
        model = getattr(response, "model", None) or request.model or settings.ai_model
        return AIResponse(
            content=getattr(response, "output_text", "") or "",
            provider=self.name,
            model=model,
            usage=usage,
            cost=calculate_cost(usage),
            raw=self._response_metadata(response),
            request_id=request.request_id,
        )

    def _extract_usage(self, response: Any) -> TokenUsage:
        usage = getattr(response, "usage", None)
        if usage is None:
            return TokenUsage()

        prompt_tokens = (
            getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", 0) or 0
        )
        completion_tokens = (
            getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", 0) or 0
        )
        total_tokens = getattr(usage, "total_tokens", None) or prompt_tokens + completion_tokens
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def _response_metadata(self, response: Any) -> dict[str, Any]:
        return {
            "id": getattr(response, "id", None),
            "status": getattr(response, "status", None),
        }
