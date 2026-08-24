# Phase 12 — Full browser UI/UX and accessibility acceptance

**Status: PARTIAL / BLOCKED for authenticated acceptance**

## Scope and safety boundary

This phase was executed against the current `portproject_rag` checkout only. The
browser checks were read-only: no login form was submitted, no database account
was created, and no workflow, billing, tender, document, chat, or logout mutation
was performed. The browser surfaced pre-filled login fields, but those values
were not transmitted. The existing hardening rule remains in force: successful
authenticated acceptance requires an approved non-production account and an
isolated fixture, neither of which is present in this checkout.

## Runtime evidence

| Component | Evidence | Result |
|---|---|---|
| React UI | `http://127.0.0.1:5173/` served the current Vite build | PASS |
| Project API | `http://127.0.0.1:8001/health` returned `status=ok`, database `portproject`, schema `rag` | PASS |
| RAG readiness | `/health/ready` returned HTTP 200 with `rag_ready=true`, 48 documents, 1,474 pages, 3,399 chunks, 3,399 vectors, 0 pending, 0 processing, 1 quarantined, 0 failed | PASS |
| Unauthenticated protection | `/api/v1/auth/me`, `/api/authority/dashboard/metrics`, and `/api/authority/tenants` returned HTTP 401 without a session | PASS |
| Wrong process isolation | Port 8000 was a separate/stale service and returned 404 for this project’s auth route; the UI proxy is configured for port 8001 | Not used |

The project API was started using the existing documented local service entry
point. No source or configuration files were changed by starting it.

## Browser viewport checks

Browser zoom was left at 100%. The following checks were run at each viewport:

```text
1024×768
1280×720
1366×768
1440×900
1920×1080
```

### Public home surface

At all five sizes, the DOM reported equal document and client widths (the only
difference was the normal browser scrollbar), so no whole-page horizontal
overflow was observed. The home page showed the public navigation, hero, module
cards, and footer without a clipped right edge.

### Authority and Tenant login surfaces

At all five sizes, both login routes rendered one form with two inputs and no
document-level horizontal overflow. At 1024×768 the Authority form and its
primary action remained inside the viewport; the visual capture showed no
clipping or overlap. Public navigation from Home reached both
`/authority/login` and `/tenant/login`.

These checks prove the unauthenticated shell and login layout only. They do not
prove that a real account can authenticate.

## Required authenticated acceptance matrix

The Phase 12 prompt requires an approved authenticated test account and checks
for Dashboard, Tenants, AI Assistant, Workflow, Billing, Tender, and Logout.
Those checks could not be honestly completed because:

1. `GET /api/v1/auth/me` correctly returns 401 without a session.
2. The repository contains no approved test-account file, sanitized role fixture,
   or disposable database declaration.
3. The live source identity path reads operational database identity/password
   fields. Guessing or submitting those credentials would be unsafe and would
   not constitute a controlled acceptance test.

| Required surface/check | Result | Reason |
|---|---|---|
| Login success and session establishment | BLOCKED | No approved test credential supplied |
| Dashboard at five viewports | BLOCKED | Requires an authenticated Authority session |
| Tenants table, internal scrolling, filters, sorting, pagination | BLOCKED | Requires an authenticated Authority session |
| AI conversation list, splitter min/max, double-click reset, keyboard splitter | BLOCKED | Requires an authenticated session and persisted conversations |
| AI long chat, citations, generation, Stop, error state | BLOCKED | Requires chat data and model request under a session |
| Workflow agenda list, stepper, read-only state, handoff, owner changes | BLOCKED | Requires role-specific agenda fixtures and authenticated principals |
| Billing and Tender screens | BLOCKED | Requires authenticated route access and safe source fixtures |
| Logout | BLOCKED | No session was established |

## Static implementation evidence reviewed

The source contains the intended responsive and accessibility mechanisms:

- `web/src/main.tsx` renders protected content only after `/api/v1/auth/me`
  succeeds and renders an explicit login surface otherwise.
- The authenticated shell exposes a keyboard-focusable `role="separator"`
  splitter with `aria-valuemin`, `aria-valuemax`, and `aria-valuenow`; the
  splitter supports pointer drag, double-click reset, and keyboard changes in
  source.
- AI empty/loading/error states use explicit status or alert regions, retry
  actions, source/citation UI, and disabled-action explanations.
- The responsive stylesheet collapses the authenticated sidebar and assistant
  columns below the documented breakpoints, keeps tenant/document tables in
  `overflow-x:auto` containers, and hides splitters when the layout becomes a
  single column.
- Login inputs are wrapped by native `<label>` elements; the public shell has a
  skip link, native form controls, visible `:focus-visible` styles, and named
  icon/control labels where the authenticated UI is rendered.

These are source-level findings, not a substitute for the blocked authenticated
browser checks.

## Accessibility scanner and keyboard limitation

No automated accessibility scanner is installed in the web package, so no axe
or equivalent automated score is claimed. The public login DOM inventory was
read-only and confirmed native labels, buttons, a language selector, and the
skip link. The browser control surface did not advance focus when a synthetic
Tab was sent after focusing the username field; therefore a complete manual
keyboard-only traversal, Escape behavior, modal focus trap, and authenticated
splitter keyboard test are explicitly **not claimed**.

## Build and regression validation

The existing application checks were rerun after the browser work:

```text
pytest -q                         45 passed
ruff check src tests              passed
python -m compileall -q src       passed
web: npm run build                passed (tsc -b + Vite build)
```

No application source changes were required by the evidence available in this
phase. This report is the only Phase 12 artifact. Phase 13 was not started.

## Required unblock for a complete Phase 12 acceptance

Provide an approved isolated fixture and non-production credentials for at least
the supported Authority roles (DO/NO/HO) plus one Tenant principal, or provide a
safe browser session already authenticated to that fixture. Then rerun the full
matrix above, including real long-chat/citation/error/generation states,
workflow ownership and read-only rules, table behavior, modal/drawer behavior,
splitter pointer/double-click/keyboard behavior, logout, and automated/manual
accessibility checks.
