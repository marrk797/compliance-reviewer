"""ORM model package.

Importing this module ensures all SQLAlchemy models are registered with the
declarative metadata used by Alembic.
"""
from __future__ import annotations

from app.models.audit import AuditEvent, AuditLog
from app.models.document import Document, DocumentKind, DocumentStatus
from app.models.report import (
    ComplianceStatus,
    Report,
    ReportFinding,
    ReportStatus,
    RiskLevel,
)
from app.models.requirement import CompanyChunk, Requirement
from app.models.user import User


def register_models() -> None:
    """No-op call to keep linters happy after side-effectful imports."""
    return None


__all__ = [
    "AuditEvent",
    "AuditLog",
    "CompanyChunk",
    "ComplianceStatus",
    "Document",
    "DocumentKind",
    "DocumentStatus",
    "Report",
    "ReportFinding",
    "ReportStatus",
    "Requirement",
    "RiskLevel",
    "User",
    "register_models",
]
