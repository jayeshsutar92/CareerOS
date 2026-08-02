"""add company intelligence

Revision ID: 20260802_0004
Revises: 20260802_0003
Create Date: 2026-08-02 00:04:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260802_0004"
down_revision: str | None = "20260802_0003"
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
        "company_intelligence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=2048), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("products_services", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tech_stack", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("careers_url", sa.String(length=2048), nullable=True),
        sa.Column("about_url", sa.String(length=2048), nullable=True),
        sa.Column("contact_info", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("analysis_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_analyzed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_company_intelligence_company_id_companies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_intelligence")),
    )
    op.create_index(
        op.f("ix_company_intelligence_company_id"), "company_intelligence", ["company_id"]
    )
    op.create_index(
        op.f("ix_company_intelligence_company_name"), "company_intelligence", ["company_name"]
    )
    op.create_index(
        op.f("ix_company_intelligence_website_url"), "company_intelligence", ["website_url"]
    )
    op.create_index(
        op.f("ix_company_intelligence_status"), "company_intelligence", ["status"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_company_intelligence_status"), table_name="company_intelligence")
    op.drop_index(op.f("ix_company_intelligence_website_url"), table_name="company_intelligence")
    op.drop_index(op.f("ix_company_intelligence_company_name"), table_name="company_intelligence")
    op.drop_index(op.f("ix_company_intelligence_company_id"), table_name="company_intelligence")
    op.drop_table("company_intelligence")
