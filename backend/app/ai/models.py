from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

AIMessageRole = Literal["system", "user", "assistant", "tool"]


class AIMessage(BaseModel):
    role: AIMessageRole
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CostBreakdown(BaseModel):
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    currency: str = "USD"


class AIRequest(BaseModel):
    messages: list[AIMessage]
    model: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(default_factory=lambda: str(uuid4()))


class AIResponse(BaseModel):
    content: str
    provider: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    cost: CostBreakdown = Field(default_factory=CostBreakdown)
    raw: dict[str, Any] = Field(default_factory=dict)
    request_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
