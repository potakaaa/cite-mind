from typing import Any
from pydantic import TypeAdapter

from .base import BaseTool, ToolExecutionError
from .citation_lookup import CitationLookup, CitationLookupError


class AcademicSearchTool(BaseTool):
    """Tool for finding academic papers via OpenAlex and Semantic Scholar."""

    name = "AcademicSearch"
    description = (
        "Search for peer-reviewed academic papers, journals, and studies. "
        "Returns titles, authors, abstracts, and publication metadata. "
        "Use this for scholarly or academic research queries."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query (keywords, topics, or exact paper title)."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of papers to return (default 5).",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def __init__(self, timeout_seconds: float = 10.0):
        self.lookup = CitationLookup(timeout_seconds=timeout_seconds)

    def execute(self, **kwargs: Any) -> Any:
        query = kwargs.get("query")
        if not query:
            raise ToolExecutionError("AcademicSearch requires a 'query' argument.")
            
        limit = kwargs.get("limit", 5)
        
        try:
            results = self.lookup.search_papers(query, limit=limit)
            return [res.model_dump() for res in results]
        except CitationLookupError as exc:
            raise ToolExecutionError(f"Academic search failed: {exc}") from exc
