from __future__ import annotations

from pathlib import Path

import pytest

from app.orchestrator.task_schema import TaskResult, TaskType
from app.services.document_service import DocumentService, DocumentServiceError
from app.services.research_service import ResearchService, ResearchServiceError


class StubOrchestrator:
    def __init__(self) -> None:
        self.calls = []

    def run(self, payload):
        self.calls.append(payload)
        return TaskResult(task_type=payload.task_type, final_output="# Final Markdown", intermediate={}, steps=[])


def test_document_service_prepare_document_with_raw_text_chunks():
    service = DocumentService(chunk_size=12, chunk_overlap=0)

    result = service.prepare_document(raw_text="abcdefghijklmno")

    assert result["source_type"] == "raw_text"
    assert result["chunk_count"] == 2
    assert result["paper_text"] == "abcdefghijklmno"


def test_document_service_prepare_document_with_pdf_path(monkeypatch, tmp_path: Path):
    service = DocumentService()
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(service, "validate_pdf", lambda p: Path(p))
    monkeypatch.setattr(
        service,
        "extract_text_from_pdf",
        lambda p: {
            "source_file": "paper.pdf",
            "source_path": str(pdf_path),
            "extracted_text_path": str(tmp_path / "paper.txt"),
            "page_count": 1,
            "chunk_count": 1,
            "chunks": [{"chunk_id": 1, "text": "Study content"}],
        },
    )

    result = service.prepare_document(pdf_path=pdf_path)

    assert result["source_type"] == "pdf"
    assert result["paper_text"] == "Study content"
    assert result["source_file"] == "paper.pdf"


def test_document_service_rejects_missing_and_mixed_inputs():
    service = DocumentService()

    with pytest.raises(DocumentServiceError):
        service.prepare_document()

    with pytest.raises(DocumentServiceError):
        service.prepare_document(raw_text="x", pdf_path="paper.pdf")


def test_research_service_returns_markdown_for_raw_text():
    orchestrator = StubOrchestrator()
    service = ResearchService(orchestrator=orchestrator)

    output = service.run(task_type=TaskType.STUDY_TABLE, raw_text="paper text " * 10)

    assert output == "# Final Markdown"
    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0].paper_text == ("paper text " * 10).strip()


def test_research_service_supports_pdf_input_and_metadata(monkeypatch, tmp_path: Path):
    orchestrator = StubOrchestrator()
    service = ResearchService(orchestrator=orchestrator)

    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(
        service.document_service,
        "prepare_document",
        lambda **kwargs: {
            "paper_text": "PDF extracted text " * 6,
            "source_type": "pdf",
            "source_file": "paper.pdf",
            "source_path": str(pdf_path),
            "chunk_count": 3,
            "page_count": 5,
            "extracted_text_path": str(tmp_path / "paper.txt"),
        },
    )

    result = service.run(
        task_type="full_report",
        pdf_path=pdf_path,
        include_metadata=True,
    )

    assert isinstance(result, dict)
    assert result["final_output"] == "# Final Markdown"
    assert result["metadata"]["document"]["source_type"] == "pdf"
    assert orchestrator.calls[0].paper_text == ("PDF extracted text " * 6).strip()


def test_research_service_wraps_document_errors(monkeypatch):
    service = ResearchService(orchestrator=StubOrchestrator())

    def _raise(**kwargs):
        raise DocumentServiceError("bad input")

    monkeypatch.setattr(service.document_service, "prepare_document", _raise)

    with pytest.raises(ResearchServiceError) as exc:
        service.run(task_type=TaskType.STUDY_TABLE, raw_text="x")

    assert "Document processing failed" in str(exc.value)


def test_research_service_rejects_too_short_input_before_pipeline():
    orchestrator = StubOrchestrator()
    service = ResearchService(orchestrator=orchestrator)

    with pytest.raises(ResearchServiceError, match="too short"):
        service.run(task_type=TaskType.STUDY_TABLE, raw_text="tiny")

    assert orchestrator.calls == []
