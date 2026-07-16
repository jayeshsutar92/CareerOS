"""add user authentication fields

Revision ID: 20260716_0002
Revises: 20260714_0001
Create Date: 2026-07-16 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0002"
down_revision: str | None = "20260714_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), server_default="", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("refresh_token_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("users", "hashed_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "refresh_token_version")
    op.drop_column("users", "is_active")
    op.drop_column("users", "hashed_password")
