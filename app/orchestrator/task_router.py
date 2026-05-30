from __future__ import annotations

from dataclasses import dataclass
import re

from app.orchestrator.task_schema import TaskInput, TaskType


class UnsupportedTaskTypeError(ValueError):
    """Raised when a task has no configured pipeline."""


@dataclass(frozen=True)
class RouteConfig:
    """Pipeline route configuration for a task type."""

    task_type: TaskType
    pipeline_name: str
    writer_mode: str | None = None
    include_critic: bool | None = None
    reason: str | None = None


class TaskRouter:
    """Deterministic router from explicit task types or chat intent to pipelines."""

    _ROUTES: dict[TaskType, RouteConfig] = {
        TaskType.STUDY_TABLE: RouteConfig(
            task_type=TaskType.STUDY_TABLE,
            pipeline_name="study_table",
        ),
        TaskType.STUDY_TABLE_WITH_GAPS: RouteConfig(
            task_type=TaskType.STUDY_TABLE_WITH_GAPS,
            pipeline_name="study_table_with_gaps",
        ),
        TaskType.PAPER_SUMMARY: RouteConfig(
            task_type=TaskType.PAPER_SUMMARY,
            pipeline_name="paper_summary",
        ),
        TaskType.FULL_REPORT: RouteConfig(
            task_type=TaskType.FULL_REPORT,
            pipeline_name="full_report",
        ),
    }

    _TABLE_TERMS = (
        "table",
        "tabulate",
        "matrix",
        "spreadsheet",
        "compare",
        "comparison",
        "extract fields",
        "study characteristics",
    )
    _SUMMARY_TERMS = (
        "summary",
        "summarize",
        "overview",
        "abstract",
        "brief",
        "explain",
        "what is this about",
        "tldr",
        "tl;dr",
    )
    _CRITIQUE_TERMS = (
        "gap",
        "gaps",
        "limitation",
        "limitations",
        "weakness",
        "weaknesses",
        "critique",
        "criticize",
        "evaluate",
        "assess",
        "recommendation",
        "recommendations",
        "future work",
        "research direction",
    )
    _REPORT_TERMS = (
        "full report",
        "report",
        "comprehensive",
        "detailed",
        "rrl",
        "review of related literature",
        "literature review",
        "write-up",
    )

    def route(self, task: TaskType | TaskInput) -> RouteConfig:
        if isinstance(task, TaskInput):
            if task.task_type == TaskType.CHAT:
                return self.route_chat(task)
            task_type = task.task_type
        else:
            task_type = task

        route = self._ROUTES.get(task_type)
        if route is None:
            supported = ", ".join(sorted(t.value for t in self._ROUTES))
            raise UnsupportedTaskTypeError(
                f"Unsupported task_type '{task_type}'. Supported task types: {supported}"
            )
        return route

    def route_chat(self, task_input: TaskInput) -> RouteConfig:
        prompt = self._prompt_text(task_input)
        metadata = task_input.metadata
        attachment_count = self._attachment_count(metadata)
        has_attachment = attachment_count > 0 or bool(
            metadata.get("source_file") or metadata.get("source_path") or metadata.get("source_type")
        )

        wants_critique = self._contains_any(prompt, self._CRITIQUE_TERMS)
        wants_table = self._contains_any(prompt, self._TABLE_TERMS)
        wants_report = self._contains_any(prompt, self._REPORT_TERMS)
        wants_summary = self._contains_any(prompt, self._SUMMARY_TERMS)

        if wants_table and wants_critique:
            writer_mode = "gaps"
            include_critic = True
            reason = "chat prompt asks for tabular study details plus gaps or critique"
        elif wants_table:
            writer_mode = "study_table"
            include_critic = False
            reason = "chat prompt asks for a table or comparison"
        elif wants_critique:
            writer_mode = "gaps"
            include_critic = True
            reason = "chat prompt asks for gaps, limitations, critique, or recommendations"
        elif wants_report:
            writer_mode = "full_report"
            include_critic = True
            reason = "chat prompt asks for a report or literature-review style output"
        elif wants_summary:
            writer_mode = "summary"
            include_critic = False
            reason = "chat prompt asks for a summary or explanation"
        elif has_attachment:
            writer_mode = "summary"
            include_critic = False
            reason = "attachments are present but no critique/report intent was detected"
        else:
            writer_mode = "summary"
            include_critic = False
            reason = "default chat route"

        return RouteConfig(
            task_type=TaskType.CHAT,
            pipeline_name=f"chat_{writer_mode}{'_with_critic' if include_critic else ''}",
            writer_mode=writer_mode,
            include_critic=include_critic,
            reason=reason,
        )

    def _prompt_text(self, task_input: TaskInput) -> str:
        metadata_prompt = task_input.metadata.get("user_prompt")
        raw = task_input.user_prompt if task_input.user_prompt is not None else metadata_prompt
        return re.sub(r"\s+", " ", str(raw or "")).strip().lower()

    def _contains_any(self, prompt: str, terms: tuple[str, ...]) -> bool:
        return any(term in prompt for term in terms)

    def _attachment_count(self, metadata: dict) -> int:
        raw_count = metadata.get("attachment_count")
        if isinstance(raw_count, int):
            return raw_count
        attachments = metadata.get("attachments")
        if isinstance(attachments, list):
            return len(attachments)
        return 0
