# Phase 12 — Full browser UI/UX and accessibility acceptance

**Final result: PARTIAL / BLOCKED**

Authenticated browser acceptance is blocked pending operator confirmation to
enter the locally seeded acceptance test credential. The public shell, login
surface, acceptance runtime, responsive-width checks, and non-browser gates
were verified. No unauthenticated check was promoted to an authenticated PASS.

## Required summary

| Area | Result | Evidence |
|---|---|---|
| Acceptance safety gate | PASS | `scripts/check_acceptance_fixture.ps1` reported `database=portproject_acceptance` and `sentinel=acceptance/1`. |
| Authenticated Login | BLOCKED | Credential entry was not authorized; no login form was submitted. |
| Dashboard / Tenants / AI Assistant / Workflow / Billing / Tender / Logout | BLOCKED | Each requires an authenticated session. |
| Public responsive shell | PASS | Five required viewport sizes; no document-level horizontal overflow observed. |
| Accessibility scanner | NOT AVAILABLE | `web/package.json` contains no axe/Playwright/Cypress/Selenium scanner. |
| Manual authenticated keyboard checks | BLOCKED | Requires an authenticated session. |
| Full Python suite | PASS | `63 passed, 27 skipped` (`pytest -q --tb=no`). |
| Ruff | PASS | `ruff check src tests` returned `All checks passed!`. |
| Frontend production build | PASS | `npm run build` (`tsc -b` and Vite) completed successfully. |
| Operational `portproject` database modified | NO | The browser run used an acceptance API; fixture check remained healthy after the run. |

## Scope and safety boundary

The browser was pointed at an acceptance-backed frontend on
`http://127.0.0.1:5180/`, with API requests directed to
`http://127.0.0.1:8016/`. The acceptance API reported:

```text
/health       status=ok, database=portproject_acceptance, schema=rag
/health/ready status=ready, rag_ready=true
corpus        4 documents, 4 pages, 4 chunks, 4 vectors, 0 pending
```

The acceptance fixture check passed before and after browser inspection. No
password, token, cookie, or credential value is included in this report. No
login, chat, workflow, billing, tender, upload, delete, or logout mutation was
performed.

## Public responsive evidence

Browser zoom remained at 100%. The browser viewport override was applied to
each required size:

```text
1024×768   1280×720   1366×768   1440×900   1920×1080
```

On the public home surface, the measured `documentElement.scrollWidth` equaled
`clientWidth` at every size (the 15px difference from `innerWidth` was the
normal vertical scrollbar). No whole-page horizontal scrollbar, clipped right
edge, or overlapping public controls was observed.

At 1024×768, the Authority login card, labelled Username and Password fields,
primary sign-in button, navigation, and footer rendered within the viewport
width. The page used vertical scrolling for the full-height content; no
horizontal overflow was measured.

These checks cover only unauthenticated surfaces. They do not prove successful
authentication or role-specific rendering.

## Authenticated acceptance matrix

The Phase 12 prompt requires an authenticated Authority/DO/NO/HO/Tenant test
session and checks the following surfaces and interactions:

| Required check | Result | Evidence-based reason |
|---|---|---|
| Login and session establishment | BLOCKED | No password was entered into the local login form. |
| Dashboard at five viewports | BLOCKED | Protected route requires a session. |
| Tenants filters, sorting, rows, internal scrolling, pagination | BLOCKED | Protected route requires a session. |
| AI conversation list, new chat, citations, generation, Stop, error | BLOCKED | Requires an authenticated conversation session and model request. |
| AI splitter drag, min/max, double-click reset, keyboard resize | BLOCKED | Requires the protected assistant shell. |
| Workflow agenda list, stepper, read-only state, handoff, owner changes | BLOCKED | Requires role-specific authenticated fixtures. |
| Billing modal and loading/error/disabled states | BLOCKED | Protected Authority route requires a session. |
| Tender modal and workflow controls | BLOCKED | Protected Authority route requires a session. |
| Logout and post-logout protection | BLOCKED | No session was established. |

## Accessibility evidence and limits

Source inspection confirms the implemented UI exposes several intended
accessibility mechanisms: a skip link, native labels for login and form
controls, named icon buttons, visible focus styles, status/alert regions, and a
keyboard-focusable splitter with `role="separator"`, orientation, and value
attributes. Tenant/document table containers are configured for internal
horizontal scrolling in the stylesheet.

Those are implementation observations, not a runtime accessibility PASS. No
automated scanner is installed in the web package. Because authenticated
navigation was not authorized, the following remain unverified:

- complete keyboard-only traversal and Tab order in protected shells;
- Escape handling and modal focus containment;
- authenticated splitter keyboard and pointer behavior;
- workflow read-only controls and non-color status communication;
- citation/source interaction and long-content reflow;
- contrast and clipping at every protected route and modal.

## Defects and fixes

No application defect was changed in Phase 12. The public responsive checks did
not produce a verified defect. The only blocker is test authorization, not a
reported product failure. Phase 13 was not started.

## Exact unblock

Confirm that the local acceptance password for the seeded DO test account may
be entered into `http://127.0.0.1:5180/authority/login`. After confirmation,
rerun the authenticated matrix for the required roles and widths, then update
this report with observed PASS/FAIL results, screenshots where useful, and any
minimal evidence-backed fixes.
