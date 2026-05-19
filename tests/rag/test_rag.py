from __future__ import annotations

from pathlib import Path

from app.rag.embeddings import HashingEmbeddingProvider
from app.rag.rag_pipeline import RAGPipeline
from app.rag.retriever import RAGRetriever
from app.rag.vector_store import JsonVectorStore


class FakeLLM:
    def __init__(self) -> None:
        self.prompt = ""

    def generate(self, prompt: str, provider: str | None = None, task_type: str | None = None) -> str:
        self.prompt = prompt
        return "The evidence says neural retrieval improves question answering. [1]"


def test_hashing_embeddings_are_deterministic_and_normalized():
    provider = HashingEmbeddingProvider(dimensions=16)

    first = provider.embed_query("retrieval augmented generation")
    second = provider.embed_query("retrieval augmented generation")

    assert first == second
    assert len(first) == 16
    assert any(value != 0 for value in first)


def test_vector_store_persists_records_and_retrieves_by_similarity(tmp_path: Path):
    retriever = RAGRetriever(
        embedding_provider=HashingEmbeddingProvider(dimensions=64),
        vector_store=JsonVectorStore(persist_dir=tmp_path),
    )
    retriever.index_chunks(
        [
            {
                "chunk_id": 1,
                "source_file": "paper-a.pdf",
                "page_start": 2,
                "page_end": 2,
                "char_start": 10,
                "char_end": 80,
                "text": "Graph neural networks classify citation edges.",
            },
            {
                "chunk_id": 2,
                "source_file": "paper-b.pdf",
                "page_start": 5,
                "page_end": 5,
                "char_start": 0,
                "char_end": 60,
                "text": "Interview protocols were used for qualitative coding.",
            },
        ],
        paper_id="paper-a",
    )

    matches = retriever.retrieve("citation graph neural network", top_k=1)

    assert len(matches) == 1
    assert matches[0].metadata["source_file"] == "paper-a.pdf"
    assert matches[0].metadata["page_start"] == 2
    assert "citation" in matches[0].text.lower()


def test_rag_pipeline_answers_with_retrieved_source_metadata(tmp_path: Path):
    fake_llm = FakeLLM()
    pipeline = RAGPipeline(
        enabled=True,
        llm=fake_llm,  # type: ignore[arg-type]
        retriever=RAGRetriever(
            embedding_provider=HashingEmbeddingProvider(dimensions=64),
            vector_store=JsonVectorStore(persist_dir=tmp_path),
        ),
    )
    pipeline.ingest_documents(
        [
            {
                "paper_id": "rag-paper",
                "raw_text": (
                    "Neural retrieval systems answer questions by retrieving passages "
                    "from indexed documents before synthesis."
                ),
            },
            {
                "paper_id": "survey-paper",
                "raw_text": "Survey methodology depends on sampling and response bias controls.",
            },
        ]
    )

    result = pipeline.ask("How does neural retrieval help question answering?", top_k=2)

    assert "neural retrieval" in result["answer"]
    assert result["sources"]
    assert result["sources"][0]["metadata"]["paper_id"] in {"rag-paper", "survey-paper"}
    assert "Retrieved context" in fake_llm.prompt
    assert "source_file" in fake_llm.prompt
