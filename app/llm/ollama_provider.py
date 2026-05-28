"""Ollama provider implementation."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from config import settings

from .base_provider import BaseLLMProvider, LLMProviderError, LLMResponse


class OllamaProvider(BaseLLMProvider):
    def __init__(self, timeout: int | None = None, retries: int | None = None) -> None:
        timeout = timeout if timeout is not None else settings.ollama_timeout_seconds
        retries = retries if retries is not None else settings.ollama_retries
        super().__init__(provider_name="ollama", timeout=timeout, retries=retries)

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        settings.validate_provider_config("ollama")

        model = kwargs.get("model", settings.ollama_model)
        temperature = kwargs.get("temperature", 0.2)
        base_url = settings.ollama_base_url.rstrip("/")

        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }

        text = self._stream_generate(url=url, payload=payload)
        if not text:
            raise LLMProviderError("Ollama returned an empty response.")

        return LLMResponse(text=self._normalize_text(text))

    def _stream_generate(self, url: str, payload: dict[str, Any]) -> str:
        """Call Ollama in streaming mode to avoid idle read timeouts on slow local models."""
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout,
                    stream=True,
                )
                response.raise_for_status()

                chunks: list[str] = []
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except ValueError as exc:
                        raise LLMProviderError(f"Ollama returned invalid streaming JSON: {line}") from exc

                    if "error" in data:
                        raise LLMProviderError(f"Ollama returned an error: {data['error']}")
                    chunk = data.get("response")
                    if chunk is not None:
                        chunks.append(str(chunk))
                    if data.get("done"):
                        break

                return "".join(chunks)
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError, LLMProviderError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                time.sleep(0.5 * (attempt + 1))

        raise LLMProviderError(
            f"{self.provider_name} request failed after {self.retries + 1} attempts: {last_error}"
        )
