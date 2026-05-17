from __future__ import annotations

from dataclasses import dataclass

from app.orchestrator.task_schema import TaskType


class UnsupportedTaskTypeError(ValueError):
    """Raised when a task has no configured pipeline."""


@dataclass(frozen=True)
class RouteConfig:
    """Pipeline route configuration for a task type."""

    task_type: TaskType
    pipeline_name: str


class TaskRouter:
    """Simple deterministic router from task type to pipeline."""

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

    def route(self, task_type: TaskType) -> RouteConfig:
        route = self._ROUTES.get(task_type)
        if route is None:
            supported = ", ".join(sorted(t.value for t in self._ROUTES))
            raise UnsupportedTaskTypeError(
                f"Unsupported task_type '{task_type}'. Supported task types: {supported}"
            )
        return route
