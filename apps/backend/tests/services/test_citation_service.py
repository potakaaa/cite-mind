from __future__ import annotations

from app.services.citation_service import CitationService
from app.tools.citation_lookup import CitationLookup, CitationMetadata


class StubLookup(CitationLookup):
    def __init__(self) -> None:
        super().__init__(timeout_seconds=0.1)

    def lookup_by_doi(self, doi: str) -> CitationMetadata:
        return self.mark_incomplete(
            CitationMetadata(
                title="Effects of Sleep on Memory",
                authors=["Jane Smith", "John Doe"],
                year=2020,
                doi=doi,
                journal="Journal of Sleep",
                volume="12",
                issue="3",
                pages="44-58",
                source="crossref_doi",
            )
        )

    def lookup_by_title(self, title: str) -> CitationMetadata:
        return self.mark_incomplete(
            CitationMetadata(
                title=title,
                authors=["Jane Smith"],
                year=2021,
                doi=None,
                journal=None,
                source="crossref_title",
            )
        )


def test_citation_service_uses_doi_from_text():
    service = CitationService(lookup=StubLookup())
    result = service.build_apa_reference(extracted_text="doi: 10.1234/example", include_metadata=True)
    assert isinstance(result, dict)
    assert "https://doi.org/10.1234/example" in result["reference"]
    assert result["metadata"]["doi"] == "10.1234/example"


def test_citation_service_best_effort_apa_with_missing_markers():
    service = CitationService(lookup=StubLookup())
    reference = service.build_apa_reference(title="A Missing Metadata Paper")
    assert "[incomplete citation data:" in reference
    assert "[missing pages]" in reference
