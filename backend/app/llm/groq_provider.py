"""Groq LLM provider.

Groq exposes an OpenAI-compatible chat-completions endpoint with a generous
free tier. Get a free key (no credit card) at https://console.groq.com/keys.
"""
from __future__ import annotations

import json
from typing import Any

from groq import Groq

from app.llm.base import LLMProvider


class GroqLLM(LLMProvider):
    name = "groq"

    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self._client = Groq(api_key=api_key)

    def complete_json(
        self,
        system: str,
        user: str,
        schema_hint: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Ask the model for a strict-JSON response.

        Groq supports ``response_format={"type": "json_object"}`` for
        Llama-3.x and Mixtral models. We additionally remind the model in the
        system prompt that JSON is required, since some smaller free-tier
        models occasionally drift.
        """
        instruction = (
            "Respond with a single valid JSON object that matches the requested schema. "
            "Do not include markdown fences, prose, or any text outside the JSON object."
        )
        if schema_hint:
            instruction = f"{instruction}\n\nSchema:\n{schema_hint}"
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"{system}\n\n{instruction}"},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        # Defensive: strip accidental fences before parsing.
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Groq did not return a JSON object.")
        return parsed
