from app.models.report import ComplianceStatus, RiskLevel
from app.services.compliance import _coerce_finding


def test_invalid_status_falls_back_to_human_review() -> None:
    finding = _coerce_finding(
        {
            "status": "totally_made_up",
            "confidence": 0.9,
            "risk_level": "spicy",
            "explanation": "x",
            "suggested_fix": "y",
            "evidence": [],
        }
    )
    assert finding.status == ComplianceStatus.NEEDS_HUMAN_REVIEW
    assert finding.risk_level == RiskLevel.MEDIUM


def test_confidence_is_clamped_and_evidence_filtered() -> None:
    finding = _coerce_finding(
        {
            "status": "compliant",
            "confidence": 5.0,
            "risk_level": "low",
            "explanation": "ok",
            "suggested_fix": "",
            "evidence": [
                {"chunk_ordinal": 2, "quote": "valid quote"},
                {"chunk_ordinal": "bad", "quote": "still ok"},
                {"quote": ""},  # dropped
                "garbage",  # dropped
            ],
        }
    )
    assert finding.status == ComplianceStatus.COMPLIANT
    assert finding.confidence == 1.0
    assert len(finding.evidence) == 2
    assert finding.evidence[0]["chunk_ordinal"] == 2
    assert finding.evidence[1]["chunk_ordinal"] is None
