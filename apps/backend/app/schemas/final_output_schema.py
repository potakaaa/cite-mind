from __future__ import annotations

from pydantic import Field

from .agent_output_schema import CritiqueSchema
from .study_schema import BaseLLMSchema, StudySchema


class FinalOutputSchema(BaseLLMSchema):
    summary: str = Field(..., min_length=1)
    study: StudySchema
    critique: CritiqueSchema | None = Field(default=None)
    key_findings: list[str] = Field(default_factory=list)
    actionable_recommendations: list[str] = Field(default_factory=list)
    confidence: str | None = Field(default=None)
    disclaimer: str | None = Field(default=None)
