from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.lead_discovery import LeadDiscoveryRequest
from app.workers.queue import enqueue_task
from app.core.config import get_settings

router = APIRouter(prefix="/lead-discovery", tags=["lead-discovery"])

class LeadDiscoveryResponse(BaseModel):
    status: str
    task_id: str | None = None

@router.post("", response_model=LeadDiscoveryResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_lead_discovery(
    payload: LeadDiscoveryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LeadDiscoveryResponse:
    settings = get_settings()
    job = await enqueue_task(
        settings.agent_worker_task_name,
        {
            "agent_name": "lead_discovery",
            "payload": payload.model_dump(),
        },
    )
    return LeadDiscoveryResponse(status="queued", task_id=job.id)
