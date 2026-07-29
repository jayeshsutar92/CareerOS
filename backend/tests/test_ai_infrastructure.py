from __future__ import annotations

from typing import Any

import pytest
from app.ai.client import AIClient
from app.ai.costs import calculate_cost
from app.ai.exceptions import AIConfigurationError, AIPromptError
from app.ai.models import AIMessage, AIRequest, AIResponse, CostBreakdown, TokenUsage
from app.ai.prompts import PromptRegistry, PromptTemplate
from app.ai.providers.base import AIProvider
from app.ai.providers.factory import get_ai_provider
from app.core.config import get_settings


class FakeProvider(AIProvider):
    name = "fake"

    async def complete(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            content="done",
            provider=self.name,
            model=request.model or "fake-model",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            cost=CostBreakdown(total_cost=0.01),
            request_id=request.request_id,
        )


def reset_settings(monkeypatch: pytest.MonkeyPatch, **env: Any) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    get_settings.cache_clear()


def test_prompt_template_renders_values() -> None:
    template = PromptTemplate(name="greeting", template="Hello {name}")

    assert template.render(name="CareerOS") == "Hello CareerOS"
    assert template.variables == {"name"}


def test_prompt_template_raises_for_missing_values() -> None:
    template = PromptTemplate(name="greeting", template="Hello {name}")

    with pytest.raises(AIPromptError):
        template.render()


def test_prompt_registry_prevents_duplicate_templates() -> None:
    registry = PromptRegistry()
    registry.register(PromptTemplate(name="one", template="First"))

    with pytest.raises(AIPromptError):
        registry.register(PromptTemplate(name="one", template="Duplicate"))


def test_cost_tracking_uses_configured_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings(
        monkeypatch,
        AI_INPUT_TOKEN_COST_PER_1M=2,
        AI_OUTPUT_TOKEN_COST_PER_1M=8,
    )

    cost = calculate_cost(
        TokenUsage(prompt_tokens=1_000, completion_tokens=500, total_tokens=1_500)
    )

    assert cost.input_cost == 0.002
    assert cost.output_cost == 0.004
    assert cost.total_cost == 0.006


def test_provider_factory_uses_configured_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings(monkeypatch, AI_PROVIDER="pydantic_ai")

    provider = get_ai_provider()

    assert provider.name == "pydantic_ai"


def test_provider_factory_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings(monkeypatch, AI_PROVIDER="unknown")

    with pytest.raises(AIConfigurationError):
        get_ai_provider()


@pytest.mark.asyncio
async def test_ai_client_applies_defaults_and_returns_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_settings(
        monkeypatch,
        AI_MODEL="test-model",
        AI_TEMPERATURE=0.4,
        AI_MAX_OUTPUT_TOKENS=128,
    )
    client = AIClient(provider=FakeProvider())
    request = AIRequest(messages=[AIMessage(role="user", content="Hello")])

    response = await client.complete(request)

    assert response.content == "done"
    assert response.provider == "fake"
    assert response.model == "test-model"
    assert request.temperature == 0.4
    assert request.max_output_tokens == 128
    assert response.usage.total_tokens == 15
