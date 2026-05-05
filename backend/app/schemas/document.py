"""Document upload schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentKind, DocumentStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    kind: DocumentKind
    status: DocumentStatus
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    deleted_at: datetime | None

    class Config:
        from_attributes = True
