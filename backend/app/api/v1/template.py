import uuid
from typing import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.template import TemplateResponse
from app.services.template import TemplateService

router = APIRouter()


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db_session),
) -> Sequence[TemplateResponse]:
    """
    Retrieve all templates.
    """
    service = TemplateService(db)
    return await service.list_templates()


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """
    Retrieve a specific template by ID.
    """
    service = TemplateService(db)
    return await service.get_template(template_id)
