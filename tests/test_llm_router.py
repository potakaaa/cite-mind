from __future__ import annotations

import pytest

from app.llm.base_provider import LLMProviderError
from app.llm.llm_router import LLMRouter


class FakeProvider:
    def __init__(self, response: str = "ok", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def generate(self, prompt: str, **kwargs):
        self.calls.append((prompt, kwargs))
        if self.error:
            raise self.error
        return self.response


def build_router() -> LLMRouter:
    router = LLMRouter()
    router.providers = {
        "gemini": FakeProvider("gemini-response"),
        "ollama": FakeProvider("ollama-response"),
        "openrouter": FakeProvider("openrouter-response"),
    }
    return router


def test_llm_router_uses_explicit_provider_and_passes_kwargs():
    router = build_router()

    result = router.generate("prompt", provider="openrouter", temperature=0.1)

    assert result == "openrouter-response"
    provider = router.providers["openrouter"]
    assert provider.calls == [("prompt", {"temperature": 0.1})]


def test_llm_router_routes_long_document_reasoning_to_gemini():
    router = build_router()

    result = router.generate("long prompt", task_type="long_document_reasoning")

    assert result == "gemini-response"
    assert router.providers["gemini"].calls[0][0] == "long prompt"


def test_llm_router_wraps_unexpected_provider_errors_but_preserves_provider_errors():
    router = build_router()
    router.providers["ollama"] = FakeProvider(error=RuntimeError("boom"))

    with pytest.raises(LLMProviderError, match="ollama"):
        router.generate("prompt", provider="ollama")

    router.providers["ollama"] = FakeProvider(error=LLMProviderError("provider failed"))
    with pytest.raises(LLMProviderError, match="provider failed"):
        router.generate("prompt", provider="ollama")


def test_llm_router_rejects_unknown_provider():
    router = build_router()

    with pytest.raises(LLMProviderError, match="Unknown LLM provider"):
        router.generate("prompt", provider="missing")  # type: ignore[arg-type]
