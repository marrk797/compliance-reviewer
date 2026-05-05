"""Local filesystem storage for uploaded documents.

Files are stored under ``settings.storage_dir`` keyed by user ID and a UUID
per document. We never serve these files to other users; the only consumer
is the in-process compliance pipeline.
"""
from __future__ import annotations

import hashlib
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


class UploadValidationError(ValueError):
    """Raised when an upload fails server-side validation."""


@dataclass(slots=True)
class StoredFile:
    document_id: uuid.UUID
    path: Path
    size_bytes: int
    sha256: str
    extension: str


def validate_extension(filename: str) -> str:
    """Return the lowercase extension if allowed, else raise."""
    if "." not in filename:
        raise UploadValidationError("Filename has no extension")
    ext = filename.rsplit(".", 1)[-1].lower().strip()
    if ext not in settings.allowed_extensions_set:
        raise UploadValidationError(
            f"Extension .{ext} is not allowed. "
            f"Allowed: {sorted(settings.allowed_extensions_set)}"
        )
    return ext


def save_upload(
    upload: UploadFile,
    *,
    user_id: uuid.UUID,
) -> StoredFile:
    """Stream an upload to disk while enforcing size + extension limits."""
    if not upload.filename:
        raise UploadValidationError("Filename is required")
    extension = validate_extension(upload.filename)

    document_id = uuid.uuid4()
    user_dir = settings.storage_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    target = user_dir / f"{document_id}.{extension}"

    hasher = hashlib.sha256()
    size_bytes = 0
    with target.open("wb") as out:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > settings.max_upload_bytes:
                out.close()
                target.unlink(missing_ok=True)
                raise UploadValidationError(
                    f"File exceeds maximum size of {settings.max_upload_bytes} bytes"
                )
            hasher.update(chunk)
            out.write(chunk)
    if size_bytes == 0:
        target.unlink(missing_ok=True)
        raise UploadValidationError("Uploaded file was empty")
    return StoredFile(
        document_id=document_id,
        path=target,
        size_bytes=size_bytes,
        sha256=hasher.hexdigest(),
        extension=extension,
    )


def delete_file(path: str | Path | None) -> None:
    """Best-effort secure-ish deletion of a stored file."""
    if path is None:
        return
    p = Path(path)
    try:
        if p.is_file():
            p.unlink()
    except FileNotFoundError:
        pass


def purge_user_storage(user_id: uuid.UUID) -> None:  # pragma: no cover - admin tool
    user_dir = settings.storage_dir / str(user_id)
    if user_dir.exists():
        shutil.rmtree(user_dir, ignore_errors=True)
