from typing import Any
from .base import BaseTool, ToolExecutionError


class UpdateGraphTool(BaseTool):
    """Tool for adding semantic nodes (Concepts, Methodologies, Gaps) and linking them to Papers."""

    name = "UpdateGraph"
    description = (
        "Add semantic concepts, research gaps, or methodologies to the persistent knowledge graph "
        "and link them to specific papers. Use this to actively synthesize information you read."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "node_type": {
                "type": "string",
                "description": "The type of node you are creating (e.g. 'Concept', 'ResearchGap', 'Methodology')."
            },
            "node_name": {
                "type": "string",
                "description": "A short, unique name for the concept or gap (e.g., 'Isolated Sign Language Recognition' or 'My Paper Summary')."
            },
            "attributes": {
                "type": "object",
                "description": "Optional JSON attributes for the node (e.g., description, context, or the full rundown of a paper)."
            },
            "linked_paper_title": {
                "type": "string",
                "description": "Optional exact title of an existing Paper in the graph to link this concept to."
            },
            "relation_type": {
                "type": "string",
                "description": "Optional relation type (e.g. 'ADDRESSES', 'USES', 'CONTRADICTS', 'SUPPORTS') if linked_paper_title is provided."
            }
        },
        "required": ["node_type", "node_name"]
    }

    def __init__(self):
        from app.services.knowledge_graph import KnowledgeGraphService
        from app.llm.llm_router import LLMRouter
        
        self.router = LLMRouter()
        self.kg_service = KnowledgeGraphService(
            embedding_fn=self.router.generate_embedding
        )

    def execute(self, **kwargs: Any) -> Any:
        node_type = kwargs.get("node_type")
        node_name = kwargs.get("node_name")
        linked_paper_title = kwargs.get("linked_paper_title")
        relation_type = kwargs.get("relation_type")
        attributes = kwargs.get("attributes", {})

        if not all([node_type, node_name]):
            raise ToolExecutionError("Missing required arguments (node_type, node_name) for UpdateGraph.")

        try:
            # Upsert the new semantic node
            semantic_node_id = self.kg_service.upsert_node(node_type, node_name, attributes)
            
            # Link them if requested
            if linked_paper_title and relation_type:
                paper_node = self.kg_service.get_node_by_name("Paper", linked_paper_title)
                if not paper_node:
                    return f"Successfully created {node_type} '{node_name}', but failed to link: No paper found with title '{linked_paper_title}'."
                
                self.kg_service.upsert_edge(
                    source_id=paper_node.id,
                    target_id=semantic_node_id,
                    relation=relation_type
                )
                return f"Successfully created and linked '{linked_paper_title}' to {node_type} '{node_name}' via {relation_type}."
            
            # If it's a standalone node (like a user's personal project rundown), automatically PIN it so it stays in context.
            self.kg_service.pin_node(semantic_node_id)
            return f"Successfully created standalone {node_type} '{node_name}' and pinned it to Core Memory!"
        except Exception as exc:
            raise ToolExecutionError(f"Failed to update knowledge graph: {exc}") from exc


class QueryGraphTool(BaseTool):
    """Tool for querying the persistent knowledge graph to recall context across sessions."""

    name = "QueryGraph"
    description = (
        "Query the persistent knowledge graph to find previously discovered concepts, papers, or gaps. "
        "Use this if the user asks about past research or requests a summary of existing knowledge."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional keyword to search for in node names. Leave empty to retrieve the most recently added nodes."
            },
            "limit": {
                "type": "integer",
                "description": "Max edges to return per node to avoid context blowout (default 20)."
            },
            "offset": {
                "type": "integer",
                "description": "Offset for pagination (default 0)."
            },
            "relation_filter": {
                "type": "string",
                "description": "Optional relation to filter by (e.g., 'AUTHORED', 'CITES')."
            }
        },
        "required": []
    }

    def __init__(self):
        from app.services.knowledge_graph import KnowledgeGraphService
        from app.llm.llm_router import LLMRouter
        
        self.router = LLMRouter()
        self.kg_service = KnowledgeGraphService(
            embedding_fn=self.router.generate_embedding
        )

    def execute(self, **kwargs: Any) -> Any:
        query = kwargs.get("query")
        limit = kwargs.get("limit", 20)
        offset = kwargs.get("offset", 0)
        relation_filter = kwargs.get("relation_filter")
            
        try:
            if not query:
                nodes = self.kg_service.get_recent_nodes(limit=limit)
                if not nodes:
                    return "The knowledge graph is currently empty."
            else:
                nodes = self.kg_service.search_nodes_semantic(query, limit=limit)
                if not nodes:
                    return f"No nodes found matching '{query}'."
                
            results = []
            for node in nodes:
                nhood = self.kg_service.get_neighborhood(
                    node.id, 
                    limit=limit, 
                    offset=offset, 
                    relation_filter=relation_filter
                )
                results.append(nhood)
                
            return results
        except Exception as exc:
            raise ToolExecutionError(f"Failed to query knowledge graph: {exc}") from exc


class MergeNodesTool(BaseTool):
    """Tool for merging a duplicate node into a primary node to keep the graph clean."""

    name = "MergeNodes"
    description = (
        "Merge a duplicate semantic node (e.g. 'ML') into a primary node (e.g. 'Machine Learning'). "
        "This moves all edges to the primary node and deletes the duplicate."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "primary_node_type": {"type": "string", "description": "Type of the primary node."},
            "primary_node_name": {"type": "string", "description": "Exact name of the primary node."},
            "duplicate_node_type": {"type": "string", "description": "Type of the duplicate node."},
            "duplicate_node_name": {"type": "string", "description": "Exact name of the duplicate node."}
        },
        "required": ["primary_node_type", "primary_node_name", "duplicate_node_type", "duplicate_node_name"]
    }

    def __init__(self):
        from app.services.knowledge_graph import KnowledgeGraphService
        self.kg_service = KnowledgeGraphService()

    def execute(self, **kwargs: Any) -> Any:
        try:
            primary = self.kg_service.get_node_by_name(kwargs["primary_node_type"], kwargs["primary_node_name"])
            duplicate = self.kg_service.get_node_by_name(kwargs["duplicate_node_type"], kwargs["duplicate_node_name"])
            if not primary or not duplicate:
                return "Error: Could not find one or both nodes."
            success = self.kg_service.merge_nodes(primary.id, duplicate.id)
            return "Merge successful." if success else "Merge failed (maybe they are the same node)."
        except Exception as exc:
            raise ToolExecutionError(f"Failed to merge nodes: {exc}") from exc


class DeleteNodeTool(BaseTool):
    """Tool for deleting a bad or irrelevant node."""

    name = "DeleteNode"
    description = "Delete a node from the knowledge graph entirely if it is irrelevant or malformed."
    parameters_schema = {
        "type": "object",
        "properties": {
            "node_type": {"type": "string", "description": "The type of the node."},
            "node_name": {"type": "string", "description": "The exact name of the node."}
        },
        "required": ["node_type", "node_name"]
    }

    def __init__(self):
        from app.services.knowledge_graph import KnowledgeGraphService
        self.kg_service = KnowledgeGraphService()

    def execute(self, **kwargs: Any) -> Any:
        try:
            node = self.kg_service.get_node_by_name(kwargs["node_type"], kwargs["node_name"])
            if not node:
                return f"Error: No {kwargs['node_type']} named '{kwargs['node_name']}' found."
            success = self.kg_service.delete_node(node.id)
            return f"Node '{kwargs['node_name']}' deleted." if success else "Failed to delete node."
        except Exception as exc:
            raise ToolExecutionError(f"Failed to delete node: {exc}") from exc


class PinNodeTool(BaseTool):
    """Tool for pinning a node to Core Memory."""

    name = "PinNode"
    description = "Pin a very important node to your Core Memory so it stays in your context window across all future queries."
    parameters_schema = {
        "type": "object",
        "properties": {
            "node_type": {"type": "string", "description": "The type of the node."},
            "node_name": {"type": "string", "description": "The exact name of the node."}
        },
        "required": ["node_type", "node_name"]
    }

    def __init__(self):
        from app.services.knowledge_graph import KnowledgeGraphService
        self.kg_service = KnowledgeGraphService()

    def execute(self, **kwargs: Any) -> Any:
        try:
            node = self.kg_service.get_node_by_name(kwargs["node_type"], kwargs["node_name"])
            if not node:
                return f"Error: No {kwargs['node_type']} named '{kwargs['node_name']}' found."
            success = self.kg_service.pin_node(node.id)
            return f"Node '{kwargs['node_name']}' pinned to Core Memory." if success else "Failed to pin node."
        except Exception as exc:
            raise ToolExecutionError(f"Failed to pin node: {exc}") from exc


class UnpinNodeTool(BaseTool):
    """Tool for unpinning a node from Core Memory."""

    name = "UnpinNode"
    description = "Unpin a node from your Core Memory when it is no longer relevant to your current research focus."
    parameters_schema = {
        "type": "object",
        "properties": {
            "node_type": {"type": "string", "description": "The type of the node."},
            "node_name": {"type": "string", "description": "The exact name of the node."}
        },
        "required": ["node_type", "node_name"]
    }

    def __init__(self):
        from app.services.knowledge_graph import KnowledgeGraphService
        self.kg_service = KnowledgeGraphService()

    def execute(self, **kwargs: Any) -> Any:
        try:
            node = self.kg_service.get_node_by_name(kwargs["node_type"], kwargs["node_name"])
            if not node:
                return f"Error: No {kwargs['node_type']} named '{kwargs['node_name']}' found."
            success = self.kg_service.unpin_node(node.id)
            return f"Node '{kwargs['node_name']}' unpinned from Core Memory." if success else "Failed to unpin node."
        except Exception as exc:
            raise ToolExecutionError(f"Failed to unpin node: {exc}") from exc
