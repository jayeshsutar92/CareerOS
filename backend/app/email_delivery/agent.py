from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agents.base import AgentRequest, BaseAgent
from app.agents.registry import agent_registry
from app.db.session import AsyncSessionLocal
from app.core.config import get_settings
from app.email_delivery.providers.mock import MockEmailProvider
from app.email_delivery.providers.smtp import SmtpEmailProvider
from app.models.email import EmailStatus
from app.repositories.email import EmailRepository
from app.services.email_delivery import EmailDeliveryService

logger = logging.getLogger(__name__)


class EmailDeliveryAgent(BaseAgent):
    name = "email_delivery"
    description = "Handles delivery of scheduled emails."

    def __init__(self) -> None:
        super().__init__()
        self.settings = get_settings()
        if self.settings.smtp_host and self.settings.smtp_user:
            self.provider = SmtpEmailProvider()
        else:
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
                email = await repo.get_by_id(email_id)
                if not email:
                    raise ValueError("Email not found")
                
                # Resolve recipient email address
                recipient_email = None
                if email.recruiter_id:
                    from app.repositories.contact import ContactRepository
                    contact_repo = ContactRepository(session)
                    contact = await contact_repo.get_by_id(email.recruiter_id)
                    if contact:
                        for method in contact.contact_methods:
                            if method.get("type") == "email":
                                recipient_email = method.get("value")
                                break
                
                if not recipient_email:
                    # For testing/demo purposes, we could fallback, but here we require it
                    # Just mock it if mock provider
                    if isinstance(self.provider, MockEmailProvider):
                        recipient_email = "test@example.com"
                    else:
                        raise ValueError("Recipient email address not found for this contact")
                
                email.resolved_recipient_email = recipient_email
                
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
