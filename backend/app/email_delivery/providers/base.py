from abc import ABC, abstractmethod
from typing import Any

from app.models.email import Email


class EmailProvider(ABC):
    """Base interface for all email delivery providers (Mock, SMTP, SES, etc.)."""

    @abstractmethod
    async def send_email(self, email: Email) -> dict[str, Any]:
        """
        Send the provided email.
        
        Args:
            email: The Email model instance containing subject, body, and recipient information.
            
        Returns:
            A dictionary containing provider-specific delivery metadata (e.g., external message ID).
            
        Raises:
            Exception: If delivery fails. The worker framework will handle retries or dead-lettering.
        """
        pass
