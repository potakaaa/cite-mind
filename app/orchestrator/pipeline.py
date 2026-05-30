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
    task_type: TaskType | None
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
        "user_prompt": ctx.get("user_prompt"),
    }


def _common_steps() -> tuple[PipelineStep, PipelineStep, PipelineStep]:
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

    return research, critic, writer


def build_pipeline(
    *,
    name: str,
    writer_mode: str,
    include_critic: bool,
    task_type: TaskType | None = None,
) -> PipelineDefinition:
    """Build a pipeline from selected capabilities."""

    research, critic, writer = _common_steps()
    steps = (research, critic, writer) if include_critic else (research, writer)
    return PipelineDefinition(
        name=name,
        task_type=task_type,
        writer_mode=writer_mode,
        steps=steps,
    )


def get_pipeline_map() -> dict[str, PipelineDefinition]:
    """Return all fixed MVP pipelines."""

    return {
        "study_table": build_pipeline(
            name="study_table",
            task_type=TaskType.STUDY_TABLE,
            writer_mode="study_table",
            include_critic=False,
        ),
        "study_table_with_gaps": build_pipeline(
            name="study_table_with_gaps",
            task_type=TaskType.STUDY_TABLE_WITH_GAPS,
            writer_mode="gaps",
            include_critic=True,
        ),
        "paper_summary": build_pipeline(
            name="paper_summary",
            task_type=TaskType.PAPER_SUMMARY,
            writer_mode="summary",
            include_critic=False,
        ),
        "full_report": build_pipeline(
            name="full_report",
            task_type=TaskType.FULL_REPORT,
            writer_mode="full_report",
            include_critic=True,
        ),
    }
