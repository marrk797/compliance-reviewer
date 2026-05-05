"""Report schemas (input + output)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.report import ComplianceStatus, ReportStatus, RiskLevel


class CreateReportRequest(BaseModel):
    regulatory_document_id: uuid.UUID
    company_document_id: uuid.UUID


class EvidenceItem(BaseModel):
    chunk_ordinal: int | None = None
    quote: str
    score: float | None = None


class FindingOut(BaseModel):
    ordinal: int
    requirement_id: str
    requirement_text: str
    status: ComplianceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    explanation: str
    suggested_fix: str
    evidence: list[EvidenceItem]

    class Config:
        from_attributes = True


class ReportSummary(BaseModel):
    total_requirements: int
    compliant: int
    non_compliant: int
    partially_compliant: int
    not_found: int
    needs_human_review: int


class ReportOut(BaseModel):
    id: uuid.UUID
    status: ReportStatus
    regulatory_document_id: uuid.UUID | None
    company_document_id: uuid.UUID | None
    summary: ReportSummary | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None
    findings: list[FindingOut] = []

    class Config:
        from_attributes = True
