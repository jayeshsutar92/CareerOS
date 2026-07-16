from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyRead,
    CompanySortField,
    CompanyUpdate,
    SortOrder,
)
from app.services.company import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyRead:
    company = await CompanyService(session).create(payload)
    return CompanyRead.model_validate(company)


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    name: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    has_website: bool | None = None,
    sort_by: CompanySortField = "created_at",
    sort_order: SortOrder = "desc",
) -> CompanyListResponse:
    return await CompanyService(session).list(
        page=page,
        page_size=page_size,
        search=search,
        name=name,
        has_website=has_website,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyRead:
    company = await CompanyService(session).get(company_id)
    return CompanyRead.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyRead:
    company = await CompanyService(session).update(company_id, payload)
    return CompanyRead.model_validate(company)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    await CompanyService(session).delete(company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
