from __future__ import annotations

import ast
import json
from json import JSONDecodeError
import re
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from app.utils.logging import get_logger, log_failure


class SchemaValidationError(ValueError):
    """Raised when a JSON payload cannot be decoded or validated against a schema."""


class BaseLLMSchema(BaseModel):
    """Base schema with helper parsers for LLM JSON output."""

    model_config = ConfigDict(extra="forbid")
    _logger: ClassVar = get_logger("app.schemas.llm")

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

    @staticmethod
    def _cleanup_json_candidate(candidate: str) -> str:
        """Repair common LLM JSON defects without changing field content."""
        text = candidate.strip()
        if text.startswith("json"):
            text = text[4:].strip()
        text = text.replace("\ufeff", "").replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        return text

    @classmethod
    def _decode_json_candidate(cls, candidate: str) -> Any:
        cleaned = cls._cleanup_json_candidate(candidate)
        try:
            return json.loads(cleaned)
        except JSONDecodeError:
            pythonish = re.sub(r"\bnull\b", "None", cleaned)
            pythonish = re.sub(r"\btrue\b", "True", pythonish)
            pythonish = re.sub(r"\bfalse\b", "False", pythonish)
            try:
                python_value = ast.literal_eval(pythonish)
            except (SyntaxError, ValueError) as exc:
                raise JSONDecodeError(str(exc), cleaned, 0) from exc
            if isinstance(python_value, (dict, list)):
                return python_value
            raise JSONDecodeError("Decoded value is not a JSON object or array", cleaned, 0)

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
            candidate_texts.insert(0, extracted)

        for candidate in candidate_texts:
            try:
                raw = cls._decode_json_candidate(candidate)
                break
            except JSONDecodeError as exc:
                parse_errors.append(f"{exc.msg} (line {exc.lineno}, column {exc.colno})")
        else:
            cls._logger.warning(
                "LLM JSON parse failed for %s. response_preview=%r errors=%s",
                cls.__name__,
                payload[:500],
                parse_errors,
            )
            raise SchemaValidationError(
                "Invalid JSON response. Parse attempts failed: "
                + " | ".join(parse_errors)
            )

        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            log_failure(cls._logger, "schema_validation", exc, schema=cls.__name__)
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

    @field_validator(
        "title",
        "abstract",
        "objective",
        "methodology",
        "dataset_or_participants",
        "conclusion",
        mode="before",
    )
    @classmethod
    def _coerce_scalar_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, list):
            text_parts = [str(v).strip() for v in value if str(v).strip()]
            return " ".join(text_parts) or None
        return str(value).strip() or None

    @field_validator("authors", "findings", "limitations", "source_notes", mode="before")
    @classmethod
    def _coerce_text_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        cleaned = str(value).strip()
        return [cleaned] if cleaned else []

    @field_validator("year", mode="before")
    @classmethod
    def _coerce_year(cls, value: Any) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            digits = "".join(ch for ch in value if ch.isdigit())
            if len(digits) >= 4:
                return int(digits[:4])
        return None
