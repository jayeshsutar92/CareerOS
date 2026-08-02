from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

ContactRoleCategory = Literal[
    "hr",
    "recruiter",
    "hiring_manager",
    "engineering_manager",
    "other",
]
ContactMethodType = Literal["email", "linkedin", "phone", "website", "source_page"]
ContactSortField = Literal["name", "role", "company_name", "created_at", "updated_at"]
SortOrder = Literal["asc", "desc"]
DiscoveryStatus = Literal["queued", "completed"]


class ContactMethod(BaseModel):
    type: ContactMethodType
    value: str = Field(min_length=1, max_length=2048)


class ContactCandidate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=255)
    company_name: str = Field(min_length=1, max_length=255)
    contact_methods: list[ContactMethod] = Field(default_factory=list)
    source_url: HttpUrl

    @model_validator(mode="after")
    def require_public_method(self) -> "ContactCandidate":
        if not self.contact_methods:
            self.contact_methods.append(
                ContactMethod(type="source_page", value=str(self.source_url))
            )
        return self


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    name: str
    role: str
    role_category: str
    company_name: str
    contact_methods: list[ContactMethod]
    source_url: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ContactListResponse(BaseModel):
    items: list[ContactRead]
    total: int
    page: int
    page_size: int
    pages: int


class ContactDiscoveryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_name: str = Field(min_length=1, max_length=255)
    company_id: UUID | None = None
    source_urls: list[HttpUrl] = Field(min_length=1, max_length=10)
    run_in_background: bool = True


class ContactDiscoveryResponse(BaseModel):
    status: DiscoveryStatus
    task_id: str | None = None
    contacts: list[ContactRead] = Field(default_factory=list)
    discovered: int = 0
    stored: int = 0
