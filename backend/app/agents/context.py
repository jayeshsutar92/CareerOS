from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    agent_name: str
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentContext(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    events: list[AgentEvent] = Field(default_factory=list)

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        self.state[key] = value

    def add_event(self, agent_name: str, event: str, **data: Any) -> None:
        self.events.append(AgentEvent(agent_name=agent_name, event=event, data=data))
