"""Optional multi-paper retrieval-augmented generation layer."""

from app.rag.embeddings import EmbeddingError, EmbeddingProvider, build_embedding_provider
from app.rag.rag_pipeline import RAGDisabledError, RAGPipeline
from app.rag.retriever import RAGRetriever, RetrievedChunk
from app.rag.vector_store import JsonVectorStore, VectorRecord

__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "JsonVectorStore",
    "RAGDisabledError",
    "RAGPipeline",
    "RAGRetriever",
    "RetrievedChunk",
    "VectorRecord",
    "build_embedding_provider",
]
