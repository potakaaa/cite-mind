# Frontend Context

This is the canonical frontend context entrypoint for cite-mind.

Read it after `process/context/all-context.md` when the task touches the Next.js app.

## Scope

This group covers:

- Next.js app structure
- current chat workspace UI
- client-side conversation state
- provider selection UI
- styling and component conventions

It does not cover:

- backend orchestration internals
- detailed PDF extraction logic
- planning artifacts

## Read When

Read this entrypoint when:

- changing `apps/web/app/`
- editing the chat workspace
- adjusting API integration from the browser
- changing shared UI primitives or styling tokens

## Frontend Overview

- The current app is concentrated in `apps/web/app/page.tsx`.
- There is no separate `app/chat/page.tsx` route yet; the root page is the primary research workspace.
- Conversations are stored client-side in browser `localStorage` under `cite-mind:conversations`.
- The page fetches provider availability from the backend and submits chat requests as multipart `FormData`.
- Placeholder sections for Library, Projects, History, Settings, and Account exist in the UI state, but the main functional area is the chat workspace.

## Key Source Paths

- `apps/web/app/page.tsx` -- main workspace UI, conversation state, provider selection, file upload, chat request flow
- `apps/web/app/layout.tsx` -- root layout with theme and tooltip providers
- `apps/web/app/globals.css` -- Tailwind imports, token definitions, shared prose styles, motion helpers
- `apps/web/components/ui/` -- shared UI primitives
- `apps/web/components/theme-provider.tsx` -- theme wiring
- `apps/web/lib/utils.ts` -- shared class utility
- `apps/web/tsconfig.json` -- `@/*` import alias
- `apps/web/components.json` -- shadcn configuration

## Frontend Patterns

- The codebase currently favors a single rich page component over many route segments.
- API base URL is read from `NEXT_PUBLIC_API_BASE_URL` with a localhost fallback.
- Conversation titles are derived from the first user message.
- Pending-state messaging is staged in the client to visually reflect a lightweight multi-agent feel.
- Styling uses Tailwind 4 tokens defined in `globals.css` plus shadcn/Radix primitives.

## Current UX Direction

- Keep the app simple and focused rather than broad and crowded.
- Emphasize a strong chat workflow over many partially implemented side features.
- Preserve source-grounded, research-oriented framing in labels and interactions.

## Known Gaps

- No frontend automated tests are configured yet.
- The UI currently centralizes a lot of logic in `app/page.tsx`, which is fine for the current size but worth watching as the workspace grows.
- Some navigation sections are placeholders rather than full product areas.

## Update Triggers

Update this file when:

- routes split out of `app/page.tsx`
- the storage model changes
- frontend API integration or environment variables change
- a real testing surface is added for the web app
