from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Any

from app.api.deps import get_current_user
from app.models.user import User
from app.workers.queue import get_task_result
from app.workers.base import TaskResult

router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskStatusResponse(BaseModel):
    status: str
    error: str | None = None
    result: dict[str, Any] | None = None

@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> TaskStatusResponse:
    task_result = await get_task_result(task_id, str(current_user.id))
    
    if not task_result:
        return TaskStatusResponse(status="processing")
        
    return TaskStatusResponse(
        status=task_result.status.value,
        error=task_result.error,
        result=task_result.result,
    )

@router.post("/{task_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    from app.core.redis import get_redis_client
    redis = get_redis_client()
    await redis.set(f"task:cancel:{current_user.id}:{task_id}", "1", ex=3600)
