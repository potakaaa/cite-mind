# Browser Automation

Use this file when a task needs browser-driven verification for cite-mind.

## Current Reality

- No dedicated browser test suite is configured yet.
- Browser verification is currently manual or tool-assisted.
- The frontend usually runs on `http://localhost:3000`.
- The backend API usually runs on `http://localhost:8000`.

## Read When

Read this file when:

- using browser automation to verify UI behavior
- validating frontend/backend integration locally
- checking file upload, provider selection, or message rendering in the real app

## Suggested Workflow

1. start the web app and backend locally
2. open the main workspace
3. verify provider discovery from `/api/providers`
4. verify multipart chat submission to `/api/chat`
5. verify conversation persistence and attachment handling

## Known Constraints

- There is no Playwright harness yet.
- The main UI lives at `apps/web/app/page.tsx`, so browser checks should focus there first.
- Placeholder sections in the sidebar should not be mistaken for fully implemented product areas.
