"""LLM-based compliance evaluation for a single requirement."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.llm.base import LLMProvider
from app.models.report import ComplianceStatus, RiskLevel

_VALID_STATUSES = {s.value for s in ComplianceStatus}
_VALID_RISKS = {r.value for r in RiskLevel}

SYSTEM_PROMPT = """You are an assistant helping a human compliance reviewer.

You are given a single regulatory requirement and a small set of excerpts from \
a company submission document. Your job is to assess whether the company \
document satisfies the requirement, citing only the provided excerpts.

Important rules:
- You are NOT a lawyer and you do NOT provide legal advice.
- Your output assists a human reviewer; the human makes the final decision.
- Only cite text that is actually present in the provided excerpts.
- If the excerpts do not contain relevant information, return status \
"not_found" rather than guessing.
- If the answer requires legal interpretation, jurisdictional knowledge, or \
information clearly outside the excerpts, return "needs_human_review".
"""

SCHEMA_HINT: dict[str, Any] = {
    "status": "compliant|non_compliant|partially_compliant|not_found|needs_human_review",
    "confidence": "number between 0 and 1",
    "risk_level": "low|medium|high",
    "explanation": "string, 1-3 sentences",
    "suggested_fix": "string, may be empty if status is compliant",
    "evidence": [
        {"chunk_ordinal": "integer", "quote": "string, exact substring of an excerpt"}
    ],
}


@dataclass(slots=True)
class ExcerptForEval:
    ordinal: int
    text: str
    similarity: float


@dataclass(slots=True)
class ComplianceFinding:
    status: ComplianceStatus
    confidence: float
    risk_level: RiskLevel
    explanation: str
    suggested_fix: str
    evidence: list[dict[str, Any]]


def evaluate_requirement(
    *,
    llm: LLMProvider,
    requirement_id: str,
    requirement_text: str,
    excerpts: list[ExcerptForEval],
) -> ComplianceFinding:
    """Evaluate a single requirement against retrieved company excerpts."""
    if not excerpts:
        return ComplianceFinding(
            status=ComplianceStatus.NOT_FOUND,
            confidence=0.0,
            risk_level=RiskLevel.MEDIUM,
            explanation="No relevant content was retrieved from the company document.",
            suggested_fix="Provide a section that addresses this requirement.",
            evidence=[],
        )

    user_prompt_parts = [
        f"Requirement ID: {requirement_id}",
        f"Requirement text:\n{requirement_text}",
        "",
        "Company document excerpts (with chunk_ordinal and similarity score):",
    ]
    for excerpt in excerpts:
        user_prompt_parts.append(
            f"--- chunk_ordinal={excerpt.ordinal} similarity={excerpt.similarity:.3f} ---\n{excerpt.text}"
        )
    user_prompt = "\n".join(user_prompt_parts)

    raw = llm.complete_json(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        schema_hint=SCHEMA_HINT,
        temperature=0.0,
        max_tokens=800,
    )
    return _coerce_finding(raw)


def _coerce_finding(raw: dict[str, Any]) -> ComplianceFinding:
    status_value = str(raw.get("status", "")).strip().lower()
    if status_value not in _VALID_STATUSES:
        status_value = ComplianceStatus.NEEDS_HUMAN_REVIEW.value
    risk_value = str(raw.get("risk_level", "")).strip().lower()
    if risk_value not in _VALID_RISKS:
        risk_value = RiskLevel.MEDIUM.value
    try:
        confidence = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    explanation = str(raw.get("explanation", "")).strip()
    suggested_fix = str(raw.get("suggested_fix", "")).strip()
    evidence_in = raw.get("evidence", [])
    evidence: list[dict[str, Any]] = []
    if isinstance(evidence_in, list):
        for item in evidence_in:
            if not isinstance(item, dict):
                continue
            quote = str(item.get("quote", "")).strip()
            if not quote:
                continue
            try:
                ordinal: int | None = int(item["chunk_ordinal"]) if "chunk_ordinal" in item else None
            except (TypeError, ValueError):
                ordinal = None
            evidence.append({"chunk_ordinal": ordinal, "quote": quote})
    return ComplianceFinding(
        status=ComplianceStatus(status_value),
        confidence=confidence,
        risk_level=RiskLevel(risk_value),
        explanation=explanation,
        suggested_fix=suggested_fix,
        evidence=evidence,
    )
