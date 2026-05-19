"""Retrieval helpers for multi-paper RAG."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from app.rag.embeddings import EmbeddingProvider, build_embedding_provider
from app.rag.vector_store import JsonVectorStore, VectorRecord


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    score: float
    metadata: dict[str, Any]


class RAGRetriever:
    """Indexes and retrieves relevant chunks across uploaded papers."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: JsonVectorStore | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or build_embedding_provider()
        self.vector_store = vector_store or JsonVectorStore()

    def index_chunks(
        self,
        chunks: list[dict[str, Any]],
        *,
        paper_id: str,
        source_metadata: dict[str, Any] | None = None,
    ) -> list[VectorRecord]:
        texts = [str(chunk.get("text", "")).strip() for chunk in chunks if str(chunk.get("text", "")).strip()]
        embeddings = self.embedding_provider.embed_texts(texts)

        records: list[VectorRecord] = []
        text_index = 0
        for chunk in chunks:
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue
            chunk_id = str(chunk.get("chunk_id") or text_index + 1)
            metadata = {
                **(source_metadata or {}),
                "paper_id": paper_id,
                "chunk_id": chunk_id,
                "source_file": chunk.get("source_file") or (source_metadata or {}).get("source_file"),
                "source_path": chunk.get("source_path") or (source_metadata or {}).get("source_path"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "char_start": chunk.get("char_start"),
                "char_end": chunk.get("char_end"),
                "embedding_provider": self.embedding_provider.name,
            }
            record_id = f"{_slug(paper_id)}::{chunk_id}"
            records.append(
                VectorRecord(
                    id=record_id,
                    text=text,
                    embedding=embeddings[text_index],
                    metadata={key: value for key, value in metadata.items() if value is not None},
                )
            )
            text_index += 1

        self.vector_store.add(records)
        return records

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("query is required for retrieval.")
        query_embedding = self.embedding_provider.embed_query(cleaned)
        matches = self.vector_store.search(query_embedding, top_k=top_k, filters=filters)
        return [
            RetrievedChunk(id=record.id, text=record.text, score=score, metadata=record.metadata)
            for record, score in matches
        ]

    @staticmethod
    def format_context(chunks: list[RetrievedChunk], max_chars: int = 12000) -> str:
        blocks: list[str] = []
        total = 0
        for index, chunk in enumerate(chunks, start=1):
            source = _format_source(chunk.metadata)
            block = f"[{index}] {source}\n{chunk.text}"
            if total + len(block) > max_chars:
                remaining = max_chars - total
                if remaining <= 0:
                    break
                block = block[:remaining].rstrip()
            blocks.append(block)
            total += len(block)
        return "\n\n".join(blocks)


def _format_source(metadata: dict[str, Any]) -> str:
    source = str(metadata.get("source_file") or metadata.get("paper_id") or "unknown source")
    page_start = metadata.get("page_start")
    page_end = metadata.get("page_end")
    chunk_id = metadata.get("chunk_id")
    page_label = ""
    if page_start and page_end and page_start != page_end:
        page_label = f", pages {page_start}-{page_end}"
    elif page_start:
        page_label = f", page {page_start}"
    chunk_label = f", chunk {chunk_id}" if chunk_id else ""
    return f"{Path(source).name}{page_label}{chunk_label}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return slug.strip("-") or "paper"
