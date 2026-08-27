# Security model

**Status: CURRENT SOURCE OF TRUTH**

The portal is designed for local/internal operation first. Security settings
make the deployment boundary explicit instead of silently treating development
defaults as production-safe.

## Authentication

Authority and Tenant login resolve existing PMS identities through
`public.admin_users`/`public.admin_roles` or `public.applicant_registration`.
Signup is intentionally disabled (`POST /api/v1/auth/bootstrap` returns `410`).
The server issues an opaque `portproject_session` cookie and stores only a
SHA-256 token digest in the configured RAG schema.

Sessions have idle and absolute expiry. Failed-login history is recorded in
`login_attempt` and rate-limited using the configured window/attempt limits.
Logout revokes the current session.

## Authorization and isolation

- Authority-only routes enforce the `authority` role.
- Agenda operations re-check the active source role/owner (`DO`, `NO`, `HO`)
  before reading or mutating official state.
- Private chats are keyed by principal. A user cannot read or delete another
  principal's chat.
- Workflow-linked private chats cannot be deleted because that would remove
  provenance from an official record.
- Lexical and dense retrieval apply document ACL roles before RRF and
  CrossEncoder reranking; unauthorized candidates are not returned as
  citations. Adjacent-page and parent/context expansion also join
  `chunk_acl` and apply the same public-or-current-role predicate before the
  row is assembled into model context. The acceptance suite includes a
  mixed-ACL document and proves that restricted neighbours are excluded for a
  tenant-role query. This is evidence for the implemented paths, not a claim
  that future retrieval code can bypass the shared authorization boundary.
- Heavy RAG requests use a bounded process-local gate (one active pipeline and
  one waiter in the local profile). Capacity rejection happens before any chat
  or agenda persistence, and the safe response does not reveal host memory,
  model, or database details.

## Deployment modes

| Mode | Intended use | Required posture |
| --- | --- | --- |
| `local` | Developer workstation/loopback demo | Local origins, non-secure cookie may be used, and legacy plaintext compatibility may be enabled only for the existing source-system compatibility path. |
| `internal` | Controlled private network | HTTPS public base URL, secure cookies, explicit HTTPS origins, private/loopback Ollama, and legacy plaintext compatibility disabled. |
| `production` | Approved deployment | All internal requirements plus a named non-privileged database role and strong PostgreSQL SSL mode (`require`, `verify-ca`, or `verify-full`). |

These constraints are enforced by the `Settings` model. `allowed_origins` must
be explicit; wildcard CORS is rejected. Ollama endpoints must resolve to
loopback/private hosts outside local mode.

## Sensitive data rules

Do not commit `.env`, passwords, session cookies, raw database dumps, tenant
records, or unnecessary document contents. Logs record safe event summaries and
timings, not passwords, tokens, or full secrets. Database troubleshooting must
use redacted configuration and never print a password.

## Credential compatibility decision

Local development still exposes an explicit `allow_legacy_plaintext_passwords`
flag because the source-system compatibility path exists. Internal and
production settings reject that flag. A future deployment must choose a
reviewed migration, SSO, or isolated compatibility strategy; this project does
not silently rewrite source-system passwords.

## Remaining gate

The code-level security contract is covered by settings/auth regression tests
and the acceptance mixed-ACL context-expansion regression. Production
promotion still requires an approved HTTPS deployment, least-privilege
database role, source-credential decision, and an authenticated
cross-principal acceptance run.
