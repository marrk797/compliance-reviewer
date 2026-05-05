"""Initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    document_kind = postgresql.ENUM("regulatory", "company", name="document_kind")
    document_kind.create(op.get_bind(), checkfirst=True)
    document_status = postgresql.ENUM(
        "uploaded", "parsed", "processed", "deleted", "failed", name="document_status"
    )
    document_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", document_kind, nullable=False),
        sa.Column(
            "status", document_status, nullable=False, server_default=sa.text("'uploaded'")
        ),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("requirement_id", sa.String(64), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "company_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS company_chunks_embedding_idx "
        "ON company_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    report_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", name="report_status"
    )
    report_status.create(op.get_bind(), checkfirst=True)
    compliance_status = postgresql.ENUM(
        "compliant",
        "non_compliant",
        "partially_compliant",
        "not_found",
        "needs_human_review",
        name="compliance_status",
    )
    compliance_status.create(op.get_bind(), checkfirst=True)
    risk_level = postgresql.ENUM("low", "medium", "high", name="risk_level")
    risk_level.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "regulatory_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "company_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", report_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("summary", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "report_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("requirement_id", sa.String(64), nullable=False),
        sa.Column("requirement_text", sa.Text, nullable=False),
        sa.Column("status", compliance_status, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("risk_level", risk_level, nullable=False, server_default=sa.text("'medium'")),
        sa.Column("explanation", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("suggested_fix", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column(
            "evidence", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )

    audit_event = postgresql.ENUM(
        "user_registered",
        "user_logged_in",
        "document_uploaded",
        "document_deleted",
        "report_created",
        "report_completed",
        "report_failed",
        name="audit_event",
    )
    audit_event.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("event", audit_event, nullable=False, index=True),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("meta", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.execute("DROP TYPE IF EXISTS audit_event")
    op.drop_table("report_findings")
    op.drop_table("reports")
    op.execute("DROP TYPE IF EXISTS risk_level")
    op.execute("DROP TYPE IF EXISTS compliance_status")
    op.execute("DROP TYPE IF EXISTS report_status")
    op.execute("DROP INDEX IF EXISTS company_chunks_embedding_idx")
    op.drop_table("company_chunks")
    op.drop_table("requirements")
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS document_status")
    op.execute("DROP TYPE IF EXISTS document_kind")
    op.drop_table("users")
