from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import main


class StubChatService:
    def configured_providers(self):
        return ["ollama", "gemini"], "ollama"

    def run(self, **kwargs):
        assert kwargs["message"] == "Hello"
        return {
            "answer": "Response",
            "trace": [{"actor": "Coordinator", "action": "Prepared", "status": "ok"}],
            "attachments": [item.filename for item in kwargs["attachments"]],
        }


client = TestClient(main.app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_provider_discovery(monkeypatch):
    monkeypatch.setattr(main, "get_chat_service", lambda: StubChatService())

    response = client.get("/api/providers")

    assert response.status_code == 200
    assert response.json() == {"providers": ["ollama", "gemini"], "default": "ollama"}


def test_chat_accepts_multipart_attachments(monkeypatch):
    monkeypatch.setattr(main, "get_chat_service", lambda: StubChatService())

    response = client.post(
        "/api/chat",
        data={"message": "Hello", "history": '[{"role":"user","content":"Earlier"}]'},
        files={"attachments": ("paper.md", b"notes", "text/markdown")},
    )

    assert response.status_code == 200
    assert response.json()["attachments"] == ["paper.md"]


def test_chat_rejects_malformed_history():
    response = client.post("/api/chat", data={"message": "Hello", "history": "not-json"})

    assert response.status_code == 422
    assert response.json()["detail"] == "History must be valid JSON."
