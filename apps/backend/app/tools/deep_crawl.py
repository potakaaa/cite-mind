import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Any

from .base import BaseTool, ToolExecutionError


class DeepCrawlTool(BaseTool):
    """Tool for autonomously crawling a webpage and its outbound links, injecting data into the Knowledge Graph."""

    name = "DeepCrawl"
    description = (
        "An autonomous spider that crawls a starting URL and follows its outbound links. "
        "It extracts text content and automatically injects all discovered pages as interconnected nodes "
        "into the persistent Knowledge Graph. Use this for deep, automated research of a topic."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The starting URL to crawl."
            },
            "max_depth": {
                "type": "integer",
                "description": "How deep to crawl. 0 = only the starting page. 1 = starting page + immediate links.",
                "default": 1
            },
            "max_pages": {
                "type": "integer",
                "description": "Hard limit on total pages to crawl to prevent infinite loops.",
                "default": 10
            }
        },
        "required": ["url"]
    }

    def __init__(self):
        # Lazy imports to prevent circular dependency issues
        from app.services.knowledge_graph import KnowledgeGraphService
        from app.llm.llm_router import LLMRouter
        
        self.router = LLMRouter()
        self.kg = KnowledgeGraphService(embedding_fn=self.router.generate_embedding)

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and HTTP/HTTPS."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https")
        except ValueError:
            return False

    def _fetch_and_parse(self, url: str) -> tuple[str, str, list[str]]:
        """Fetch URL, return (title, text_content, outbound_links)."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url
        
        # Remove junk
        for element in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            element.decompose()
            
        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        condensed_text = "\n".join(lines)
        if len(condensed_text) > 8000:
            condensed_text = condensed_text[:8000] + "\n... (Content truncated)"
            
        # Extract outbound links
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(url, href)
            # Basic deduplication and anchor stripping
            full_url = full_url.split("#")[0]
            if self._is_valid_url(full_url):
                links.append(full_url)
                
        return title, condensed_text, list(set(links))

    def execute(self, **kwargs: Any) -> Any:
        start_url = kwargs.get("url")
        max_depth = int(kwargs.get("max_depth", 1))
        max_pages = int(kwargs.get("max_pages", 10))
        
        if not start_url:
            raise ToolExecutionError("DeepCrawl requires a 'url' argument.")

        visited = set()
        queue = [(start_url, 0, None)]  # (url, depth, parent_url)
        nodes_injected = 0
        edges_injected = 0
        starting_page_content = None

        while queue and len(visited) < max_pages:
            current_url, depth, parent_url = queue.pop(0)
            
            if current_url in visited:
                continue
                
            visited.add(current_url)
            
            try:
                title, content, links = self._fetch_and_parse(current_url)
                
                # Capture the parent page text for the AI's immediate context window
                if depth == 0 and not starting_page_content:
                    starting_page_content = content[:4000] + "\n...(Truncated for LLM Context Window)" if len(content) > 4000 else content
                
                # Upsert into Knowledge Graph
                # This will automatically trigger embedding_fn because of __init__ setup
                self.kg.upsert_node(
                    node_type="Source", 
                    name=current_url, 
                    attributes={
                        "title": title,
                        "text": content,
                        "source": "DeepCrawl"
                    }
                )
                nodes_injected += 1
                
                if parent_url:
                    self.kg.upsert_edge(parent_url, current_url, "CITES")
                    edges_injected += 1
                    
                # Queue children if we haven't hit depth limit
                if depth < max_depth:
                    for link in links:
                        if link not in visited:
                            queue.append((link, depth + 1, current_url))
                            
            except requests.RequestException:
                # Silently skip failed pages during crawl
                continue
            except Exception as exc:
                print(f"DeepCrawl error on {current_url}: {exc}")
                continue

        return {
            "status": "success",
            "message": f"Successfully crawled {len(visited)} pages. The starting page text is provided below. All other pages were safely mapped into the Knowledge Graph in the background.",
            "nodes_injected": nodes_injected,
            "edges_injected": edges_injected,
            "starting_url": start_url,
            "starting_page_text": starting_page_content or "No content extracted."
        }
