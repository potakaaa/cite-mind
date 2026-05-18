from __future__ import annotations

from app.tools.citation_lookup import PaperSearchResult
from app.ui.streamlit_app import _format_paper_results, _is_paper_search_request, _paper_search_query


def test_detects_paper_search_request_and_extracts_topic():
    message = "can you search for existing papers and their methodologies on public transport route optimization?"

    assert _is_paper_search_request(message)
    assert _paper_search_query(message) == "public transport route optimization"


def test_ignores_general_chat_without_scholarly_target():
    assert not _is_paper_search_request("can you explain this paragraph?")


def test_formats_papers_with_methodology_clues():
    markdown = _format_paper_results(
        [
            PaperSearchResult(
                title="Route Zoning Study",
                authors=["Ada Lovelace"],
                year=2024,
                abstract="This case study uses survey data and optimization analysis for route design.",
            )
        ]
    )

    assert "Existing papers found" in markdown
    assert "Route Zoning Study" in markdown
    assert "Methodology clue" in markdown
