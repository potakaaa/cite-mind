# Setup

## Requirements

- Node.js 22 or newer
- pnpm 10
- Python 3.11 or newer
- Ollama, Gemini, or OpenRouter credentials

## Install

From the repository root:

```bash
pnpm install
python -m venv .venv
source .venv/bin/activate
pip install -r apps/backend/requirements.txt
cp apps/backend/.env.example apps/backend/.env
```

Configure `apps/backend/.env`. Ollama is the local default:

```env
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

The web client defaults to `http://localhost:8000`. Override that by copying `apps/web/.env.example` to `apps/web/.env.local`.

## Run

Start both apps through Turbo:

```bash
pnpm dev
```

To start only one app:

```bash
pnpm dev:backend
pnpm dev:web
```

## Verify

```bash
pnpm test:backend
pnpm test
pnpm lint
pnpm typecheck
pnpm build
```
