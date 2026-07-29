from __future__ import annotations

import logging
from functools import lru_cache

from app.ai.exceptions import AIError, AIProviderError
from app.ai.models import AIRequest, AIResponse
from app.ai.providers.base import AIProvider
from app.ai.providers.factory import get_ai_provider
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider or get_ai_provider()

    async def complete(self, request: AIRequest) -> AIResponse:
        settings = get_settings()
        if request.model is None:
            request.model = settings.ai_model
        if request.temperature is None:
            request.temperature = settings.ai_temperature
        if request.max_output_tokens is None:
            request.max_output_tokens = settings.ai_max_output_tokens

        log_extra = {
            "ai_provider": self.provider.name,
            "ai_model": request.model,
            "ai_request_id": request.request_id,
        }
        if settings.ai_log_prompts:
            log_extra["ai_messages"] = [message.model_dump() for message in request.messages]

        logger.info("AI request started", extra=log_extra)

        try:
            response = await self.provider.complete(request)
        except AIError:
            logger.exception("AI request failed", extra=log_extra)
            raise
        except Exception as exc:
            logger.exception("AI request failed", extra=log_extra)
            raise AIProviderError("AI provider request failed") from exc

        logger.info(
            "AI request completed",
            extra={
                **log_extra,
                "ai_prompt_tokens": response.usage.prompt_tokens,
                "ai_completion_tokens": response.usage.completion_tokens,
                "ai_total_tokens": response.usage.total_tokens,
                "ai_total_cost": response.cost.total_cost,
            },
        )
        return response


@lru_cache
def get_ai_client() -> AIClient:
    return AIClient()
