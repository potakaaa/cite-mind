"""Provider-agnostic router for LLM generation calls."""

from __future__ import annotations

from typing import Any

from config import LlmProvider, settings

from .base_provider import BaseLLMProvider, LLMProviderError
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from .openrouter_provider import OpenRouterProvider


class LLMRouter:
    """Single entry point for agents to call LLMs."""

    def __init__(self) -> None:
        self.providers: dict[LlmProvider, BaseLLMProvider] = {
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
            "openrouter": OpenRouterProvider(),
        }

    def _select_provider(
        self,
        provider: LlmProvider | None = None,
        task_type: str | None = None,
    ) -> LlmProvider:
        if provider:
            return provider

        if task_type == "long_document_reasoning":
            return "gemini"

        return settings.default_llm_provider

    def generate(
        self,
        prompt: str,
        provider: LlmProvider | None = None,
        task_type: str | None = None,
        **kwargs: Any,
    ) -> str:
        selected = self._select_provider(provider=provider, task_type=task_type)
        llm = self.providers[selected]

        try:
            return llm.generate(prompt, **kwargs)
        except Exception as exc:
            if isinstance(exc, LLMProviderError):
                raise
            raise LLMProviderError(
                f"Failed to generate response using '{selected}' provider: {exc}"
            ) from exc
