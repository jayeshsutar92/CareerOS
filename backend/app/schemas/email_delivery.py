from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailScheduleRequest(BaseModel):
    """Request schema for scheduling an email."""
    scheduled_at: datetime | None = Field(
        default=None,
        description="The time the email should be sent. If None or in the past, it will be sent immediately.",
    )


class EmailDeliveryStatusRead(BaseModel):
    """Schema for reading the delivery status of an email."""
    id: UUID
    subject: str
    status: str
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    sent_at: datetime | None = None
    error_message: str | None = None
    task_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmailDeliveryResponse(BaseModel):
    status: str
    data: EmailDeliveryStatusRead | None = None
