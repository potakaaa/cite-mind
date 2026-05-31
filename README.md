# Cite Mind

Cite Mind is a chat-first academic assistant. The repository is a pnpm and Turborepo monorepo with a Next.js web client and a Python FastAPI backend.

## Structure

```text
apps/
├── backend/   # FastAPI, agents, services, tools, tests, and local data
└── web/       # Next.js and shadcn/ui client
```

Turbo orchestrates development, build, lint, typecheck, and test tasks across both apps. The backend keeps the existing Ollama, Gemini, and OpenRouter routing, document extraction, research pipelines, tools, and optional RAG modules. The web client is now the supported user interface.

## Setup

Install the web dependencies from the repository root:

```bash
pnpm install
```

Create the backend environment and install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r apps/backend/requirements.txt
cp apps/backend/.env.example apps/backend/.env
```

## Run

Start both apps from the repository root:

```bash
pnpm dev
```

Turbo runs the FastAPI and Next.js development servers together. To run them separately:

```bash
pnpm dev:backend
pnpm dev:web
```

Open `http://localhost:3000`. The backend API runs at `http://localhost:8000`.

## Checks

```bash
pnpm test:backend
pnpm test
pnpm lint
pnpm typecheck
pnpm build
```

See [docs/setup.md](docs/setup.md), [docs/architecture.md](docs/architecture.md), and [docs/usage.md](docs/usage.md) for details.
