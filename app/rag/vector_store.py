"""Persistent local vector store for retrieved paper chunks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any

from config import settings


@dataclass(frozen=True)
class VectorRecord:
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


class JsonVectorStore:
    """Simple JSON-backed vector store.

    The storage format is intentionally small and dependency-free so the RAG
    layer can be disabled or omitted without affecting the MVP pipeline.
    """

    def __init__(self, persist_dir: str | Path | None = None, filename: str = "chunks.json") -> None:
        self.persist_dir = Path(persist_dir or settings.vector_db_dir)
        self.path = self.persist_dir / filename
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    def add(self, records: list[VectorRecord]) -> None:
        existing = {record.id: record for record in self.load_all()}
        for record in records:
            if not record.text.strip():
                continue
            if not record.embedding:
                raise ValueError(f"Vector record '{record.id}' has an empty embedding.")
            existing[record.id] = record
        self._write(list(existing.values()))

    def clear(self) -> None:
        self._write([])

    def count(self) -> int:
        return len(self.load_all())

    def load_all(self) -> list[VectorRecord]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Vector store file is not valid JSON: {self.path}") from exc

        records: list[VectorRecord] = []
        for item in payload:
            records.append(
                VectorRecord(
                    id=str(item["id"]),
                    text=str(item["text"]),
                    embedding=[float(value) for value in item["embedding"]],
                    metadata=dict(item.get("metadata", {})),
                )
            )
        return records

    def search(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[tuple[VectorRecord, float]]:
        if top_k <= 0:
            return []

        results: list[tuple[VectorRecord, float]] = []
        for record in self.load_all():
            if filters and any(record.metadata.get(key) != value for key, value in filters.items()):
                continue
            score = _cosine_similarity(query_embedding, record.embedding)
            results.append((record, score))

        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    def _write(self, records: list[VectorRecord]) -> None:
        payload = [asdict(record) for record in records]
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
