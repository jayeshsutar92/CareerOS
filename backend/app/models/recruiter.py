from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.email import Email

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Recruiter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recruiters"
    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_recruiters_company_email"),)

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    company: Mapped[Company | None] = relationship(back_populates="recruiters")
    emails: Mapped[list[Email]] = relationship(back_populates="recruiter")
