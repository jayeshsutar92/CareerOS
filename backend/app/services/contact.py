from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.contact_discovery.extractor import PublicContactExtractor, PublicContactFetcher
from app.contact_discovery.normalizer import (
    build_dedupe_key,
    classify_role,
    normalize_contact_methods,
    normalize_whitespace,
)
import logging

logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.models.contact import Contact
from app.repositories.contact import ContactRepository
from app.schemas.contact import (
    ContactCandidate,
    ContactDiscoveryRequest,
    ContactDiscoveryResponse,
    ContactListResponse,
    ContactRead,
    ContactSortField,
    SortOrder,
)
from app.workers.queue import enqueue_task


class ContactService:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id
        self.repository = ContactRepository(session, user_id)

    async def discover(self, payload: ContactDiscoveryRequest) -> ContactDiscoveryResponse:
        if payload.run_in_background:
            settings = get_settings()
            from uuid import uuid4
            from sqlalchemy import select
            from app.models.user import User
            
            user = (await self.session.execute(select(User).where(User.id == self.user_id))).scalar_one_or_none()
            token_version = user.refresh_token_version if user else 0
            task_id = str(uuid4())
            
            task = await enqueue_task(
                settings.agent_worker_task_name,
                {
                    "agent_name": "contact_discovery",
                    "payload": payload.model_dump(mode="json", exclude={"run_in_background"}),
                    "context": {
                        "user_id": str(self.user_id),
                        "run_id": task_id,
                        "metadata": {"token_version": token_version}
                    },
                },
                task_id=task_id,
                user_id=str(self.user_id)
            )
            return ContactDiscoveryResponse(status="queued", task_id=task.id)

        contacts = await self.discover_now(payload)
        return ContactDiscoveryResponse(
            status="completed",
            contacts=[ContactRead.model_validate(contact) for contact in contacts],
            discovered=len(contacts),
            stored=len(contacts),
        )

    async def discover_now(self, payload: ContactDiscoveryRequest, run_id: str | None = None, expected_token_version: int | None = None) -> list[Contact]:
        from app.core.redis import get_redis_client
        from sqlalchemy import select
        from app.models.user import User
        from app.contact_discovery.providers import ContactExtractionPipeline
        
        pipeline = ContactExtractionPipeline()
        stored_contacts: list[Contact] = []

        if run_id:
            redis = get_redis_client()
            is_cancelled = await redis.get(f"task:cancel:{self.user_id}:{run_id}")
            if is_cancelled:
                return []
                
        if expected_token_version is not None:
            user_record = (await self.session.execute(select(User).where(User.id == self.user_id))).scalar_one_or_none()
            if not user_record or user_record.refresh_token_version != expected_token_version:
                return []

        candidates = await pipeline.extract_contacts(
            company_name=payload.company_name,
            source_urls=[str(u) for u in payload.source_urls]
        )
        logger.info("Contacts extracted", extra={"action": "contacts_extracted", "count": len(candidates), "company_name": payload.company_name})
        
        for candidate in candidates:
            try:
                stored_contacts.append(await self.upsert_candidate(candidate, payload.company_id))
            except HTTPException:
                # Skip candidates with unsupported roles (like 'other')
                pass

        return stored_contacts

    async def upsert_candidate(
        self,
        candidate: ContactCandidate,
        company_id: UUID | None = None,
    ) -> Contact:
        role_category = classify_role(candidate.role)
        if role_category == "other":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Contact role is not a supported discovery target",
            )

        dedupe_key = build_dedupe_key(candidate)
        existing = await self.repository.get_by_dedupe_key(dedupe_key)
        contact_methods = normalize_contact_methods(candidate.contact_methods)

        if existing is not None:
            existing.contact_methods = contact_methods
            existing.source_url = str(candidate.source_url)
            logger.info("Contacts deduplicated", extra={"action": "contacts_deduplicated", "dedupe_key": dedupe_key})
            return await self.repository.commit_and_refresh(existing)

        contact = Contact(
            company_id=company_id,
            user_id=self.user_id,
            name=normalize_whitespace(candidate.name),
            role=normalize_whitespace(candidate.role),
            role_category=role_category,
            company_name=normalize_whitespace(candidate.company_name),
            contact_methods=contact_methods,
            source_url=str(candidate.source_url),
            dedupe_key=dedupe_key,
        )
        new_contact = await self.repository.create(contact)
        logger.info("Contacts persisted", extra={"action": "contacts_persisted", "contact_id": str(new_contact.id)})
        return new_contact

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        company_name: str | None,
        role_category: str | None,
        sort_by: ContactSortField,
        sort_order: SortOrder,
    ) -> ContactListResponse:
        contacts, total = await self.repository.list(
            page=page,
            page_size=page_size,
            search=search,
            company_name=company_name,
            role_category=role_category,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return ContactListResponse(
            items=[ContactRead.model_validate(contact) for contact in contacts],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def get(self, contact_id: UUID) -> Contact:
        contact = await self.repository.get_by_id(contact_id)
        if contact is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        return contact

    async def delete(self, contact_id: UUID) -> None:
        from sqlalchemy import delete
        from app.models.contact import Contact
        contact = await self.get(contact_id)
        await self.repository.session.execute(
            delete(Contact).where(Contact.id == contact_id, Contact.user_id == self.user_id)
        )
        await self.repository.session.commit()
        logger.info("Contact deleted", extra={"action": "user_deleted_contact", "contact_id": str(contact_id)})
