from __future__ import annotations

from types import SimpleNamespace

from app.ui import streamlit_app
from app.ui.streamlit_app import _finish_chat_response, _friendly_error, _render_chat_agent_activity
from app.services.research_service import ResearchServiceError


def test_friendly_error_formats_properly():
    exc = ValueError("Something bad happened.")
    formatted = _friendly_error(exc)
    assert "The request could not be completed." in formatted
    assert "Something bad happened." in formatted


def test_friendly_error_returns_clean_service_errors():
    exc = ResearchServiceError("Please provide at least 80 characters of paper text.")
    formatted = _friendly_error(exc)
    assert formatted == "Please provide at least 80 characters of paper text."


def test_finish_chat_response_clears_activity_and_persists_once(monkeypatch):
    class Placeholder:
        cleared = False

        def empty(self):
            self.cleared = True

    placeholder = Placeholder()
    rerun_calls = []
    fake_st = SimpleNamespace(
        session_state=SimpleNamespace(chat_messages=[]),
        rerun=lambda: rerun_calls.append(True),
    )
    monkeypatch.setattr(streamlit_app, "st", fake_st)

    _finish_chat_response(placeholder, "Final answer")

    assert placeholder.cleared is True
    assert fake_st.session_state.chat_messages == [{"role": "assistant", "content": "Final answer"}]
    assert rerun_calls == [True]


def test_render_chat_agent_activity_clears_when_work_is_complete():
    class Placeholder:
        cleared = False

        def empty(self):
            self.cleared = True

        def markdown(self, *_args, **_kwargs):
            raise AssertionError("completed activity should not render another status")

    placeholder = Placeholder()

    _render_chat_agent_activity(placeholder, active="")

    assert placeholder.cleared is True
