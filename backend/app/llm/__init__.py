"""LLM provider abstraction.

The compliance pipeline talks to LLMs only through the protocols defined in
``app.llm.base``. Concrete providers (Groq / OpenAI / Anthropic) live in this
package and are selected via the ``LLM_PROVIDER`` and ``EMBEDDING_PROVIDER``
settings. The default Groq + fastembed combo requires only one free, no-card
API key (Groq) and zero signups (fastembed runs locally).
"""
from __future__ import annotations

from app.config import settings
from app.llm.base import EmbeddingProvider, LLMProvider


def get_llm_provider() -> LLMProvider:
    """Return the configured chat/completion provider."""
    if settings.llm_provider == "groq":
        from app.llm.groq_provider import GroqLLM

        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys"
            )
        return GroqLLM(model=settings.llm_model, api_key=settings.groq_api_key)
    if settings.llm_provider == "openai":
        from app.llm.openai_provider import OpenAILLM

        return OpenAILLM(model=settings.llm_model, api_key=settings.openai_api_key)
    if settings.llm_provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicLLM

        return AnthropicLLM(model=settings.llm_model, api_key=settings.anthropic_api_key)
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider!r}")


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider."""
    if settings.embedding_provider == "fastembed":
        from app.llm.fastembed_provider import FastEmbedEmbeddings

        return FastEmbedEmbeddings(
            model=settings.embedding_model,
            dimension=settings.embedding_dim,
        )
    if settings.embedding_provider == "openai":
        from app.llm.openai_provider import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=settings.embedding_model,
            dimension=settings.embedding_dim,
            api_key=settings.openai_api_key,
        )
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider!r}")


__all__ = [
    "EmbeddingProvider",
    "LLMProvider",
    "get_embedding_provider",
    "get_llm_provider",
]
