"""Provider-agnostic protocols for LLMs and embeddings."""
from __future__ import annotations

from typing import Any, Protocol


class LLMProvider(Protocol):
    """Protocol implemented by chat/completion providers."""

    name: str
    model: str

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Run a single LLM call and return parsed JSON.

        Implementations MUST request JSON output and MUST raise ``ValueError``
        if the response cannot be parsed as a JSON object.

        ``schema_hint`` is a free-form description of the expected fields,
        embedded into the system prompt by implementations to nudge the model;
        it is not a strict JSON Schema validator.
        """
        ...


class EmbeddingProvider(Protocol):
    """Protocol implemented by embedding model providers."""

    name: str
    model: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts and return one float vector per input."""
        ...
