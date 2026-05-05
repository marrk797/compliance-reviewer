"""Top-level compliance pipeline: ingest → extract → embed → retrieve → evaluate.

This orchestrator is deliberately synchronous and single-process for the MVP.
For production use it would move behind a queue (Celery/RQ/Arq) so long
documents don't block API workers.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.llm import get_embedding_provider, get_llm_provider
from app.models.audit import AuditEvent
from app.models.document import Document, DocumentKind, DocumentStatus
from app.models.report import (
    ComplianceStatus,
    Report,
    ReportFinding,
    ReportStatus,
)
from app.models.requirement import CompanyChunk, Requirement
from app.services.audit import write_audit
from app.services.chunking import chunk_text
from app.services.compliance import ExcerptForEval, evaluate_requirement
from app.services.parsing import ParsingError, extract_text
from app.services.requirements import extract_requirements
from app.services.retrieval import (
    delete_document_embeddings,
    retrieve_relevant_chunks,
    upsert_chunk_embedding,
)
from app.services.storage import delete_file

logger = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    pass


def run_compliance_pipeline(
    db: Session,
    *,
    user_id: uuid.UUID,
    regulatory_document_id: uuid.UUID,
    company_document_id: uuid.UUID,
) -> Report:
    """Execute the full pipeline and persist a structured Report.

    On success the report is committed and returned. On failure the report is
    saved with status ``failed`` and a sanitized error message; the original
    files are still deleted if the privacy flag is on, to minimise residual
    risk after a bad run.
    """
    report = Report(
        user_id=user_id,
        regulatory_document_id=regulatory_document_id,
        company_document_id=company_document_id,
        status=ReportStatus.RUNNING,
    )
    db.add(report)
    db.flush()
    write_audit(
        db,
        event=AuditEvent.REPORT_CREATED,
        user_id=user_id,
        target_type="report",
        target_id=report.id,
        meta={
            "regulatory_document_id": str(regulatory_document_id),
            "company_document_id": str(company_document_id),
        },
    )
    db.commit()
    db.refresh(report)

    try:
        regulatory = _load_document(db, user_id, regulatory_document_id, DocumentKind.REGULATORY)
        company = _load_document(db, user_id, company_document_id, DocumentKind.COMPANY)
        regulatory_text = _safe_extract(regulatory)
        company_text = _safe_extract(company)

        requirements = _persist_requirements(db, regulatory.id, regulatory_text)
        if not requirements:
            raise PipelineError("No requirements could be extracted from the regulatory document.")
        chunks = _persist_company_chunks(db, company.id, company_text)
        if not chunks:
            raise PipelineError("Company document produced no usable chunks.")

        embeddings = get_embedding_provider()
        requirement_vectors = _embed_requirements(requirements, embeddings)
        _embed_and_index_chunks(db, company.id, chunks, embeddings)
        db.commit()

        llm = get_llm_provider()
        _evaluate_all(db, report, requirements, requirement_vectors, company.id, llm)

        report.status = ReportStatus.COMPLETED
        report.completed_at = datetime.now(UTC)
        report.summary = _compute_summary(report)
        write_audit(
            db,
            event=AuditEvent.REPORT_COMPLETED,
            user_id=user_id,
            target_type="report",
            target_id=report.id,
            meta={"summary": report.summary},
        )
        db.commit()
        db.refresh(report)
    except Exception as exc:
        db.rollback()
        report = db.get(Report, report.id) or report
        report.status = ReportStatus.FAILED
        # Sanitized: do not echo document contents through the error path.
        report.error_message = _sanitize_error(exc)
        write_audit(
            db,
            event=AuditEvent.REPORT_FAILED,
            user_id=user_id,
            target_type="report",
            target_id=report.id,
            meta={"error_kind": type(exc).__name__},
        )
        db.commit()
        logger.exception("Compliance pipeline failed for report %s", report.id)
    finally:
        if settings.delete_source_files_after_processing:
            _delete_sources(db, regulatory_document_id, company_document_id, user_id)
    return report


def _load_document(
    db: Session, user_id: uuid.UUID, document_id: uuid.UUID, expected: DocumentKind
) -> Document:
    doc = db.get(Document, document_id)
    if doc is None or doc.user_id != user_id:
        raise PipelineError("Document not found or not owned by user.")
    if doc.kind != expected:
        raise PipelineError(f"Expected a {expected.value} document, got {doc.kind.value}.")
    if doc.storage_path is None or not Path(doc.storage_path).exists():
        raise PipelineError(f"Document {expected.value} file is no longer available on disk.")
    return doc


def _safe_extract(doc: Document) -> str:
    assert doc.storage_path is not None
    try:
        return extract_text(Path(doc.storage_path), doc.original_filename.rsplit(".", 1)[-1])
    except ParsingError as exc:
        raise PipelineError(f"Could not parse {doc.kind.value} document: {exc}") from exc


def _persist_requirements(
    db: Session, document_id: uuid.UUID, text: str
) -> list[Requirement]:
    extracted = extract_requirements(text)
    rows: list[Requirement] = []
    for ordinal, item in enumerate(extracted):
        row = Requirement(
            document_id=document_id,
            ordinal=ordinal,
            requirement_id=item.requirement_id,
            text=item.text,
            section=item.section,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _persist_company_chunks(
    db: Session, document_id: uuid.UUID, text: str
) -> list[CompanyChunk]:
    rows: list[CompanyChunk] = []
    for chunk in chunk_text(text):
        row = CompanyChunk(
            document_id=document_id,
            ordinal=chunk.ordinal,
            text=chunk.text,
            token_count=chunk.token_count,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def _embed_requirements(items: list[Requirement], embeddings) -> dict[uuid.UUID, list[float]]:
    """Embed requirement texts and return them keyed by requirement.id.

    We do *not* persist requirement embeddings; they are used only for
    retrieval during this pipeline run and are discarded afterwards.
    """
    if not items:
        return {}
    vectors = embeddings.embed([item.text for item in items])
    return dict(zip([item.id for item in items], vectors, strict=True))


def _embed_and_index_chunks(
    db: Session,
    company_document_id: uuid.UUID,
    chunks: list[CompanyChunk],
    embeddings,
) -> None:
    if not chunks:
        return
    vectors = embeddings.embed([c.text for c in chunks])
    for chunk, vec in zip(chunks, vectors, strict=True):
        upsert_chunk_embedding(
            db,
            chunk_id=chunk.id,
            document_id=company_document_id,
            embedding=vec,
        )


def _evaluate_all(
    db: Session,
    report: Report,
    requirements: list[Requirement],
    requirement_vectors: dict[uuid.UUID, list[float]],
    company_document_id: uuid.UUID,
    llm,
) -> None:
    for ordinal, req in enumerate(requirements):
        query_vec = requirement_vectors[req.id]
        retrieved = retrieve_relevant_chunks(
            db,
            company_document_id=company_document_id,
            query_embedding=query_vec,
        )
        excerpts = [
            ExcerptForEval(ordinal=r.ordinal, text=r.text, similarity=r.similarity)
            for r in retrieved
        ]
        finding = evaluate_requirement(
            llm=llm,
            requirement_id=req.requirement_id,
            requirement_text=req.text,
            excerpts=excerpts,
        )
        db.add(
            ReportFinding(
                report_id=report.id,
                ordinal=ordinal,
                requirement_id=req.requirement_id,
                requirement_text=req.text,
                status=finding.status,
                confidence=finding.confidence,
                risk_level=finding.risk_level,
                explanation=finding.explanation,
                suggested_fix=finding.suggested_fix,
                evidence=finding.evidence,
            )
        )
    db.flush()


def _compute_summary(report: Report) -> dict:
    counts = {s.value: 0 for s in ComplianceStatus}
    for finding in report.findings:
        counts[finding.status.value] += 1
    counts["total_requirements"] = len(report.findings)
    return counts


def _sanitize_error(exc: BaseException) -> str:
    """Produce a short error string that cannot leak document content."""
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
    if len(message) > 240:
        message = message[:240] + "..."
    return message


def _delete_sources(
    db: Session,
    regulatory_document_id: uuid.UUID,
    company_document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    for doc_id in (regulatory_document_id, company_document_id):
        doc = db.get(Document, doc_id)
        if doc is None:
            continue
        delete_file(doc.storage_path)
        doc.storage_path = None
        doc.status = DocumentStatus.DELETED
        doc.deleted_at = datetime.now(UTC)
        write_audit(
            db,
            event=AuditEvent.DOCUMENT_DELETED,
            user_id=user_id,
            target_type="document",
            target_id=doc.id,
            meta={"reason": "post_report_privacy"},
        )
    # Also wipe the chunks / requirements / vec embeddings linked to these
    # documents to comply with "store only the final structured report".
    delete_document_embeddings(db, document_id=company_document_id)
    db.execute(
        Requirement.__table__.delete().where(
            Requirement.document_id.in_([regulatory_document_id, company_document_id])
        )
    )
    db.execute(
        CompanyChunk.__table__.delete().where(
            CompanyChunk.document_id.in_([regulatory_document_id, company_document_id])
        )
    )
    db.commit()
