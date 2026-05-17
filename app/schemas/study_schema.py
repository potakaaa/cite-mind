from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SchemaValidationError(ValueError):
    """Raised when a JSON payload cannot be decoded or validated against a schema."""


class BaseLLMSchema(BaseModel):
    """Base schema with helper parsers for LLM JSON output."""

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_llm_json(cls, payload: str) -> "BaseLLMSchema":
        """
        Parse and validate a JSON string from an LLM response.

        Raises:
            SchemaValidationError: If JSON is malformed or fails schema validation.
        """
        try:
            raw = json.loads(payload)
        except JSONDecodeError as exc:
            raise SchemaValidationError(f"Invalid JSON response: {exc.msg} (line {exc.lineno}, column {exc.colno})") from exc

        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            raise SchemaValidationError(f"Schema validation failed for {cls.__name__}: {exc}") from exc

    @classmethod
    def from_llm_data(cls, payload: Any) -> "BaseLLMSchema":
        """
        Validate pre-parsed LLM payloads (dict/list) against a schema.

        Raises:
            SchemaValidationError: If payload type/content does not match schema.
        """
        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise SchemaValidationError(f"Schema validation failed for {cls.__name__}: {exc}") from exc


class StudySchema(BaseLLMSchema):
    title: str | None = Field(default=None)
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=0)
    abstract: str | None = Field(default=None)
    objective: str | None = Field(default=None)
    methodology: str | None = Field(default=None)
    dataset_or_participants: str | None = Field(default=None)
    findings: list[str] = Field(default_factory=list)
    conclusion: str | None = Field(default=None)
    limitations: list[str] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
