"""Anthropic implementation of the LLM protocol."""
from __future__ import annotations

import json
import re
from typing import Any

import anthropic


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, *, model: str, api_key: str | None) -> None:
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Configure it in the environment to use the Anthropic provider."
            )
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        full_system = (
            system
            + "\n\nYou MUST respond with a single JSON object and nothing else."
            + " Do not wrap the response in Markdown code fences."
        )
        if schema_hint is not None:
            full_system += "\nExpected shape: " + json.dumps(schema_hint, separators=(",", ":"))
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=full_system,
            messages=[{"role": "user", "content": user}],
        )
        text_parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        raw = "".join(text_parts).strip()
        cleaned = _strip_code_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Anthropic returned non-JSON content: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Anthropic response was not a JSON object")
        return data


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.DOTALL)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _FENCE_RE.sub("", stripped)
    return stripped.strip()
