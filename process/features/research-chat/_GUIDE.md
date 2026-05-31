# Research Chat

<!-- Part of cite-mind -->

## Scope

The main single-user research workspace where a user starts a conversation, uploads files, selects an LLM provider, and receives grounded AI responses. Covers the core browser-to-API chat loop and the product experience that should stay simple but powerful.

## Key Source Files

- `apps/web/app/page.tsx` -- main workspace UI, local conversation history, provider selection, file upload flow
- `apps/web/app/layout.tsx` -- app shell providers
- `apps/backend/app/api/main.py` -- `/api/providers` and `/api/chat`
- `apps/backend/app/services/chat_service.py` -- request preparation and attachment context assembly
- `apps/backend/app/agents/chat_agent.py` -- final chat generation path

## Related Context

- `process/context/frontend/all-frontend.md` -- UI structure and conventions
- `process/context/backend/all-backend.md` -- API/service flow
- `process/context/tests/all-tests.md` -- current verification surface

## Current Status

Status: in-progress

## Folder Contents

```
process/features/research-chat/
  active/       -- in-progress plans for this feature
  completed/    -- archived completed plans
  backlog/      -- deferred/future plans
  reports/      -- feature-specific operational reports
  references/   -- feature-specific research and reference docs
```
