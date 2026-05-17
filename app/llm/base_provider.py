"""Base LLM provider abstractions and shared request behavior."""

from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import Any

import requests


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider call fails."""


class BaseLLMProvider(ABC):
    """Provider interface used by agents and the LLM router."""

    provider_name: str

    def __init__(self, provider_name: str, timeout: int = 30, retries: int = 2) -> None:
        self.provider_name = provider_name
        self.timeout = timeout
        self.retries = retries

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text response for the given prompt."""

    def _normalize_text(self, text: Any) -> str:
        """Normalize provider responses into a consistent text output."""
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        return text.strip()

    def _post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """POST JSON with basic retry and timeout handling."""
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=request_headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                time.sleep(0.5 * (attempt + 1))

        raise LLMProviderError(
            f"{self.provider_name} request failed after {self.retries + 1} attempts: {last_error}"
        )
