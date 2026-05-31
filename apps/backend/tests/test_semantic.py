import json
from app.services.knowledge_graph import KnowledgeGraphService
from app.llm.llm_router import LLMRouter

def main():
    print("Initializing LLM Router and Knowledge Graph Service...")
    router = LLMRouter()
    kg = KnowledgeGraphService(embedding_fn=router.generate_embedding)

    print("\n[1] Inserting sample nodes...")
    # This will now automatically call router.generate_embedding() under the hood!
    kg.upsert_node("Concept", "Sign Language Recognition", {"description": "A field of AI focused on recognizing sign language gestures."})
    kg.upsert_node("Concept", "Photosynthesis", {"description": "The process by which plants convert sunlight into energy."})
    kg.upsert_node("Concept", "Machine Learning", {"description": "Training neural networks and algorithms on large datasets."})
    
    query = "Hand movements and gestures"
    print(f"\n[2] Performing SEMANTIC SEARCH for: '{query}'")
    
    results = kg.search_nodes_semantic(query, limit=2)
    
    print("\n--- RESULTS ---")
    if not results:
        print("No results found.")
    for r in results:
        print(f"Node: {r.name}")
        score = r.attributes.get('similarity_score', 'N/A')
        print(f"Score: {score:.4f}" if isinstance(score, float) else f"Score: {score}")
        print(f"Desc: {r.attributes.get('description', '')}")
        print("-" * 15)

if __name__ == "__main__":
    main()
