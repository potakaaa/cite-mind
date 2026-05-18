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


def test_search_papers_uses_openalex_and_rebuilds_abstract(monkeypatch):
    lookup = CitationLookup()

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "display_name": "Route Optimization for Public Transport",
                        "publication_year": 2024,
                        "doi": "https://doi.org/10.1000/routes",
                        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
                        "primary_location": {"source": {"display_name": "Transport Journal"}},
                        "id": "https://openalex.org/W123",
                        "abstract_inverted_index": {
                            "uses": [0],
                            "genetic": [1],
                            "algorithms": [2],
                        },
                    }
                ]
            }

    monkeypatch.setattr("app.tools.citation_lookup.requests.get", lambda *args, **kwargs: Response())

    results = lookup.search_papers("public transport route optimization")

    assert len(results) == 1
    assert results[0].title == "Route Optimization for Public Transport"
    assert results[0].doi == "10.1000/routes"
    assert results[0].abstract == "uses genetic algorithms"


def test_search_papers_handles_null_openalex_nested_fields(monkeypatch):
    lookup = CitationLookup()

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "display_name": "Public Transport Route Zoning",
                        "publication_year": 2022,
                        "doi": None,
                        "authorships": [],
                        "primary_location": None,
                        "id": "https://openalex.org/W456",
                        "abstract_inverted_index": None,
                    }
                ]
            }

    monkeypatch.setattr("app.tools.citation_lookup.requests.get", lambda *args, **kwargs: Response())

    results = lookup.search_papers("route zoning jeepney philippines")

    assert len(results) == 1
    assert results[0].title == "Public Transport Route Zoning"
    assert results[0].venue is None
    assert results[0].abstract is None
