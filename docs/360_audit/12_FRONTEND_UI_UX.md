# Frontend and UI/UX audit

## Architecture

web/src/main.tsx is a single React entry containing the shell, login/setup
states, dashboard, tenant registry, assistant chat, workflow screen, billing
modal, tender modal, shared citation rendering, and data-state components.
web/src/styles.css contains shared tokens, responsive layout, controls, cards,
splitters, charts, table styles, and modal styles.

This is a functioning feature-rich single-page shell, but main.tsx (about 2,511
lines observed) and styles.css (about 5,458 lines observed) are maintenance
risks. A broad split is NOT recommended without UI regression coverage.

## Verified UX capabilities

- Authority/Tenant login screens.
- Dashboard metrics and charts.
- Tenant filters, sorting, paging, page jump, and responsive table handling.
- Assistant conversation list, empty/loading/error states, citations, model and
  document context controls, suggestions, and resizable conversation splitter.
- Official workflow agenda list, thread, evidence snapshots, and handoff panel.
- Billing and tender source-backed modals.

## Role UX review

DO/NO/HO read-only and owner states are represented by API state and workflow
rendering. The intended permission behavior is implemented in backend and UI,
but full role-by-role browser acceptance is NOT VERIFIED without real accounts.

## Accessibility and responsive risks

Keyboard and aria support exist for many controls and splitters. A complete
keyboard-only pass, screen-reader pass, chart alternative pass, and all-width
visual matrix are NOT VERIFIED in this audit. The audit prompt’s requested
1024px/1280px/1366px/1440px/1920px matrix should be a future QA run.

## Safe future boundaries

Extract shared CitationList/Markdown rendering first, then feature modals,
then assistant/workflow panels. Each extraction requires TypeScript build,
unit tests for props/state, and authenticated browser checks.

