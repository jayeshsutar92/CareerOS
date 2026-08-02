from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company_intelligence import CompanyIntelligence, IntelligenceStatus


class CompanyIntelligenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, intelligence_id: UUID) -> CompanyIntelligence | None:
        result = await self.session.execute(
            select(CompanyIntelligence).where(CompanyIntelligence.id == intelligence_id)
        )
        return result.scalar_one_or_none()

    async def get_by_company_id(self, company_id: UUID) -> CompanyIntelligence | None:
        result = await self.session.execute(
            select(CompanyIntelligence)
            .where(CompanyIntelligence.company_id == company_id)
            .order_by(CompanyIntelligence.created_at.desc())
        )
        return result.scalars().first()

    async def get_by_website_url(self, website_url: str) -> CompanyIntelligence | None:
        result = await self.session.execute(
            select(CompanyIntelligence)
            .where(CompanyIntelligence.website_url == website_url)
            .order_by(CompanyIntelligence.created_at.desc())
        )
        return result.scalars().first()

    async def upsert(
        self,
        *,
        website_url: str,
        company_name: str,
        company_id: UUID | None = None,
        overview: str | None = None,
        products_services: list[str] | None = None,
        tech_stack: list[str] | None = None,
        careers_url: str | None = None,
        about_url: str | None = None,
        contact_info: dict[str, Any] | None = None,
        raw_content: dict[str, Any] | None = None,
        raw_summary: str | None = None,
        status: str = IntelligenceStatus.COMPLETED,
        error: str | None = None,
    ) -> CompanyIntelligence:
        # Search existing record by company_id or website_url
        existing: CompanyIntelligence | None = None
        if company_id:
            existing = await self.get_by_company_id(company_id)
        if not existing:
            existing = await self.get_by_website_url(website_url)

        now = datetime.now(UTC)

        if existing is not None:
            existing.company_name = company_name or existing.company_name
            existing.website_url = website_url
            if company_id:
                existing.company_id = company_id
            existing.overview = overview
            existing.products_services = products_services or []
            existing.tech_stack = tech_stack or []
            existing.careers_url = careers_url
            existing.about_url = about_url
            existing.contact_info = contact_info or {}
            existing.raw_content = raw_content or {}
            existing.raw_summary = raw_summary
            existing.status = status
            existing.error = error
            existing.last_analyzed_at = now
            existing.analysis_version += 1
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        record = CompanyIntelligence(
            company_id=company_id,
            company_name=company_name,
            website_url=website_url,
            overview=overview,
            products_services=products_services or [],
            tech_stack=tech_stack or [],
            careers_url=careers_url,
            about_url=about_url,
            contact_info=contact_info or {},
            raw_content=raw_content or {},
            raw_summary=raw_summary,
            status=status,
            error=error,
            analysis_version=1,
            last_analyzed_at=now,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[CompanyIntelligence], int]:
        stmt = select(CompanyIntelligence)
        count_stmt = select(func.count(CompanyIntelligence.id))

        if search:
            pattern = f"%{search}%"
            filter_cond = (CompanyIntelligence.company_name.ilike(pattern)) | (
                CompanyIntelligence.website_url.ilike(pattern)
            )
            stmt = stmt.where(filter_cond)
            count_stmt = count_stmt.where(filter_cond)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(CompanyIntelligence.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
