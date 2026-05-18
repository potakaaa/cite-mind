"""Service layer for citation metadata and APA-style formatting."""

from __future__ import annotations

from typing import Any
import logging

from app.tools.citation_lookup import CitationLookup, CitationLookupError, CitationMetadata


class CitationServiceError(RuntimeError):
    """Raised when citation generation fails."""


class CitationService:
    """Coordinates citation lookup and formatting independent of agent flow."""

    def __init__(self, lookup: CitationLookup | None = None) -> None:
        self.lookup = lookup or CitationLookup()
        self.logger = logging.getLogger("app.services.citation")

    def extract_doi(self, text: str) -> str | None:
        return self.lookup.extract_doi(text)

    def resolve_metadata(
        self,
        *,
        extracted_text: str | None = None,
        doi: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        detected_doi = doi or self.extract_doi(extracted_text or "")

        try:
            if detected_doi:
                metadata = self.lookup.lookup_by_doi(detected_doi)
            elif title and title.strip():
                metadata = self.lookup.lookup_by_title(title.strip())
            else:
                raise CitationServiceError(
                    "Unable to resolve citation metadata: provide DOI, title, or text containing DOI."
                )
        except CitationLookupError as exc:
            self.logger.exception("Citation metadata lookup failed: %s", exc)
            raise CitationServiceError(str(exc)) from exc

        return metadata.to_dict()

    def format_apa(
        self,
        *,
        title: str | None = None,
        authors: list[str] | None = None,
        year: int | None = None,
        doi: str | None = None,
        journal: str | None = None,
        volume: str | None = None,
        issue: str | None = None,
        pages: str | None = None,
        url: str | None = None,
    ) -> str:
        metadata = CitationMetadata(
            title=title,
            authors=authors or [],
            year=year,
            doi=doi,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            url=url,
        )
        metadata = self.lookup.mark_incomplete(metadata)
        return self._format_apa_from_metadata(metadata)

    def build_apa_reference(
        self,
        *,
        extracted_text: str | None = None,
        doi: str | None = None,
        title: str | None = None,
        include_metadata: bool = False,
    ) -> str | dict[str, Any]:
        metadata = self.resolve_metadata(extracted_text=extracted_text, doi=doi, title=title)
        reference = self._format_apa_from_metadata(
            CitationMetadata(
                title=metadata.get("title"),
                authors=list(metadata.get("authors", [])),
                year=metadata.get("year"),
                doi=metadata.get("doi"),
                journal=metadata.get("journal"),
                volume=metadata.get("volume"),
                issue=metadata.get("issue"),
                pages=metadata.get("pages"),
                url=metadata.get("url"),
                source=metadata.get("source"),
                incomplete_fields=list(metadata.get("incomplete_fields", [])),
            )
        )
        if not include_metadata:
            return reference
        return {"reference": reference, "metadata": metadata}

    def _format_apa_from_metadata(self, metadata: CitationMetadata) -> str:
        authors = self._format_authors(metadata.authors)
        year = str(metadata.year) if metadata.year else "[missing year]"
        title = metadata.title.strip() if metadata.title else "[missing title]"
        journal = metadata.journal.strip() if metadata.journal else "[missing journal]"

        volume_issue = ""
        if metadata.volume and metadata.issue:
            volume_issue = f"{metadata.volume}({metadata.issue})"
        elif metadata.volume:
            volume_issue = metadata.volume
        elif metadata.issue:
            volume_issue = f"[missing volume]({metadata.issue})"
        else:
            volume_issue = "[missing volume/issue]"

        pages = metadata.pages.strip() if metadata.pages else "[missing pages]"
        locator = f"https://doi.org/{metadata.doi.strip()}" if metadata.doi else (metadata.url or "[missing DOI/URL]")

        reference = f"{authors} ({year}). {title}. {journal}, {volume_issue}, {pages}. {locator}"
        if metadata.incomplete_fields:
            missing = ", ".join(metadata.incomplete_fields)
            reference = f"{reference} [incomplete citation data: missing {missing}]"
        return reference

    def _format_authors(self, authors: list[str]) -> str:
        if not authors:
            return "[missing authors]"

        formatted = [self._format_single_author(name) for name in authors if name.strip()]
        if not formatted:
            return "[missing authors]"
        if len(formatted) == 1:
            return formatted[0]
        if len(formatted) == 2:
            return f"{formatted[0]}, & {formatted[1]}"
        return f"{', '.join(formatted[:-1])}, & {formatted[-1]}"

    def _format_single_author(self, name: str) -> str:
        parts = [part.strip() for part in name.split() if part.strip()]
        if not parts:
            return "[missing author]"
        family = parts[-1]
        initials = " ".join(f"{part[0]}." for part in parts[:-1] if part and part[0].isalpha())
        return f"{family}, {initials}".strip().rstrip(",")
