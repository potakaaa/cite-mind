from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskType(str, Enum):
    """Supported orchestrator task types for the MVP."""

    STUDY_TABLE = "study_table"
    STUDY_TABLE_WITH_GAPS = "study_table_with_gaps"
    PAPER_SUMMARY = "paper_summary"
    FULL_REPORT = "full_report"


class TaskInput(BaseModel):
    """Normalized input accepted by the orchestrator."""

    model_config = ConfigDict(extra="forbid")

    task_type: TaskType
    paper_text: str = Field(..., min_length=1)
    provider: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StepMeta(BaseModel):
    """Debug metadata for one pipeline step."""

    model_config = ConfigDict(extra="forbid")

    step_name: str
    agent: str
    status: str
    duration_ms: int
    output_keys: list[str] = Field(default_factory=list)
    error: str | None = None


class TaskResult(BaseModel):
    """Final orchestrator output with intermediate debug information."""

    model_config = ConfigDict(extra="forbid")

    task_type: TaskType
    final_output: str
    intermediate: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepMeta] = Field(default_factory=list)
