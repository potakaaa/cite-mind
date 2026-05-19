from __future__ import annotations

import pytest

from app.agents.base_agent import AgentExecutionError
from app.agents.critic_agent import CriticAgent
from app.agents.research_reader_agent import ResearchReaderAgent
from app.agents.writer_agent import WriterAgent
from app.schemas.agent_output_schema import CritiqueSchema
from app.schemas.study_schema import StudySchema


class MockLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def generate(self, prompt: str, provider=None, task_type=None):
        self.calls.append({"prompt": prompt, "provider": provider, "task_type": task_type})
        if not self.responses:
            raise RuntimeError("No mocked LLM response left")
        return self.responses.pop(0)


STUDY_JSON = (
    '{"title":"Stable Study","authors":["A"],"year":2024,"abstract":null,'
    '"objective":"Test objective","methodology":null,"dataset_or_participants":null,'
    '"findings":["F1"],"conclusion":null,"limitations":[],"source_notes":[]}'
)

CRITIQUE_JSON = (
    '{"gaps":["G1"],"limitations":["L1"],"methodological_weaknesses":[],'
    '"recommendations":["R1"],"confidence_notes":"Mocked"}'
)


def test_research_reader_uses_mock_llm_and_never_external_provider():
    llm = MockLLM([STUDY_JSON])
    agent = ResearchReaderAgent(llm=llm, prompt_template="reader prompt")

    result = agent.run(paper_text="paper body", provider="mock", task_type="paper_summary")

    assert isinstance(result, StudySchema)
    assert result.title == "Stable Study"
    assert llm.calls[0]["provider"] == "mock"
    assert "paper body" in llm.calls[0]["prompt"]


def test_research_reader_merges_multiple_mocked_chunk_responses():
    llm = MockLLM([STUDY_JSON, STUDY_JSON, STUDY_JSON, STUDY_JSON.replace("Stable Study", "Merged Study")])
    agent = ResearchReaderAgent(llm=llm, chunk_size=8, chunk_overlap=0, prompt_template="reader prompt")

    result = agent.run(paper_text="alpha\n\nbeta\n\ngamma")

    assert result.title == "Merged Study"
    assert len(llm.calls) == 4
    assert "Merge multiple partial JSON" in llm.calls[-1]["prompt"]


def test_critic_and_writer_agents_parse_mocked_provider_responses():
    study = StudySchema.from_llm_json(STUDY_JSON)
    critic_llm = MockLLM([CRITIQUE_JSON])
    writer_llm = MockLLM(["# Stable report"])

    critique = CriticAgent(llm=critic_llm, prompt_template="critic prompt").run(study=study)
    report = WriterAgent(llm=writer_llm, prompt_template="writer prompt").run(
        study=study,
        critique=critique,
        mode="full_report",
    )

    assert isinstance(critique, CritiqueSchema)
    assert critique.gaps == ["G1"]
    assert "Extracted facts" in report
    assert "# Stable report" in report
    assert "Inferred analysis" in report
    assert "Study data (JSON)" in critic_llm.calls[0]["prompt"]
    assert "Critique data" in writer_llm.calls[0]["prompt"]


def test_agents_raise_execution_error_for_bad_mock_responses():
    with pytest.raises(AgentExecutionError, match="invalid study JSON"):
        ResearchReaderAgent(llm=MockLLM(["not json"]), prompt_template="reader").run(paper_text="text")

    with pytest.raises(AgentExecutionError, match="empty response"):
        WriterAgent(llm=MockLLM(["   "]), prompt_template="writer").run(
            study=StudySchema(title="T"),
            mode="summary",
        )
