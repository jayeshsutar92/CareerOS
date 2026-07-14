from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.recruiter import Recruiter


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("name", name="uq_companies_name"),
        Index("ix_companies_name", "name", unique=True),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    jobs: Mapped[list[Job]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recruiters: Mapped[list[Recruiter]] = relationship(back_populates="company")
