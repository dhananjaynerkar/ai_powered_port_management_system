# Blockers and required follow-up

These are evidence-backed blockers from the acceptance matrix. They are
ordered by release impact, not by visual priority.

## P0 — do not promote

### P0-1 — production security configuration is not proven

- **Evidence:** local settings resolve `cookie_secure=false`; the external
  authentication compatibility path reads `public.admin_users.demo_password`
  and `public.admin_users.passwd`; the live database contains 232 authority
  rows with each of those password-material columns populated.
- **Impact:** a local-development setting or legacy credential representation
  must not be carried into a production deployment without an explicit
  security decision.
- **Required action:** enforce HTTPS and secure cookies in production, review
  the reverse-proxy/CORS boundary, remove or isolate plaintext password
  compatibility, rotate affected credentials, and obtain a security review.

### P0-2 — backup and restore are unverified

- **Evidence:** no approved backup artifact, restore log, RPO/RTO, or isolated
  recovery drill was supplied.
- **Impact:** database, vector corpus, local model, and workflow recovery are
  not acceptance-proven.
- **Required action:** create an encrypted backup plan, restore into an
  isolated database, start the API, and verify readiness, corpus counts,
  permissions, and representative documents.

## P1 — required for authenticated acceptance

### P1-1 — no authorized test accounts or role fixtures

- **Evidence:** no Authority/DO/NO/HO/Tenant credentials were supplied. The
  audit deliberately did not guess passwords, create accounts, or bypass
  authentication. Protected endpoints correctly returned 401 without a
  session.
- **Impact:** login, role matrix, cross-role leakage, workflow ownership,
  private chat, deletion, billing, tender API, and browser acceptance remain
  blocked.
- **Required action:** provide approved non-production accounts or a safe
  fixture containing at least one user for each supported role and a second
  principal for isolation tests.

### P1-2 — live answer/retrieval acceptance is incomplete

- **Evidence:** corpus coverage tests passed for 48 indexed documents, but a
  direct retrieval smoke attempt did not complete within the local command
  runner window while embedding/reranker startup was occurring. No live
  answer, source chip, citation relevance, model timing, or fallback result
  was asserted.
- **Impact:** the most important user-facing RAG behavior is not acceptance
  proven, even though the stored corpus and pipeline code are present.
- **Required action:** warm the local models, execute a reviewed question set,
  capture retrieval/generation/citation timings, and verify every source page.

### P1-3 — workflow and mutation concurrency are unverified

- **Evidence:** source state machine and locking/version fields exist, but no
  disposable agenda fixture or two-session concurrency test was available.
- **Impact:** valid transitions, invalid transitions, stale-owner rejection,
  deletion protection, audit writes, and rollback are not proven end to end.
- **Required action:** use a cloned fixture and execute valid, invalid, stale,
  duplicate, and concurrent requests without touching operational records.

### P1-4 — dashboard occupancy terminology is ambiguous

- **Evidence:** status `V` is 65,847.28 sq.m (6.58 ha), while
  `is_vacant=true` is 1,030,814.67 sq.m (103.08 ha). The API uses status and
  vacancy fields as separate concepts but the user-facing word “vacant” can
  collapse them.
- **Impact:** users can interpret the KPI as either 6.58 ha or 103.08 ha.
- **Required action:** obtain domain sign-off on status versus physical
  occupancy, name both metrics explicitly, and reuse the mapping in KPI,
  chart, filter, billing, and tender screens.

## P2 — quality and maintainability follow-up

### P2-1 — pending extraction

One document has pages but no chunks/embeddings. The readiness endpoint
correctly reports `pending_documents=1`; the release should either complete
that extraction or clearly keep the corpus in a pending state.

### P2-2 — target has no independent Git root

`git rev-parse` resolves to `C:/Users/15dha`, which also contains unrelated
files. This prevents a reliable target-only diff, release commit, or clean
worktree claim.

### P2-3 — viewport/accessibility evidence is missing

The source contains responsive breakpoints, scoped table overflow, keyboard
splitter handlers, and labels, but no authenticated browser matrix or
automated accessibility report was available.

### P2-4 — performance evidence is only a warm local sample

Read-only medians were approximately 90.7ms for dashboard metrics, 59.7ms for
tenant data, 44.0ms for corpus stats, and 282.8ms for readiness over a small
sample. These are not load-test SLOs.

## Explicit non-blockers observed during this audit

- Unauthenticated 401 responses on protected routes are expected and are not
  treated as authentication failures.
- Vite development HMR invalidation messages in historical logs are not a
  production build failure; the production build completed successfully.
- The one pending document is visible in readiness and is not silently counted
  as indexed.
