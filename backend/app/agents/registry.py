from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.exceptions import AgentRegistrationError


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> BaseAgent:
        if not agent.name:
            raise AgentRegistrationError("Agent name is required")
        if agent.name in self._agents:
            raise AgentRegistrationError(f"Agent already registered: {agent.name}")
        self._agents[agent.name] = agent
        return agent

    def get(self, name: str) -> BaseAgent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise AgentRegistrationError(f"Agent is not registered: {name}") from exc

    def discover(self) -> list[dict[str, str]]:
        return [
            {"name": agent.name, "description": agent.description}
            for agent in sorted(self._agents.values(), key=lambda item: item.name)
        ]

    def names(self) -> list[str]:
        return sorted(self._agents)

    def clear(self) -> None:
        self._agents.clear()


agent_registry = AgentRegistry()
