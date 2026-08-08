from __future__ import annotations

from app.ai.exceptions import AIConfigurationError
from app.ai.providers.base import AIProvider
from app.ai.providers.langgraph import LangGraphProvider
from app.ai.providers.grok import GrokProvider
from app.core.config import get_settings


def get_ai_provider(provider_name: str | None = None) -> AIProvider:
    settings = get_settings()
    provider = (provider_name or settings.ai_provider).lower()

    if provider == "grok":
        return GrokProvider()
    if provider == "langgraph":
        return LangGraphProvider()

    raise AIConfigurationError(f"Unknown AI provider: {provider}")
