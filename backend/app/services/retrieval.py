"""Vector retrieval over the company submission chunks."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
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


def retrieve_relevant_chunks(
    db: Session,
    *,
    company_document_id: uuid.UUID,
    query_embedding: list[float],
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Return the top-k company chunks most similar to ``query_embedding``."""
    k = top_k or settings.retrieval_top_k
    distance = CompanyChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(
            CompanyChunk.id,
            CompanyChunk.ordinal,
            CompanyChunk.text,
            distance.label("distance"),
        )
        .where(CompanyChunk.document_id == company_document_id)
        .order_by(distance)
        .limit(k)
    )
    rows = db.execute(stmt).all()
    return [
        RetrievedChunk(id=row.id, ordinal=row.ordinal, text=row.text, distance=float(row.distance))
        for row in rows
    ]
