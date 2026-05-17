"""File management utilities for research document ingestion."""

from __future__ import annotations

from pathlib import Path
import mimetypes

from config import settings


class FileValidationError(ValueError):
    """Raised when an input file is invalid for processing."""


class FileManager:
    """Handles upload validation and extracted text output paths."""

    def __init__(self) -> None:
        self.upload_dir = settings.upload_dir
        self.output_dir = settings.output_dir
        self.extracted_text_dir = settings.base_dir / "data" / "extracted_text"

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_text_dir.mkdir(parents=True, exist_ok=True)

    def resolve_upload_pdf(self, filename: str) -> Path:
        """Resolve and validate a PDF path under upload dir."""
        candidate = (self.upload_dir / filename).resolve()

        if not str(candidate).startswith(str(self.upload_dir.resolve())):
            raise FileValidationError("Invalid file path: path traversal is not allowed.")

        self.validate_pdf_file(candidate)
        return candidate

    def validate_pdf_file(self, file_path: Path) -> None:
        """Validate that the path exists and points to a readable PDF file."""
        if not file_path.exists():
            raise FileValidationError(f"PDF file not found: {file_path}")

        if not file_path.is_file():
            raise FileValidationError(f"Not a file: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise FileValidationError(
                f"Unsupported file type '{file_path.suffix}'. Only .pdf files are supported."
            )

        mime_type, _ = mimetypes.guess_type(file_path.name)
        if mime_type and mime_type != "application/pdf":
            raise FileValidationError(
                f"Unsupported MIME type '{mime_type}'. Expected application/pdf."
            )

    def build_extracted_text_path(self, source_pdf: Path) -> Path:
        """Build output path for extracted text based on source filename."""
        output_name = f"{source_pdf.stem}.txt"
        return self.extracted_text_dir / output_name

    def save_extracted_text(self, source_pdf: Path, text: str) -> Path:
        """Save cleaned extracted text to output directory."""
        out_path = self.build_extracted_text_path(source_pdf)
        out_path.write_text(text, encoding="utf-8")
        return out_path
