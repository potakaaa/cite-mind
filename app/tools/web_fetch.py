import requests
from bs4 import BeautifulSoup
from typing import Any

from .base import BaseTool, ToolExecutionError


class ReadUrlTool(BaseTool):
    """Tool for fetching and reading the text content of a web page."""

    name = "ReadUrl"
    description = (
        "Read the main text content of a webpage from a URL. "
        "Use this after WebSearch if a search snippet is ambiguous or you need the full article text. "
        "Do NOT use this on PDF files or non-HTML links."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the webpage to read."
            }
        },
        "required": ["url"]
    }

    def execute(self, **kwargs: Any) -> Any:
        url = kwargs.get("url")
        if not url:
            raise ToolExecutionError("ReadUrl requires a 'url' argument.")
            
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove scripts, styles, and unwanted tags
            for element in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
                element.decompose()
                
            text = soup.get_text(separator="\n", strip=True)
            
            # Condense multiple newlines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            condensed = "\n".join(lines)
            
            # Limit the output to 5000 chars to avoid overwhelming the LLM
            if len(condensed) > 5000:
                condensed = condensed[:5000] + "\n... (Content truncated)"
                
            return {"url": url, "content": condensed or "No text content found."}
            
        except requests.RequestException as exc:
            raise ToolExecutionError(f"Failed to fetch URL: {exc}") from exc
        except Exception as exc:
            raise ToolExecutionError(f"Failed to parse webpage: {exc}") from exc
