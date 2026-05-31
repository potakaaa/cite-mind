from typing import Any
from duckduckgo_search import DDGS

from .base import BaseTool, ToolExecutionError


class WebSearchTool(BaseTool):
    """Tool for finding general articles, news, and web pages via DuckDuckGo."""

    name = "WebSearch"
    description = (
        "Search the general web for articles, news, and information. "
        "Returns titles, brief snippets, and URLs. "
        "Use this for general knowledge, recent news, or non-academic topics."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5).",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def execute(self, **kwargs: Any) -> Any:
        query = kwargs.get("query")
        if not query:
            raise ToolExecutionError("WebSearch requires a 'query' argument.")
            
        limit = kwargs.get("limit", 5)
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=limit))
            return results
        except Exception as exc:
            raise ToolExecutionError(f"Web search failed: {exc}") from exc
