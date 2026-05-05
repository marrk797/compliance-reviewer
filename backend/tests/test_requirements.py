from app.services.requirements import extract_requirements


def test_numbered_sections_become_requirements() -> None:
    text = """
1. The system shall encrypt all data at rest.

2. The system shall encrypt all data in transit.

3.1 User accounts must be protected with multi-factor authentication.
""".strip()
    reqs = extract_requirements(text)
    assert len(reqs) == 3
    ids = [r.requirement_id for r in reqs]
    assert ids == ["R-1", "R-2", "R-3.1"]
    assert "encrypt all data at rest" in reqs[0].text


def test_bullets_and_imperatives() -> None:
    text = """
- The vendor must publish an annual security report.
- The vendor must allow customer audits.

The system should retain logs for at least 90 days.
""".strip()
    reqs = extract_requirements(text)
    assert len(reqs) >= 3
    assert any("annual security report" in r.text for r in reqs)
    assert any("retain logs" in r.text for r in reqs)


def test_dedupes_repeated_requirements() -> None:
    text = """
1. Data must be encrypted at rest.

2. Data must be encrypted at rest.
""".strip()
    reqs = extract_requirements(text)
    assert len(reqs) == 1
