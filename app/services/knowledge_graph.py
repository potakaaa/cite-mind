import sqlite3
import json
from typing import Any, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
import math

from config import settings

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


@dataclass
class GraphNode:
    id: int | None
    type: str
    name: str
    attributes: dict[str, Any]


@dataclass
class GraphEdge:
    id: int | None
    source_id: int
    target_id: int
    relation: str
    attributes: dict[str, Any]


class KnowledgeGraphServiceError(Exception):
    pass


class KnowledgeGraphService:
    """Service for interacting with the SQLite Persistent Knowledge Graph."""

    def __init__(
        self, 
        db_path: str = "./data/db/knowledge_graph.db", 
        embedding_fn: Callable[[str], list[float]] | None = None
    ):
        self.db_path = Path(db_path)
        self.embedding_fn = embedding_fn
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.setup_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def setup_db(self) -> None:
        """Initialize the graph schema."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    attributes TEXT,
                    is_pinned BOOLEAN DEFAULT 0,
                    UNIQUE(type, name)
                )
            ''')
            # Handle migration if is_pinned is missing
            try:
                conn.execute("ALTER TABLE nodes ADD COLUMN is_pinned BOOLEAN DEFAULT 0")
            except sqlite3.OperationalError:
                pass # Column already exists
                
            # Handle migration for embeddings
            try:
                conn.execute("ALTER TABLE nodes ADD COLUMN embedding TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists
                
            conn.execute('''
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    relation TEXT NOT NULL,
                    attributes TEXT,
                    FOREIGN KEY(source_id) REFERENCES nodes(id),
                    FOREIGN KEY(target_id) REFERENCES nodes(id),
                    UNIQUE(source_id, target_id, relation)
                )
            ''')
            # Add an index for quicker name lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)')

    def upsert_node(self, node_type: str, name: str, attributes: dict[str, Any] | None = None) -> int:
        """Insert a node or update its attributes if it exists. Returns node ID."""
        attributes = attributes or {}
        attr_json = json.dumps(attributes)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if it exists
            cursor.execute("SELECT id, attributes FROM nodes WHERE type = ? AND name = ?", (node_type, name))
            row = cursor.fetchone()
            
            if row:
                node_id = row['id']
                existing_attrs = json.loads(row['attributes'] or "{}")
                existing_attrs.update(attributes)
                
                # Check if we need to update embedding
                embed_val = row.get('embedding') if 'embedding' in row.keys() else None
                if not embed_val and self.embedding_fn:
                    embed_vector = self.embedding_fn(f"{node_type} {name} {json.dumps(existing_attrs)}")
                    embed_val = json.dumps(embed_vector)
                    
                if embed_val:
                    cursor.execute(
                        "UPDATE nodes SET attributes = ?, embedding = ? WHERE id = ?",
                        (json.dumps(existing_attrs), embed_val, node_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE nodes SET attributes = ? WHERE id = ?",
                        (json.dumps(existing_attrs), node_id)
                    )
                return node_id
            else:
                embed_val = None
                if self.embedding_fn:
                    embed_vector = self.embedding_fn(f"{node_type} {name} {attr_json}")
                    embed_val = json.dumps(embed_vector)
                    
                cursor.execute(
                    "INSERT INTO nodes (type, name, attributes, embedding) VALUES (?, ?, ?, ?)",
                    (node_type, name, attr_json, embed_val)
                )
                return cursor.lastrowid

    def upsert_edge(self, source_id: int, target_id: int, relation: str, attributes: dict[str, Any] | None = None) -> int:
        """Insert an edge or update its attributes if it exists. Returns edge ID."""
        attributes = attributes or {}
        attr_json = json.dumps(attributes)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, attributes FROM edges WHERE source_id = ? AND target_id = ? AND relation = ?", 
                (source_id, target_id, relation)
            )
            row = cursor.fetchone()
            
            if row:
                edge_id = row['id']
                existing_attrs = json.loads(row['attributes'] or "{}")
                existing_attrs.update(attributes)
                cursor.execute(
                    "UPDATE edges SET attributes = ? WHERE id = ?",
                    (json.dumps(existing_attrs), edge_id)
                )
                return edge_id
            else:
                cursor.execute(
                    "INSERT INTO edges (source_id, target_id, relation, attributes) VALUES (?, ?, ?, ?)",
                    (source_id, target_id, relation, attr_json)
                )
                return cursor.lastrowid

    def search_nodes(self, query: str, limit: int = 10) -> list[GraphNode]:
        """Search for nodes by name using simple LIKE."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nodes WHERE name LIKE ? LIMIT ?",
                (f"%{query}%", limit)
            )
            return [
                GraphNode(
                    id=row['id'],
                    type=row['type'],
                    name=row['name'],
                    attributes=json.loads(row['attributes'] or "{}")
                )
                for row in cursor.fetchall()
            ]

    def search_nodes_semantic(self, query: str, limit: int = 5) -> list[GraphNode]:
        """Search for nodes using Cosine Similarity on vectors."""
        if not self.embedding_fn:
            # Fallback to simple text search if no embedding function is provided
            return self.search_nodes(query, limit)
            
        query_vector = self.embedding_fn(query)
        if not query_vector:
            return self.search_nodes(query, limit)
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE embedding IS NOT NULL")
            rows = cursor.fetchall()
            
            scored_nodes = []
            for row in rows:
                try:
                    node_vec = json.loads(row['embedding'])
                    score = cosine_similarity(query_vector, node_vec)
                    scored_nodes.append((score, row))
                except (ValueError, TypeError):
                    continue
                    
            scored_nodes.sort(key=lambda x: x[0], reverse=True)
            
            return [
                GraphNode(
                    id=r['id'],
                    type=r['type'],
                    name=r['name'],
                    attributes=json.loads(r['attributes'] or "{}")
                )
                for score, r in scored_nodes[:limit]
            ]

    def get_node_by_name(self, node_type: str, name: str) -> GraphNode | None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE type = ? AND name = ?", (node_type, name))
            row = cursor.fetchone()
            if row:
                return GraphNode(
                    id=row['id'],
                    type=row['type'],
                    name=row['name'],
                    attributes=json.loads(row['attributes'] or "{}")
                )
            return None

    def get_recent_nodes(self, limit: int = 10) -> list[GraphNode]:
        """Fetch the most recently added nodes (by highest ID)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes ORDER BY id DESC LIMIT ?", (limit,))
            return [
                GraphNode(
                    id=row['id'],
                    type=row['type'],
                    name=row['name'],
                    attributes=json.loads(row['attributes'] or "{}")
                )
                for row in cursor.fetchall()
            ]

    def get_neighborhood(self, node_id: int, limit: int = 50, offset: int = 0, relation_filter: str | None = None) -> dict[str, Any]:
        """Get the 1-hop neighborhood of a node with pagination and filtering."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the center node
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            center_row = cursor.fetchone()
            if not center_row:
                return {}
                
            center = GraphNode(
                id=center_row['id'], type=center_row['type'], 
                name=center_row['name'], attributes=json.loads(center_row['attributes'] or "{}")
            )
            
            rel_cond = "AND e.relation = ?" if relation_filter else ""
            params_inc = (node_id, relation_filter, limit, offset) if relation_filter else (node_id, limit, offset)
            
            # Get incoming edges (where target is this node)
            cursor.execute(f'''
                SELECT e.*, n.type as source_type, n.name as source_name, n.attributes as source_attrs
                FROM edges e
                JOIN nodes n ON e.source_id = n.id
                WHERE e.target_id = ? {rel_cond}
                LIMIT ? OFFSET ?
            ''', params_inc)
            incoming = cursor.fetchall()
            
            # Get outgoing edges (where source is this node)
            cursor.execute(f'''
                SELECT e.*, n.type as target_type, n.name as target_name, n.attributes as target_attrs
                FROM edges e
                JOIN nodes n ON e.target_id = n.id
                WHERE e.source_id = ? {rel_cond}
                LIMIT ? OFFSET ?
            ''', params_inc)
            outgoing = cursor.fetchall()
            
            return {
                "center": asdict(center),
                "incoming": [
                    {
                        "relation": r["relation"],
                        "edge_attributes": json.loads(r["attributes"] or "{}"),
                        "source": {
                            "id": r["source_id"],
                            "type": r["source_type"],
                            "name": r["source_name"],
                            "attributes": json.loads(r["source_attrs"] or "{}")
                        }
                    } for r in incoming
                ],
                "outgoing": [
                    {
                        "relation": r["relation"],
                        "edge_attributes": json.loads(r["attributes"] or "{}"),
                        "target": {
                            "id": r["target_id"],
                            "type": r["target_type"],
                            "name": r["target_name"],
                            "attributes": json.loads(r["target_attrs"] or "{}")
                        }
                    } for r in outgoing
                ]
            }

    def delete_node(self, node_id: int) -> bool:
        """Deletes a node and all connected edges."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
            cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            return cursor.rowcount > 0

    def merge_nodes(self, primary_id: int, duplicate_id: int) -> bool:
        """Merges duplicate_id into primary_id, moving all edges and deleting the duplicate."""
        if primary_id == duplicate_id:
            return False
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Move outgoing edges (IGNORE ignores unique constraint violations if edge already exists)
            cursor.execute("UPDATE OR IGNORE edges SET source_id = ? WHERE source_id = ?", (primary_id, duplicate_id))
            # Move incoming edges
            cursor.execute("UPDATE OR IGNORE edges SET target_id = ? WHERE target_id = ?", (primary_id, duplicate_id))
            
            # Delete the duplicate node and any edges that weren't moved due to UNIQUE conflicts
            cursor.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (duplicate_id, duplicate_id))
            cursor.execute("DELETE FROM nodes WHERE id = ?", (duplicate_id,))
            return True

    def pin_node(self, node_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE nodes SET is_pinned = 1 WHERE id = ?", (node_id,))
            return cursor.rowcount > 0

    def unpin_node(self, node_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE nodes SET is_pinned = 0 WHERE id = ?", (node_id,))
            return cursor.rowcount > 0

    def get_pinned_nodes(self) -> list[GraphNode]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE is_pinned = 1")
            return [
                GraphNode(
                    id=row['id'], type=row['type'], 
                    name=row['name'], attributes=json.loads(row['attributes'] or "{}")
                ) for row in cursor.fetchall()
            ]
