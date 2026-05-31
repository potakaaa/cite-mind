"""Provider-agnostic router for LLM generation calls."""

from __future__ import annotations

from typing import Any

from config import LlmProvider, settings
from app.utils.logging import get_logger, log_failure

from .base_provider import BaseLLMProvider, LLMProviderError, LLMResponse
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from .openrouter_provider import OpenRouterProvider


class LLMRouter:
    """Single entry point for agents to call LLMs."""

    def __init__(self) -> None:
        self.logger = get_logger("app.llm.router")
        self.providers: dict[LlmProvider, BaseLLMProvider] = {
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
            "openrouter": OpenRouterProvider(),
        }

    def configured_providers(self) -> list[LlmProvider]:
        """Return providers with enough local configuration to attempt a call."""
        configured: list[LlmProvider] = []
        for provider in self.providers:
            try:
                settings.validate_provider_config(provider=provider)
                configured.append(provider)
            except ValueError as exc:
                self.logger.debug("Provider '%s' is not configured: %s", provider, exc)
        return configured

    def _select_provider(
        self,
        provider: LlmProvider | None = None,
        task_type: str | None = None,
    ) -> LlmProvider:
        if provider:
            if provider not in self.providers:
                raise LLMProviderError(
                    f"Unknown LLM provider '{provider}'. Supported providers: {', '.join(self.providers)}."
                )
            return provider

        if task_type == "long_document_reasoning":
            if not isinstance(self.providers.get("gemini"), BaseLLMProvider):
                return "gemini"
            try:
                settings.validate_provider_config("gemini")
                return "gemini"
            except ValueError as exc:
                fallback = self._configured_fallback(exclude={"gemini"})
                if fallback:
                    self.logger.info(
                        "Gemini is not configured for long_document_reasoning; falling back to '%s': %s",
                        fallback,
                        exc,
                    )
                    return fallback
                self.logger.info(
                    "Gemini is not configured for long_document_reasoning; using default '%s': %s",
                    settings.default_llm_provider,
                    exc,
                )

        return settings.default_llm_provider

    def _configured_fallback(self, exclude: set[LlmProvider] | None = None) -> LlmProvider | None:
        excluded = exclude or set()
        for provider in (settings.default_llm_provider, "ollama", "gemini", "openrouter"):
            if provider in excluded:
                continue
            try:
                settings.validate_provider_config(provider=provider)
            except ValueError:
                continue
            return provider
        return None

    def generate(
        self,
        prompt: str,
        provider: LlmProvider | None = None,
        task_type: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        selected = self._select_provider(provider=provider, task_type=task_type)
        llm = self.providers[selected]

        try:
            if isinstance(llm, BaseLLMProvider):
                settings.validate_provider_config(selected)
            return llm.generate(prompt, **kwargs)
        except ValueError as exc:
            fallback = self._configured_fallback(exclude={selected})
            if provider is None and fallback:
                self.logger.info(
                    "Provider '%s' is unavailable; falling back to '%s': %s",
                    selected,
                    fallback,
                    exc,
                )
                return self.providers[fallback].generate(prompt, **kwargs)
            log_failure(self.logger, "provider_config", exc, provider=selected, task_type=task_type)
            raise LLMProviderError(str(exc)) from exc
        except Exception as exc:
            if isinstance(exc, LLMProviderError):
                fallback = self._configured_fallback(exclude={selected})
                if provider is None and fallback:
                    self.logger.info(
                        "Provider '%s' failed at runtime; falling back to '%s': %s",
                        selected,
                        fallback,
                        exc,
                    )
                    return self.providers[fallback].generate(prompt, **kwargs)
            log_failure(self.logger, "provider_generation", exc, provider=selected, task_type=task_type)
            if isinstance(exc, LLMProviderError):
                raise
            raise LLMProviderError(
                f"Failed to generate response using '{selected}' provider: {exc}"
            ) from exc
