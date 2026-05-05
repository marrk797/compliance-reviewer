"""Helper for writing append-only audit log entries."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent, AuditLog


def write_audit(
    db: Session,
    *,
    event: AuditEvent,
    user_id: uuid.UUID | None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditLog:
    """Insert an audit log row.

    Audit metadata MUST NOT contain document contents or LLM prompts. This
    helper does not validate that beyond accepting the dict; callers are
    responsible for passing only safe metadata (filename, sha256, byte sizes,
    counts, status enum values, etc.).
    """
    entry = AuditLog(
        user_id=user_id,
        event=event,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        meta=meta,
    )
    db.add(entry)
    db.flush()
    return entry
