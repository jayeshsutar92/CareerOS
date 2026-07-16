from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

CompanySortField = Literal["name", "created_at", "updated_at"]
SortOrder = Literal["asc", "desc"]


class CompanyBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    website_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=10_000)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    website_url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def validate_patch_payload(self) -> "CompanyUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Company name cannot be null")
        return self


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    website_url: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class CompanyListResponse(BaseModel):
    items: list[CompanyRead]
    total: int
    page: int
    page_size: int
    pages: int
