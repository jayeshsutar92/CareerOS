import json
import logging
from typing import Any
from uuid import UUID
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.session import AsyncSessionLocal
from app.models.contact import Contact
from app.models.email import Email, EmailStatus
from app.repositories.email import EmailRepository
from app.repositories.template import TemplateRepository
from app.services.email_delivery import EmailDeliveryService
from app.workers.base import WorkerTask
from app.email_delivery.providers.smtp import SmtpEmailProvider
from app.email_delivery.providers.mock import MockEmailProvider
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class BulkEmailWorker(WorkerTask):
    name = "bulk_email"

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        task_id = kwargs.get("task_id")
        user_id_str = kwargs.get("user_id")
        template_id_str = kwargs.get("template_id")
        recipient_ids_str = kwargs.get("recipient_ids", [])

        if not all([task_id, user_id_str, template_id_str, recipient_ids_str]):
            raise ValueError("task_id, user_id, template_id, and recipient_ids are required")

        user_id = UUID(user_id_str)
        template_id = UUID(template_id_str)
        recipient_ids = [UUID(rid) for rid in recipient_ids_str]

        redis = get_redis_client()
        progress_key = f"task:progress:{task_id}"

        settings = get_settings()
        if settings.smtp_host and settings.smtp_user:
            provider = SmtpEmailProvider()
        else:
            provider = MockEmailProvider()

        progress = {
            "total": len(recipient_ids),
            "completed": 0,
            "failed": 0,
            "remaining": len(recipient_ids),
        }

        async def update_progress():
            await redis.set(progress_key, json.dumps(progress), ex=86400)

        await update_progress()

        async with AsyncSessionLocal() as session:
            template_repo = TemplateRepository(session)
            email_repo = EmailRepository(session)
            delivery_service = EmailDeliveryService(session)

            template = await template_repo.get_by_id(template_id)
            if not template:
                raise ValueError("Template not found")

            for rec_id in recipient_ids:
                try:
                    contact_res = await session.execute(
                        select(Contact).where(Contact.id == rec_id, Contact.user_id == user_id)
                    )
                    contact = contact_res.scalar_one_or_none()
                    if not contact:
                        raise ValueError(f"Contact {rec_id} not found")

                    recipient_email = None
                    for method in contact.contact_methods:
                        if method.get("type") == "email":
                            recipient_email = method.get("value")
                            break
                    
                    if not recipient_email and not isinstance(provider, MockEmailProvider):
                        raise ValueError("No email found for contact")
                    elif not recipient_email:
                        recipient_email = "test@example.com"

                    subject = template.subject
                    body = template.body

                    # Simple replacements
                    replacements = {
                        "[Name]": contact.name or "",
                        "[Company]": contact.company_name or "",
                        "[Role]": contact.role or "",
                    }
                    for k, v in replacements.items():
                        subject = subject.replace(k, str(v))
                        body = body.replace(k, str(v))

                    # Create Email
                    email = Email(
                        user_id=user_id,
                        recruiter_id=contact.id, # Map Contact ID to recruiter_id as existing pattern
                        subject=subject,
                        body=body,
                        status=EmailStatus.SCHEDULED,
                        scheduled_at=datetime.now(UTC),
                        task_id=task_id,
                    )
                    session.add(email)
                    await session.commit()
                    await session.refresh(email)

                    # Mark resolved recipient email
                    email.resolved_recipient_email = recipient_email

                    # Process delivery
                    await delivery_service.process_delivery(email.id, provider)

                    progress["completed"] += 1
                except Exception as e:
                    logger.exception(f"Failed to process recipient {rec_id}")
                    progress["failed"] += 1
                finally:
                    progress["remaining"] = progress["total"] - progress["completed"] - progress["failed"]
                    await update_progress()

        return progress
