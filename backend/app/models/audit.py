"""Append-only audit log of uploads and report generation events.

Metadata only — never document contents or LLM prompts.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditEvent(str, enum.Enum):
    USER_REGISTERED = "user_registered"
    USER_LOGGED_IN = "user_logged_in"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"
    REPORT_CREATED = "report_created"
    REPORT_COMPLETED = "report_completed"
    REPORT_FAILED = "report_failed"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event: Mapped[AuditEvent] = mapped_column(
        Enum(AuditEvent, name="audit_event"), nullable=False, index=True
    )
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
