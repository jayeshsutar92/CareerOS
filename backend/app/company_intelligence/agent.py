from __future__ import annotations

from typing import Any

from app.agents.base import AgentRequest, BaseAgent
from app.agents.registry import agent_registry
from app.db.session import AsyncSessionLocal
from app.schemas.company_intelligence import CompanyIntelligenceRequest
from app.services.company_intelligence import CompanyIntelligenceService


class CompanyIntelligenceAgent(BaseAgent):
    name = "company_intelligence"
    description = "Analyzes company websites, extracts structured content, tech stack, and generates AI intelligence summaries."

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        payload = CompanyIntelligenceRequest.model_validate(
            {**request.payload, "run_in_background": False}
        )
        async with AsyncSessionLocal() as session:
            intelligence = await CompanyIntelligenceService(session).analyze_now(payload)
        return {
            "status": intelligence.status,
            "intelligence_id": str(intelligence.id),
            "company_name": intelligence.company_name,
            "website_url": intelligence.website_url,
            "tech_stack": intelligence.tech_stack,
        }


def register_company_intelligence_agent() -> None:
    if "company_intelligence" not in agent_registry.names():
        agent_registry.register(CompanyIntelligenceAgent())
