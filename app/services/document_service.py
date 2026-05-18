"""Service layer for document validation, ingestion, extraction, and chunking."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

from app.tools.file_manager import FileManager, FileValidationError
from app.tools.pdf_reader import PDFReadError, PDFReader
from app.tools.text_chunker import TextChunker


class DocumentServiceError(RuntimeError):
    """Raised when document processing fails."""


class DocumentService:
    """Coordinates document ingestion paths for raw text and PDFs."""

    def __init__(
        self,
        file_manager: FileManager | None = None,
        pdf_reader: PDFReader | None = None,
        chunk_size: int = 3000,
        chunk_overlap: int = 300,
    ) -> None:
        self.file_manager = file_manager or FileManager()
        self.pdf_reader = pdf_reader or PDFReader(file_manager=self.file_manager)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.logger = logging.getLogger("app.services.document")

    def validate_pdf(self, pdf_path: str | Path) -> Path:
        path = Path(pdf_path).expanduser().resolve()
        self.file_manager.validate_pdf_file(path)
        return path

    def save_uploaded_pdf(self, filename: str, content: bytes) -> Path:
        if not filename or not filename.strip():
            raise DocumentServiceError("filename is required when saving uploaded PDF content.")
        if not content:
            raise DocumentServiceError("Uploaded PDF content is empty.")

        candidate = (self.file_manager.upload_dir / Path(filename).name).resolve()
        if not str(candidate).startswith(str(self.file_manager.upload_dir.resolve())):
            raise DocumentServiceError("Invalid upload path.")

        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_bytes(content)
        self.file_manager.validate_pdf_file(candidate)
        self.logger.info("Saved uploaded PDF to %s", candidate)
        return candidate

    def extract_text_from_pdf(self, pdf_path: str | Path) -> dict[str, Any]:
        path = self.validate_pdf(pdf_path)
        try:
            extracted = self.pdf_reader.extract_from_path(
                path,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            self.logger.info(
                "Extracted text from PDF '%s' (pages=%s, chunks=%s)",
                path.name,
                extracted.get("page_count"),
                extracted.get("chunk_count"),
            )
            return extracted
        except (FileValidationError, PDFReadError, ValueError) as exc:
            self.logger.exception("Failed to extract text from PDF '%s': %s", path, exc)
            raise DocumentServiceError(str(exc)) from exc

    def chunk_text(self, text: str, source_name: str = "raw_text.txt") -> list[dict[str, Any]]:
        cleaned = text.strip()
        if not cleaned:
            raise DocumentServiceError("Text input is empty.")

        chunker = TextChunker(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = chunker.chunk_pages(
            source_file=source_name,
            pages=[{"page_number": 1, "text": cleaned}],
        )
        return [
            {
                "chunk_id": chunk.chunk_id,
                "source_file": chunk.source_file,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "text": chunk.text,
            }
            for chunk in chunks
        ]

    def prepare_document(
        self,
        *,
        raw_text: str | None = None,
        pdf_path: str | Path | None = None,
        pdf_bytes: bytes | None = None,
        pdf_filename: str | None = None,
    ) -> dict[str, Any]:
        has_raw_text = bool(raw_text and raw_text.strip())
        has_pdf_path = pdf_path is not None
        has_pdf_bytes = pdf_bytes is not None

        if has_raw_text and (has_pdf_path or has_pdf_bytes):
            raise DocumentServiceError("Provide either raw_text or PDF input, not both.")
        if not has_raw_text and not has_pdf_path and not has_pdf_bytes:
            raise DocumentServiceError("Either raw_text or PDF input is required.")

        if has_raw_text:
            text = str(raw_text).strip()
            chunks = self.chunk_text(text)
            return {
                "paper_text": text,
                "source_type": "raw_text",
                "source_file": None,
                "source_path": None,
                "chunks": chunks,
                "chunk_count": len(chunks),
                "page_count": 1,
                "extracted_text_path": None,
            }

        try:
            final_pdf_path = (
                self.save_uploaded_pdf(filename=pdf_filename or "upload.pdf", content=pdf_bytes)
                if has_pdf_bytes
                else self.validate_pdf(pdf_path)
            )
            extracted = self.extract_text_from_pdf(final_pdf_path)
            paper_text = "\n\n".join(
                str(chunk.get("text", "")).strip()
                for chunk in extracted.get("chunks", [])
                if str(chunk.get("text", "")).strip()
            ).strip()

            if not paper_text:
                raise DocumentServiceError("No readable text was extracted from the PDF.")

            return {
                "paper_text": paper_text,
                "source_type": "pdf",
                **extracted,
            }
        except (FileValidationError, PDFReadError, OSError, ValueError, DocumentServiceError) as exc:
            self.logger.exception("Document preparation failed: %s", exc)
            if isinstance(exc, DocumentServiceError):
                raise
            raise DocumentServiceError(str(exc)) from exc
