from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.email_delivery import (
    EmailDeliveryResponse,
    EmailDeliveryStatusRead,
    EmailScheduleRequest,
)
from app.services.email_delivery import (
    CooldownActive,
    EmailDeliveryService,
    InvalidStateTransition,
    RateLimitExceeded,
)

router = APIRouter()


@router.post(
    "/{email_id}/schedule",
    response_model=EmailDeliveryResponse,
    status_code=status.HTTP_200_OK,
)
async def schedule_email(
    email_id: UUID,
    request: EmailScheduleRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Schedule an email for future or immediate delivery."""
    from app.repositories.email import EmailRepository
    repo = EmailRepository(session)
    email = await repo.get_by_id(email_id)
    if not email or email.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    service = EmailDeliveryService(session)
    try:
        email = await service.schedule_email(email_id, request)
        return EmailDeliveryResponse(
            status="success",
            data=EmailDeliveryStatusRead.model_validate(email),
        )
    except (RateLimitExceeded, CooldownActive, InvalidStateTransition, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{email_id}/cancel",
    response_model=EmailDeliveryResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_email(
    email_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Cancel a scheduled email."""
    from app.repositories.email import EmailRepository
    repo = EmailRepository(session)
    email = await repo.get_by_id(email_id)
    if not email or email.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

    service = EmailDeliveryService(session)
    try:
        email = await service.cancel_email(email_id)
        return EmailDeliveryResponse(
            status="success",
            data=EmailDeliveryStatusRead.model_validate(email),
        )
    except (InvalidStateTransition, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{email_id}/delivery-status",
    response_model=EmailDeliveryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_email_delivery_status(
    email_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Get the current delivery status of an email."""
    # We can just fetch it using the repo directly
    from app.repositories.email import EmailRepository
    
    repo = EmailRepository(session)
    email = await repo.get_by_id(email_id)
    if not email or email.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        
    return EmailDeliveryResponse(
        status="success",
        data=EmailDeliveryStatusRead.model_validate(email),
    )


@router.get(
    "/scheduled",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def list_scheduled_emails(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """List all scheduled emails for the current user."""
    from app.models.email import EmailStatus
    from app.repositories.email import EmailRepository
    
    repo = EmailRepository(session)
    emails = await repo.list_by_status(current_user.id, EmailStatus.SCHEDULED)
    
    return {
        "status": "success",
        "data": [EmailDeliveryStatusRead.model_validate(e) for e in emails]
    }
