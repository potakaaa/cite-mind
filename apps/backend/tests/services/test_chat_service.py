from __future__ import annotations

import pytest

from app.services.chat_service import (
    MAX_CONTEXT_CHARS,
    ChatAttachment,
    ChatService,
    ChatServiceError,
)


class StubAgent:
    def __init__(self, answer: str = "final answer", error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.calls: list[dict] = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.answer


class StubRouter:
    providers = {"ollama": object()}

    def configured_providers(self):
        return ["ollama"]


def build_service(agent: StubAgent | None = None) -> ChatService:
    return ChatService(chat_agent=agent or StubAgent(), router=StubRouter())  # type: ignore[arg-type]


def test_chat_service_runs_agent_with_history_and_text_attachment():
    agent = StubAgent()
    result = build_service(agent).run(
        message="Summarize this",
        history=[{"role": "user", "content": "Earlier question"}],
        provider="ollama",
        attachments=[ChatAttachment("notes.md", b"Important notes")],
    )

    assert result["answer"] == "final answer"
    assert result["attachments"] == ["notes.md"]
    assert [item["actor"] for item in result["trace"]] == ["Coordinator", "DocumentReader", "Synthesizer"]
    assert "Earlier question" in agent.calls[0]["prompt"]
    assert "Important notes" in agent.calls[0]["prompt"]


def test_chat_service_rejects_invalid_attachment_type():
    with pytest.raises(ChatServiceError, match="Unsupported attachment type"):
        build_service().run(
            message="Read this",
            attachments=[ChatAttachment("notes.docx", b"content")],
        )


def test_chat_service_rejects_invalid_history():
    with pytest.raises(ChatServiceError, match="requires a user or assistant role"):
        build_service().run(message="Hello", history=[{"role": "system", "content": "No"}])


def test_chat_service_wraps_provider_error():
    service = build_service(StubAgent(error=RuntimeError("provider unavailable")))

    with pytest.raises(ChatServiceError, match="provider unavailable"):
        service.run(message="Hello")


def test_chat_service_truncates_attachment_context():
    context, names = build_service().build_attachment_context(
        [ChatAttachment("notes.txt", b"a" * (MAX_CONTEXT_CHARS + 100))],
        "",
    )

    assert len(context) == MAX_CONTEXT_CHARS
    assert names == ["notes.txt"]
