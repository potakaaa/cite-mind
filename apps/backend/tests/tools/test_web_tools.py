import pytest
from unittest.mock import patch, MagicMock
from app.tools.web_fetch import ReadUrlTool
from app.tools.web_search import WebSearchTool

def test_web_search_tool_success():
    """Test WebSearchTool parses DDG HTML correctly."""
    tool = WebSearchTool()
    
    # DDGS.text() yields dictionaries
    mock_results = [
        {"title": "Example Title", "href": "https://example.com", "body": "This is a snippet about AI."}
    ]
    
    with patch("app.tools.web_search.DDGS") as MockDDGS:
        mock_ddgs_instance = MockDDGS.return_value.__enter__.return_value
        mock_ddgs_instance.text.return_value = mock_results
        
        result = tool.execute(query="Artificial Intelligence")
        
        assert "This is a snippet about AI." in result[0]["body"]
        assert "https://example.com" in result[0]["href"]

def test_web_search_tool_failure():
    """Test WebSearchTool handles errors properly."""
    tool = WebSearchTool()
    
    with patch("app.tools.web_search.DDGS") as MockDDGS:
        mock_ddgs_instance = MockDDGS.return_value.__enter__.return_value
        mock_ddgs_instance.text.side_effect = Exception("403 Forbidden")
        
        from app.tools.base import ToolExecutionError
        with pytest.raises(ToolExecutionError) as excinfo:
            tool.execute(query="Artificial Intelligence")
        assert "403 Forbidden" in str(excinfo.value)

def test_fetch_url_content_tool_success():
    """Test ReadUrlTool extracts text from HTML without scripts."""
    tool = ReadUrlTool()
    
    mock_html = """
    <html>
        <head><script>alert('bad');</script></head>
        <body>
            <h1>Main Title</h1>
            <p>Some useful text.</p>
        </body>
    </html>
    """
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response
        
        result = tool.execute(url="https://example.com")
        
        assert "Main Title" in result["content"]
        assert "Some useful text." in result["content"]
        # Ensure scripts are stripped
        assert "alert" not in result["content"]
