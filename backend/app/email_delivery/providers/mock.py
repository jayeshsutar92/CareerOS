import asyncio
import logging
import uuid
from typing import Any

from app.email_delivery.providers.base import EmailProvider
from app.models.email import Email

logger = logging.getLogger(__name__)


class MockEmailProvider(EmailProvider):
    """
    Mock email provider for development and testing.
    Simulates sending an email by sleeping briefly and logging the output.
    """

    async def send_email(self, email: Email) -> dict[str, Any]:
        logger.info(f"MockProvider: Preparing to send email {email.id}")
        logger.info(f"MockProvider: To user {email.user_id} - Subject: {email.subject}")
        
        # Simulate network latency
        await asyncio.sleep(0.5)
        
        mock_message_id = f"mock-msg-{uuid.uuid4()}"
        logger.info(f"MockProvider: Successfully sent email {email.id}. Msg ID: {mock_message_id}")
        
        return {
            "provider": "mock",
            "message_id": mock_message_id,
            "status": "delivered",
        }
