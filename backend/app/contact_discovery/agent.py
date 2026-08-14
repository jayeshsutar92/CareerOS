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
        from uuid import UUID
        user_id_str = request.context.user_id if request.context else None
        
        if not user_id_str:
            raise ValueError("user_id is required in agent context for contact discovery")
            
        user_id = UUID(user_id_str)

        payload = ContactDiscoveryRequest.model_validate(
            {**request.payload, "run_in_background": False}
        )
        
        run_id = request.context.run_id if request.context else None
        token_version = request.context.metadata.get("token_version") if request.context else None
        
        async with AsyncSessionLocal() as session:
            contacts = await ContactService(session, user_id=user_id).discover_now(
                payload, 
                run_id=run_id, 
                expected_token_version=token_version
            )
        return {
            "discovered": len(contacts),
            "stored": len(contacts),
            "contact_ids": [str(contact.id) for contact in contacts],
        }


def register_contact_discovery_agent() -> None:
    if "contact_discovery" not in agent_registry.names():
        agent_registry.register(ContactDiscoveryAgent())
