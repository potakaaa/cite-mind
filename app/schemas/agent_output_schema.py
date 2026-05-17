from __future__ import annotations

from pydantic import Field

from .study_schema import BaseLLMSchema, StudySchema


class CritiqueSchema(BaseLLMSchema):
    gaps: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    methodological_weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence_notes: str | None = Field(default=None)


class AgentOutputSchema(BaseLLMSchema):
    study: StudySchema
    critique: CritiqueSchema | None = Field(default=None)
