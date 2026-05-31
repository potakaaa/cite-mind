from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.pdf_reader import PDFReadError, PDFReader


class TempFileManager:
    def __init__(self, extracted_text_dir: Path) -> None:
        self.extracted_text_dir = extracted_text_dir

    def validate_pdf_file(self, file_path: Path) -> None:
        if file_path.suffix != ".pdf":
            raise ValueError("expected a PDF")

    def save_extracted_text(self, source_pdf: Path, text: str) -> Path:
        out_path = self.extracted_text_dir / f"{source_pdf.stem}.txt"
        out_path.write_text(text, encoding="utf-8")
        return out_path


def test_pdf_reader_extracts_cleans_saves_and_chunks_mocked_pdf(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% mocked test pdf\n")
    reader = PDFReader(file_manager=TempFileManager(tmp_path))

    monkeypatch.setattr(
        reader,
        "_extract_pages_with_pymupdf",
        lambda path: [
            {"page_number": 1, "text": "Hyphen-\nated text\ncontinues"},
            {"page_number": 2, "text": "Second page has enough words."},
        ],
    )

    result = reader.extract_from_path(pdf_path, chunk_size=24, chunk_overlap=4)

    saved_text = Path(result["extracted_text_path"]).read_text(encoding="utf-8")
    assert "Hyphenated text continues" in saved_text
    assert result["source_file"] == "sample.pdf"
    assert result["page_count"] == 2
    assert result["chunk_count"] >= 2
    assert result["chunks"][0]["page_start"] == 1


def test_pdf_reader_falls_back_then_rejects_image_only_pdf(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "scanned.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% mocked image-only pdf\n")
    reader = PDFReader(file_manager=TempFileManager(tmp_path))

    monkeypatch.setattr(reader, "_extract_pages_with_pymupdf", lambda path: [{"page_number": 1, "text": ""}])
    monkeypatch.setattr(reader, "_extract_pages_with_pdfplumber", lambda path: [{"page_number": 1, "text": ""}])

    with pytest.raises(PDFReadError, match="No readable text"):
        reader.extract_from_path(pdf_path)
