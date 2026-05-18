from __future__ import annotations

from app.tools.citation_lookup import CitationLookup


def test_extract_doi_from_text():
    lookup = CitationLookup()
    text = "This paper DOI is 10.1000/xyz-123. and should be captured."
    assert lookup.extract_doi(text) == "10.1000/xyz-123"


def test_normalize_crossref_marks_missing_fields():
    lookup = CitationLookup()
    metadata = lookup._normalize_crossref(
        {
            "title": ["Test Title"],
            "author": [{"given": "Ada", "family": "Lovelace"}],
            "issued": {"date-parts": [[2023]]},
            "DOI": "10.1000/abc",
        },
        source="crossref_doi",
    )
    metadata = lookup.mark_incomplete(metadata)
    assert metadata.title == "Test Title"
    assert metadata.authors == ["Ada Lovelace"]
    assert metadata.year == 2023
    assert "journal" in metadata.incomplete_fields
