import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any
import uuid
import asyncio

from app.core.config import get_settings
from app.email_delivery.providers.base import EmailProvider
from app.models.email import Email

logger = logging.getLogger(__name__)

class SmtpEmailProvider(EmailProvider):
    def __init__(self, recipient_email: str = None):
        self.settings = get_settings()

    async def send_email(self, email: Email) -> dict[str, Any]:
        if not self.settings.smtp_host or not self.settings.smtp_user:
            raise ValueError("SMTP configuration is missing. Cannot send email.")
            
        # The recipient email address should be resolved in the agent and passed to the provider,
        # or we fetch it here. Since the provider signature only takes `email`, we can attach it
        # dynamically in the agent before calling `send_email`.
        recipient = getattr(email, "resolved_recipient_email", None)
        if not recipient:
            raise ValueError("Resolved recipient email is missing from email object")

        msg = EmailMessage()
        msg.set_content(email.body)
        msg['Subject'] = email.subject
        msg['From'] = self.settings.smtp_from_email or self.settings.smtp_user
        msg['To'] = recipient

        # Since smtplib is synchronous, we run it in a thread to not block the asyncio event loop
        def _send():
            context = ssl.create_default_context()
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.settings.smtp_user, self.settings.smtp_password)
                server.send_message(msg)

        logger.info(f"Sending real email {email.id} to {recipient}")
        await asyncio.to_thread(_send)
        
        message_id = f"smtp-msg-{uuid.uuid4()}"
        logger.info(f"Successfully sent email {email.id}. Msg ID: {message_id}")
        
        return {
            "provider": "smtp",
            "message_id": message_id,
            "status": "delivered",
        }
