from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import AgentExecutionError, BaseAgent
from app.schemas.agent_output_schema import CritiqueSchema
from app.schemas.study_schema import StudySchema
from app.utils.prompt_loader import load_prompt_template

class WriterAgent(BaseAgent):
    """Generate user-facing markdown from structured study and critique data."""

    ALLOWED_MODES: tuple[str, ...] = ("study_table", "summary", "gaps", "rrl", "full_report")

    def __init__(self, **kwargs: Any) -> None:
        prompt_template = kwargs.pop("prompt_template", load_prompt_template("writer_prompt.txt"))
        super().__init__(name=kwargs.pop("name", "writer_agent"), prompt_template=prompt_template, **kwargs)

    def _normalize_study(self, study: StudySchema | dict[str, Any]) -> StudySchema:
        if isinstance(study, StudySchema):
            return study
        if isinstance(study, dict):
            return StudySchema.from_llm_data(study)
        raise AgentExecutionError("study must be a StudySchema or dict.")

    def _normalize_critique(self, critique: CritiqueSchema | dict[str, Any] | None) -> CritiqueSchema | None:
        if critique is None:
            return None
        if isinstance(critique, CritiqueSchema):
            return critique
        if isinstance(critique, dict):
            return CritiqueSchema.from_llm_data(critique)
        raise AgentExecutionError("critique must be a CritiqueSchema, dict, or None.")

    def build_prompt(self, **kwargs: Any) -> str:
        mode = str(kwargs.get("mode", "full_report")).strip()
        if mode not in self.ALLOWED_MODES:
            raise AgentExecutionError(
                f"Invalid mode '{mode}'. Supported modes: {', '.join(self.ALLOWED_MODES)}"
            )

        study = kwargs.get("study")
        if study is None:
            raise AgentExecutionError("study is required.")

        study_schema = self._normalize_study(study)
        critique_schema = self._normalize_critique(kwargs.get("critique"))

        study_json = json.dumps(study_schema.model_dump(), ensure_ascii=True)
        critique_json = json.dumps(critique_schema.model_dump(), ensure_ascii=True) if critique_schema else "null"

        return (
            f"{self.prompt_template}\n\n"
            f"Selected output mode: {mode}\n"
            "Task:\n"
            "- Produce markdown that matches the selected output mode.\n"
            "- Ground every statement in provided data.\n"
            "- If a value is unavailable, state it as unavailable/unspecified.\n\n"
            "Study data (JSON):\n"
            f"{study_json}\n\n"
            "Critique data (JSON or null):\n"
            f"{critique_json}"
        )

    def handle_response(self, response: str) -> str:
        text = str(response).strip()
        if not text:
            raise AgentExecutionError("WriterAgent returned an empty response.")
        return text

    def run(
        self,
        provider: str | None = None,
        task_type: str | None = None,
        **kwargs: Any,
    ) -> str:
        if "mode" not in kwargs:
            kwargs["mode"] = "full_report"
        return super().run(provider=provider, task_type=task_type, **kwargs)
