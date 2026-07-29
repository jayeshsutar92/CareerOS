from __future__ import annotations

from app.ai.exceptions import AIConfigurationError
from app.ai.providers.base import AIProvider
from app.ai.providers.langgraph import LangGraphProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.pydantic_ai import PydanticAIProvider
from app.core.config import get_settings


def get_ai_provider(provider_name: str | None = None) -> AIProvider:
    settings = get_settings()
    provider = (provider_name or settings.ai_provider).lower()

    if provider == "openai":
        return OpenAIProvider()
    if provider in {"pydantic_ai", "pydanticai"}:
        return PydanticAIProvider()
    if provider == "langgraph":
        return LangGraphProvider()

    raise AIConfigurationError(f"Unsupported AI provider: {provider}")
