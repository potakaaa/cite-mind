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

    @staticmethod
    def _extract_json_candidate(payload: str) -> str | None:
        """Extract a likely JSON object/array from mixed LLM output text."""
        text = payload.strip()
        if not text:
            return None

        # Prefer fenced code blocks if present.
        if "```" in text:
            segments = text.split("```")
            for segment in segments:
                candidate = segment.strip()
                if not candidate:
                    continue
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("{") or candidate.startswith("["):
                    return candidate

        # Fallback: find the first balanced JSON object/array in the text.
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            if start == -1:
                continue

            depth = 0
            in_string = False
            escape = False
            for idx in range(start, len(text)):
                ch = text[idx]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_string = False
                    continue

                if ch == '"':
                    in_string = True
                    continue
                if ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        return text[start : idx + 1]

        return None

    @classmethod
    def from_llm_json(cls, payload: str) -> "BaseLLMSchema":
        """
        Parse and validate a JSON string from an LLM response.

        Raises:
            SchemaValidationError: If JSON is malformed or fails schema validation.
        """
        raw: Any
        parse_errors: list[str] = []
        candidate_texts = [payload]

        extracted = cls._extract_json_candidate(payload)
        if extracted and extracted != payload:
            candidate_texts.append(extracted)

        for candidate in candidate_texts:
            try:
                raw = json.loads(candidate)
                break
            except JSONDecodeError as exc:
                parse_errors.append(f"{exc.msg} (line {exc.lineno}, column {exc.colno})")
        else:
            raise SchemaValidationError(
                "Invalid JSON response. Parse attempts failed: "
                + " | ".join(parse_errors)
            )

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
