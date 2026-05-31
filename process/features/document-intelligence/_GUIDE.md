# Document Intelligence

<!-- Part of cite-mind -->

## Scope

The document-grounding layer for Cite Mind: PDF ingestion, text extraction, chunking, retrieval, and source-aware research support. Covers the path from uploaded paper to usable context for summaries, grounded answers, and later multi-document workflows.

## Key Source Files

- `apps/backend/app/services/document_service.py` -- document preparation entrypoint
- `apps/backend/app/tools/file_manager.py` -- upload/output path validation
- `apps/backend/app/tools/pdf_reader.py` -- PDF extraction and cleanup
- `apps/backend/app/tools/text_chunker.py` -- chunking logic
- `apps/backend/app/rag/rag_pipeline.py` -- optional retrieval workflow
- `apps/backend/app/rag/retriever.py` -- retrieval and context formatting
- `apps/backend/app/rag/vector_store.py` -- local vector persistence

## Related Context

- `process/context/rag/all-rag.md` -- ingestion and retrieval conventions
- `process/context/backend/all-backend.md` -- backend runtime and provider flow
- `process/context/tests/all-tests.md` -- backend verification commands and gaps

## Current Status

Status: in-progress

## Folder Contents

```
process/features/document-intelligence/
  active/       -- in-progress plans for this feature
  completed/    -- archived completed plans
  backlog/      -- deferred/future plans
  reports/      -- feature-specific operational reports
  references/   -- feature-specific research and reference docs
```
