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
    def __init__(self, session: AsyncSession, user_id: UUID | None = None) -> None:
        self.session = session
        self.user_id = user_id
        self.repository = ContactRepository(session, user_id)

    async def discover(self, payload: ContactDiscoveryRequest) -> ContactDiscoveryResponse:
        if payload.run_in_background:
            settings = get_settings()
            task = await enqueue_task(
                settings.agent_worker_task_name,
                {
                    "agent_name": "contact_discovery",
                    "payload": payload.model_dump(mode="json", exclude={"run_in_background"}),
                    "context": {"user_id": str(self.user_id)} if self.user_id else None,
                },
            )
            return ContactDiscoveryResponse(status="queued", task_id=task.id)

        contacts = await self.discover_now(payload)
        return ContactDiscoveryResponse(
            status="completed",
            contacts=[ContactRead.model_validate(contact) for contact in contacts],
            discovered=len(contacts),
            stored=len(contacts),
        )

    async def discover_now(self, payload: ContactDiscoveryRequest) -> list[Contact]:
        import asyncio
        fetcher = PublicContactFetcher()
        extractor = PublicContactExtractor()
        stored_contacts: list[Contact] = []

        for source_url in payload.source_urls:
            base_url = str(source_url).rstrip('/')
            paths = ["", "/about", "/about-us", "/team", "/careers"]
            
            async def fetch_path(p):
                try:
                    return await fetcher.fetch(base_url + p)
                except Exception:
                    return ""
            
            # Fetch pages concurrently
            htmls = await asyncio.gather(*[fetch_path(p) for p in paths])
            combined_html = "\n".join([h for h in htmls if h])
            
            if not combined_html:
                continue

            candidates = await extractor.extract(
                combined_html,
                source_url=str(source_url),
                company_name=payload.company_name,
            )
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
        return await self.repository.create(contact)

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
