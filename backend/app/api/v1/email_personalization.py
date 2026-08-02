from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.email_personalization import (
    EmailPersonalizationRequest,
    EmailPersonalizationResponse,
)
from app.services.email_personalization import EmailPersonalizationService

router = APIRouter(prefix="/email-personalization", tags=["email-personalization"])


@router.post(
    "/generate",
    response_model=EmailPersonalizationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_email(
    payload: EmailPersonalizationRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EmailPersonalizationResponse:
    return await EmailPersonalizationService(session).generate(payload)
