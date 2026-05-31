# UI/UX Context

This is the UI and UX reference for cite-mind.

## Scope

This file covers:

- the current visual direction
- interface simplicity rules
- UI priorities for the research workspace
- guardrails for future frontend work

It does not cover:

- backend implementation
- retrieval internals
- general planning workflow

## Read When

Read this file when:

- designing or redesigning screens
- changing the main research workspace
- adding new navigation areas
- making visual or interaction decisions that affect the product identity

## Current Direction

- The product should feel simple, calm, and focused.
- The UI should help researchers move faster without looking overloaded.
- The strongest workflow is still the main chat workspace, not secondary navigation sections.
- New interface work should reinforce "simple but powerful AI" rather than broad dashboards or cluttered control panels.

## Current Implementation Notes

- The primary experience is the root page in `apps/web/app/page.tsx`.
- Styling is token-driven through `apps/web/app/globals.css`.
- The app already uses shadcn/Radix primitives and a soft green/taupe palette.
- Several sidebar sections are present as placeholders; they should stay secondary until they have clear product value.

## Design Guardrails

- Prefer fewer, stronger flows over many partially implemented surfaces.
- Keep research context and sources visible when it improves trust.
- Avoid adding decorative complexity that competes with reading, writing, and synthesis.
- Preserve good mobile behavior; the current workspace already includes a responsive sidebar sheet.

## Update Triggers

Update this file when:

- the visual system changes materially
- navigation structure changes
- the app gains multiple mature product surfaces beyond the main chat workspace
