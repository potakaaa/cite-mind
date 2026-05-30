from __future__ import annotations

import pytest

from app.orchestrator.orchestrator import Orchestrator, PipelineValidationError
from app.orchestrator.task_schema import TaskInput, TaskType
from app.utils.logging import WorkflowActivityLogger


class StubResearch:
    name = "research_reader_agent"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        from app.schemas.study_schema import StudySchema

        return StudySchema(title="Study", authors=["A"], findings=["F"])


class StubCritic:
    name = "critic_agent"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        from app.schemas.agent_output_schema import CritiqueSchema

        return CritiqueSchema(gaps=["gap 1"], recommendations=["rec 1"])


class StubWriter:
    name = "writer_agent"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        mode = kwargs["mode"]
        has_critique = kwargs.get("critique") is not None
        return f"mode={mode};critique={has_critique}"


class FailingCritic(StubCritic):
    def run(self, **kwargs):
        raise ValueError("invalid critique payload")


def build_orchestrator(research=None, critic=None, writer=None) -> Orchestrator:
    return Orchestrator(
        research_reader=research or StubResearch(),
        critic=critic or StubCritic(),
        writer=writer or StubWriter(),
    )


@pytest.mark.parametrize(
    "task_type,expected_steps,expected_mode,expects_critique",
    [
        (TaskType.STUDY_TABLE, ["research_reader", "writer"], "study_table", False),
        (TaskType.STUDY_TABLE_WITH_GAPS, ["research_reader", "critic", "writer"], "gaps", True),
        (TaskType.PAPER_SUMMARY, ["research_reader", "writer"], "summary", False),
        (TaskType.FULL_REPORT, ["research_reader", "critic", "writer"], "full_report", True),
    ],
)
def test_orchestrator_runs_fixed_pipeline(task_type, expected_steps, expected_mode, expects_critique):
    research = StubResearch()
    critic = StubCritic()
    writer = StubWriter()
    orchestrator = build_orchestrator(research=research, critic=critic, writer=writer)

    result = orchestrator.run(
        TaskInput(task_type=task_type, paper_text="sample paper", provider="dummy")
    )

    assert [s.step_name for s in result.steps] == expected_steps
    assert all(s.status == "ok" for s in result.steps)
    assert result.final_output == f"mode={expected_mode};critique={expects_critique}"
    assert writer.calls[0]["mode"] == expected_mode
    assert writer.calls[0]["study"].title == "Study"

    if expects_critique:
        assert "critique" in result.intermediate
        assert writer.calls[0]["critique"].gaps == ["gap 1"]
        assert len(critic.calls) == 1
    else:
        assert "critique" not in result.intermediate
        assert writer.calls[0]["critique"] is None
        assert len(critic.calls) == 0


def test_orchestrator_stops_pipeline_on_validation_error():
    research = StubResearch()
    critic = FailingCritic()
    writer = StubWriter()
    orchestrator = build_orchestrator(research=research, critic=critic, writer=writer)

    with pytest.raises(PipelineValidationError) as exc:
        orchestrator.run(TaskInput(task_type=TaskType.FULL_REPORT, paper_text="sample paper"))

    assert "stopped at step 'critic'" in str(exc.value)
    assert len(research.calls) == 1
    assert len(writer.calls) == 0


def test_orchestrator_records_human_readable_activity_log():
    activity_logger = WorkflowActivityLogger()
    orchestrator = build_orchestrator()
    orchestrator.activity_logger = activity_logger

    result = orchestrator.run(TaskInput(task_type=TaskType.FULL_REPORT, paper_text="sample paper"))

    assert result.final_output == "mode=full_report;critique=True"
    entries = activity_logger.dumps()
    agent_entries = [entry for entry in entries if entry["actor"] != "Orchestrator"]
    assert [entry["actor"] for entry in agent_entries] == [
        "Researcher",
        "Researcher",
        "Critic",
        "Critic",
        "Writer",
        "Writer",
    ]
    assert entries[0]["actor"] == "Orchestrator"
    assert agent_entries[0]["status"] == "running"
    assert "is reading the paper" in agent_entries[0]["action"]
    assert agent_entries[-1]["status"] == "ok"
    assert "duration_ms=" in agent_entries[-1]["detail"]


def test_orchestrator_records_failed_activity_log_entry():
    activity_logger = WorkflowActivityLogger()
    research = StubResearch()
    critic = FailingCritic()
    writer = StubWriter()
    orchestrator = build_orchestrator(research=research, critic=critic, writer=writer)
    orchestrator.activity_logger = activity_logger

    with pytest.raises(PipelineValidationError):
        orchestrator.run(TaskInput(task_type=TaskType.FULL_REPORT, paper_text="sample paper"))

    failed_entries = [entry for entry in activity_logger.dumps() if entry["status"] == "failed"]
    assert len(failed_entries) == 1
    assert failed_entries[0]["actor"] == "Critic"
    assert "invalid critique payload" in failed_entries[0]["detail"]


def test_unsupported_task_type_returns_clear_error():
    orchestrator = build_orchestrator()

    with pytest.raises(ValueError) as exc:
        orchestrator.run({"task_type": "not_supported", "paper_text": "text"})

    assert "task_type" in str(exc.value)


def test_debug_metadata_contains_pipeline_info_and_study_dump():
    orchestrator = build_orchestrator()

    result = orchestrator.run(
        TaskInput(task_type=TaskType.STUDY_TABLE, paper_text="sample", metadata={"trace_id": "123"})
    )

    assert result.intermediate["pipeline"] == "study_table"
    assert result.intermediate["writer_mode"] == "study_table"
    assert result.intermediate["input_metadata"] == {"trace_id": "123"}
    assert result.intermediate["study"]["title"] == "Study"
    assert result.steps[0].duration_ms >= 0


@pytest.mark.parametrize(
    "prompt,expected_steps,expected_mode,expects_critique",
    [
        ("make a study table from this attachment", ["research_reader", "writer"], "study_table", False),
        ("summarize this paper", ["research_reader", "writer"], "summary", False),
        ("identify gaps and recommendations", ["research_reader", "critic", "writer"], "gaps", True),
        ("write a full report", ["research_reader", "critic", "writer"], "full_report", True),
    ],
)
def test_chat_task_infers_pipeline_from_prompt(
    prompt,
    expected_steps,
    expected_mode,
    expects_critique,
):
    writer = StubWriter()
    orchestrator = build_orchestrator(writer=writer)

    result = orchestrator.run(
        TaskInput(
            task_type=TaskType.CHAT,
            user_prompt=prompt,
            paper_text="sample paper",
            metadata={"attachment_count": 1},
        )
    )

    assert [s.step_name for s in result.steps] == expected_steps
    assert result.final_output == f"mode={expected_mode};critique={expects_critique}"
    assert writer.calls[0]["user_prompt"] == prompt
    assert result.intermediate["writer_mode"] == expected_mode
    assert result.intermediate["route_reason"]
