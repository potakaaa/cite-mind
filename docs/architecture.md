# Architecture

Cite Mind is a pnpm and Turborepo monorepo with two applications:

```text
Next.js web client
        |
     FastAPI
        |
  chat service
        |
 agents / tools / LLM router
```

## Web Client

`apps/web` is a Next.js and shadcn/ui application. It provides the research chat workspace, PDF/TXT/MD attachments, configured-provider selection, reasoning trace display, browser-local conversations, responsive navigation, and placeholder sections for future product areas.

## Backend

`apps/backend` contains the Python app. FastAPI exposes:

- `GET /api/health`
- `GET /api/providers`
- `POST /api/chat`

The chat endpoint accepts multipart form data and returns the final answer, completed high-level trace entries, and accepted attachment names.

The existing research pipelines, document ingestion, provider routing, citation tools, exports, and optional cross-paper RAG remain available as backend modules.

## Task Orchestration

The root `turbo.json` defines shared `dev`, `build`, `lint`, `typecheck`, and `test` tasks. Each app exposes matching scripts in its package manifest, allowing Turbo to run the Next.js and Python workflows from the repository root.

## Storage

Chat history is stored in browser local storage. Uploaded PDFs are processed through the backend document service and saved under `apps/backend/data/uploads` when extraction is required.
