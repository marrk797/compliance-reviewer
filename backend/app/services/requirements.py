"""Split a regulatory document into atomic requirements.

The extractor uses cheap, deterministic heuristics first (numbered clauses,
"shall"/"must" sentences) so the pipeline still produces useful output without
calling the LLM. Callers may layer LLM-based refinement on top.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Section header like "1.", "1.1", "Article 5", "Section 3.2"
# The separator after the number accepts:
#   - "." not followed by a digit (so "3.1" still parses as a single number)
#   - ")" or ":"
#   - " -" or " --"
#   - any run of whitespace
_SECTION_RE = re.compile(
    r"^\s*(?:(?:Article|Section|Clause|Part|Chapter)\s+)?"
    r"(?P<num>\d+(?:\.\d+)*)"
    r"(?:\.(?!\d)|[\)\:]|\s+-{1,2}|\s+)"
    r"\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
# Bulleted clause markers
_BULLET_RE = re.compile(r"^\s*(?:[\-\*\u2022])\s+(?P<rest>.+)$")
# Imperative cue words used by regulations.
_IMPERATIVE_RE = re.compile(
    r"\b(shall|must|should|is required to|are required to|will|may not|shall not|must not)\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\?!])\s+(?=[A-Z(])")


@dataclass(slots=True)
class ExtractedRequirement:
    requirement_id: str
    text: str
    section: str | None


def extract_requirements(text: str) -> list[ExtractedRequirement]:
    """Heuristically split regulatory text into atomic requirements.

    The function tries, in order:

    1. Numbered/lettered section headers (``"1."``, ``"1.1"``, ``"Article 5"``).
    2. Bulleted lists.
    3. Imperative sentences containing ``shall``/``must``.
    """
    paragraphs: list[str] = []
    for raw in re.split(r"\n{2,}", text):
        block = raw.strip()
        if not block:
            continue
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        # Bulleted lists separated by single newlines should each be their own
        # requirement, not a single concatenated paragraph.
        if len(lines) > 1 and all(_BULLET_RE.match(line) for line in lines):
            paragraphs.extend(lines)
        else:
            paragraphs.append(block)
    if not paragraphs:
        return []

    extracted: list[ExtractedRequirement] = []
    fallback_index = 1
    for paragraph in paragraphs:
        section_match = _SECTION_RE.match(paragraph)
        if section_match:
            req_id = section_match.group("num")
            rest = section_match.group("rest").strip()
            body = rest if rest else paragraph
            extracted.append(
                ExtractedRequirement(
                    requirement_id=f"R-{req_id}",
                    text=body,
                    section=req_id,
                )
            )
            continue
        bullet_match = _BULLET_RE.match(paragraph)
        if bullet_match:
            extracted.append(
                ExtractedRequirement(
                    requirement_id=f"R-B{fallback_index:03d}",
                    text=bullet_match.group("rest").strip(),
                    section=None,
                )
            )
            fallback_index += 1
            continue
        # Fall back to sentence-level splitting on imperative cue words.
        sentences = _SENTENCE_SPLIT_RE.split(paragraph)
        any_imperative = False
        for sentence in sentences:
            if not _IMPERATIVE_RE.search(sentence):
                continue
            any_imperative = True
            extracted.append(
                ExtractedRequirement(
                    requirement_id=f"R-S{fallback_index:03d}",
                    text=sentence.strip(),
                    section=None,
                )
            )
            fallback_index += 1
        if not any_imperative and len(paragraph) <= 600:
            # Whole-paragraph fallback for short prescriptive text.
            extracted.append(
                ExtractedRequirement(
                    requirement_id=f"R-P{fallback_index:03d}",
                    text=paragraph,
                    section=None,
                )
            )
            fallback_index += 1

    # Deduplicate by text (preserving order) and re-number.
    seen: set[str] = set()
    deduped: list[ExtractedRequirement] = []
    for req in extracted:
        key = re.sub(r"\s+", " ", req.text).strip().lower()
        if key in seen or len(key) < 5:
            continue
        seen.add(key)
        deduped.append(req)
    return deduped
