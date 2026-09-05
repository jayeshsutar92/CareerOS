from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from uuid import UUID

from app.api.deps import get_current_user
from app.models.user import User
from app.workers.queue import enqueue_task

router = APIRouter(prefix="/outreach", tags=["outreach"])

class BulkEmailRequest(BaseModel):
    template_id: str
    recipient_ids: List[str]

class BulkEmailResponse(BaseModel):
    task_id: str

@router.post("/send-bulk", response_model=BulkEmailResponse)
async def send_bulk_emails(
    payload: BulkEmailRequest,
    current_user: User = Depends(get_current_user),
) -> BulkEmailResponse:
    import uuid
    task_id = str(uuid.uuid4())
    
    await enqueue_task(
        name="bulk_email",
        args={
            "task_id": task_id,
            "template_id": payload.template_id,
            "recipient_ids": payload.recipient_ids,
            "user_id": str(current_user.id),
        },
        task_id=task_id,
        user_id=str(current_user.id)
    )
    
    return BulkEmailResponse(task_id=task_id)
