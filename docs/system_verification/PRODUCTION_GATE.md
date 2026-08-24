# Production gate

## Decision

**NOT READY FOR PRODUCTION.**

This is a deliberate gate decision, not a statement that the local project is
unusable. The local API/UI/database/model stack is running and the code/build
checks are healthy, but production acceptance requires evidence that is not
available or currently fails.

## Gate checklist

| Gate | Required evidence | Decision |
|---|---|---|
| Build and dependency health | `pip check`, pytest, Ruff, and production UI build | **PASS** — all observed clean (31 tests passed) |
| Runtime/readiness | Intended ports and readiness with no init error | **PASS** — API/UI/DB/Ollama listeners and ready response confirmed |
| Database integrity | Correct DB, extensions, references, vector dimensions | **PARTIAL** — checked references/dimensions clean; one pending document remains |
| Authentication | Approved accounts can log in and receive scoped sessions | **BLOCKED** — no authorized credentials supplied |
| Authorization/isolation | DO/NO/HO/Tenant allow/deny and cross-principal tests | **BLOCKED** — role fixtures unavailable |
| RAG answers/citations | Reviewed questions return grounded, page-verifiable answers | **BLOCKED/PARTIAL** — corpus coverage exists; live generation/evidence not accepted |
| Workflow governance | Valid, invalid, stale, concurrent transitions and audit records | **BLOCKED/PARTIAL** — state machine exists; fixture unavailable |
| Dashboard/tenant semantics | Domain-approved labels and reconciled metrics | **FAIL/PARTIAL** — status `V` and `is_vacant=true` produce different vacancy areas |
| Billing/tender | Source-backed calculations and persistence through authorized API | **PARTIAL** — isolated service tests pass; live path not accepted |
| Failure/API contracts | Controlled outage and protected-route contracts | **PARTIAL** — readiness/401/CORS/guardrails checked; outage matrix open |
| Performance | Agreed SLOs under representative concurrent load | **PARTIAL** — warm local reads only; no load test |
| Responsive/accessibility | Browser viewport matrix, keyboard, contrast, and semantic audit | **NOT TESTED** |
| Backup/recovery | Successful isolated restore and post-restore readiness | **NOT TESTED** |
| Security deployment | HTTPS, secure cookies, secret handling, external auth review | **FAIL** — local secure-cookie setting is false and legacy password material is present |

## Required release conditions

The gate can move to **CONDITIONAL** only after all P0 and P1 blockers in
[`BLOCKERS.md`](BLOCKERS.md) have evidence-backed closure. It can move to
**PASS** only after:

1. a target-only immutable commit/release artifact exists;
2. approved role fixtures complete the authentication, isolation, workflow,
   billing, tender, and browser tests;
3. a reviewed RAG question/evidence set passes with captured timings;
4. domain owners approve the status/occupancy/tenant terminology;
5. secure production configuration is independently reviewed; and
6. backup/restore plus responsive/accessibility gates pass.

No production deployment, external publication, credential rotation, schema
change, or source refactor was performed by this audit.
