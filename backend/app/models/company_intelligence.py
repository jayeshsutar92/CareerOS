from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class IntelligenceStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CompanyIntelligence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "company_intelligence"
    __table_args__ = (
        Index("ix_company_intelligence_website_url", "website_url"),
        Index("ix_company_intelligence_company_id", "company_id"),
        Index("ix_company_intelligence_status", "status"),
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    website_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    products_services: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tech_stack: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    careers_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    about_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    contact_info: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=IntelligenceStatus.PENDING, index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company = relationship("Company")
