from datetime import datetime
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.repositories.company import CompanyRepository
from app.repositories.job import JobRepository
from app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobRead,
    JobSortField,
    JobUpdate,
    SortOrder,
)


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = JobRepository(session)
        self.company_repository = CompanyRepository(session)

    async def create(self, payload: JobCreate) -> Job:
        await self._ensure_company_exists(payload.company_id)
        source_url = self._normalize_url(payload.source_url)
        if source_url is not None:
            await self._ensure_unique_source_url(source_url)

        job = Job(
            company_id=payload.company_id,
            title=payload.title,
            location=payload.location,
            employment_type=payload.employment_type,
            source_url=source_url,
            status=payload.status,
            description=payload.description,
            posted_at=payload.posted_at,
        )
        return await self.repository.create(job)

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        company_id: UUID | None,
        status: str | None,
        location: str | None,
        employment_type: str | None,
        has_source_url: bool | None,
        posted_from: datetime | None,
        posted_to: datetime | None,
        sort_by: JobSortField,
        sort_order: SortOrder,
    ) -> JobListResponse:
        if company_id is not None:
            await self._ensure_company_exists(company_id)
        if posted_from is not None and posted_to is not None and posted_from > posted_to:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="posted_from must be before or equal to posted_to",
            )

        jobs, total = await self.repository.list(
            page=page,
            page_size=page_size,
            search=search,
            company_id=company_id,
            status=status,
            location=location,
            employment_type=employment_type,
            has_source_url=has_source_url,
            posted_from=posted_from,
            posted_to=posted_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return JobListResponse(
            items=[JobRead.model_validate(job) for job in jobs],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def get(self, job_id: UUID) -> Job:
        job = await self.repository.get_by_id(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return job

    async def update(self, job_id: UUID, payload: JobUpdate) -> Job:
        job = await self.get(job_id)

        if "company_id" in payload.model_fields_set and payload.company_id is not None:
            if payload.company_id != job.company_id:
                await self._ensure_company_exists(payload.company_id)
                job.company_id = payload.company_id

        if "title" in payload.model_fields_set and payload.title is not None:
            job.title = payload.title
        if "location" in payload.model_fields_set:
            job.location = payload.location
        if "employment_type" in payload.model_fields_set:
            job.employment_type = payload.employment_type
        if "source_url" in payload.model_fields_set:
            source_url = self._normalize_url(payload.source_url)
            if source_url != job.source_url:
                await self._ensure_unique_source_url(source_url)
                job.source_url = source_url
        if "status" in payload.model_fields_set and payload.status is not None:
            job.status = payload.status
        if "description" in payload.model_fields_set:
            job.description = payload.description
        if "posted_at" in payload.model_fields_set:
            job.posted_at = payload.posted_at

        return await self.repository.commit_and_refresh(job)

    async def delete(self, job_id: UUID) -> None:
        job = await self.get(job_id)
        await self.repository.delete(job)

    async def _ensure_company_exists(self, company_id: UUID) -> None:
        company = await self.company_repository.get_by_id(company_id)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    async def _ensure_unique_source_url(self, source_url: str | None) -> None:
        if source_url is None:
            return
        existing_job = await self.repository.get_by_source_url(source_url)
        if existing_job is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A job with this source URL already exists",
            )

    def _normalize_url(self, url: object | None) -> str | None:
        return str(url) if url is not None else None
