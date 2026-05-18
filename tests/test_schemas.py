from __future__ import annotations

import pytest

from app.schemas.agent_output_schema import AgentOutputSchema, CritiqueSchema
from app.schemas.final_output_schema import FinalOutputSchema
from app.schemas.study_schema import SchemaValidationError, StudySchema


def test_study_schema_extracts_fenced_json_and_coerces_llm_values():
    payload = """
    Here is the extraction:
    ```json
    {
      "title": ["A", "Study"],
      "authors": "Ada Lovelace",
      "year": "Published in 2024",
      "findings": "Finding one",
      "limitations": null,
      "source_notes": [" page 1 "]
    }
    ```
    """

    study = StudySchema.from_llm_json(payload)

    assert study.title == "A Study"
    assert study.authors == ["Ada Lovelace"]
    assert study.year == 2024
    assert study.findings == ["Finding one"]
    assert study.limitations == []
    assert study.source_notes == ["page 1"]


def test_schema_validation_rejects_extra_fields_and_invalid_json():
    with pytest.raises(SchemaValidationError, match="Invalid JSON"):
        StudySchema.from_llm_json("not json")

    with pytest.raises(SchemaValidationError, match="extra_forbidden"):
        StudySchema.from_llm_data({"title": "T", "unsupported": "value"})


def test_nested_agent_and_final_output_schemas_validate_required_shapes():
    agent_output = AgentOutputSchema.from_llm_data(
        {
            "study": {"title": "T", "authors": ["A"], "findings": ["F"]},
            "critique": {"gaps": ["G"], "recommendations": ["R"]},
        }
    )
    final_output = FinalOutputSchema.from_llm_data(
        {
            "summary": "Concise summary",
            "study": agent_output.study.model_dump(),
            "critique": agent_output.critique.model_dump(),
            "key_findings": ["F"],
        }
    )

    assert isinstance(agent_output.critique, CritiqueSchema)
    assert final_output.study.title == "T"
    assert final_output.key_findings == ["F"]

    with pytest.raises(SchemaValidationError, match="summary"):
        FinalOutputSchema.from_llm_data({"summary": "", "study": {"title": "T"}})
