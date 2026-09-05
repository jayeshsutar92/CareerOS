import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class TemplateBase(BaseModel):
    name: str = Field(..., max_length=255, description="The name of the template")
    subject: str = Field(..., max_length=512, description="The email subject line, can contain placeholders")
    body: str = Field(..., description="The email body content, can contain placeholders")


class TemplateCreate(TemplateBase):
    pass


class TemplateUpdate(TemplateBase):
    pass


class TemplateResponse(TemplateBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
