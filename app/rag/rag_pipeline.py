"""Optional question-answering workflow across multiple uploaded papers."""

from __future__ import annotations

from typing import Any

from config import settings
from app.llm import LLMRouter
from app.rag.retriever import RAGRetriever, RetrievedChunk
from app.services.document_service import DocumentService
from app.utils.logging import get_logger, log_failure


class RAGDisabledError(RuntimeError):
    """Raised when the optional RAG workflow is used while disabled."""


class RAGPipeline:
    """Index uploaded papers and answer questions using retrieved chunks."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        retriever: RAGRetriever | None = None,
        document_service: DocumentService | None = None,
        llm: LLMRouter | None = None,
    ) -> None:
        self.enabled = settings.rag_enabled if enabled is None else enabled
        self._retriever = retriever
        self.document_service = document_service or DocumentService()
        self.llm = llm or LLMRouter()
        self.logger = get_logger("app.rag.pipeline")

    @property
    def retriever(self) -> RAGRetriever:
        if self._retriever is None:
            self._retriever = RAGRetriever()
        return self._retriever

    def ingest_documents(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prepare and index multiple documents.

        Each item can contain `raw_text`, `pdf_path`, or `pdf_bytes` plus
        optional `pdf_filename` and metadata fields.
        """
        self._ensure_enabled()
        summaries: list[dict[str, Any]] = []
        for index, item in enumerate(documents, start=1):
            prepared = self.document_service.prepare_document(
                raw_text=item.get("raw_text"),
                pdf_path=item.get("pdf_path"),
                pdf_bytes=item.get("pdf_bytes"),
                pdf_filename=item.get("pdf_filename"),
            )
            source_file = prepared.get("source_file") or item.get("pdf_filename") or f"paper-{index}"
            paper_id = str(item.get("paper_id") or source_file or f"paper-{index}")
            metadata = {
                **dict(item.get("metadata") or {}),
                "source_type": prepared.get("source_type"),
                "source_file": source_file,
                "source_path": prepared.get("source_path"),
                "page_count": prepared.get("page_count"),
            }
            records = self.retriever.index_chunks(
                list(prepared.get("chunks", [])),
                paper_id=paper_id,
                source_metadata=metadata,
            )
            summaries.append(
                {
                    "paper_id": paper_id,
                    "source_file": source_file,
                    "chunk_count": len(records),
                    "page_count": prepared.get("page_count"),
                }
            )
            self.logger.info("Indexed paper '%s' for RAG (chunks=%s)", paper_id, len(records))
        return summaries

    def ingest_prepared_document(
        self,
        document: dict[str, Any],
        *,
        paper_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Index a document that was already prepared by DocumentService."""
        self._ensure_enabled()
        source_file = document.get("source_file") or paper_id
        records = self.retriever.index_chunks(
            list(document.get("chunks", [])),
            paper_id=paper_id,
            source_metadata={
                **(metadata or {}),
                "source_type": document.get("source_type"),
                "source_file": source_file,
                "source_path": document.get("source_path"),
                "page_count": document.get("page_count"),
            },
        )
        return {
            "paper_id": paper_id,
            "source_file": source_file,
            "chunk_count": len(records),
            "page_count": document.get("page_count"),
        }

    def ask(
        self,
        question: str,
        *,
        provider: str | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """Answer a user question using retrieved chunk context."""
        self._ensure_enabled()
        matches = self.retriever.retrieve(question, top_k=top_k or settings.rag_top_k)
        if not matches:
            return {
                "answer": "No indexed paper chunks were available for retrieval.",
                "sources": [],
                "context": "",
            }

        context = self.retriever.format_context(matches, max_chars=settings.rag_context_max_chars)
        prompt = _build_rag_prompt(question=question, context=context, sources=matches)
        try:
            answer = self.llm.generate(prompt=prompt, provider=provider, task_type="rag_qa")
        except Exception as exc:
            log_failure(self.logger, "rag_answer_generation", exc)
            raise

        return {
            "answer": answer,
            "sources": [_source_payload(match) for match in matches],
            "context": context,
        }

    def clear(self) -> None:
        self.retriever.vector_store.clear()

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise RAGDisabledError("The optional RAG layer is disabled. Set RAG_ENABLED=true to use it.")


def _build_rag_prompt(question: str, context: str, sources: list[RetrievedChunk]) -> str:
    source_lines = []
    for index, chunk in enumerate(sources, start=1):
        metadata = chunk.metadata
        source_lines.append(
            f"[{index}] source_file={metadata.get('source_file')}; "
            f"page_start={metadata.get('page_start')}; chunk_id={metadata.get('chunk_id')}; "
            f"score={chunk.score:.3f}"
        )

    return (
        "You are Cite Mind's cross-paper research assistant. Answer the user using only the retrieved "
        "paper chunks below. If the chunks do not contain enough evidence, say what is missing. "
        "Cite source bracket numbers like [1] when making claims.\n\n"
        f"Question:\n{question.strip()}\n\n"
        f"Retrieved source metadata:\n{chr(10).join(source_lines)}\n\n"
        f"Retrieved context:\n{context}\n\n"
        "Answer with a concise synthesis followed by a short Sources section."
    )


def _source_payload(chunk: RetrievedChunk) -> dict[str, Any]:
    metadata = dict(chunk.metadata)
    return {
        "id": chunk.id,
        "score": chunk.score,
        "text": chunk.text,
        "metadata": metadata,
    }
