"""add contacts

Revision ID: 20260802_0003
Revises: 20260716_0002
Create Date: 2026-08-02 00:03:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260802_0003"
down_revision: str | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("role_category", sa.String(length=100), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("contact_methods", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("dedupe_key", sa.String(length=512), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_contacts_company_id_companies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contacts")),
        sa.UniqueConstraint("dedupe_key", name="uq_contacts_dedupe_key"),
    )
    op.create_index("ix_contacts_company_role", "contacts", ["company_name", "role_category"])
    op.create_index("ix_contacts_name_role", "contacts", ["name", "role"])
    op.create_index(op.f("ix_contacts_company_id"), "contacts", ["company_id"])
    op.create_index(op.f("ix_contacts_company_name"), "contacts", ["company_name"])
    op.create_index(op.f("ix_contacts_dedupe_key"), "contacts", ["dedupe_key"], unique=True)
    op.create_index(op.f("ix_contacts_name"), "contacts", ["name"])
    op.create_index(op.f("ix_contacts_role"), "contacts", ["role"])
    op.create_index(op.f("ix_contacts_role_category"), "contacts", ["role_category"])


def downgrade() -> None:
    op.drop_index(op.f("ix_contacts_role_category"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_role"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_name"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_dedupe_key"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_company_name"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_company_id"), table_name="contacts")
    op.drop_index("ix_contacts_name_role", table_name="contacts")
    op.drop_index("ix_contacts_company_role", table_name="contacts")
    op.drop_table("contacts")
