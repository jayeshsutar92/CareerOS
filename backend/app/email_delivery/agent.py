from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agents.base import AgentRequest, BaseAgent
from app.agents.registry import agent_registry
from app.db.session import AsyncSessionLocal
from app.email_delivery.providers.mock import MockEmailProvider
from app.models.email import EmailStatus
from app.repositories.email import EmailRepository
from app.services.email_delivery import EmailDeliveryService

logger = logging.getLogger(__name__)


class EmailDeliveryAgent(BaseAgent):
    name = "email_delivery"
    description = "Handles delivery of scheduled emails."

    def __init__(self) -> None:
        super().__init__()
        # In the future, this can be dynamically loaded or configured based on settings
        self.provider = MockEmailProvider()

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        email_id_str = request.payload.get("email_id")
        if not email_id_str:
            raise ValueError("email_id is required in payload")

        email_id = UUID(email_id_str)

        async with AsyncSessionLocal() as session:
            service = EmailDeliveryService(session)
            repo = EmailRepository(session)
            
            try:
                email = await service.process_delivery(email_id, self.provider)
                return {
                    "status": "completed",
                    "email_id": str(email.id),
                    "delivery_status": email.status,
                }
            except Exception as e:
                # If an error occurs, we must update the error message but STILL raise it
                # so the worker framework knows it failed and can apply retries.
                # However, if it's the last retry, the worker framework handles dead-lettering.
                # We update the DB here to capture the error immediately.
                logger.exception(f"Delivery failed for email {email_id}")
                email = await repo.get_by_id(email_id)
                if email:
                    await repo.update_email(email, error_message=str(e), status=EmailStatus.FAILED)
                raise


def register_email_delivery_agent() -> None:
    if "email_delivery" not in agent_registry.names():
        agent_registry.register(EmailDeliveryAgent())
