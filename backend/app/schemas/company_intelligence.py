from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CompanyIntelligenceRequest(BaseModel):
    website_url: HttpUrl
    company_name: str | None = Field(default=None, max_length=255)
    company_id: UUID | None = None
    run_in_background: bool = False


class CompanyIntelligenceRead(BaseModel):
    id: UUID
    company_id: UUID | None = None
    company_name: str
    website_url: str
    overview: str | None = None
    products_services: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    careers_url: str | None = None
    about_url: str | None = None
    contact_info: dict[str, Any] = Field(default_factory=dict)
    raw_content: dict[str, Any] = Field(default_factory=dict)
    raw_summary: str | None = None
    status: str
    error: str | None = None
    analysis_version: int = 1
    last_analyzed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyIntelligenceResponse(BaseModel):
    status: str
    task_id: str | None = None
    data: CompanyIntelligenceRead | None = None


class CompanyIntelligenceListResponse(BaseModel):
    items: list[CompanyIntelligenceRead]
    total: int
    page: int
    page_size: int
    pages: int
