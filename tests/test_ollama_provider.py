from __future__ import annotations

import requests
import pytest

from config import Settings
from app.llm.base_provider import LLMProviderError
from app.llm.ollama_provider import OllamaProvider


class FakeStreamingResponse:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self, decode_unicode: bool = False):
        return iter(self.lines)


def test_ollama_provider_accumulates_streaming_chunks(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeStreamingResponse(
            [
                '{"response":"hello ","done":false}',
                '{"response":"world","done":true}',
            ]
        )

    monkeypatch.setattr("app.llm.ollama_provider.requests.post", fake_post)
    monkeypatch.setattr(Settings, "validate_provider_config", lambda self, provider=None: None)

    result = OllamaProvider(timeout=3, retries=0).generate("prompt")

    assert result == "hello world"
    assert captured["stream"] is True
    assert captured["json"]["stream"] is True


def test_ollama_provider_wraps_streaming_timeout(monkeypatch):
    def fake_post(url, **kwargs):
        raise requests.Timeout("slow response")

    monkeypatch.setattr("app.llm.ollama_provider.requests.post", fake_post)
    monkeypatch.setattr(Settings, "validate_provider_config", lambda self, provider=None: None)

    with pytest.raises(LLMProviderError, match="ollama request failed after 1 attempts"):
        OllamaProvider(timeout=3, retries=0).generate("prompt")
