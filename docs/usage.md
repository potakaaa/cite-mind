# Usage

Start the backend and web client, then open `http://localhost:3000`.

## Chat

1. Choose a configured provider near the composer.
2. Type a research question.
3. Optionally attach PDF, TXT, or MD files.
4. Send the message.
5. Expand `Agent Reasoning` to inspect the high-level completed trace.

Recent conversations are stored in browser local storage. `New Chat` creates a fresh conversation. Library, Projects, History, Settings, and Account currently provide polished placeholder views.

## API

Health check:

```bash
curl http://localhost:8000/api/health
```

Provider discovery:

```bash
curl http://localhost:8000/api/providers
```

Chat:

```bash
curl -X POST http://localhost:8000/api/chat \
  -F 'message=Summarize the attached notes.' \
  -F 'history=[]' \
  -F 'attachments=@notes.md'
```

## Backend Modules

Structured research pipelines, exports, citation lookup, and optional RAG remain available programmatically under `apps/backend/app`.
