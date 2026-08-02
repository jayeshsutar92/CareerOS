from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_contacts_dedupe_key"),
        Index("ix_contacts_company_role", "company_name", "role_category"),
        Index("ix_contacts_name_role", "name", "role"),
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_methods: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    company = relationship("Company")
