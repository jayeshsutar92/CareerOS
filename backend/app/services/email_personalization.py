from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.email_personalization.engine import EmailPersonalizationEngine
from app.models.portfolio import Portfolio
from app.models.resume import Resume
from app.models.user import User
from app.repositories.company_intelligence import CompanyIntelligenceRepository
from app.repositories.email import EmailRepository
from app.schemas.email_personalization import (
    CompanyContext,
    EmailPersonalizationRead,
    EmailPersonalizationRequest,
    EmailPersonalizationResponse,
    PortfolioLinkContext,
    UserProfileContext,
)
from app.workers.queue import enqueue_task

logger = logging.getLogger(__name__)


class EmailPersonalizationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.email_repository = EmailRepository(session)
        self.intel_repository = CompanyIntelligenceRepository(session)
        self.engine = EmailPersonalizationEngine()

    async def generate(self, payload: EmailPersonalizationRequest) -> EmailPersonalizationResponse:
        if payload.run_in_background:
            settings = get_settings()
            task = await enqueue_task(
                settings.agent_worker_task_name,
                {
                    "agent_name": "email_personalization",
                    "payload": payload.model_dump(mode="json", exclude={"run_in_background"}),
                },
            )
            return EmailPersonalizationResponse(status="queued", task_id=task.id)

        result = await self.generate_now(payload)
        return EmailPersonalizationResponse(status="completed", data=result)

    async def generate_now(self, payload: EmailPersonalizationRequest) -> EmailPersonalizationRead:
        # Pipeline Stage 1: Template received (payload.template_content)

        # Pipeline Stage 2: Context Aggregation (Resolve DB context if IDs provided)
        aggregated_payload = await self._aggregate_context(payload)

        # Pipeline Stage 3 & 4: AI Personalization & Validation
        result_read = await self.engine.generate(aggregated_payload)

        # Pipeline Stage 5: Draft Output & Storage (Draft only)
        if aggregated_payload.save_draft and aggregated_payload.user_id:
            try:
                draft_record = await self.email_repository.create_draft(
                    user_id=aggregated_payload.user_id,
                    subject=result_read.subject,
                    body=result_read.body,
                    recruiter_id=aggregated_payload.contact_id,
                )
                result_read.id = draft_record.id
                result_read.status = "draft"
            except Exception as db_exc:
                logger.warning(
                    "Could not persist generated email draft to database",
                    extra={"error": str(db_exc)},
                )

        return result_read

    async def _aggregate_context(
        self, payload: EmailPersonalizationRequest
    ) -> EmailPersonalizationRequest:
        payload_copy = payload.model_copy(deep=True)

        # Auto-resolve Company Intelligence from DB if ID provided
        if payload_copy.company_intelligence_id and not payload_copy.company_intelligence:
            intel = await self.intel_repository.get_by_id(payload_copy.company_intelligence_id)
            if intel:
                payload_copy.company_intelligence = CompanyContext(
                    company_name=intel.company_name,
                    website_url=intel.website_url,
                    overview=intel.overview,
                    tech_stack=intel.tech_stack,
                    key_insights=[intel.raw_summary] if intel.raw_summary else [],
                )

        # Auto-resolve Recipient Context from Contact DB if ID provided
        if payload_copy.contact_id and not payload_copy.recipient:
            from app.models.contact import Contact
            contact_res = await self.session.execute(
                select(Contact).where(Contact.id == payload_copy.contact_id)
            )
            contact = contact_res.scalar_one_or_none()
            if contact:
                from app.schemas.email_personalization import RecipientContext
                # Use the first available email if any
                contact_email = None
                for method in contact.contact_methods:
                    if method.get("type") == "email":
                        contact_email = method.get("value")
                        break
                payload_copy.recipient = RecipientContext(
                    name=contact.name,
                    role=contact.role,
                    email=contact_email,
                )

        # Auto-resolve User Profile & Portfolios from DB if user_id provided
        if payload_copy.user_id:
            if not payload_copy.user_profile:
                user_res = await self.session.execute(
                    select(User).where(User.id == payload_copy.user_id)
                )
                user = user_res.scalar_one_or_none()
                if user:
                    payload_copy.user_profile = UserProfileContext(
                        name=user.full_name or "Applicant",
                    )

            if not payload_copy.portfolio_links:
                port_res = await self.session.execute(
                    select(Portfolio).where(Portfolio.user_id == payload_copy.user_id)
                )
                portfolios = list(port_res.scalars().all())
                payload_copy.portfolio_links = [
                    PortfolioLinkContext(
                        title=p.title,
                        url=p.url,
                        description=p.description,
                    )
                    for p in portfolios
                ]

            if not payload_copy.resume_link:
                resume_res = await self.session.execute(
                    select(Resume)
                    .where(Resume.user_id == payload_copy.user_id, Resume.is_primary == True)  # noqa: E712
                )
                primary_resume = resume_res.scalars().first()
                if primary_resume and primary_resume.file_url:
                    payload_copy.resume_link = primary_resume.file_url

        return payload_copy
