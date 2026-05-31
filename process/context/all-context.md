# cite-mind - All Context

Last updated: 2026-06-01

This file is the root context entrypoint for the repo.

Use it for two things:

1. quick routing to the right context pack or root file
2. broad architecture and repository understanding

Start here before loading deeper context files.

---

## How This File Works (the `all-*.md` Convention)

Every `process/context/` directory has one `all-*.md` entrypoint that acts as an attachable quick router for that domain. This root file (`all-context.md`) is the top-level router. Context groups each have their own `all-{group}.md` entrypoint.

**The pattern:**

```
process/context/
  all-context.md                      <-- THIS FILE: root router
  planning/
    all-planning.md                   <-- group router for planning
    example-simple-prd.md             <-- deep doc within the group
    example-complex-prd.md            <-- deep doc within the group
  tests/
    all-tests.md                      <-- group router for tests
    debugging-and-pitfalls.md         <-- deep doc within the group
    e2e-tests.md                      <-- deep doc within the group
  database/
    all-database.md                   <-- group router for database
    schema-guide.md                   <-- deep doc within the group
    migration-procedures.md           <-- deep doc within the group
```

**How agents use it:**

1. Agent reads `all-context.md` first (this file)
2. Finds the relevant context group from the routing tables below
3. Reads that group's `all-{group}.md` entrypoint
4. Only then loads the specific deep doc needed

This layered routing keeps context windows small. Never load the whole `process/context/` tree.

**What each `all-{group}.md` must contain:**

- Scope (what the group covers and does NOT cover)
- Read-when rules (when an agent should load this group)
- Quick procedures or decision rules
- Source paths (list of deeper docs in the group)
- Update triggers (when to refresh this group's content)
- Routing to deeper docs within the group

---

## Quick Start

For most substantial tasks:

1. read this file first
2. choose the smallest relevant root file or context group from the tables below
3. only then load deeper files

---

## Current Root Entry Points

| File | Read when |
|---|---|
| `process/context/all-context.md` | any substantial planning, research, review, or implementation task |
| `process/context/backend/all-backend.md` | FastAPI, services, orchestration, provider routing, ingestion, or backend architecture work |
| `process/context/frontend/all-frontend.md` | Next.js UI, chat workspace, styling, client state, or frontend integration work |
| `process/context/rag/all-rag.md` | PDF ingestion, chunking, retrieval, vector storage, or grounded answer flow work |
| `process/context/uxui/all-uxui.md` | UI/UX conventions, visual direction, and frontend design guidance |
| `process/context/tests/all-tests.md` | testing, verification, debugging test failures, execution planning |
| `process/context/planning/all-planning.md` | plan-shape calibration, planning examples, SIMPLE vs COMPLEX reference docs |

## Current Context Groups

| Group | Entry point | Scope |
|---|---|---|
| `backend/` | `process/context/backend/all-backend.md` | FastAPI API surface, service layer, orchestration, provider routing, data paths, and backend conventions |
| `frontend/` | `process/context/frontend/all-frontend.md` | Next.js app structure, main chat page, styling system, client state, and API integration points |
| `rag/` | `process/context/rag/all-rag.md` | document ingestion, PDF extraction, chunking, retrieval, embeddings, and optional RAG workflow |
| `uxui/` | `process/context/uxui/all-uxui.md` | visual direction, UI conventions, simplicity guardrails, and future design guidance |
| `planning/` | `process/context/planning/all-planning.md` | plan-shape calibration, planning examples, SIMPLE vs COMPLEX reference docs |
| `tests/` | `process/context/tests/all-tests.md` | test runners, commands, debugging, gaps |

## Task Routing Table

| If the task involves... | Start with |
|---|---|
| architecture or stack questions | this file |
| backend API, services, or provider routing | `process/context/backend/all-backend.md` |
| frontend UI or client integration | `process/context/frontend/all-frontend.md` |
| UI/UX or visual design direction | `process/context/uxui/all-uxui.md` |
| PDF ingestion, retrieval, or grounded-answer flow | `process/context/rag/all-rag.md` |
| testing or verification | `process/context/tests/all-tests.md` |
| creating a new plan | `process/context/planning/all-planning.md` |

## Context Group Lifecycle

Context groups are durable knowledge domains, not feature folders.

Create a group when:

- a topic has 3+ durable docs
- a single doc exceeds roughly 800 lines with separable subtopics
- multiple agents repeatedly need only one slice of a large context file
- the topic maps to a stable operational domain (tests, infra, database, auth, UI, workflows, etc.)

Do not create a group when:

- the content is a temporary report
- the content is a plan or execution artifact
- the topic is feature-specific and belongs in `process/features/...`

Move or split one group at a time. Use `all-{group}.md` entrypoints. Run the `audit-context` skill after every context organization change.

## Naming Convention

There are no `README.md` files inside `process/context/`.

Canonical entrypoints use `all-*.md`:

- root: `process/context/all-context.md`
- group: `process/context/{group}/all-{group}.md`

Each `all-{group}.md` file should act as the attachable quick router for that domain:

- tell the agent what the group covers
- give quick procedures and decision rules
- route to smaller deeper files

## Context Update Protocol

When durable project knowledge changes:

1. update the smallest relevant context file
2. update this file if routing, ownership, naming, or groups changed
3. update the owning `all-{group}.md` entrypoint when a group exists
4. run `audit-context`

---

## Repository Structure

```
cite-mind/
  apps/
    backend/
      app/
        agents/           -- research_reader, critic, writer, chat agents
        api/              -- FastAPI entrypoint and HTTP routes
        llm/              -- Gemini, Ollama, OpenRouter providers + router
        orchestrator/     -- task routing, pipeline definitions, execution engine
        rag/              -- retriever, embeddings, vector store, RAG pipeline
        services/         -- chat, document, citation, export, research services
        tools/            -- PDF, web, academic search, file utilities
      tests/              -- pytest suites for api, services, rag, tools, orchestrator
      data/               -- uploads, outputs, extracted text, local vector store
      config.py           -- env-backed settings and runtime paths
      main.py             -- CLI entrypoint / FastAPI launcher
    web/
      app/                -- Next.js App Router entrypoints
      components/ui/      -- shadcn/radix UI primitives
      lib/                -- small shared helpers
      next.config.ts      -- standalone build output
  process/
    context/              -- repo context routers and durable knowledge
    general-plans/        -- cross-cutting plans, references, reports
    features/             -- feature-scoped artifacts when work grows larger
    development-protocols/ -- RIPER-5 shared workflow docs
  package.json            -- root turbo scripts
  pnpm-workspace.yaml     -- workspace definition
  turbo.json              -- pipeline config
```

## Technology Stack

## Product Direction

- Single-user research assistant for students, academic researchers, thesis writers, and policy researchers
- Local-first development path, with a likely hosted future split between Vercel frontend and a separate Python backend host
- Main user jobs:
  - upload PDFs
  - ask grounded questions over papers
  - summarize and draft from source material
  - support literature review and source-grounded synthesis
- Product bias: simple interface, strong backend, minimal clutter

## Technology Stack

- Monorepo tooling:
  - `pnpm@10.30.3`
  - `turbo@2.9.16`
- Frontend:
  - Next.js `16.2.6`
  - React `19.2.4`
  - TypeScript `5`
  - Tailwind CSS `4`
  - shadcn UI config with Radix-based primitives and Remix icons
- Backend:
  - Python app launched from `apps/backend/main.py`
  - FastAPI `>=0.115.0`
  - Pydantic `>=2.7.0`
  - Uvicorn `>=0.30.0`
  - Requests / HTTPX for outbound calls
- LLM providers:
  - Ollama for local models
  - Gemini
  - OpenRouter
- Research / document tooling:
  - PyMuPDF + pdfplumber fallback for PDF extraction
  - local JSON-backed vector store in `apps/backend/data/vector_db`
  - optional embedding backend switch (`auto`, `hash`, `sentence_transformers`)
- Testing:
  - pytest for backend coverage
  - no frontend test runner configured yet

## Key Architecture Notes

- The current primary UI is a single-page research workspace in `apps/web/app/page.tsx`.
- Frontend conversation history is persisted in browser `localStorage` under `cite-mind:conversations`.
- The web client sends multipart form requests to `POST /api/chat` and discovers providers from `GET /api/providers`.
- `ChatService` is the main request-preparation layer for chat. It normalizes history, reads attachments, builds prompt context, and delegates to `ChatAgent`.
- `DocumentService` owns PDF validation, saving, extraction, and chunk preparation.
- `LLMRouter` is the provider abstraction. It supports explicit provider selection plus fallback when the default provider is unavailable.
- The orchestrator subsystem is separate from the simple chat flow. It supports typed workflows like `paper_summary`, `study_table`, `study_table_with_gaps`, and `full_report`.
- The RAG layer is optional and env-gated with `RAG_ENABLED`. It supports indexing prepared documents and answering with retrieved chunk context plus bracketed citations.

## Environment and Runtime Paths

- Backend settings load from an optional backend-local `.env` file under `apps/backend/`, then the repo-root `.env`.
- The committed example env file is `apps/backend/.env.example`.
- Important backend env vars:
  - `DEFAULT_LLM_PROVIDER`
  - `GEMINI_API_KEY`, `GEMINI_MODEL`
  - `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, `OLLAMA_RETRIES`
  - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
  - `UPLOAD_DIR`, `OUTPUT_DIR`, `VECTOR_DB_DIR`
  - `RAG_ENABLED`, `RAG_EMBEDDING_BACKEND`, `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`, `RAG_CONTEXT_MAX_CHARS`
- The frontend currently reads `NEXT_PUBLIC_API_BASE_URL` and falls back to `http://localhost:8000`.
- Backend data directories are auto-created through file-management utilities:
  - `data/uploads`
  - `data/outputs`
  - `data/extracted_text`
  - `data/vector_db`

## Current Feature Folders

- `process/features/research-chat/` -- main chat workspace, provider selection, request/response UX
- `process/features/document-intelligence/` -- PDF ingestion, document preparation, retrieval, grounded answer flow

## Known Testing State

- Backend has real pytest coverage across:
  - API endpoints
  - chat service
  - RAG pipeline
  - orchestrator routing/execution
  - tools and PDF handling
- Frontend currently has no automated test runner configured.
- Stronger coverage is a stated project goal, especially as the chat UI and backend research flow evolve.

## Open Questions / Outstanding Work

- Frontend testing surface is still missing and should be added as the chat workspace grows.
- Decide whether the long-term hosted deployment should standardize on a single backend host/runtime.
- Decide whether attachment grounding in chat should remain direct-prompt context or converge with automatic RAG indexing.
