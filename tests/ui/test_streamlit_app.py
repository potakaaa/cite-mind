from __future__ import annotations

from app.ui.streamlit_app import _friendly_error
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
