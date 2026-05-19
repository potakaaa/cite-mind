"""Embedding providers for the optional multi-paper RAG layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
import hashlib
import math
import re
from typing import Literal

from config import settings


EmbeddingBackend = Literal["auto", "hash", "sentence_transformers"]


class EmbeddingError(RuntimeError):
    """Raised when embedding generation fails."""


class EmbeddingProvider(ABC):
    """Interface for text embedding providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for metadata/debugging."""

    @abstractmethod
    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""

    def embed_query(self, query: str) -> list[float]:
        """Embed a retrieval query."""
        return self.embed_texts([query])[0]


class HashingEmbeddingProvider(EmbeddingProvider):
    """Small deterministic local embedding provider used when ML deps are absent.

    This is not as semantically strong as sentence-transformers, but it keeps the
    RAG feature optional and gives tests/development a dependency-light backend.
    """

    _token_pattern = re.compile(r"[A-Za-z0-9_]+")

    def __init__(self, dimensions: int = 384) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than 0")
        self.dimensions = dimensions

    @property
    def name(self) -> str:
        return f"hash-{self.dimensions}"

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            tokens = self._token_pattern.findall(text.lower())
            for token in tokens:
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "big") % self.dimensions
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[bucket] += sign
            embeddings.append(_normalize(vector))
        return embeddings


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """sentence-transformers embedding provider loaded lazily."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise EmbeddingError(
                "sentence-transformers is not installed. Install it or set RAG_EMBEDDING_BACKEND=hash."
            ) from exc

        try:
            self._model = SentenceTransformer(model_name)
        except Exception as exc:  # pragma: no cover - model/runtime dependent
            raise EmbeddingError(f"Failed to load embedding model '{model_name}': {exc}") from exc

    @property
    def name(self) -> str:
        return f"sentence-transformers:{self.model_name}"

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        cleaned = [text if text.strip() else " " for text in texts]
        try:
            embeddings = self._model.encode(
                cleaned,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:  # pragma: no cover - model/runtime dependent
            raise EmbeddingError(f"Failed to generate embeddings: {exc}") from exc

        return [list(map(float, vector)) for vector in embeddings]


def build_embedding_provider(
    backend: EmbeddingBackend | str | None = None,
    model_name: str | None = None,
) -> EmbeddingProvider:
    """Build the configured embedding provider.

    `auto` prefers sentence-transformers when installed and falls back to the
    deterministic hashing backend otherwise.
    """
    selected = backend or settings.rag_embedding_backend
    model = model_name or settings.rag_embedding_model

    if selected == "hash":
        return HashingEmbeddingProvider(dimensions=settings.rag_hash_dimensions)
    if selected == "sentence_transformers":
        return SentenceTransformerEmbeddingProvider(model_name=model)
    if selected != "auto":
        raise EmbeddingError(f"Unsupported embedding backend '{selected}'.")

    try:
        return SentenceTransformerEmbeddingProvider(model_name=model)
    except EmbeddingError:
        return HashingEmbeddingProvider(dimensions=settings.rag_hash_dimensions)


def _normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]
