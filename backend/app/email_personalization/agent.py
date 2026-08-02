from __future__ import annotations

from typing import Any

from app.agents.base import AgentRequest, BaseAgent
from app.agents.registry import agent_registry
from app.db.session import AsyncSessionLocal
from app.schemas.email_personalization import EmailPersonalizationRequest
from app.services.email_personalization import EmailPersonalizationService


class EmailPersonalizationAgent(BaseAgent):
    name = "email_personalization"
    description = "Generates personalized outreach email subject lines and bodies using candidate and company context."

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        payload = EmailPersonalizationRequest.model_validate(
            {**request.payload, "run_in_background": False}
        )
        async with AsyncSessionLocal() as session:
            result = await EmailPersonalizationService(session).generate(payload)

        return {
            "status": "completed",
            "email_id": str(result.data.id) if result.data and result.data.id else None,
            "subject": result.data.subject if result.data else "",
            "confidence_score": result.data.confidence_score if result.data else 0.0,
            "is_valid": result.data.is_valid if result.data else False,
        }


def register_email_personalization_agent() -> None:
    if "email_personalization" not in agent_registry.names():
        agent_registry.register(EmailPersonalizationAgent())
