"""Chunking utilities for extracted research text."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextChunk:
    chunk_id: int
    source_file: str
    page_start: int | None
    page_end: int | None
    char_start: int
    char_end: int
    text: str


class TextChunker:
    """Split text blocks into manageable chunks while preserving order and metadata."""

    def __init__(self, chunk_size: int = 3000, chunk_overlap: int = 300) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(self, source_file: str, pages: list[dict[str, object]]) -> list[TextChunk]:
        """Chunk page-level text records into fixed-size chunks.

        Expected page item shape:
        {
            "page_number": int,
            "text": str,
        }
        """
        chunks: list[TextChunk] = []
        chunk_id = 1
        global_offset = 0

        for page in pages:
            page_number = int(page["page_number"])
            page_text = str(page.get("text", ""))
            if not page_text.strip():
                global_offset += len(page_text)
                continue

            start = 0
            while start < len(page_text):
                end = min(start + self.chunk_size, len(page_text))
                piece = page_text[start:end].strip()

                if piece:
                    chunks.append(
                        TextChunk(
                            chunk_id=chunk_id,
                            source_file=source_file,
                            page_start=page_number,
                            page_end=page_number,
                            char_start=global_offset + start,
                            char_end=global_offset + end,
                            text=piece,
                        )
                    )
                    chunk_id += 1

                if end >= len(page_text):
                    break
                start = end - self.chunk_overlap

            global_offset += len(page_text)

        return chunks
