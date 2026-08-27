# Phase 16 — Maintainability Refactor

**Status: PASS (two incremental boundaries completed and verified)**

Phase 16 was intentionally limited to two low-risk frontend extractions. No
broad rewrite, API change, visual redesign, or backend split was performed.

## Scope and baseline

Before the first Phase 16 extraction, the frontend entry point was a single file:

```text
web/src/main.tsx       2,548 lines (baseline)
web/src/styles.css     5,465 lines (baseline)
```

`main.tsx` contained routing, page components, modal components, layout/splitter
behavior, API calls, pure display/formatting helpers, and the shared data-state
renderer. The backend structure was not changed because this phase's verified
maintenance risk is concentrated in the frontend monolith and no backend
boundary was required for these steps.

## Dependency map for the selected boundary

The first safe boundary was the set of pure shared utilities used by multiple
screens:

| Boundary | Source before | Consumers in `main.tsx` | Side effects |
| --- | --- | --- | --- |
| width clamping and persisted pane widths | local functions near the layout/splitter code | `ResizableSplitter`, `Dashboard`, `Assistant` | `storedWidth` reads existing localStorage keys; no writes or API calls |
| user display and initials | local functions near shared UI state | `Dashboard`, workflow messages, chat messages | none |
| chat/workflow/evidence time formatting | local functions near chat rendering | conversation list, workflow evidence, chat metadata | none |
| agenda status/stage mapping | local functions near workflow rendering | agenda filters, status chips, workflow stage/owner text | none |
| conversation grouping | local functions near chat rendering | conversation filters and grouped history | none |
| tenant display/filter labels | local functions near tenant rendering | tenant table and filter controls | none |
| pagination item generation | local function near tenant rendering | tenant pagination controls | none |
| loading/empty/error data state | local `DataState` component near shared render helpers | Dashboard, Documents, Tenants, Assistant, Workflow | none |

The boundary was extracted to:

```text
web/src/shared/utils.ts
web/src/shared/DataState.tsx
```

`web/src/main.tsx` now imports these helpers from `./shared/utils` and retains
all page components, state, event handlers, API paths, and rendering decisions.

## Changes actually made

1. The existing first boundary is `web/src/shared/utils.ts` with the 15 pure
   helper functions.
2. Added `web/src/shared/DataState.tsx` with the existing loading, empty, and
   error renderer and its `DataStateTone` type.
3. Replaced the local `DataState` definition in `web/src/main.tsx` with a named
   import; all existing call sites remain unchanged.
4. Preserved the helper and renderer implementations byte-for-byte in
   behavior, including:
   - width min/max clamping and persisted width keys;
   - 24-hour time formatting;
   - agenda state labels and buckets;
   - tenant placeholder normalization to an em dash;
   - pagination ellipsis behavior.
5. Did not modify `web/src/styles.css`, Python source, API contracts, database
   access, authentication, or workflow transitions.

The resulting current `main.tsx` is 2,453 lines. Runtime responsibilities remain
in their original component owners; only pure shared helpers and the existing
data-state primitive moved to dedicated modules.

## Why this extraction is safe

- The moved functions have no React hooks and no component lifecycle dependency.
- The only browser dependency, `window.localStorage`, was already used by the
  same `useState` initializers and remains invoked at the same runtime boundary.
- Call sites and argument/return types are unchanged.
- No imports were added to backend code and no API route or payload changed.
- The CSS class names and DOM structure are unchanged, so the extraction cannot
  alter layout by itself.

## Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| TypeScript/Vite production build | **PASS** | `web`: `npm run build`; Vite transformed 1,672 modules and emitted `dist` successfully. |
| Full Python regression suite | **PASS** | `.venv\\Scripts\\python.exe -m pytest -q --tb=no`: **64 passed, 27 skipped**. |
| Targeted Python regression checks | **PASS** | `tests/test_inspection.py` and `tests/test_chat_payload.py`: **5 passed**. |
| Ruff | **PASS** | `.venv\\Scripts\\ruff.exe check src tests`: `All checks passed!` |
| Live UI smoke | **PASS** | Disposable Vite server on `http://127.0.0.1:5177/`; the root shell rendered, the expected connecting state was visible without the API, and browser error/warning logs were empty. |
| Diff hygiene | **PASS** | `git diff --check` returned no whitespace errors for the Phase 16 source files. |

The full and targeted checks validate that backend-facing code and existing
Python contracts still pass; the frontend build validates both extracted
modules and all imports. The live smoke intentionally stops at the
unauthenticated shell because Phase 16 made no API/runtime change.

## Remaining candidates (not changed in this phase)

The following are candidates for later, separately verified boundaries:

1. shared status chips and toast primitives;
2. citation/source renderer;
3. resizable splitter component and related layout hooks;
4. shared header/profile/document-status controls;
5. document-management, billing, and tender modals;
6. AI Assistant, Workflow, Dashboard, and Tenant feature components;
7. backend module boundaries after profiling import/API coupling.

Each candidate requires its own extraction, build, targeted regression check,
and visual comparison. No candidate was pre-emptively moved in Phase 16.

## Phase boundary

This phase stops after the second incremental frontend extraction and its
verification.
No Phase 17 or later work is included.
