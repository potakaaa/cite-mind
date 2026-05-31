from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.orchestrator.task_schema import TaskType
from app.services.export_service import ExportService, ExportServiceError


SAMPLE_MARKDOWN = """# Sample Study

| Field | Value |
| --- | --- |
| Objective | Test export behavior |
| Finding | Tables remain readable |

- First implication
- Second implication
"""


def test_markdown_export_saves_named_file(tmp_path: Path):
    service = ExportService(output_dir=tmp_path)

    exported = service.export(
        content=SAMPLE_MARKDOWN,
        task_type=TaskType.STUDY_TABLE,
        extension="md",
        created_on=date(2026, 5, 18),
    )

    assert exported.path.exists()
    assert exported.filename == "sample-study_2026-05-18_study_table.md"
    assert exported.path.read_text(encoding="utf-8").startswith("# Sample Study")


def test_export_all_returns_supported_formats(tmp_path: Path):
    service = ExportService(output_dir=tmp_path)

    try:
        exported = service.export_all(
            content=SAMPLE_MARKDOWN,
            task_type="full_report",
            created_on=date(2026, 5, 18),
        )
    except ExportServiceError as exc:
        if "Missing dependency" in str(exc):
            pytest.skip(str(exc))
        raise

    assert set(exported) == {"md", "docx", "pdf"}
    assert all(file.path.exists() for file in exported.values())
    assert exported["docx"].mime_type.endswith("wordprocessingml.document")
    assert exported["pdf"].mime_type == "application/pdf"


def test_export_rejects_empty_content(tmp_path: Path):
    service = ExportService(output_dir=tmp_path)

    with pytest.raises(ExportServiceError):
        service.export(content=" ", task_type="summary", extension="md")
