"""OpenRouter provider implementation."""

from __future__ import annotations

from typing import Any

from config import settings

from .base_provider import BaseLLMProvider, LLMProviderError


class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, timeout: int = 45, retries: int = 2) -> None:
        super().__init__(provider_name="openrouter", timeout=timeout, retries=retries)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        settings.validate_provider_config("openrouter")

        temperature = kwargs.get("temperature", 0.2)
        model = kwargs.get("model", settings.openrouter_model)
        api_key = settings.openrouter_api_key

        if not api_key:
            raise LLMProviderError("OPENROUTER_API_KEY is required to use OpenRouter.")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Cite Mind",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        data = self._post_json(url=url, payload=payload, headers=headers)
        choices = data.get("choices", [])
        if not choices:
            raise LLMProviderError(f"OpenRouter returned no choices: {data}")

        text = choices[0].get("message", {}).get("content")
        if text is None:
            raise LLMProviderError(f"OpenRouter response missing text content: {data}")

        return self._normalize_text(text)
