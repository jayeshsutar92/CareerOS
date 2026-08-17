from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.company_intelligence import (
    CompanyIntelligenceListResponse,
    CompanyIntelligenceRead,
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)
from app.services.company_intelligence import CompanyIntelligenceService

router = APIRouter(prefix="/company-intelligence", tags=["company-intelligence"])


@router.post(
    "/analyze",
    response_model=CompanyIntelligenceResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze_company(
    payload: CompanyIntelligenceRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(get_current_user),
) -> CompanyIntelligenceResponse:
    return await CompanyIntelligenceService(session).analyze(payload, user_id=current_user.id)


@router.get("", response_model=CompanyIntelligenceListResponse)
async def list_company_intelligence(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
) -> CompanyIntelligenceListResponse:
    return await CompanyIntelligenceService(session).list(
        page=page, page_size=page_size, search=search
    )


@router.get("/{intelligence_id}", response_model=CompanyIntelligenceRead)
async def get_company_intelligence(
    intelligence_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyIntelligenceRead:
    record = await CompanyIntelligenceService(session).get(intelligence_id)
    return CompanyIntelligenceRead.model_validate(record)


@router.get("/company/{company_id}", response_model=CompanyIntelligenceRead)
async def get_company_intelligence_by_company_id(
    company_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyIntelligenceRead:
    record = await CompanyIntelligenceService(session).get_by_company_id(company_id)
    return CompanyIntelligenceRead.model_validate(record)


@router.post("/{intelligence_id}/refresh", response_model=CompanyIntelligenceResponse)
async def refresh_company_intelligence(
    intelligence_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompanyIntelligenceResponse:
    return await CompanyIntelligenceService(session).refresh(intelligence_id)
