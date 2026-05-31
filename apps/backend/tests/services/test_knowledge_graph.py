import pytest
import sqlite3
import json
from app.services.knowledge_graph import KnowledgeGraphService, cosine_similarity

# Dummy embedding function for deterministic tests
def dummy_embed(text: str) -> list[float]:
    if "Cars" in text or "Automobiles" in text:
        return [1.0, 0.0, 0.0]
    elif "Apples" in text or "Fruits" in text:
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]

import tempfile
import os

@pytest.fixture
def kg_service():
    """Returns a KnowledgeGraphService backed by a temporary SQLite file."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        db_path = tmp.name
        
    service = KnowledgeGraphService(db_path=db_path, embedding_fn=dummy_embed)
    yield service
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass

def test_db_initialization(kg_service):
    """Test that the DB is set up correctly with all columns, including embeddings."""
    with kg_service.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(nodes)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        assert 'id' in columns
        assert 'name' in columns
        assert 'attributes' in columns
        assert 'is_pinned' in columns
        assert 'embedding' in columns

def test_upsert_and_get_node(kg_service):
    """Test basic CRUD operations for nodes."""
    node_id = kg_service.upsert_node("Concept", "Machine Learning", {"status": "active"})
    assert node_id == 1
    
    # Retrieve
    node = kg_service.get_node_by_name("Concept", "Machine Learning")
    assert node is not None
    assert node.id == 1
    assert node.name == "Machine Learning"
    assert node.attributes.get("status") == "active"
    
    # Upsert existing (should merge attributes)
    node_id_2 = kg_service.upsert_node("Concept", "Machine Learning", {"new_attr": 123})
    assert node_id_2 == 1 # ID remains same
    
    node = kg_service.get_node_by_name("Concept", "Machine Learning")
    assert node.attributes.get("status") == "active"
    assert node.attributes.get("new_attr") == 123

def test_upsert_and_get_edge(kg_service):
    """Test creating and retrieving directional edges."""
    node1 = kg_service.upsert_node("Concept", "AI")
    node2 = kg_service.upsert_node("Concept", "ML")
    
    edge_id = kg_service.upsert_edge(node1, node2, "INCLUDES", {"confidence": 0.99})
    assert edge_id == 1
    
    # Test neighborhood retrieval
    nhood = kg_service.get_neighborhood(node1)
    assert nhood["center"]["name"] == "AI"
    assert len(nhood["outgoing"]) == 1
    assert nhood["outgoing"][0]["target"]["name"] == "ML"
    assert nhood["outgoing"][0]["relation"] == "INCLUDES"

def test_cosine_similarity():
    """Test the pure Python cosine similarity math."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0
    
    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == 0.0
    
    v4 = [0.5, 0.5, 0.0]
    assert round(cosine_similarity(v1, v4), 2) == 0.71

def test_vector_search_semantic(kg_service):
    """Test semantic search relying on mock embeddings."""
    # Insert nodes. Dummy embed returns [1, 0, 0] for Cars/Automobiles
    kg_service.upsert_node("Concept", "Automobiles")
    # Dummy embed returns [0, 1, 0] for Apples/Fruits
    kg_service.upsert_node("Concept", "Apples")
    # Dummy embed returns [0, 0, 1] for anything else
    kg_service.upsert_node("Concept", "Random Thing")
    
    # Search for 'Cars'. The query vector will be [1, 0, 0].
    # Automobiles vector is [1, 0, 0]. Cosine sim = 1.0
    results = kg_service.search_nodes_semantic("Cars", limit=2)
    assert len(results) >= 1
    assert results[0].name == "Automobiles"

    # Search for 'Fruits'. Query vector is [0, 1, 0]
    # Apples vector is [0, 1, 0]. Cosine sim = 1.0
    results2 = kg_service.search_nodes_semantic("Fruits", limit=2)
    assert len(results2) >= 1
    assert results2[0].name == "Apples"

def test_get_recent_nodes(kg_service):
    """Test fetching recently added nodes."""
    kg_service.upsert_node("Concept", "Node 1")
    kg_service.upsert_node("Concept", "Node 2")
    kg_service.upsert_node("Concept", "Node 3")
    
    recent = kg_service.get_recent_nodes(limit=2)
    assert len(recent) == 2
    assert recent[0].name == "Node 3"
    assert recent[1].name == "Node 2"
