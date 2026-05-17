"""Gemini provider implementation."""

from __future__ import annotations

from typing import Any

from config import settings

from .base_provider import BaseLLMProvider, LLMProviderError


class GeminiProvider(BaseLLMProvider):
    def __init__(self, timeout: int = 45, retries: int = 2) -> None:
        super().__init__(provider_name="gemini", timeout=timeout, retries=retries)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        settings.validate_provider_config("gemini")

        temperature = kwargs.get("temperature", 0.2)
        model = kwargs.get("model", settings.gemini_model)
        api_key = settings.gemini_api_key

        if not api_key:
            raise LLMProviderError("GEMINI_API_KEY is required to use Gemini.")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }

        data = self._post_json(url=url, payload=payload)
        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMProviderError(f"Gemini returned no candidates: {data}")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "\n".join(chunk for chunk in text_chunks if chunk)

        return self._normalize_text(text)
