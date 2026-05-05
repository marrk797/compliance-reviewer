"""Vector retrieval over the company-submission chunks via sqlite-vec.

Embeddings are stored in a ``vec0`` virtual table (``company_chunks_vec``)
keyed by the chunk's UUID and partitioned by ``document_id``. We query that
table for top-k nearest neighbours, then load the chunk text/ordinal from the
regular ``company_chunks`` ORM table.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlite_vec
from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.requirement import CompanyChunk


@dataclass(slots=True)
class RetrievedChunk:
    id: uuid.UUID
    ordinal: int
    text: str
    distance: float

    @property
    def similarity(self) -> float:
        # Cosine distance (0 = identical, 2 = opposite). Clamp to [0, 1].
        sim = 1.0 - max(0.0, min(2.0, self.distance)) / 2.0
        return max(0.0, min(1.0, sim))


def upsert_chunk_embedding(
    db: Session,
    *,
    chunk_id: uuid.UUID,
    document_id: uuid.UUID,
    embedding: list[float],
) -> None:
    """Insert or replace a chunk's embedding in the vec0 virtual table."""
    blob = sqlite_vec.serialize_float32(embedding)
    db.execute(
        text(
            "INSERT OR REPLACE INTO company_chunks_vec(chunk_id, document_id, embedding) "
            "VALUES (:chunk_id, :document_id, :embedding)"
        ).bindparams(bindparam("embedding")),
        {"chunk_id": str(chunk_id), "document_id": str(document_id), "embedding": blob},
    )


def delete_document_embeddings(db: Session, *, document_id: uuid.UUID) -> None:
    """Drop all vec rows for a document (called on privacy-mode cleanup)."""
    db.execute(
        text("DELETE FROM company_chunks_vec WHERE document_id = :document_id"),
        {"document_id": str(document_id)},
    )


def retrieve_relevant_chunks(
    db: Session,
    *,
    company_document_id: uuid.UUID,
    query_embedding: list[float],
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Return the top-k company chunks most similar to ``query_embedding``."""
    k = top_k or settings.retrieval_top_k
    blob = sqlite_vec.serialize_float32(query_embedding)
    rows = db.execute(
        text(
            "SELECT chunk_id, distance FROM company_chunks_vec "
            "WHERE document_id = :document_id "
            "AND embedding MATCH :embedding "
            "AND k = :k "
            "ORDER BY distance"
        ).bindparams(bindparam("embedding")),
        {"document_id": str(company_document_id), "embedding": blob, "k": k},
    ).all()
    if not rows:
        return []

    chunk_ids = [uuid.UUID(row.chunk_id) for row in rows]
    distance_by_id = {uuid.UUID(row.chunk_id): float(row.distance) for row in rows}
    stmt = select(CompanyChunk).where(CompanyChunk.id.in_(chunk_ids))
    chunks = {chunk.id: chunk for chunk in db.execute(stmt).scalars().all()}
    return sorted(
        (
            RetrievedChunk(
                id=chunk.id,
                ordinal=chunk.ordinal,
                text=chunk.text,
                distance=distance_by_id[chunk.id],
            )
            for chunk in chunks.values()
        ),
        key=lambda r: r.distance,
    )
