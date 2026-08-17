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

import logging
logger = logging.getLogger(__name__)

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
    user_id_str = str(current_user.id)
    payload.user_id = user_id_str
    
    from app.core.redis import get_redis_client
    redis = get_redis_client()
    
    # Check for active task
    active_task_key = f"active_discovery:{user_id_str}"
    old_task_id = await redis.get(active_task_key)
    
    if old_task_id:
        old_task_id_str = old_task_id.decode() if isinstance(old_task_id, bytes) else old_task_id
        # Cancel the old task gracefully
        await redis.set(f"task:cancel:{user_id_str}:{old_task_id_str}", "1", ex=3600)
        logger.info("Automatically cancelled previous orphaned discovery task", extra={
            "user_id": user_id_str,
            "cancelled_task_id": old_task_id_str
        })
        
    from uuid import uuid4
    task_id = str(uuid4())
    context = AgentContext(
        run_id=task_id, 
        user_id=user_id_str, 
        metadata={"token_version": current_user.refresh_token_version}
    )
    
    # Register new active task
    await redis.set(active_task_key, task_id, ex=86400)
    logger.info("Registered new active discovery task", extra={
        "user_id": user_id_str,
        "active_task_id": task_id
    })
    
    job = await enqueue_task(
        settings.agent_worker_task_name,
        {
            "agent_name": "lead_discovery",
            "payload": payload.model_dump(),
            "context": context.model_dump(),
        },
        task_id=task_id,
        user_id=user_id_str
    )
    
    return LeadDiscoveryResponse(status="queued", task_id=job.id)
