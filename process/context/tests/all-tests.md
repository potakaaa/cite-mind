# cite-mind - All Tests

Last updated: (auto-generated)

Attach this file first when the task involves testing, verification, or test debugging.

This is the fast operator guide for the testing surface:

- which runner to use
- what command to start with
- how to quickly debug common failures
- which deeper file to read next

Do not load the whole `process/context/tests/` folder by default. Start here, then drill down.

---

## How This File Works

This is the `all-tests.md` entrypoint for the `tests/` context group. It follows the `all-*.md` routing convention:

1. Agents read `all-context.md` first and get routed here for testing tasks
2. This file gives quick decision rules and commands
3. For deeper details, agents follow the routing table below to specific docs

As the project grows, add deeper docs to this group (e.g., `e2e-tests.md`, `debugging-and-pitfalls.md`) and add routing entries below. This file stays the fast-start entrypoint.

---

## What This Covers

- test runner selection
- quick commands by package
- fast debugging procedures
- current testing gaps worth remembering

## Read This When

Use this file when you need to:

- run tests after implementation
- decide between test runners
- debug failing tests

## Quick Routing

| If you need... | Read next |
|---|---|
| backend architecture before changing tests | `process/context/backend/all-backend.md` |
| retrieval/document-grounding behavior under test | `process/context/rag/all-rag.md` |
| frontend structure before adding a test surface | `process/context/frontend/all-frontend.md` |
| browser-driven local verification guidance | `process/context/tests/browser-automation.md` |

## Quick Decision Guide

### Use `pytest` when

- the change is in `apps/backend`
- the behavior is API, service, orchestrator, provider, PDF, tool, or RAG logic
- you need the existing automated regression surface

### Use typecheck/lint-only verification when

- the change is in `apps/web`
- there is no existing frontend test for the behavior
- the work is mostly component/state/UI integration

### There is no current browser or frontend unit-test runner

- no Playwright, Vitest, or React Testing Library surface is configured yet
- frontend verification is currently manual plus `typecheck` / `build`

## Default Verification Order

Unless the task clearly needs a different path:

1. run the narrowest existing automated test
2. use unit/integration tests before browser tests
3. use end-to-end tests only when the real UI is the thing being verified

## Commands

| Package | Runner | Command |
|---|---|---|
| repo root | turbo | `pnpm test` |
| repo root | turbo backend only | `pnpm test:backend` |
| `apps/backend` | pytest | `../../.venv/bin/python -m pytest -q` |
| `apps/backend` single file | pytest | `../../.venv/bin/python -m pytest -q tests/services/test_chat_service.py` |
| repo root | all typechecks | `pnpm typecheck` |
| `apps/web` | TypeScript | `pnpm --dir apps/web typecheck` |
| `apps/web` | Next production build | `pnpm --dir apps/web build` |
| `apps/web` | ESLint | `pnpm --dir apps/web lint` |

## Debugging Quick Reference

- Backend package scripts assume a local Python virtualenv at `.venv/`.
- `apps/backend/tests/conftest.py` injects `apps/backend` onto `sys.path`, so imports expect tests to run from the backend package context.
- API tests use FastAPI `TestClient` and monkeypatch service getters rather than spinning up a live server.
- Service and tool tests rely heavily on stubs, `tmp_path`, and monkeypatching instead of external services.
- PDF-related tests expect the document toolchain dependencies to be installed in the active backend environment.
- Frontend changes currently have no automated UI runner, so manual verification is still required.

## Known Gaps

- No frontend test runner is configured.
- No end-to-end browser test suite is configured.
- Stronger coverage is a project goal, especially for the web chat experience and cross-layer research workflow.
