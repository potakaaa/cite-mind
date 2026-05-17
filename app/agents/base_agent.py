from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any

from app.llm.base_provider import LLMProviderError
from app.llm.llm_router import LLMRouter


class AgentExecutionError(RuntimeError):
    """Raised when agent execution fails."""


class BaseAgent(ABC):
    """Reusable base class for all agents with shared LLM execution flow."""

    def __init__(self, name: str, llm: LLMRouter | None = None, prompt_template: str = "") -> None:
        self.name = name
        self.llm = llm or LLMRouter()
        self.prompt_template = prompt_template
        self.logger = logging.getLogger(f"app.agents.{self.name}")

    @abstractmethod
    def build_prompt(self, **kwargs: Any) -> str:
        """Build the final prompt from input data. Override in child agents."""

    def handle_response(self, response: str) -> Any:
        """Optional post-processing hook for child agents."""
        return response

    def run(self, provider: str | None = None, task_type: str | None = None, **kwargs: Any) -> Any:
        """Run agent flow: prompt build -> LLM call -> response handling."""
        self.logger.info("Agent '%s' started", self.name)

        try:
            prompt = self.build_prompt(**kwargs)
            if not isinstance(prompt, str) or not prompt.strip():
                raise AgentExecutionError(
                    f"Agent '{self.name}' built an empty or invalid prompt."
                )

            raw_response = self.llm.generate(
                prompt=prompt,
                provider=provider,
                task_type=task_type,
            )
            parsed = self.handle_response(raw_response)

            self.logger.info("Agent '%s' finished", self.name)
            return parsed
        except (LLMProviderError, AgentExecutionError, ValueError, TypeError) as exc:
            self.logger.exception("Agent '%s' failed: %s", self.name, exc)
            raise AgentExecutionError(f"Agent '{self.name}' failed: {exc}") from exc
