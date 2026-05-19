"""Service layer for executing research workflows via orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.orchestrator.orchestrator import Orchestrator, PipelineValidationError
from app.orchestrator.task_schema import TaskInput, TaskType
from app.services.document_service import DocumentService, DocumentServiceError
from app.utils.logging import get_logger, log_failure


class ResearchServiceError(RuntimeError):
    """Raised when research workflow execution fails."""


class ResearchService:
    """Coordinates document intake and orchestrator execution for UI/CLI callers."""

    MIN_RESEARCH_TEXT_CHARS = 80

    def __init__(
        self,
        document_service: DocumentService | None = None,
        orchestrator: Orchestrator | None = None,
    ) -> None:
        self.document_service = document_service or DocumentService()
        self.orchestrator = orchestrator or Orchestrator()
        self.logger = get_logger("app.services.research")

    def run(
        self,
        *,
        task_type: TaskType | str,
        raw_text: str | None = None,
        pdf_path: str | Path | None = None,
        pdf_bytes: bytes | None = None,
        pdf_filename: str | None = None,
        provider: str | None = None,
        metadata: dict[str, Any] | None = None,
        include_metadata: bool = False,
    ) -> str | dict[str, Any]:
        try:
            normalized_task = task_type if isinstance(task_type, TaskType) else TaskType(task_type)
        except ValueError as exc:
            log_failure(self.logger, "task_validation", exc, task_type=task_type)
            raise ResearchServiceError(f"Unsupported task_type '{task_type}'.") from exc

        try:
            document = self.document_service.prepare_document(
                raw_text=raw_text,
                pdf_path=pdf_path,
                pdf_bytes=pdf_bytes,
                pdf_filename=pdf_filename,
            )
        except DocumentServiceError as exc:
            log_failure(self.logger, "document_processing", exc, task_type=normalized_task)
            raise ResearchServiceError(f"Document processing failed: {exc}") from exc

        paper_text = str(document.get("paper_text", "")).strip()
        if len(paper_text) < self.MIN_RESEARCH_TEXT_CHARS:
            message = (
                "The input is too short for a reliable research workflow. "
                f"Please provide at least {self.MIN_RESEARCH_TEXT_CHARS} characters of paper text."
            )
            self.logger.warning(
                "input_validation failed: text too short (chars=%s, task_type=%s)",
                len(paper_text),
                normalized_task.value,
            )
            raise ResearchServiceError(message)

        payload = TaskInput(
            task_type=normalized_task,
            paper_text=paper_text,
            provider=provider,
            metadata={
                **(metadata or {}),
                "source_type": document.get("source_type"),
                "source_file": document.get("source_file"),
                "source_path": document.get("source_path"),
                "chunk_count": document.get("chunk_count"),
                "page_count": document.get("page_count"),
                "extracted_text_path": document.get("extracted_text_path"),
            },
        )

        try:
            result = self.orchestrator.run(payload)
        except (PipelineValidationError, ValueError, TypeError) as exc:
            log_failure(self.logger, "research_workflow", exc, task_type=normalized_task, provider=provider)
            raise ResearchServiceError(f"Research workflow failed: {exc}") from exc

        if not include_metadata:
            return result.final_output

        return {
            "final_output": result.final_output,
            "metadata": {
                "task_type": result.task_type.value,
                "steps": [step.model_dump() for step in result.steps],
                "intermediate": result.intermediate,
                "document": {
                    "source_type": document.get("source_type"),
                    "source_file": document.get("source_file"),
                    "source_path": document.get("source_path"),
                    "chunk_count": document.get("chunk_count"),
                    "page_count": document.get("page_count"),
                    "extracted_text_path": document.get("extracted_text_path"),
                },
            },
        }
