"""Document upload endpoints. Requires an authenticated user."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user
from app.models.audit import AuditEvent
from app.models.document import Document, DocumentKind, DocumentStatus
from app.models.user import User
from app.schemas.document import DocumentOut
from app.services.audit import write_audit
from app.services.storage import UploadValidationError, save_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])

KindLiteral = Literal["regulatory", "company"]


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    kind: KindLiteral = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Document:
    """Upload a regulatory or company document.

    The user must be authenticated and must agree (out of band) not to upload
    personal or confidential data they are not authorized to share. The
    backend enforces extension and size validation; private storage and
    optional post-processing deletion are handled by the pipeline.
    """
    try:
        stored = save_upload(file, user_id=current_user.id)
    except UploadValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    doc = Document(
        id=stored.document_id,
        user_id=current_user.id,
        kind=DocumentKind(kind),
        status=DocumentStatus.UPLOADED,
        original_filename=file.filename or f"upload.{stored.extension}",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=stored.size_bytes,
        storage_path=str(stored.path),
        sha256=stored.sha256,
    )
    db.add(doc)
    write_audit(
        db,
        event=AuditEvent.DOCUMENT_UPLOADED,
        user_id=current_user.id,
        target_type="document",
        target_id=doc.id,
        meta={
            "kind": kind,
            "size_bytes": stored.size_bytes,
            "extension": stored.extension,
            "sha256": stored.sha256,
        },
    )
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Document:
    doc = db.get(Document, document_id)
    if doc is None or doc.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc
