from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

JobSortField = Literal["title", "status", "posted_at", "created_at", "updated_at"]
SortOrder = Literal["asc", "desc"]


class JobBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_id: UUID
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = None
    status: str = Field(default="open", min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=20_000)
    posted_at: datetime | None = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = None
    status: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=20_000)
    posted_at: datetime | None = None

    @model_validator(mode="after")
    def validate_patch_payload(self) -> "JobUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        for field_name in ("company_id", "title", "status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    title: str
    location: str | None
    employment_type: str | None
    source_url: str | None
    status: str
    description: str | None
    posted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int
    pages: int
