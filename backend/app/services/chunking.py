"""Token-aware chunking for the company submission document."""
from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from app.config import settings

_ENCODING_CACHE: dict[str, tiktoken.Encoding] = {}


def _get_encoding() -> tiktoken.Encoding:
    name = "cl100k_base"
    if name not in _ENCODING_CACHE:
        try:
            _ENCODING_CACHE[name] = tiktoken.get_encoding(name)
        except Exception:  # pragma: no cover - offline fallback
            _ENCODING_CACHE[name] = tiktoken.get_encoding("p50k_base")
    return _ENCODING_CACHE[name]


@dataclass(slots=True, frozen=True)
class Chunk:
    ordinal: int
    text: str
    token_count: int


def chunk_text(
    text: str,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """Split ``text`` into overlapping token-bounded chunks.

    Empty input yields an empty list. Chunks preserve original token order so
    the underlying text can be reconstructed (modulo the overlap).
    """
    chunk_size = chunk_size or settings.chunk_token_size
    overlap = overlap or settings.chunk_token_overlap
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    text = text.strip()
    if not text:
        return []

    enc = _get_encoding()
    tokens = enc.encode(text)
    chunks: list[Chunk] = []
    step = chunk_size - overlap
    ordinal = 0
    for start in range(0, len(tokens), step):
        window = tokens[start : start + chunk_size]
        if not window:
            break
        chunk_text_value = enc.decode(window).strip()
        if not chunk_text_value:
            continue
        chunks.append(Chunk(ordinal=ordinal, text=chunk_text_value, token_count=len(window)))
        ordinal += 1
        if start + chunk_size >= len(tokens):
            break
    return chunks
