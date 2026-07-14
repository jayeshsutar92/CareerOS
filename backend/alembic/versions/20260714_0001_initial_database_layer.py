"""initial database layer

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14 00:01:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260714_0001"
down_revision: str | None = None
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
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "companies",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("name", name=op.f("uq_companies_name")),
        sa.UniqueConstraint("website_url", name=op.f("uq_companies_website_url")),
    )
    op.create_index(op.f("ix_companies_name"), "companies", ["name"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="open", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_jobs_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint("source_url", name=op.f("uq_jobs_source_url")),
    )
    op.create_index("ix_jobs_company_id_status", "jobs", ["company_id", "status"], unique=False)
    op.create_index(op.f("ix_jobs_company_id"), "jobs", ["company_id"], unique=False)
    op.create_index(op.f("ix_jobs_title"), "jobs", ["title"], unique=False)

    op.create_table(
        "recruiters",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("linkedin_url", sa.String(length=2048), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_recruiters_company_id_companies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recruiters")),
        sa.UniqueConstraint("company_id", "email", name="uq_recruiters_company_email"),
    )
    op.create_index(op.f("ix_recruiters_company_id"), "recruiters", ["company_id"], unique=False)
    op.create_index(op.f("ix_recruiters_email"), "recruiters", ["email"], unique=False)

    op.create_table(
        "applications",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="tracked", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["job_id"], ["jobs.id"], name=op.f("fk_applications_job_id_jobs"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_applications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )
    op.create_index(
        "ix_applications_user_id_status", "applications", ["user_id", "status"], unique=False
    )
    op.create_index(op.f("ix_applications_job_id"), "applications", ["job_id"], unique=False)
    op.create_index(op.f("ix_applications_user_id"), "applications", ["user_id"], unique=False)

    op.create_table(
        "resumes",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=2048), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_resumes_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resumes")),
    )
    op.create_index(
        "ix_resumes_user_id_is_primary", "resumes", ["user_id", "is_primary"], unique=False
    )
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"], unique=False)

    op.create_table(
        "portfolios",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_portfolios_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolios")),
        sa.UniqueConstraint("user_id", "url", name="uq_portfolios_user_url"),
    )
    op.create_index(op.f("ix_portfolios_user_id"), "portfolios", ["user_id"], unique=False)

    op.create_table(
        "emails",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recruiter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="draft", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_emails_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recruiter_id"],
            ["recruiters.id"],
            name=op.f("fk_emails_recruiter_id_recruiters"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_emails_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emails")),
    )
    op.create_index("ix_emails_user_id_status", "emails", ["user_id", "status"], unique=False)
    op.create_index(op.f("ix_emails_application_id"), "emails", ["application_id"], unique=False)
    op.create_index(op.f("ix_emails_recruiter_id"), "emails", ["recruiter_id"], unique=False)
    op.create_index(op.f("ix_emails_user_id"), "emails", ["user_id"], unique=False)

    op.create_table(
        "agent_logs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_agent_logs_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_agent_logs_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_logs")),
    )
    op.create_index(
        "ix_agent_logs_agent_name_event_type",
        "agent_logs",
        ["agent_name", "event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_logs_application_id"), "agent_logs", ["application_id"], unique=False
    )
    op.create_index(op.f("ix_agent_logs_user_id"), "agent_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_logs_user_id"), table_name="agent_logs")
    op.drop_index(op.f("ix_agent_logs_application_id"), table_name="agent_logs")
    op.drop_index("ix_agent_logs_agent_name_event_type", table_name="agent_logs")
    op.drop_table("agent_logs")
    op.drop_index(op.f("ix_emails_user_id"), table_name="emails")
    op.drop_index(op.f("ix_emails_recruiter_id"), table_name="emails")
    op.drop_index(op.f("ix_emails_application_id"), table_name="emails")
    op.drop_index("ix_emails_user_id_status", table_name="emails")
    op.drop_table("emails")
    op.drop_index(op.f("ix_portfolios_user_id"), table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    op.drop_index("ix_resumes_user_id_is_primary", table_name="resumes")
    op.drop_table("resumes")
    op.drop_index(op.f("ix_applications_user_id"), table_name="applications")
    op.drop_index(op.f("ix_applications_job_id"), table_name="applications")
    op.drop_index("ix_applications_user_id_status", table_name="applications")
    op.drop_table("applications")
    op.drop_index(op.f("ix_recruiters_email"), table_name="recruiters")
    op.drop_index(op.f("ix_recruiters_company_id"), table_name="recruiters")
    op.drop_table("recruiters")
    op.drop_index(op.f("ix_jobs_title"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_company_id"), table_name="jobs")
    op.drop_index("ix_jobs_company_id_status", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index(op.f("ix_companies_name"), table_name="companies")
    op.drop_table("companies")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
