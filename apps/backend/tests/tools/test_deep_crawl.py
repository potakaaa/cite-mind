import pytest
from unittest.mock import patch, MagicMock
from app.tools.deep_crawl import DeepCrawlTool
from app.tools.base import ToolExecutionError
import requests

@pytest.fixture
def mock_kg():
    # Setup mock knowledge graph
    with patch("app.services.knowledge_graph.KnowledgeGraphService") as mock:
        yield mock.return_value

@pytest.fixture
def mock_router():
    # Setup mock router
    with patch("app.llm.llm_router.LLMRouter") as mock:
        yield mock.return_value

class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        
    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.RequestException(f"Error: {self.status_code}")

@pytest.fixture
def mock_requests():
    with patch("app.tools.deep_crawl.requests.get") as mock_get:
        
        def side_effect(url, *args, **kwargs):
            if url == "https://example.com":
                html = "<html><title>Main</title><body>Hello World! <a href='/child1'>Link</a></body></html>"
                return MockResponse(html)
            elif url == "https://example.com/child1":
                html = "<html><title>Child 1</title><body>Child content! <a href='https://external.com'>Ext</a></body></html>"
                return MockResponse(html)
            elif url == "https://external.com":
                html = "<html><title>External</title><body>External content!</body></html>"
                return MockResponse(html)
            return MockResponse("", 404)
            
        mock_get.side_effect = side_effect
        yield mock_get

def test_deep_crawl_depth_0(mock_kg, mock_router, mock_requests):
    """Test deep crawl only fetches the main URL if max_depth=0."""
    tool = DeepCrawlTool()
    
    result = tool.execute(url="https://example.com", max_depth=0)
    
    # Assert output
    assert "Successfully crawled 1 pages" in result["message"]
    assert result["nodes_injected"] == 1
    assert result["edges_injected"] == 0
    
    # Assert requests
    assert mock_requests.call_count == 1
    
    # Assert graph injections
    mock_kg.upsert_node.assert_called_once()
    assert not mock_kg.upsert_edge.called

def test_deep_crawl_depth_1(mock_kg, mock_router, mock_requests):
    """Test deep crawl follows links once if max_depth=1."""
    tool = DeepCrawlTool()
    
    result = tool.execute(url="https://example.com", max_depth=1)
    
    # Should crawl: Main, Child1
    # Main has link to /child1 -> https://example.com/child1
    assert "Successfully crawled 2 pages" in result["message"]
    assert result["nodes_injected"] == 2
    assert result["edges_injected"] == 1
    
    # Assert requests (Main, Child1)
    assert mock_requests.call_count == 2
    
    # Assert graph injections
    assert mock_kg.upsert_node.call_count == 2
    mock_kg.upsert_edge.assert_called_once_with("https://example.com", "https://example.com/child1", "CITES")

def test_deep_crawl_depth_2(mock_kg, mock_router, mock_requests):
    """Test deep crawl follows links twice if max_depth=2."""
    tool = DeepCrawlTool()
    
    result = tool.execute(url="https://example.com", max_depth=2)
    
    # Should crawl: Main, Child1, External
    assert "Successfully crawled 3 pages" in result["message"]
    assert result["nodes_injected"] == 3
    assert result["edges_injected"] == 2
    
    # Assert requests (Main, Child1, External)
    assert mock_requests.call_count == 3
    
    assert mock_kg.upsert_node.call_count == 3
    assert mock_kg.upsert_edge.call_count == 2
