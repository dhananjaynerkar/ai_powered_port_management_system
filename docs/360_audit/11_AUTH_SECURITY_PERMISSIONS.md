# Authentication, security, and permissions audit

## Authentication flow

auth.py resolves Authority users from public.admin_users joined to active
public.admin_roles. Tenant users are resolved from public.applicant_registration.
Authority login accepts the source role IDs DO, NO, and HO through the
workflow-specific authority_identity check.

Passwords may be verified against bcrypt hashes, with legacy source field
fallbacks present in the existing code. This inherited behavior is a P1
production decision and must not be expanded without source-system approval.

## Sessions

create_session creates a random token, stores only its SHA-256 digest in
rag.user_session, sets an HTTP-only SameSite=Lax cookie, and checks idle and
absolute expiry. Logout deletes the digest. Login failures are rate-limited by
hashed username/IP key.

COOKIE_SECURE defaults false for local HTTP. This is acceptable only for
loopback development and must be true behind HTTPS.

## Authorization

current_user is a backend dependency. Authority metrics, tenant mappings,
billing, tender, and official agendas enforce Authority or participant checks.
Private chat and deletion use principal ownership. Agenda operations re-check
owner, state, source role, and target officer in workflow.py.

## Threat findings

| Threat | Evidence | Assessment |
| --- | --- | --- |
| SQL injection | Values are parameterized; schema identifiers are validated/composed. | Good for inspected paths; continue review of every new query. |
| Prompt injection | guardrails blocked selected patterns. | Partial control; semantic attacks remain possible. |
| Cross-principal chat leakage | Principal ownership predicates in chat routes. | Protected in inspected routes; needs role E2E tests. |
| Cross-role RAG leakage | ACL is applied in retrieval query. | Implemented; needs adversarial fixture tests. |
| Session theft | Opaque HTTP-only cookie and digest storage. | Local risk reduced; HTTPS required outside loopback. |
| CSRF | SameSite=Lax and local origins are present. | Formal CSRF threat test NOT VERIFIED. |
| XSS | React escaping is the default; custom Markdown renderer exists. | Review any raw HTML path before external exposure. |
| Credential exposure | Legacy source password fields are read. | P1 source-governance risk. |
| File/path traversal | Tender source keys are config-resolved; upload path needs a full test. | File-upload threat review NOT VERIFIED. |
| Destructive requests | Guardrail patterns and workflow state checks exist. | Not a complete authorization policy for every business action. |

## Recommended production gate

HTTPS, secure cookies, least-privilege database role, origin allowlist, source
credential remediation, backup/restore tests, dependency scanning, adversarial
ACL tests, and authenticated UI acceptance.

