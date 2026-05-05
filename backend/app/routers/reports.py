"""Compliance report endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.deps import get_current_user
from app.models.report import Report
from app.models.user import User
from app.schemas.report import CreateReportRequest, ReportOut, ReportSummary
from app.services.pipeline import run_compliance_pipeline

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: CreateReportRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReportOut:
    """Run the compliance pipeline synchronously and return the structured report."""
    report = run_compliance_pipeline(
        db,
        user_id=current_user.id,
        regulatory_document_id=payload.regulatory_document_id,
        company_document_id=payload.company_document_id,
    )
    return _to_out(report)


@router.get("", response_model=list[ReportOut])
def list_reports(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ReportOut]:
    reports = db.scalars(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
    ).all()
    return [_to_out(r) for r in reports]


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReportOut:
    report = db.get(Report, report_id)
    if report is None or report.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _to_out(report)


def _to_out(report: Report) -> ReportOut:
    summary = report.summary or {}
    summary_model = (
        ReportSummary(
            total_requirements=summary.get("total_requirements", len(report.findings)),
            compliant=summary.get("compliant", 0),
            non_compliant=summary.get("non_compliant", 0),
            partially_compliant=summary.get("partially_compliant", 0),
            not_found=summary.get("not_found", 0),
            needs_human_review=summary.get("needs_human_review", 0),
        )
        if summary
        else None
    )
    return ReportOut.model_validate(
        {
            "id": report.id,
            "status": report.status,
            "regulatory_document_id": report.regulatory_document_id,
            "company_document_id": report.company_document_id,
            "summary": summary_model,
            "error_message": report.error_message,
            "created_at": report.created_at,
            "completed_at": report.completed_at,
            "findings": [
                {
                    "ordinal": f.ordinal,
                    "requirement_id": f.requirement_id,
                    "requirement_text": f.requirement_text,
                    "status": f.status,
                    "confidence": f.confidence,
                    "risk_level": f.risk_level,
                    "explanation": f.explanation,
                    "suggested_fix": f.suggested_fix,
                    "evidence": f.evidence or [],
                }
                for f in report.findings
            ],
        }
    )
