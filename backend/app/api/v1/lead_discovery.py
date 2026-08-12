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

class LeadDiscoveryResponse(BaseModel):
    status: str
    task_id: str | None = None
    error: str | None = None
    contacts_discovered: int | None = None

@router.post("", response_model=LeadDiscoveryResponse, status_code=status.HTTP_200_OK)
async def start_lead_discovery(
    payload: LeadDiscoveryRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: User = Depends(get_current_user),
) -> LeadDiscoveryResponse:
    payload.user_id = str(current_user.id)
    
    agent = agent_registry.get("lead_discovery")
    if not agent:
        return LeadDiscoveryResponse(status="failed", error="Agent not found")
        
    req = AgentRequest(payload=payload.model_dump())
    result = await agent.run(req)
    
    if result.get("status") == "failed":
        # Can return 400 if we want, or just return status="failed"
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    if result.get("contacts_discovered", 0) == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No contacts found on discovered domains")
        
    return LeadDiscoveryResponse(
        status="completed", 
        contacts_discovered=result.get("contacts_discovered", 0)
    )
