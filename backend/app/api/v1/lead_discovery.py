from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.lead_discovery import LeadDiscoveryRequest
from app.workers.queue import enqueue_task
from app.core.config import get_settings

router = APIRouter(prefix="/lead-discovery", tags=["lead-discovery"])

from app.agents.registry import agent_registry
from app.agents.base import AgentRequest
from app.agents.context import AgentContext

class LeadDiscoveryResponse(BaseModel):
    status: str
    task_id: str | None = None
    error: str | None = None
    contacts_discovered: int | None = None

@router.post("", response_model=LeadDiscoveryResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_lead_discovery(
    payload: LeadDiscoveryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(get_current_user),
) -> LeadDiscoveryResponse:
    settings = get_settings()
    payload.user_id = str(current_user.id)
    
    from uuid import uuid4
    task_id = str(uuid4())
    context = AgentContext(
        run_id=task_id, 
        user_id=str(current_user.id), 
        metadata={"token_version": current_user.refresh_token_version}
    )
    
    job = await enqueue_task(
        settings.agent_worker_task_name,
        {
            "agent_name": "lead_discovery",
            "payload": payload.model_dump(),
            "context": context.model_dump(),
        },
        task_id=task_id
    )
    
    return LeadDiscoveryResponse(status="queued", task_id=job.id)
