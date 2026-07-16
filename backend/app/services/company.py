from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.repositories.company import CompanyRepository
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyRead,
    CompanySortField,
    CompanyUpdate,
    SortOrder,
)


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = CompanyRepository(session)

    async def create(self, payload: CompanyCreate) -> Company:
        await self._ensure_unique_name(payload.name)
        website_url = self._normalize_url(payload.website_url)
        if website_url is not None:
            await self._ensure_unique_website_url(website_url)

        company = Company(
            name=payload.name,
            website_url=website_url,
            description=payload.description,
        )
        return await self.repository.create(company)

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        name: str | None,
        has_website: bool | None,
        sort_by: CompanySortField,
        sort_order: SortOrder,
    ) -> CompanyListResponse:
        companies, total = await self.repository.list(
            page=page,
            page_size=page_size,
            search=search,
            name=name,
            has_website=has_website,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return CompanyListResponse(
            items=[CompanyRead.model_validate(company) for company in companies],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def get(self, company_id: UUID) -> Company:
        company = await self.repository.get_by_id(company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return company

    async def update(self, company_id: UUID, payload: CompanyUpdate) -> Company:
        company = await self.get(company_id)

        if "name" in payload.model_fields_set and payload.name is not None:
            if payload.name.lower() != company.name.lower():
                await self._ensure_unique_name(payload.name)
                company.name = payload.name

        if "website_url" in payload.model_fields_set:
            website_url = self._normalize_url(payload.website_url)
            if website_url != company.website_url:
                await self._ensure_unique_website_url(website_url)
                company.website_url = website_url

        if "description" in payload.model_fields_set:
            company.description = payload.description

        return await self.repository.commit_and_refresh(company)

    async def delete(self, company_id: UUID) -> None:
        company = await self.get(company_id)
        await self.repository.delete(company)

    async def _ensure_unique_name(self, name: str) -> None:
        existing_company = await self.repository.get_by_name(name)
        if existing_company is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A company with this name already exists",
            )

    async def _ensure_unique_website_url(self, website_url: str | None) -> None:
        if website_url is None:
            return
        existing_company = await self.repository.get_by_website_url(website_url)
        if existing_company is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A company with this website URL already exists",
            )

    def _normalize_url(self, url: object | None) -> str | None:
        return str(url) if url is not None else None
