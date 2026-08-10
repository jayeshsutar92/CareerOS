from __future__ import annotations

import httpx

from typing import Any

from app.ai.costs import calculate_cost
from app.ai.exceptions import AIConfigurationError, AIProviderError
from app.ai.models import AIRequest, AIResponse, TokenUsage
from app.ai.providers.base import AIProvider
from app.core.config import get_settings


class GrokProvider(AIProvider):
    name = "grok"

    async def complete(self, request: AIRequest) -> AIResponse:
        settings = get_settings()
        if not settings.grok_api_key:
            raise AIConfigurationError("GROK_API_KEY is required for the Grok provider")

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.grok_api_key}",
            "Content-Type": "application/json"
        }

        messages = [message.model_dump() for message in request.messages]
        
        payload = {
            "model": request.model or settings.ai_model,
            "messages": messages,
            "temperature": request.temperature if request.temperature is not None else settings.ai_temperature,
        }
        if request.max_output_tokens or settings.ai_max_output_tokens:
            payload["max_tokens"] = request.max_output_tokens or settings.ai_max_output_tokens

        try:
            async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise AIProviderError(f"Grok request failed: {exc}") from exc
        except Exception as exc:
            raise AIProviderError("Grok request failed") from exc

        usage = data.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0)
        )

        model = data.get("model", payload["model"])
        content = ""
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            content = choices[0]["message"].get("content", "")

        return AIResponse(
            content=content,
            provider=self.name,
            model=model,
            usage=token_usage,
            cost=calculate_cost(token_usage),
            raw={"id": data.get("id"), "system_fingerprint": data.get("system_fingerprint")},
            request_id=request.request_id,
        )
