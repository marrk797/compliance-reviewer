"""Local embedding provider using fastembed.

fastembed runs ONNX models in-process. ``BAAI/bge-small-en-v1.5`` produces
384-dimensional vectors and downloads ~70 MB of model weights once on first
use, then caches them on disk. No API key, no rate limits.
"""
from __future__ import annotations

from threading import Lock

from fastembed import TextEmbedding

from app.llm.base import EmbeddingProvider


class FastEmbedEmbeddings(EmbeddingProvider):
    name = "fastembed"

    _model_cache: dict[str, TextEmbedding] = {}
    _lock = Lock()

    def __init__(self, model: str, dimension: int) -> None:
        self.model = model
        self.dimension = dimension

    def _get(self) -> TextEmbedding:
        with self._lock:
            cached = self._model_cache.get(self.model)
            if cached is None:
                cached = TextEmbedding(model_name=self.model)
                self._model_cache[self.model] = cached
            return cached

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get()
        # ``embed`` returns a generator of numpy arrays.
        vectors = [vec.tolist() for vec in model.embed(texts)]
        # Sanity-check dimensionality so a wrong EMBEDDING_DIM env var fails fast.
        if vectors and len(vectors[0]) != self.dimension:
            raise RuntimeError(
                f"fastembed model {self.model!r} returned vectors of length "
                f"{len(vectors[0])}, but EMBEDDING_DIM is set to {self.dimension}."
            )
        return vectors
