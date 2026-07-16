from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobSortField, SortOrder


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, job: Job) -> Job:
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID) -> Job | None:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_by_source_url(self, source_url: str) -> Job | None:
        result = await self.session.execute(select(Job).where(Job.source_url == source_url))
        return result.scalar_one_or_none()

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
    ) -> tuple[list[Job], int]:
        statement = self._apply_filters(
            select(Job),
            search=search,
            company_id=company_id,
            status=status,
            location=location,
            employment_type=employment_type,
            has_source_url=has_source_url,
            posted_from=posted_from,
            posted_to=posted_to,
        )
        count_statement = self._apply_filters(
            select(func.count()).select_from(Job),
            search=search,
            company_id=company_id,
            status=status,
            location=location,
            employment_type=employment_type,
            has_source_url=has_source_url,
            posted_from=posted_from,
            posted_to=posted_to,
        )

        sort_column = getattr(Job, sort_by)
        statement = statement.order_by(
            asc(sort_column) if sort_order == "asc" else desc(sort_column)
        )
        statement = statement.offset((page - 1) * page_size).limit(page_size)

        items_result = await self.session.execute(statement)
        count_result = await self.session.execute(count_statement)
        return list(items_result.scalars().all()), count_result.scalar_one()

    async def delete(self, job: Job) -> None:
        await self.session.delete(job)
        await self.session.commit()

    async def commit_and_refresh(self, job: Job) -> Job:
        await self.session.commit()
        await self.session.refresh(job)
        return job

    def _apply_filters(
        self,
        statement: Select,
        *,
        search: str | None,
        company_id: UUID | None,
        status: str | None,
        location: str | None,
        employment_type: str | None,
        has_source_url: bool | None,
        posted_from: datetime | None,
        posted_to: datetime | None,
    ) -> Select:
        if search:
            search_term = f"%{search}%"
            statement = statement.where(
                or_(
                    Job.title.ilike(search_term),
                    Job.description.ilike(search_term),
                    Job.location.ilike(search_term),
                    Job.employment_type.ilike(search_term),
                )
            )
        if company_id is not None:
            statement = statement.where(Job.company_id == company_id)
        if status:
            statement = statement.where(func.lower(Job.status) == status.lower())
        if location:
            statement = statement.where(Job.location.ilike(f"%{location}%"))
        if employment_type:
            statement = statement.where(Job.employment_type.ilike(f"%{employment_type}%"))
        if has_source_url is True:
            statement = statement.where(Job.source_url.is_not(None))
        elif has_source_url is False:
            statement = statement.where(Job.source_url.is_(None))
        if posted_from is not None:
            statement = statement.where(Job.posted_at >= posted_from)
        if posted_to is not None:
            statement = statement.where(Job.posted_at <= posted_to)
        return statement
