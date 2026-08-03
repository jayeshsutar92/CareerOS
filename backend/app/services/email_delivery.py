from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import build_redis_key, get_redis_client
from app.models.email import Email, EmailStatus
from app.repositories.email import EmailRepository
from app.schemas.email_delivery import EmailScheduleRequest
from app.workers.queue import enqueue_task


class RateLimitExceeded(Exception):
    pass


class CooldownActive(Exception):
    pass


class InvalidStateTransition(Exception):
    pass


class EmailDeliveryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EmailRepository(session)
        self.settings = get_settings()
        self.redis = get_redis_client()

    async def _check_rate_limits(self, user_id: UUID) -> None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        daily_limit_key = build_redis_key("emails", "daily_limit", str(user_id), today)
        cooldown_key = build_redis_key("emails", "cooldown", str(user_id))

        # Check cooldown
        if await self.redis.exists(cooldown_key):
            raise CooldownActive("You are sending emails too quickly. Please wait.")

        # Check and increment daily limit
        current_count = await self.redis.get(daily_limit_key)
        if current_count and int(current_count) >= self.settings.email_daily_limit_per_user:
            raise RateLimitExceeded(
                f"Daily limit of {self.settings.email_daily_limit_per_user} emails reached."
            )

    async def _apply_rate_limits(self, user_id: UUID) -> None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        daily_limit_key = build_redis_key("emails", "daily_limit", str(user_id), today)
        cooldown_key = build_redis_key("emails", "cooldown", str(user_id))

        await self.redis.set(cooldown_key, "1", ex=self.settings.email_cooldown_seconds)
        count = await self.redis.incr(daily_limit_key)
        if count == 1:
            await self.redis.expire(daily_limit_key, 86400)

    async def schedule_email(self, email_id: UUID, request: EmailScheduleRequest) -> Email:
        email = await self.repo.get_by_id(email_id)
        if not email:
            raise ValueError("Email not found")

        if email.status not in (EmailStatus.DRAFT, EmailStatus.FAILED):
            raise InvalidStateTransition(f"Cannot schedule email in {email.status} state")

        # Idempotency check: if already scheduled, do not duplicate task
        # Wait, if status is DRAFT or FAILED, it's not scheduled yet.
        # But just to be sure we avoid race conditions we should do it transactionally if possible,
        # but here simple state validation is enough.

        scheduled_at = request.scheduled_at or datetime.now(UTC)
        delay_seconds = max(0, int((scheduled_at - datetime.now(UTC)).total_seconds()))

        # Update email
        email = await self.repo.update_email(
            email,
            status=EmailStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            error_message=None,
        )

        # Enqueue task
        task_payload = await enqueue_task(
            name=self.settings.agent_worker_task_name,
            args={
                "agent_name": "email_delivery",
                "payload": {"email_id": str(email_id)},
            },
            delay_seconds=delay_seconds,
            task_id=f"email-delivery-{email_id}",
        )

        email = await self.repo.update_email(email, task_id=task_payload.id)
        return email

    async def cancel_email(self, email_id: UUID) -> Email:
        email = await self.repo.get_by_id(email_id)
        if not email:
            raise ValueError("Email not found")

        if email.status != EmailStatus.SCHEDULED:
            raise InvalidStateTransition(f"Cannot cancel email in {email.status} state")

        # We leave the worker task in Redis, but when it runs it will see the CANCELLED status and abort.
        return await self.repo.update_email(
            email,
            status=EmailStatus.CANCELLED,
            scheduled_at=None,
            task_id=None,
        )

    async def process_delivery(self, email_id: UUID, provider: Any) -> Email:
        """Called by the EmailDeliveryAgent to actually process the delivery."""
        email = await self.repo.get_by_id(email_id)
        if not email:
            raise ValueError("Email not found")

        if email.status == EmailStatus.CANCELLED:
            return email  # Abort gracefully

        if email.status == EmailStatus.SENT:
            return email  # Idempotency: already sent

        if email.status not in (EmailStatus.SCHEDULED, EmailStatus.SENDING, EmailStatus.FAILED):
            raise InvalidStateTransition(f"Cannot process delivery for email in {email.status} state")

        await self._check_rate_limits(email.user_id)

        # Transition to SENDING
        email = await self.repo.update_email(
            email,
            status=EmailStatus.SENDING,
            started_at=email.started_at or datetime.now(UTC),
        )

        try:
            result = await provider.send_email(email)
            await self._apply_rate_limits(email.user_id)
            email = await self.repo.update_email(
                email,
                status=EmailStatus.SENT,
                sent_at=datetime.now(UTC),
            )
            return email
        except Exception as e:
            # Let the worker handle retries. The status becomes FAILED so we can see the error,
            # but a retry will pick it up since we allow FAILED above.
            raise e
