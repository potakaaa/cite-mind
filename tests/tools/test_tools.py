from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.file_manager import FileManager, FileValidationError
from app.tools.pdf_reader import PDFReadError, PDFReader
from app.tools.text_chunker import TextChunker
from app.utils.prompt_loader import PromptLoadError, load_prompt_template


def test_prompt_loader_success_and_invalid_extension():
    content = load_prompt_template("writer_prompt.txt")
    assert content

    with pytest.raises(PromptLoadError):
        load_prompt_template("writer_prompt.md")


def test_text_chunker_chunks_and_preserves_order():
    chunker = TextChunker(chunk_size=5, chunk_overlap=1)
    pages = [{"page_number": 1, "text": "abcdefghij"}]

    chunks = chunker.chunk_pages(source_file="x.pdf", pages=pages)

    assert len(chunks) == 3
    assert [c.chunk_id for c in chunks] == [1, 2, 3]
    assert chunks[0].text == "abcde"
    assert chunks[1].text == "efghi"


def test_file_manager_validates_pdf_and_rejects_traversal(tmp_path: Path):
    fm = FileManager()
    good_pdf = tmp_path / "ok.pdf"
    good_pdf.write_text("dummy", encoding="utf-8")
    fm.validate_pdf_file(good_pdf)

    bad_ext = tmp_path / "bad.txt"
    bad_ext.write_text("dummy", encoding="utf-8")
    with pytest.raises(FileValidationError):
        fm.validate_pdf_file(bad_ext)

    with pytest.raises(FileValidationError):
        fm.resolve_upload_pdf("../evil.pdf")


def test_pdf_reader_extract_from_path_happy_path(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("stub", encoding="utf-8")

    reader = PDFReader()

    monkeypatch.setattr(reader.file_manager, "validate_pdf_file", lambda p: None)
    monkeypatch.setattr(
        reader,
        "_extract_pages_with_pymupdf",
        lambda p: [{"page_number": 1, "text": "Hello\nworld"}],
    )

    result = reader.extract_from_path(pdf_path, chunk_size=50, chunk_overlap=0)

    assert result["source_file"] == "doc.pdf"
    assert result["page_count"] == 1
    assert result["chunk_count"] >= 1
    assert Path(result["extracted_text_path"]).exists()


def test_pdf_reader_uses_fallback_and_raises_if_no_text(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("stub", encoding="utf-8")

    reader = PDFReader()
    monkeypatch.setattr(reader.file_manager, "validate_pdf_file", lambda p: None)
    monkeypatch.setattr(reader, "_extract_pages_with_pymupdf", lambda p: [{"page_number": 1, "text": ""}])
    monkeypatch.setattr(reader, "_extract_pages_with_pdfplumber", lambda p: [{"page_number": 1, "text": ""}])

    with pytest.raises(PDFReadError):
        reader.extract_from_path(pdf_path)
