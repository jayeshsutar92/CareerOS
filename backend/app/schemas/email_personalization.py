from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class UserProfileContext(BaseModel):
    name: str = Field(default="Applicant")
    current_role: str | None = None
    bio_summary: str | None = None
    skills: list[str] = Field(default_factory=list)


class PortfolioLinkContext(BaseModel):
    title: str
    url: str
    description: str | None = None
    tech_stack: list[str] = Field(default_factory=list)


class CompanyContext(BaseModel):
    company_name: str
    website_url: str | None = None
    overview: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)


class RecipientContext(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None


class EmailPersonalizationRequest(BaseModel):
    template_content: str = Field(
        ...,
        min_length=10,
        description="Raw email template provided by the frontend with structural guidance or placeholders",
    )
    template_name: str | None = Field(default=None, max_length=255)
    user_profile: UserProfileContext | None = None
    portfolio_links: list[PortfolioLinkContext] = Field(default_factory=list)
    resume_link: str | None = None
    company_intelligence: CompanyContext | None = None
    company_intelligence_id: UUID | None = None
    recipient: RecipientContext | None = None
    contact_id: UUID | None = Field(default=None, description="Optional contact ID to auto-resolve recipient details")
    custom_instructions: str | None = Field(default=None, max_length=1000)
    user_id: UUID | None = None
    save_draft: bool = True
    run_in_background: bool = False


class EmailPersonalizationRead(BaseModel):
    id: UUID | None = None
    subject: str
    body: str
    personalized_hooks: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    is_valid: bool = True
    validation_warnings: list[str] = Field(default_factory=list)
    template_name: str | None = None
    status: str = "draft"


class EmailPersonalizationResponse(BaseModel):
    status: str
    task_id: str | None = None
    data: EmailPersonalizationRead | None = None
