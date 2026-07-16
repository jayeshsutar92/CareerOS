from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.job import (
    JobCreate,
    JobListResponse,
    JobRead,
    JobSortField,
    JobUpdate,
    SortOrder,
)
from app.services.job import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobRead:
    job = await JobService(session).create(payload)
    return JobRead.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    company_id: UUID | None = None,
    status: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    location: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    employment_type: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    has_source_url: bool | None = None,
    posted_from: datetime | None = None,
    posted_to: datetime | None = None,
    sort_by: JobSortField = "created_at",
    sort_order: SortOrder = "desc",
) -> JobListResponse:
    return await JobService(session).list(
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


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobRead:
    job = await JobService(session).get(job_id)
    return JobRead.model_validate(job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: UUID,
    payload: JobUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobRead:
    job = await JobService(session).update(job_id, payload)
    return JobRead.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await JobService(session).delete(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
