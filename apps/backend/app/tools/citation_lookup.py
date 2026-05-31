"""Citation metadata lookup tools (DOI + title fallback)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any

import requests


DOI_PATTERN = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", re.IGNORECASE)


class CitationLookupError(RuntimeError):
    """Raised when citation metadata lookup fails."""


@dataclass
class CitationMetadata:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    url: str | None = None
    source: str | None = None
    incomplete_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "doi": self.doi,
            "journal": self.journal,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "url": self.url,
            "source": self.source,
            "incomplete_fields": list(self.incomplete_fields),
            "is_incomplete": bool(self.incomplete_fields),
        }


@dataclass
class PaperSearchResult:
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    url: str | None = None
    abstract: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "doi": self.doi,
            "venue": self.venue,
            "url": self.url,
            "abstract": self.abstract,
            "source": self.source,
        }


class CitationLookup:
    """Lookup citation metadata from free APIs."""

    def __init__(self, timeout_seconds: float = 12.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger("app.tools.citation_lookup")

    def extract_doi(self, text: str) -> str | None:
        if not text:
            return None
        match = DOI_PATTERN.search(text)
        return match.group(1).rstrip(".,;:)]}") if match else None

    def lookup(self, *, doi: str | None = None, title: str | None = None) -> CitationMetadata:
        if doi:
            return self.lookup_by_doi(doi)
        if title and title.strip():
            return self.lookup_by_title(title.strip())
        raise CitationLookupError("Either DOI or title is required for citation lookup.")

    def lookup_by_doi(self, doi: str) -> CitationMetadata:
        normalized = doi.strip()
        if not normalized:
            raise CitationLookupError("DOI cannot be empty.")

        try:
            response = requests.get(
                f"https://api.crossref.org/works/{normalized}",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CitationLookupError(f"Crossref DOI lookup failed: {exc}") from exc

        item = payload.get("message", {})
        metadata = self._normalize_crossref(item, source="crossref_doi")
        metadata.doi = metadata.doi or normalized
        return self.mark_incomplete(metadata)

    def lookup_by_title(self, title: str) -> CitationMetadata:
        errors: list[str] = []

        crossref = self._lookup_by_title_crossref(title, errors)
        if crossref:
            return self.mark_incomplete(crossref)

        openalex = self._lookup_by_title_openalex(title, errors)
        if openalex:
            return self.mark_incomplete(openalex)

        semantic = self._lookup_by_title_semantic_scholar(title, errors)
        if semantic:
            return self.mark_incomplete(semantic)

        raise CitationLookupError(
            "Title lookup failed across providers. " + "; ".join(errors or ["No provider result"])
        )

    def search_papers(self, query: str, *, limit: int = 5, min_year: int | None = None, max_year: int | None = None) -> list[PaperSearchResult]:
        normalized = query.strip()
        if not normalized:
            raise CitationLookupError("Search query cannot be empty.")

        errors: list[str] = []
        results = self._search_openalex(normalized, limit=limit, errors=errors, min_year=min_year, max_year=max_year)
        if results:
            return results

        results = self._search_semantic_scholar(normalized, limit=limit, errors=errors, min_year=min_year, max_year=max_year)
        if results:
            return results

        raise CitationLookupError(
            "Paper search failed across providers. " + "; ".join(errors or ["No provider result"])
        )

    def _search_openalex(
        self, query: str, *, limit: int, errors: list[str], min_year: int | None = None, max_year: int | None = None
    ) -> list[PaperSearchResult]:
        try:
            params = {
                "search": query,
                "per-page": max(1, min(limit, 10)),
                "select": (
                    "display_name,publication_year,doi,authorships,primary_location,"
                    "id,abstract_inverted_index"
                ),
            }
            filters = []
            if min_year and max_year:
                filters.append(f"publication_year:{min_year}-{max_year}")
            elif min_year is not None:
                filters.append(f"publication_year:>{min_year - 1}")
            elif max_year is not None:
                filters.append(f"publication_year:<{max_year + 1}")
            if filters:
                params["filter"] = ",".join(filters)
            
            response = requests.get(
                "https://api.openalex.org/works",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"openalex: {exc}")
            return []

        papers = []
        for item in payload.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("display_name") or "").strip()
            if not title:
                continue
            papers.append(
                PaperSearchResult(
                    title=title,
                    authors=[
                        str(author.get("author", {}).get("display_name", "")).strip()
                        for author in (item.get("authorships", []) or [])
                        if str(author.get("author", {}).get("display_name", "")).strip()
                    ],
                    year=item.get("publication_year"),
                    doi=self._normalize_openalex_doi(item.get("doi")),
                    venue=self._openalex_venue(item),
                    url=item.get("id"),
                    abstract=self._abstract_from_openalex_index(item.get("abstract_inverted_index")),
                    source="openalex_search",
                )
            )
        if not papers:
            errors.append("openalex: no match")
        return papers

    def _search_semantic_scholar(
        self, query: str, *, limit: int, errors: list[str], min_year: int | None = None, max_year: int | None = None
    ) -> list[PaperSearchResult]:
        try:
            params = {
                "query": query,
                "limit": max(1, min(limit, 10)),
                "fields": "title,authors,year,externalIds,venue,url,abstract",
            }
            if min_year and max_year:
                params["year"] = f"{min_year}-{max_year}"
            elif min_year:
                params["year"] = f"{min_year}-"
            elif max_year:
                params["year"] = f"-{max_year}"

            response = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"semantic_scholar: {exc}")
            return []

        papers = []
        for item in payload.get("data", []) or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            external_ids = item.get("externalIds")
            if not isinstance(external_ids, dict):
                external_ids = {}
            papers.append(
                PaperSearchResult(
                    title=title,
                    authors=[
                        str(author.get("name", "")).strip()
                        for author in (item.get("authors", []) or [])
                        if str(author.get("name", "")).strip()
                    ],
                    year=item.get("year"),
                    doi=external_ids.get("DOI"),
                    venue=item.get("venue"),
                    url=item.get("url"),
                    abstract=item.get("abstract"),
                    source="semantic_scholar_search",
                )
            )
        if not papers:
            errors.append("semantic_scholar: no match")
        return papers

    def _lookup_by_title_crossref(self, title: str, errors: list[str]) -> CitationMetadata | None:
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params={"query.title": title, "rows": 1},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("message", {}).get("items", [])
            if not items:
                errors.append("crossref: no match")
                return None
            return self._normalize_crossref(items[0], source="crossref_title")
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"crossref: {exc}")
            return None

    def _lookup_by_title_openalex(self, title: str, errors: list[str]) -> CitationMetadata | None:
        try:
            response = requests.get(
                "https://api.openalex.org/works",
                params={"search": title, "per-page": 1},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
            if not results:
                errors.append("openalex: no match")
                return None
            return self._normalize_openalex(results[0], source="openalex_title")
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"openalex: {exc}")
            return None

    def _lookup_by_title_semantic_scholar(
        self, title: str, errors: list[str]
    ) -> CitationMetadata | None:
        try:
            response = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": title,
                    "limit": 1,
                    "fields": "title,authors,year,externalIds,venue,url",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", [])
            if not data:
                errors.append("semantic_scholar: no match")
                return None
            return self._normalize_semantic_scholar(data[0], source="semantic_scholar_title")
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"semantic_scholar: {exc}")
            return None

    def _normalize_crossref(self, item: dict[str, Any], source: str) -> CitationMetadata:
        title_values = item.get("title") or []
        title = title_values[0] if title_values else None
        authors = []
        for a in item.get("author", []) or []:
            given = str(a.get("given", "")).strip()
            family = str(a.get("family", "")).strip()
            full_name = " ".join(part for part in [given, family] if part).strip()
            if full_name:
                authors.append(full_name)

        year = None
        issued = item.get("issued", {}) or {}
        parts = issued.get("date-parts", []) or []
        if parts and isinstance(parts[0], list) and parts[0]:
            first = parts[0][0]
            if isinstance(first, int):
                year = first

        journal_values = item.get("container-title") or []
        journal = journal_values[0] if journal_values else None

        return CitationMetadata(
            title=title,
            authors=authors,
            year=year,
            doi=item.get("DOI"),
            journal=journal,
            volume=str(item["volume"]) if item.get("volume") else None,
            issue=str(item["issue"]) if item.get("issue") else None,
            pages=item.get("page"),
            url=item.get("URL"),
            source=source,
        )

    def _normalize_openalex(self, item: dict[str, Any], source: str) -> CitationMetadata:
        authors = [
            str(author.get("author", {}).get("display_name", "")).strip()
            for author in (item.get("authorships", []) or [])
            if str(author.get("author", {}).get("display_name", "")).strip()
        ]

        return CitationMetadata(
            title=item.get("display_name"),
            authors=authors,
            year=item.get("publication_year"),
            doi=self._normalize_openalex_doi(item.get("doi")),
            journal=self._openalex_venue(item),
            pages=None,
            url=item.get("id"),
            source=source,
        )

    def _normalize_semantic_scholar(self, item: dict[str, Any], source: str) -> CitationMetadata:
        external_ids = item.get("externalIds", {}) or {}
        doi = external_ids.get("DOI")
        authors = [
            str(author.get("name", "")).strip()
            for author in (item.get("authors", []) or [])
            if str(author.get("name", "")).strip()
        ]
        return CitationMetadata(
            title=item.get("title"),
            authors=authors,
            year=item.get("year"),
            doi=doi,
            journal=item.get("venue"),
            url=item.get("url"),
            source=source,
        )

    def mark_incomplete(self, metadata: CitationMetadata) -> CitationMetadata:
        required = {
            "title": metadata.title,
            "authors": metadata.authors,
            "year": metadata.year,
            "doi": metadata.doi,
            "journal": metadata.journal,
        }
        metadata.incomplete_fields = [key for key, value in required.items() if not value]
        return metadata

    def _normalize_openalex_doi(self, value: Any) -> str | None:
        doi_url = str(value or "").strip()
        return doi_url.split("doi.org/")[-1] if "doi.org/" in doi_url.lower() else doi_url or None

    def _openalex_venue(self, item: dict[str, Any]) -> str | None:
        primary_location = item.get("primary_location")
        if not isinstance(primary_location, dict):
            return None
        source = primary_location.get("source")
        if not isinstance(source, dict):
            return None
        venue = source.get("display_name")
        return str(venue).strip() if venue else None

    def _abstract_from_openalex_index(self, index: Any) -> str | None:
        if not isinstance(index, dict) or not index:
            return None
        positioned_words: list[tuple[int, str]] = []
        for word, positions in index.items():
            if not isinstance(positions, list):
                continue
            for position in positions:
                if isinstance(position, int):
                    positioned_words.append((position, str(word)))
        if not positioned_words:
            return None
        return " ".join(word for _, word in sorted(positioned_words)).strip() or None
