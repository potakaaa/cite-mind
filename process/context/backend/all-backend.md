# Backend Context

This is the canonical backend context entrypoint for cite-mind.

Read it after `process/context/all-context.md` when the task touches the Python backend.

## Scope

This group covers:

- FastAPI routes
- service-layer request handling
- LLM provider routing
- orchestrator pipelines
- backend file/data paths
- backend implementation conventions

It does not cover:

- frontend layout and styling details
- general planning workflow
- detailed test commands beyond what is needed for backend work

## Read When

Read this entrypoint when:

- changing `apps/backend/app/api/`
- modifying services or provider routing
- debugging backend request handling
- adding orchestration or typed research workflows
- changing env-backed backend settings

## Backend Overview

- Entry command: `apps/backend/main.py`
- API entrypoint: `apps/backend/app/api/main.py`
- Configuration: `apps/backend/config.py`
- Primary runtime shape:
  - FastAPI exposes `/api/health`, `/api/providers`, and `/api/chat`
  - chat requests are prepared by `ChatService`
  - `ChatService` delegates final generation to `ChatAgent`
  - attachments are processed through `DocumentService`
  - provider selection and fallback go through `LLMRouter`

## Key Source Paths

- `apps/backend/main.py` -- CLI entrypoint and `--api` launcher
- `apps/backend/config.py` -- env-backed settings and runtime paths
- `apps/backend/app/api/main.py` -- FastAPI routes and multipart request handling
- `apps/backend/app/services/chat_service.py` -- chat preparation, history normalization, attachment context, user-facing errors
- `apps/backend/app/services/document_service.py` -- PDF save/validate/extract/chunk orchestration
- `apps/backend/app/llm/llm_router.py` -- provider selection and fallback behavior
- `apps/backend/app/orchestrator/` -- typed workflow routing and multi-step execution
- `apps/backend/app/tools/` -- PDF, search, citation, and file utilities

## Backend Patterns

- Keep HTTP parsing in the FastAPI layer and push behavior into services.
- User-facing backend errors should be normalized through service-specific error types where practical.
- Provider access should route through `LLMRouter` instead of talking directly to a specific provider unless there is a strong reason.
- File-system writes for uploads/extracted text/vector data are intentionally local-path based and centered under `apps/backend/data/`.
- The backend is currently single-user oriented. There is no auth/session layer to preserve.

## Orchestrator Notes

- `TaskType` values currently include:
  - `chat`
  - `study_table`
  - `study_table_with_gaps`
  - `paper_summary`
  - `full_report`
- The orchestrator uses deterministic routing in `task_router.py`.
- Multi-step pipelines are assembled from:
  - `research_reader`
  - optional `critic`
  - `writer`
- The simpler web chat path does not currently go through the full orchestrator; it uses `ChatService` and `ChatAgent` directly.

## Provider Notes

- Supported provider keys are `gemini`, `ollama`, and `openrouter`.
- Default provider comes from `DEFAULT_LLM_PROVIDER`.
- If no explicit provider is supplied, `LLMRouter` may fall back to another configured provider when the selected one is unavailable.
- Local development currently appears biased toward Ollama.

## Update Triggers

Update this file when:

- the API surface changes
- chat preparation moves to different services or pipelines
- provider support changes
- backend runtime paths or env var expectations change
- the orchestrator becomes the default path for web chat
