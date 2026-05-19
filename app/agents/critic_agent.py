from __future__ import annotations

import json
from typing import Any

from app.agents.base_agent import AgentExecutionError, BaseAgent
from app.schemas.agent_output_schema import CritiqueSchema
from app.schemas.study_schema import SchemaValidationError, StudySchema
from app.utils.logging import log_failure
from app.utils.prompt_loader import load_prompt_template


class CriticAgent(BaseAgent):
    """Review extracted study data for gaps, weaknesses, and future recommendations."""

    def __init__(self, **kwargs: Any) -> None:
        prompt_template = kwargs.pop("prompt_template", load_prompt_template("critic_prompt.txt"))
        super().__init__(name=kwargs.pop("name", "critic_agent"), prompt_template=prompt_template, **kwargs)

    def build_prompt(self, **kwargs: Any) -> str:
        study = kwargs.get("study")
        if study is None:
            raise AgentExecutionError("study is required.")

        if isinstance(study, StudySchema):
            study_data = study.model_dump()
        elif isinstance(study, dict):
            study_data = StudySchema.from_llm_data(study).model_dump()
        else:
            raise AgentExecutionError("study must be a StudySchema or dict.")

        return (
            f"{self.prompt_template}\n\n"
            "Task: Critique this study using only these fields as evidence.\n"
            "Important:\n"
            "- Separate stated limitations from inferred methodological weaknesses.\n"
            "- Do not invent facts, outcomes, sample sizes, or methods.\n"
            "- If evidence is missing, explicitly reflect that in confidence_notes.\n"
            "Study data (JSON):\n"
            f"{json.dumps(study_data, ensure_ascii=True)}"
        )

    def handle_response(self, response: str) -> CritiqueSchema:
        try:
            return CritiqueSchema.from_llm_json(response)
        except SchemaValidationError as exc:
            log_failure(self.logger, "critic_parse", exc, response_preview=response[:500])
            raise AgentExecutionError(f"CriticAgent returned invalid critique JSON: {exc}") from exc
