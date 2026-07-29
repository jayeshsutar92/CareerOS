from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.models import AIRequest, AIResponse


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse:
        """Run a completion request against the provider."""
