from __future__ import annotations

from typing import Any

from app.agents.base import AgentRequest, BaseAgent
from app.agents.registry import agent_registry
from app.db.session import AsyncSessionLocal
from app.schemas.contact import ContactDiscoveryRequest
from app.services.contact import ContactService


class ContactDiscoveryAgent(BaseAgent):
    name = "contact_discovery"
    description = "Discovers public recruiting contacts from supplied public source URLs."

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        payload = ContactDiscoveryRequest.model_validate(
            {**request.payload, "run_in_background": False}
        )
        async with AsyncSessionLocal() as session:
            contacts = await ContactService(session).discover_now(payload)
        return {
            "discovered": len(contacts),
            "stored": len(contacts),
            "contact_ids": [str(contact.id) for contact in contacts],
        }


def register_contact_discovery_agent() -> None:
    if "contact_discovery" not in agent_registry.names():
        agent_registry.register(ContactDiscoveryAgent())
