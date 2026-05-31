from __future__ import annotations

import pytest

from app.orchestrator.orchestrator import Orchestrator, PipelineValidationError
from app.orchestrator.task_schema import TaskInput, TaskType
from app.schemas.agent_output_schema import CritiqueSchema
from app.schemas.study_schema import StudySchema


class RecordingAgent:
    def __init__(self, name: str, output, calls: list[str]) -> None:
        self.name = name
        self.output = output
        self.calls = calls
        self.kwargs: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(self.name)
        self.kwargs.append(kwargs)
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


def build_recording_orchestrator():
    calls: list[str] = []
    research = RecordingAgent("research_reader_agent", StudySchema(title="Study", findings=["F"]), calls)
    critic = RecordingAgent("critic_agent", CritiqueSchema(gaps=["G"], recommendations=["R"]), calls)
    writer = RecordingAgent("writer_agent", "final markdown", calls)
    return Orchestrator(research_reader=research, critic=critic, writer=writer), calls, research, critic, writer


@pytest.mark.parametrize(
    "task_type,expected_order,expected_mode",
    [
        (TaskType.STUDY_TABLE, ["research_reader_agent", "writer_agent"], "study_table"),
        (TaskType.PAPER_SUMMARY, ["research_reader_agent", "writer_agent"], "summary"),
        (
            TaskType.STUDY_TABLE_WITH_GAPS,
            ["research_reader_agent", "critic_agent", "writer_agent"],
            "gaps",
        ),
        (TaskType.FULL_REPORT, ["research_reader_agent", "critic_agent", "writer_agent"], "full_report"),
    ],
)
def test_orchestrator_workflows_confirm_expected_agent_order(task_type, expected_order, expected_mode):
    orchestrator, calls, research, critic, writer = build_recording_orchestrator()

    result = orchestrator.run(TaskInput(task_type=task_type, paper_text="paper", provider="mock"))

    assert calls == expected_order
    assert [step.step_name for step in result.steps] == [
        name.replace("_agent", "") for name in expected_order
    ]
    assert all(step.status == "ok" for step in result.steps)
    assert writer.kwargs[0]["mode"] == expected_mode
    assert writer.kwargs[0]["study"].title == "Study"
    assert research.kwargs[0]["provider"] == "mock"
    assert result.final_output == "final markdown"
    assert ("critique" in result.intermediate) == ("critic_agent" in expected_order)
    if "critic_agent" not in expected_order:
        assert critic.kwargs == []


def test_orchestrator_stops_before_writer_when_middle_agent_fails():
    calls: list[str] = []
    orchestrator = Orchestrator(
        research_reader=RecordingAgent("research_reader_agent", StudySchema(title="Study"), calls),
        critic=RecordingAgent("critic_agent", ValueError("bad critique"), calls),
        writer=RecordingAgent("writer_agent", "should not run", calls),
    )

    with pytest.raises(PipelineValidationError, match="critic"):
        orchestrator.run(TaskInput(task_type=TaskType.FULL_REPORT, paper_text="paper"))

    assert calls == ["research_reader_agent", "critic_agent"]


def test_chat_workflow_routes_attachment_summary_without_critic():
    orchestrator, calls, research, critic, writer = build_recording_orchestrator()

    result = orchestrator.run(
        TaskInput(
            task_type=TaskType.CHAT,
            user_prompt="can you explain this attachment?",
            paper_text="paper",
            provider="mock",
            metadata={"attachment_count": 1},
        )
    )

    assert calls == ["research_reader_agent", "writer_agent"]
    assert writer.kwargs[0]["mode"] == "summary"
    assert writer.kwargs[0]["user_prompt"] == "can you explain this attachment?"
    assert critic.kwargs == []
    assert result.intermediate["pipeline"] == "chat_summary"
