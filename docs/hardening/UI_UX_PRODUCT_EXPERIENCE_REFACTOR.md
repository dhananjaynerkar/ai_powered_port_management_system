# UI/UX Product Experience Refactor

## Required result checklist

| Area | Result | Evidence |
|---|---|---|
| Landing redesign | PASS | Public landing was rebuilt around the actual AI PMS capabilities and verified in the local browser. |
| Product-specific visual identity | PASS | Navy/blue/yellow/green product language now combines port operations, documents, evidence, and governed workflow motifs. |
| Hero product preview | PASS | The right-hand preview is explicitly labelled illustrative and uses safe public-style source names, not tenant data. |
| Authority/Tenant role entry | PASS | Two equivalent role cards route to the existing Authority and Tenant login paths. |
| Platform modules | PASS | Six modules map to capabilities present in the current application. |
| Workflow storytelling | PASS | Landing flow explains documents → search → authorized evidence → local answer → citations and a DO → NO → HO handoff. |
| Trust/security presentation | PASS | Claims are limited to observed product properties; no unsupported compliance or security guarantee was added. |
| Navigation feedback | PASS | Existing route shell remains immediate and route/data regions retain their own loading/error/empty states. |
| Skeleton loading | PASS | Shared `DataState` loading presentation uses a compact skeleton treatment; feature-specific skeletons remain intact. |
| RAG long-running UX | PASS | Local elapsed time and broad lifecycle wording replace an indefinite spinner; no backend milestones are fabricated. |
| Citation UX | PASS | The existing reusable `CitationList` remains the citation surface for assistant and workflow responses. |
| Empty states | PASS | Conversation and agenda empty states explain what is missing and what the user can do next. |
| Error states | PASS | Document loading now has an inline Retry action and existing typed error surfaces were preserved. |
| Responsive 1366×768 | PASS | Browser check found no document-level horizontal overflow and the hero/evidence strip fit the primary target. |
| Mobile responsive | PASS | At 390px the hero stacks, the navigation becomes a labelled menu, and no document-level horizontal overflow was measured. |
| Keyboard accessibility | PARTIAL | Semantic landmarks, labels, focus styles, skip link, native controls, and menu state are implemented; a full automated keyboard/axe audit is not configured. |
| Reduced motion | PASS | New grid drift, skeleton, and answer-arrival animation are disabled under `prefers-reduced-motion`. |
| Frontend build | PASS | `npm.cmd run build` passed: TypeScript plus Vite, 1,673 modules transformed. |
| Browser E2E | PARTIAL | Codex in-app browser verified public landing navigation, role routing, menu behavior, and responsive overflow; no Playwright/Cypress suite or authenticated credential run exists. |
| Operational DB modified | NO | This phase changed frontend presentation only and performed no database mutation. |
| Backend/RAG behavior modified | NO | No API, retrieval, model, embedding, authorization, billing, tender, or workflow business logic was changed. |

## 1. Original UI problems

The previous public surface had a generic hero with a large unused right side,
two isolated statistics, generic feature cards, weak connection to port
operations, and no visible explanation of how evidence becomes a trusted answer.
The header and footer did not establish a role-oriented enterprise product
identity. The loading treatment also relied too heavily on spinner-like states,
and the landing skip link pointed at a missing target.

The authenticated application already contains substantial product behavior, so
the risk was changing stable routes or API contracts while improving the public
experience. The implementation therefore keeps the existing shell and changes
only bounded presentation and feedback surfaces.

## 2. Design strategy

The refactor uses a restrained enterprise/government visual system: a navy
operational canvas, blue evidence accents, yellow as a small attention accent,
and green for grounded/ready status. Existing global spacing, radius, color,
input, button, status, panel, shadow, and transition tokens remain the source
of truth. New landing rules are scoped under `.landing-*` so authenticated
dashboard, tenant, assistant, and workflow density is not globally restyled.

The implementation favors incremental extraction over a framework migration or
a rewrite of `main.tsx`. SVG iconography and CSS grid geometry communicate
documents, pages, plots, evidence, and workflow connectors without a remote
image dependency or heavy animation.

## 3. Information architecture

The logged-out information hierarchy is now:

1. Utility context and AI PMS identity.
2. Anchor navigation: Platform, AI Assistant, Workflows, Security, Help.
3. A product-first hero with two equivalent role journeys.
4. An illustrative assistant/evidence preview.
5. Live corpus evidence metrics and Local AI status.
6. Real platform modules.
7. “How AI PMS works” evidence flow.
8. Governed DO → NO → HO workflow explanation.
9. Trust properties and a Help/portal entry call to action.
10. A compact footer with working in-page anchors and plain legal/accessibility text.

The protected application route map and existing role-specific navigation were
not changed. Public role cards use the current login destinations, and no
unimplemented tenant capability is promised.

## 4. Landing-page redesign

`LandingPage` now provides an asymmetric two-column hero. The left column
answers what the product is and who it serves; the right column gives a compact
AI policy/evidence preview. The evidence strip reads `documents`, `pages`, and
`chunks` from the existing `/api/v1/public/corpus` response. During loading or
when a value is unavailable, it renders an honest em dash rather than a
volatile hardcoded statistic.

The first screen is information-dense enough for 1366×768 while the rest of the
story continues below without a blank marketing panel. Module and trust content
is concise and scannable rather than consumer-marketing copy.

## 5. Visual identity

The product identity is intentionally specific to AI PMS:

- port operations utility strip and anchor mark;
- document/page layers and evidence chips;
- source/page language in the preview;
- authorized-evidence and citation-validation status;
- grid/plot geometry in the navy hero;
- DO, NO, and HO workflow connectors;
- local AI language without unsupported accuracy or compliance claims.

The preview is labelled “Illustrative · public corpus example” and “Example
response”. It is not presented as a live tenant record or a current case
decision.

## 6. Role-entry design

Authority and Tenant are equal role cards, not a primary/secondary marketing
hierarchy. Authority copy describes operations, documents, workflow, billing,
and tender tools that exist in the current portal. Tenant copy is limited to
permitted documents and tenant-specific AI support; it does not imply broader
tenant APIs that are not present.

The existing role routes remain authoritative:

- Authority: `/authority/login`
- Tenant: `/tenant/login`

The login/setup switch links now have real `href` values plus the existing
client-side route handler, preserving keyboard and non-JavaScript semantics.

## 7. Product-preview design

The preview contains a safe question, a short illustrative grounded-answer
block, two readable source/page chips, a ready indicator, and a clear
“Citation validated / Authorized documents only” explanation. Source names are
generic public-style examples (`Port Estate Rules`, `Lease policy`) and no
private customer, tenant, or operational record is embedded.

## 8. Module design

The six module cards correspond to current product surfaces:

- AI Policy Assistant;
- Tenant Services;
- Authority Operations;
- Document & Policy Library;
- Governed Workflow;
- Billing & Tender.

They are informational cards with clear purpose copy and hover/focus treatment;
they are not falsely styled as active navigation destinations. There is no
default “selected” AI card on the home page.

## 9. Workflow and trust presentation

The “How AI PMS works” sequence uses user language: Port documents → Hybrid
search → Authorized evidence → Local AI answer → Page citations. A second
workflow card separates AI discussion from official governance: AI discussion →
DO Draft → NO Review → Return or Submit → HO → Approve/Reject.

The trust section uses only properties supported by the application and its
existing documentation: local AI processing, role-filtered information access,
page-level citations, controlled workflow ownership, and PostgreSQL-backed
application state. It does not claim “100% secure”, compliance certification,
or zero hallucinations.

## 10. Async UX

The existing feature-level async behavior was preserved and the generic shared
state was improved rather than introducing a new state-management framework.
`DataState` now has explicit loading, empty, and error semantics with a retry
action where the caller has a safe retry function. Success remains the normal
content state. Login/setup buttons clear stale errors, disable duplicate
submission, and show `Creating account…` or `Signing in…` while pending.

Document loading exposes Retry. Conversation and agenda empty states provide
next-step guidance instead of blank panels. Existing workflow, billing, tender,
and table action guards remain in place; no business action was reimplemented.

## 11. RAG waiting experience

While a real query request is pending, the UI measures elapsed time locally from
the request start. It shows one broad, truthful lifecycle message:

- under 5 seconds: “Searching authorized documents…”;
- 5–20 seconds: “Reviewing supporting evidence…”;
- later: “Complex policy questions can take longer on the local AI engine.”

The UI does not report fake percentages, backend stages, token streams, or
citation completion. Final factual content remains buffered behind the existing
validated response contract. Workflow AI uses the same broad status language
and elapsed-time presentation.

## 12. Navigation feedback

The existing lightweight route mechanism and app shell were retained. The
landing anchors scroll to real sections, role cards navigate to the existing
login routes, and the mobile menu closes after an anchor or role action. The
protected shell continues to render route-level content while each data region
resolves its own state instead of blocking the entire page on one request.

The app now records lightweight browser Performance API marks for shell mount
and route changes (`ai-pms-app-shell-mounted` and `ai-pms-route-*`). No analytics
service or sensitive payload is introduced.

## 13. Skeleton/loading system

The shared loading icon in `DataState` is a compact skeleton bar rather than a
large indefinite spinner. Existing conversation, message, agenda, and table
skeleton structures remain available in the authenticated app. The new
skeleton animation is short and is disabled for reduced-motion users.

## 14. Empty and error states

Empty conversation and agenda surfaces now state what is empty and the next
available action. Existing typed backend errors are kept inline. Document
loading errors include a Retry action. The refactor does not expose Python
exceptions, SQL, model paths, filesystem paths, or object-stringified errors.

## 15. Accessibility

The public surface has a semantic `header`, `nav`, `main`, `section`, `article`,
and `footer` structure, a visible-on-focus skip link, native form controls,
labelled language select, labelled mobile-menu button, and equivalent role
buttons. Login switch anchors now remain real links. Focus-visible styles and
minimum control sizing come from the existing shell tokens.

New motion is wrapped by a `prefers-reduced-motion: reduce` override. Status
indicators also include text, so meaning is not conveyed by color alone.

A complete keyboard-only traversal, screen-reader announcement review, axe
scan, and 200% zoom audit were not available in the current tooling; those
remain a follow-up limitation rather than an unverified PASS.

## 16. Responsive behavior

The browser check covered the requested widths: 1920, 1440, 1366, 1280, 1024,
768, and 390 pixels. The public page measured no document-level horizontal
overflow at any width. The hero uses two columns on desktop and one column on
tablet/mobile; role cards and module grids reflow; the header becomes a labelled
mobile menu. The public shell uses vertical scrolling for long content and does
not clip important role-entry controls.

Protected tables and splitters retain the existing internal scrolling and
responsive strategies; they were not redesigned in this landing-focused phase.

## 17. Frontend performance

The final production build passed with Vite 7.3.6 after TypeScript compilation:

```text
1,673 modules transformed
JavaScript 316.02 kB (93.32 kB gzip)
CSS       191.19 kB (34.39 kB gzip)
```

No new dependency was added, no large image/video asset was introduced, and no
remote visual asset is required. Feature lazy-loading was not added because
the current app is a single maintained `main.tsx` entry with lightweight route
switching and a disruptive code-splitting rewrite would create more regression
risk than evidence of benefit. The Performance API marks provide a small basis
for future measurement without an analytics platform.

## 18. Components extracted

The bounded landing surface was extracted to:

- `web/src/components/landing/Landing.tsx` — header, hero, preview, evidence strip, modules, workflow, trust, and footer;
- `web/src/shared/DataState.tsx` — reusable loading/empty/error state surface.

The existing `CitationList` in `web/src/main.tsx` remains the reusable citation
component for current assistant/workflow response paths. `main.tsx` now composes
the landing components and retains the existing authenticated feature logic.

Supporting presentation changes are in `web/src/styles.css`, `web/index.html`,
and the lightweight local `web/public/favicon.svg`.

## 19. Browser test evidence

Using the local Codex in-app browser against the existing local frontend:

- public landing DOM contained the product title, role entries, live corpus strip,
  modules, workflow, trust, Help CTA, and footer anchors;
- mobile menu changed from `aria-expanded="false"` to an open state and exposed
  the anchor links;
- Authority role entry reached `/authority/login`, then returned to `/`;
- 390px evaluation measured a 343px hero column, 375px document scroll width,
  and no overflow against a 390px viewport;
- all seven requested viewport widths measured no document-level horizontal
  overflow;
- the final landing state contained `main#main-content`, matching the skip-link
  target, and the corpus strip displayed live observed values `48`, `1,474`,
  and `3,399` from the existing public corpus endpoint.

The browser console also reported a repeated React `createRoot` warning when
the in-app test harness reloaded the same SPA document repeatedly. The warning
is associated with the harness reload sequence; it was not used as a reason to
rewrite application bootstrapping in this scoped phase. No authenticated
credentials were entered, and no authenticated browser PASS is claimed.

## 20. Files changed in this phase

The phase-specific files are:

- `web/src/components/landing/Landing.tsx` (new);
- `web/src/shared/DataState.tsx` (new);
- `web/src/main.tsx`;
- `web/src/styles.css`;
- `web/index.html`;
- `web/public/favicon.svg` (new);
- `docs/hardening/UI_UX_PRODUCT_EXPERIENCE_REFACTOR.md` (this report).

The working tree also contains earlier hardening and project-documentation
changes from prior phases; they are intentionally not attributed to this UI/UX
phase.

## 21. Remaining UX limitations

1. No Playwright, Cypress, Selenium, or axe configuration exists in
   `web/package.json`; authenticated browser journeys therefore remain
   unverified in this phase.
2. A complete keyboard-only, screen-reader, contrast, and 200% zoom audit still
   needs a dedicated accessibility tool/run.
3. Protected dashboard/table/assistant/workflow screens retain their existing
   dense layouts and were not visually redesigned beyond shared async feedback.
4. The monolithic route entry remains intentionally in place; safe route-level
   code splitting can be evaluated separately with bundle measurements.
5. The in-app browser reload harness emits a repeated React root warning; this
   phase did not change the stable application boot path to mask a test-harness
   artifact.

## Verification gate

Commands and results for this phase:

```text
npm.cmd run build                  PASS
.venv\\Scripts\\python.exe -m pytest -q --tb=no
                                    102 passed, 28 skipped
ruff check src tests                PASS
```

No frontend API payload or backend behavior changed. The operational
`portproject` database was not used or modified by this frontend-only work.

## Final phase result

**PARTIAL** — the product-facing UI/UX refactor, responsive public shell,
evidence narrative, honest AI waiting state, loading/empty/error feedback, and
production build are complete and verified. Full authenticated browser E2E and
automated accessibility scanning remain unavailable in the current repository
tooling, so they are not reported as passing.

