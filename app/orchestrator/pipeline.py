from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.orchestrator.task_schema import TaskType


@dataclass(frozen=True)
class PipelineStep:
    """One fixed pipeline step."""

    name: str
    agent_key: str
    input_builder: Callable[[dict], dict]
    output_key: str


@dataclass(frozen=True)
class PipelineDefinition:
    """Ordered steps and writer mode for a task pipeline."""

    name: str
    task_type: TaskType
    writer_mode: str
    steps: tuple[PipelineStep, ...]


def _build_research_input(ctx: dict) -> dict:
    return {"paper_text": ctx["paper_text"]}


def _build_critic_input(ctx: dict) -> dict:
    return {"study": ctx["study"]}


def _build_writer_input(ctx: dict) -> dict:
    return {
        "mode": ctx["writer_mode"],
        "study": ctx["study"],
        "critique": ctx.get("critique"),
    }


def get_pipeline_map() -> dict[str, PipelineDefinition]:
    """Return all fixed MVP pipelines."""

    research = PipelineStep(
        name="research_reader",
        agent_key="research_reader",
        input_builder=_build_research_input,
        output_key="study",
    )
    critic = PipelineStep(
        name="critic",
        agent_key="critic",
        input_builder=_build_critic_input,
        output_key="critique",
    )
    writer = PipelineStep(
        name="writer",
        agent_key="writer",
        input_builder=_build_writer_input,
        output_key="final_output",
    )

    return {
        "study_table": PipelineDefinition(
            name="study_table",
            task_type=TaskType.STUDY_TABLE,
            writer_mode="study_table",
            steps=(research, writer),
        ),
        "study_table_with_gaps": PipelineDefinition(
            name="study_table_with_gaps",
            task_type=TaskType.STUDY_TABLE_WITH_GAPS,
            writer_mode="gaps",
            steps=(research, critic, writer),
        ),
        "paper_summary": PipelineDefinition(
            name="paper_summary",
            task_type=TaskType.PAPER_SUMMARY,
            writer_mode="summary",
            steps=(research, writer),
        ),
        "full_report": PipelineDefinition(
            name="full_report",
            task_type=TaskType.FULL_REPORT,
            writer_mode="full_report",
            steps=(research, critic, writer),
        ),
    }
