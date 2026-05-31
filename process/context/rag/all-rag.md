# RAG Context

This is the canonical retrieval/document-ingestion context entrypoint for cite-mind.

Read it after `process/context/all-context.md` when the task touches uploaded documents, PDF extraction, chunking, retrieval, or grounded response behavior.

## Scope

This group covers:

- PDF validation and extraction
- text chunking and prepared-document flow
- vector indexing and retrieval
- optional RAG question answering

It does not cover:

- general frontend UI behavior
- broad provider-routing rules unrelated to retrieval
- planning artifacts

## Read When

Read this entrypoint when:

- changing `DocumentService`
- modifying PDF extraction or chunking behavior
- enabling or debugging `RAGPipeline`
- changing embeddings, vector storage, or source formatting

## RAG Overview

- The retrieval layer is optional and controlled by `RAG_ENABLED`.
- Document preparation flows through `DocumentService.prepare_document(...)`.
- PDFs can enter from:
  - a filesystem path
  - uploaded bytes plus filename
- `PDFReader` uses PyMuPDF first and falls back to pdfplumber if needed.
- Extracted text is saved locally to `apps/backend/data/extracted_text/`.
- Prepared chunks can be indexed into a local JSON vector store under `apps/backend/data/vector_db/`.
- `RAGPipeline.ask(...)` retrieves top-k chunks, formats context, and asks the LLM for a source-grounded answer with bracket citations.

## Key Source Paths

- `apps/backend/app/services/document_service.py` -- main preparation entrypoint
- `apps/backend/app/tools/file_manager.py` -- upload/output path validation and directory creation
- `apps/backend/app/tools/pdf_reader.py` -- PDF extraction, cleanup, fallback handling, chunk conversion
- `apps/backend/app/tools/text_chunker.py` -- chunking logic
- `apps/backend/app/rag/rag_pipeline.py` -- ingest + ask workflow
- `apps/backend/app/rag/retriever.py` -- retrieval formatting and query path
- `apps/backend/app/rag/vector_store.py` -- local persistence for vector records
- `apps/backend/app/rag/embeddings.py` -- embedding backend selection, including hashing fallback

## Behavioral Notes

- The simpler chat path currently reads attachments into prompt context directly through `ChatService`; it does not automatically index them into the RAG store.
- RAG is better thought of as an optional cross-document retrieval layer, not the only document-grounding path.
- File validation currently allows PDF-only ingestion for the PDF flow, while plain text and markdown attachments are handled separately in chat preparation.
- When extracted text is empty, failures are surfaced rather than silently ignored.

## Update Triggers

Update this file when:

- PDF support broadens beyond the current flow
- attachment handling starts indexing automatically into RAG
- vector-store format or embedding strategy changes
- retrieved-source formatting or citation behavior changes
