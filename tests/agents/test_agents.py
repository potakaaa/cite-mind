from __future__ import annotations

import pytest

from app.agents.base_agent import AgentExecutionError
from app.agents.critic_agent import CriticAgent
from app.agents.research_reader_agent import ResearchReaderAgent
from app.agents.writer_agent import WriterAgent
from app.schemas.agent_output_schema import CritiqueSchema
from app.schemas.study_schema import StudySchema


class DummyLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def generate(self, prompt: str, provider=None, task_type=None):
        self.calls.append({"prompt": prompt, "provider": provider, "task_type": task_type})
        if not self.responses:
            raise RuntimeError("No mock response configured")
        return self.responses.pop(0)


def test_research_reader_single_chunk_returns_study_schema():
    llm = DummyLLM([
        '{"title":"T","authors":["A"],"year":2025,"abstract":null,"objective":null,'
        '"methodology":null,"dataset_or_participants":null,"findings":["F1"],"conclusion":null,'
        '"limitations":[],"source_notes":[]}'
    ])
    agent = ResearchReaderAgent(llm=llm, chunk_size=5000)

    result = agent.run(paper_text="short paper", provider="x", task_type="study_table")

    assert isinstance(result, StudySchema)
    assert result.title == "T"
    assert result.findings == ["F1"]
    assert len(llm.calls) == 1


def test_research_reader_multi_chunk_runs_merge_phase():
    partial = '{"title":"T","authors":[],"year":null,"abstract":null,"objective":null,' \
              '"methodology":null,"dataset_or_participants":null,"findings":["F"],"conclusion":null,' \
              '"limitations":[],"source_notes":[]}'
    merged = '{"title":"Merged","authors":[],"year":null,"abstract":null,"objective":null,' \
             '"methodology":null,"dataset_or_participants":null,"findings":["MF"],"conclusion":null,' \
             '"limitations":[],"source_notes":[]}'

    llm = DummyLLM([partial, partial, partial, merged])
    agent = ResearchReaderAgent(llm=llm, chunk_size=10, chunk_overlap=0)

    result = agent.run(paper_text="A" * 30)

    assert result.title == "Merged"
    assert len(llm.calls) == 4


def test_critic_agent_validates_and_returns_critique_schema():
    llm = DummyLLM([
        '{"gaps":["g1"],"limitations":["l1"],"methodological_weaknesses":[],"recommendations":["r1"],"confidence_notes":"c"}'
    ])
    agent = CriticAgent(llm=llm)
    study = StudySchema(title="T", authors=[], findings=[])

    result = agent.run(study=study)

    assert isinstance(result, CritiqueSchema)
    assert result.gaps == ["g1"]
    assert "Study data (JSON)" in llm.calls[0]["prompt"]


def test_writer_agent_requires_valid_mode_and_returns_text():
    llm = DummyLLM(["# Output"])
    agent = WriterAgent(llm=llm)
    study = StudySchema(title="T", authors=[], findings=[])

    result = agent.run(study=study, mode="summary")
    assert result == "# Output"

    with pytest.raises(AgentExecutionError):
        agent.run(study=study, mode="unknown_mode")


def test_writer_agent_raises_on_empty_response():
    llm = DummyLLM(["   "])
    agent = WriterAgent(llm=llm)
    study = StudySchema(title="T", authors=[], findings=[])

    with pytest.raises(AgentExecutionError):
        agent.run(study=study, mode="full_report")
