"""Ollama provider implementation."""

from __future__ import annotations

from typing import Any

from config import settings

from .base_provider import BaseLLMProvider, LLMProviderError


class OllamaProvider(BaseLLMProvider):
    def __init__(self, timeout: int | None = None, retries: int | None = None) -> None:
        timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
        retries = retries if retries is not None else settings.ollama_retries
        super().__init__(provider_name="ollama", timeout=timeout, retries=retries)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        settings.validate_provider_config("ollama")

        model = kwargs.get("model", settings.ollama_model)
        temperature = kwargs.get("temperature", 0.2)
        base_url = settings.ollama_base_url.rstrip("/")

        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        data = self._post_json(url=url, payload=payload)
        text = data.get("response")
        if text is None:
            raise LLMProviderError(f"Ollama returned no 'response' field: {data}")

        return self._normalize_text(text)
