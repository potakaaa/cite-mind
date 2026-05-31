import pytest
from unittest.mock import MagicMock, patch
from app.tools.knowledge_graph_tools import UpdateGraphTool, QueryGraphTool, PinNodeTool
from app.services.knowledge_graph import GraphNode

@pytest.fixture
def mock_kg_service():
    return MagicMock()

def test_update_graph_tool_standalone(mock_kg_service):
    """Test saving a standalone node that gets automatically pinned."""
    tool = UpdateGraphTool()
    tool.kg_service = mock_kg_service # Inject mock
    
    # Mock upsert_node returning ID 1
    mock_kg_service.upsert_node.return_value = 1
    
    tool = UpdateGraphTool.__new__(UpdateGraphTool)
    tool.kg_service = mock_kg_service # Inject mock
    
    result = tool.execute(node_type="Concept", node_name="My Notes", attributes={"desc": "Important"})
    
    mock_kg_service.upsert_node.assert_called_once_with("Concept", "My Notes", {"desc": "Important"})
    mock_kg_service.execute_query.return_value = None # Assuming pinning uses execute_query
    
    assert "Successfully created standalone Concept 'My Notes'" in result

def test_update_graph_tool_linked(mock_kg_service):
    """Test saving a node that links to a paper."""
    tool = UpdateGraphTool.__new__(UpdateGraphTool)
    tool.kg_service = mock_kg_service
    
    mock_kg_service.upsert_node.return_value = 2
    mock_paper = GraphNode(id=1, type="Paper", name="Attention Is All You Need", attributes={})
    mock_kg_service.get_node_by_name.return_value = mock_paper
    
    result = tool.execute(
        node_type="Methodology", 
        node_name="Transformers", 
        linked_paper_title="Attention Is All You Need", 
        relation_type="ADDRESSES"
    )
    
    mock_kg_service.upsert_edge.assert_called_once_with(source_id=1, target_id=2, relation="ADDRESSES")
    assert "Successfully created and linked 'Attention Is All You Need' to Methodology 'Transformers'" in result

def test_query_graph_tool_recent(mock_kg_service):
    """Test querying the graph with no query falls back to recent nodes."""
    tool = QueryGraphTool.__new__(QueryGraphTool)
    tool.kg_service = mock_kg_service
    
    from app.services.knowledge_graph import GraphNode
    mock_node = GraphNode(id=1, type="Concept", name="Recent Node", attributes={})
    mock_kg_service.get_recent_nodes.return_value = [mock_node]
    mock_kg_service.get_neighborhood.return_value = {"center": mock_node, "incoming": [], "outgoing": []}
    
    result = tool.execute(query="")
    
    mock_kg_service.get_recent_nodes.assert_called_once()
    mock_kg_service.get_neighborhood.assert_called_once()
    assert isinstance(result, list)

def test_query_graph_tool_semantic(mock_kg_service):
    """Test querying the graph with a query uses semantic search."""
    tool = QueryGraphTool.__new__(QueryGraphTool)
    tool.kg_service = mock_kg_service
    
    mock_node = GraphNode(id=2, type="Concept", name="Semantic Match", attributes={})
    mock_kg_service.search_nodes_semantic.return_value = [mock_node]
    mock_kg_service.get_neighborhood.return_value = {"center": mock_node, "incoming": [], "outgoing": []}
    
    result = tool.execute(query="Match something")
    
    mock_kg_service.search_nodes_semantic.assert_called_once()
    assert isinstance(result, list)

def test_pin_node_tool(mock_kg_service):
    """Test pinning a node."""
    tool = PinNodeTool.__new__(PinNodeTool)
    tool.kg_service = mock_kg_service
    
    mock_node = GraphNode(id=5, type="Concept", name="Important", attributes={})
    mock_kg_service.get_node_by_name.return_value = mock_node
    # Note: I am mocking execute_query because pin_node is implemented differently
    
    result = tool.execute(node_type="Concept", node_name="Important")
    
    assert "pinned to Core Memory" in result
