"""PDF reading and text extraction tools for research inputs."""

from __future__ import annotations

from pathlib import Path
import re

import fitz  # PyMuPDF

from .file_manager import FileManager
from .text_chunker import TextChunk, TextChunker


class PDFReadError(RuntimeError):
    """Raised when a PDF cannot be parsed or read."""


class PDFReader:
    """Extract and clean text from PDF files with fallback support."""

    def __init__(self, file_manager: FileManager | None = None) -> None:
        self.file_manager = file_manager or FileManager()

    def extract_from_upload(
        self,
        filename: str,
        chunk_size: int = 3000,
        chunk_overlap: int = 300,
    ) -> dict[str, object]:
        """Extract text from a PDF in upload directory and return chunked output metadata."""
        pdf_path = self.file_manager.resolve_upload_pdf(filename)
        return self.extract_from_path(pdf_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def extract_from_path(
        self,
        pdf_path: Path,
        chunk_size: int = 3000,
        chunk_overlap: int = 300,
    ) -> dict[str, object]:
        self.file_manager.validate_pdf_file(pdf_path)

        pages = self._extract_pages_with_pymupdf(pdf_path)
        if not self._has_meaningful_text(pages):
            pages = self._extract_pages_with_pdfplumber(pdf_path)

        if not self._has_meaningful_text(pages):
            raise PDFReadError(
                "No readable text content found in PDF. The file may be scanned/image-only or corrupted."
            )

        cleaned_pages = self._clean_pages(pages)
        full_text = "\n\n".join(page["text"] for page in cleaned_pages if page["text"].strip())
        saved_path = self.file_manager.save_extracted_text(pdf_path, full_text)

        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk_pages(source_file=pdf_path.name, pages=cleaned_pages)

        return {
            "source_file": pdf_path.name,
            "source_path": str(pdf_path),
            "extracted_text_path": str(saved_path),
            "page_count": len(cleaned_pages),
            "chunk_count": len(chunks),
            "chunks": [self._chunk_to_dict(chunk) for chunk in chunks],
        }

    def _extract_pages_with_pymupdf(self, pdf_path: Path) -> list[dict[str, object]]:
        try:
            pages: list[dict[str, object]] = []
            with fitz.open(pdf_path) as doc:
                for index, page in enumerate(doc, start=1):
                    pages.append({"page_number": index, "text": page.get_text("text") or ""})
            return pages
        except Exception as exc:
            raise PDFReadError(f"Failed to read PDF with PyMuPDF: {exc}") from exc

    def _extract_pages_with_pdfplumber(self, pdf_path: Path) -> list[dict[str, object]]:
        try:
            import pdfplumber
        except ImportError as exc:
            raise PDFReadError(
                "PyMuPDF extraction returned no text and pdfplumber is not installed for fallback."
            ) from exc

        try:
            pages: list[dict[str, object]] = []
            with pdfplumber.open(pdf_path) as doc:
                for index, page in enumerate(doc.pages, start=1):
                    pages.append({"page_number": index, "text": page.extract_text() or ""})
            return pages
        except Exception as exc:
            raise PDFReadError(f"Fallback extraction with pdfplumber failed: {exc}") from exc

    def _clean_pages(self, pages: list[dict[str, object]]) -> list[dict[str, object]]:
        cleaned: list[dict[str, object]] = []
        for page in pages:
            raw_text = str(page.get("text", ""))
            cleaned_text = self._clean_text(raw_text)
            cleaned.append({"page_number": page["page_number"], "text": cleaned_text})
        return cleaned

    def _clean_text(self, text: str) -> str:
        # Normalize line endings and trim surrounding whitespace.
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()

        # Join words broken across line wraps/hyphenation.
        cleaned = re.sub(r"(\w)-\n(\w)", r"\1\2", cleaned)

        # Collapse line breaks that split sentences mid-line.
        cleaned = re.sub(r"(?<![\.!?])\n(?!\n)", " ", cleaned)

        # Keep paragraph breaks while collapsing excessive blank lines.
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # Remove repeated spaces and tabs.
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)

        return cleaned.strip()

    def _has_meaningful_text(self, pages: list[dict[str, object]]) -> bool:
        for page in pages:
            text = str(page.get("text", "")).strip()
            if text:
                return True
        return False

    def _chunk_to_dict(self, chunk: TextChunk) -> dict[str, object]:
        return {
            "chunk_id": chunk.chunk_id,
            "source_file": chunk.source_file,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "text": chunk.text,
        }
