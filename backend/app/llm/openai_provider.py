"""OpenAI implementations of the LLM and embedding protocols."""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI


class OpenAILLM:
    name = "openai"

    def __init__(self, *, model: str, api_key: str | None) -> None:
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Configure it in the environment to use the OpenAI provider."
            )
        self.model = model
        self._client = OpenAI(api_key=api_key)

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema_hint: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        full_system = system
        if schema_hint is not None:
            full_system += "\n\nReturn a single JSON object with this shape: " + json.dumps(
                schema_hint, separators=(",", ":")
            )
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user", "content": user},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI returned non-JSON content: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("OpenAI response was not a JSON object")
        return data


class OpenAIEmbeddings:
    name = "openai"

    def __init__(self, *, model: str, dimension: int, api_key: str | None) -> None:
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Configure it in the environment to use OpenAI embeddings."
            )
        self.model = model
        self.dimension = dimension
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in resp.data]
