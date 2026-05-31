"""Centralized logging helpers for Cite Mind."""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from config import settings


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


@dataclass(frozen=True)
class ActivityLogEntry:
    """One human-readable workflow activity event."""

    timestamp: str
    actor: str
    action: str
    status: str = "info"
    detail: str | None = None

    def model_dump(self) -> dict[str, Any]:
        """Return a serializable shape that mirrors pydantic models used elsewhere."""
        return asdict(self)


class WorkflowActivityLogger:
    """Records user-facing workflow progress while also writing to app logs."""

    _ACTOR_LABELS = {
        "orchestrator": "Orchestrator",
        "research_reader": "Researcher",
        "research_reader_agent": "Researcher",
        "critic": "Critic",
        "critic_agent": "Critic",
        "writer": "Writer",
        "writer_agent": "Writer",
    }
    _START_ACTIONS = {
        "orchestrator": "is selecting the pipeline and coordinating the agents",
        "research_reader": "is reading the paper and extracting structured study details",
        "research_reader_agent": "is reading the paper and extracting structured study details",
        "critic": "is reviewing the extracted study for gaps and limitations",
        "critic_agent": "is reviewing the extracted study for gaps and limitations",
        "writer": "is drafting the final output",
        "writer_agent": "is drafting the final output",
    }
    _FINISH_ACTIONS = {
        "orchestrator": "wrapped the agent outputs into the final workflow result",
        "research_reader": "finished extracting study details",
        "research_reader_agent": "finished extracting study details",
        "critic": "finished reviewing gaps and limitations",
        "critic_agent": "finished reviewing gaps and limitations",
        "writer": "finished drafting the final output",
        "writer_agent": "finished drafting the final output",
    }

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        on_entry: Callable[[ActivityLogEntry], None] | None = None,
    ) -> None:
        self.logger = logger or get_logger("app.workflow.activity")
        self.on_entry = on_entry
        self.entries: list[ActivityLogEntry] = []

    def record(
        self,
        actor: str,
        action: str,
        *,
        status: str = "info",
        detail: str | None = None,
    ) -> ActivityLogEntry:
        entry = ActivityLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            actor=actor,
            action=action,
            status=status,
            detail=detail,
        )
        self.entries.append(entry)

        message = "%s %s"
        if detail:
            message += " (%s)"
            self.logger.info(message, actor, action, detail)
        else:
            self.logger.info(message, actor, action)

        if self.on_entry is not None:
            self.on_entry(entry)
        return entry

    def agent_started(self, agent_name: str, *, step_name: str, pipeline_name: str) -> None:
        self.record(
            self._actor_for(agent_name),
            self._START_ACTIONS.get(agent_name, f"is running step '{step_name}'"),
            status="running",
            detail=f"pipeline={pipeline_name}, step={step_name}",
        )

    def agent_finished(
        self,
        agent_name: str,
        *,
        step_name: str,
        pipeline_name: str,
        duration_ms: int,
    ) -> None:
        self.record(
            self._actor_for(agent_name),
            self._FINISH_ACTIONS.get(agent_name, f"finished step '{step_name}'"),
            status="ok",
            detail=f"pipeline={pipeline_name}, step={step_name}, duration_ms={duration_ms}",
        )

    def agent_failed(
        self,
        agent_name: str,
        *,
        step_name: str,
        pipeline_name: str,
        error: Exception,
    ) -> None:
        self.record(
            self._actor_for(agent_name),
            f"failed while running step '{step_name}'",
            status="failed",
            detail=f"pipeline={pipeline_name}, error={error}",
        )

    def workflow_started(self, *, pipeline_name: str, task_type: str) -> None:
        self.record(
            self._actor_for("orchestrator"),
            self._START_ACTIONS["orchestrator"],
            status="running",
            detail=f"pipeline={pipeline_name}, task_type={task_type}",
        )

    def workflow_finished(self, *, pipeline_name: str, duration_ms: int) -> None:
        self.record(
            self._actor_for("orchestrator"),
            self._FINISH_ACTIONS["orchestrator"],
            status="ok",
            detail=f"pipeline={pipeline_name}, duration_ms={duration_ms}",
        )

    def dumps(self) -> list[dict[str, Any]]:
        return [entry.model_dump() for entry in self.entries]

    def _actor_for(self, agent_name: str) -> str:
        return self._ACTOR_LABELS.get(agent_name, agent_name.replace("_", " ").title())


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once for CLI, Streamlit, and tests."""
    selected_level = (level or settings.log_level).upper()
    numeric_level = getattr(logging, selected_level, logging.INFO)

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)

    root.setLevel(numeric_level)
    for handler in root.handlers:
        handler.setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """Return an app logger after ensuring logging is configured."""
    configure_logging()
    return logging.getLogger(name)


def log_failure(
    logger: logging.Logger,
    stage: str,
    exc: Exception,
    **context: Any,
) -> None:
    """Log a stage failure with compact structured context."""
    context_text = " ".join(f"{key}={value!r}" for key, value in context.items() if value is not None)
    if context_text:
        logger.exception("%s failed: %s (%s)", stage, exc, context_text)
    else:
        logger.exception("%s failed: %s", stage, exc)
