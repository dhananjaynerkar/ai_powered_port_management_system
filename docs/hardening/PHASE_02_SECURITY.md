# Phase 2 — Security gate

Status: **COMPLETE for the implemented application contract; deployment evidence remains required.**

This phase focused on session transport, source-credential compatibility, CORS,
and non-local deployment configuration. It did not change the database schema,
source-system passwords, workflow permissions, or UI behavior.

## Verified risks before this phase

- `cookie_secure` defaulted to `false`, so a non-loopback deployment could
  accidentally issue a session cookie without the Secure attribute.
- CORS origins were hard-coded to the two local Vite origins. There was no
  explicit environment contract separating local use from internal or production
  deployment.
- Authority authentication first compared `public.admin_users.demo_password`
  as plaintext, and Tenant authentication fell back to comparing
  `public.applicant_registration.password` as plaintext when bcrypt could not be
  used. The fallback was unconditional.
- Session tokens were already random and only their SHA-256 digests were stored.
  Absolute expiry, idle expiry, HttpOnly, and login-failure rate limiting were
  already present.
- The launcher binds the API to loopback. PostgreSQL and Ollama network scope,
  database role privileges, and TLS termination remain deployment concerns.

No password values were printed, copied, migrated, or rewritten.

## Explicit deployment modes

| Mode | Intended use | Cookie/CORS behavior | Credential behavior |
|---|---|---|---|
| `local` | Loopback development only | HTTP origins may be localhost/127.0.0.1; Secure may be false; SameSite defaults to `lax` | Legacy plaintext compatibility may be enabled temporarily |
| `internal` | Controlled HTTPS network | Explicit HTTPS origins, HTTPS public URL, Secure cookie, private/loopback Ollama | Legacy plaintext compatibility must be disabled |
| `production` | Public production behind HTTPS termination | All internal requirements plus a named non-privileged DB role and strong PostgreSQL SSL mode | Legacy plaintext compatibility must be disabled |

The application fails during configuration loading when an internal or
production deployment omits these requirements. It does not silently fall back
to local insecure defaults.

## Code changes

### Configuration contract

`src/portproject_rag/settings.py` now validates:

- `PORTPROJECT_RAG_DEPLOYMENT_ENVIRONMENT=local|internal|production`
- explicit comma-separated `PORTPROJECT_RAG_ALLOWED_ORIGINS` with no wildcard
- HTTPS `PORTPROJECT_RAG_PUBLIC_BASE_URL` outside local mode
- `PORTPROJECT_RAG_COOKIE_SECURE=true` outside local mode
- `PORTPROJECT_RAG_COOKIE_SAMESITE=lax|strict|none`; `none` requires Secure
- `PORTPROJECT_RAG_ALLOW_LEGACY_PLAINTEXT_PASSWORDS=false` outside local mode
- loopback/private Ollama endpoints outside local mode
- production `PORTPROJECT_RAG_DATABASE_ROLE` matching a non-privileged URL user
- production PostgreSQL URL query `sslmode=require`, `verify-ca`, or
  `verify-full`

`Settings.cors_origins` is the single parsed origin list used by the API CORS
middleware. The safe template is in `.env.example`; it contains no credentials.

### Session transport

Login cookies remain HttpOnly and now use the configured SameSite and Secure
values. Logout uses the same cookie attributes when clearing the cookie. Session
generation, token hashing, absolute expiry, idle expiry, and database-backed
revocation remain unchanged.

### Legacy credential compatibility

The source-system compatibility path is now explicit:

1. A bcrypt source hash is attempted whenever one is present.
2. A plaintext source field is consulted only when
   `allow_legacy_plaintext_passwords` is enabled.
3. That flag is allowed by validation only in `local` mode.

This is a gate, not a migration. The portal does not copy, normalize, or rewrite
source passwords. A production deployment using source rows that contain only
plaintext values will require an approved source migration or SSO decision.

## Configuration examples

### Local development

```dotenv
PORTPROJECT_RAG_DEPLOYMENT_ENVIRONMENT=local
PORTPROJECT_RAG_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
PORTPROJECT_RAG_COOKIE_SECURE=false
PORTPROJECT_RAG_COOKIE_SAMESITE=lax
PORTPROJECT_RAG_ALLOW_LEGACY_PLAINTEXT_PASSWORDS=true
```

Keep this mode on loopback only.

### Controlled internal deployment

```dotenv
PORTPROJECT_RAG_DEPLOYMENT_ENVIRONMENT=internal
PORTPROJECT_RAG_PUBLIC_BASE_URL=https://portal.internal.example
PORTPROJECT_RAG_ALLOWED_ORIGINS=https://portal.internal.example
PORTPROJECT_RAG_COOKIE_SECURE=true
PORTPROJECT_RAG_COOKIE_SAMESITE=lax
PORTPROJECT_RAG_ALLOW_LEGACY_PLAINTEXT_PASSWORDS=false
```

Use a private/loopback Ollama endpoint and a least-privilege PostgreSQL role;
restrict PostgreSQL to the application network. The reverse proxy must
terminate HTTPS and forward requests only to the loopback-bound API.

### Production

```dotenv
PORTPROJECT_RAG_DEPLOYMENT_ENVIRONMENT=production
PORTPROJECT_RAG_PUBLIC_BASE_URL=https://portal.example.com
PORTPROJECT_RAG_ALLOWED_ORIGINS=https://portal.example.com
PORTPROJECT_RAG_COOKIE_SECURE=true
PORTPROJECT_RAG_COOKIE_SAMESITE=lax
PORTPROJECT_RAG_ALLOW_LEGACY_PLAINTEXT_PASSWORDS=false
PORTPROJECT_RAG_DATABASE_URL=postgresql://portproject_app:<password>@db.internal:5432/portproject?sslmode=verify-full
PORTPROJECT_RAG_DATABASE_ROLE=portproject_app
```

The application still binds to loopback; expose it only through an HTTPS
reverse proxy. Ollama must remain on loopback or a private network, and the
database user must be restricted to the schemas and operations required by the
portal. The application cannot prove database grants from configuration alone;
that is a deployment acceptance check.

## Credential-compatibility decision still required

The source system currently exposes legacy credential fields in the verified
login queries. Before production access is approved, the system owner must
choose one of:

- migrate source accounts to an approved bcrypt/SSO identity system;
- integrate an approved identity provider and disable source-password login; or
- authorize a time-bounded isolated compatibility service outside the public
  production path.

No option was selected or executed in this phase.

## Regression checks

Added `tests/test_security_settings.py` covering:

- local defaults and loopback origins;
- HTTPS and Secure-cookie requirements for non-local modes;
- rejection of wildcard/dev origins, plaintext compatibility, weak PostgreSQL
  transport, and privileged production roles;
- acceptance of a private Ollama/HTTPS production contract;
- bcrypt versus explicitly gated plaintext verification; and
- HttpOnly, SameSite, Secure, and expiry cookie options.

Validation completed:

- `38 passed` Python tests
- Ruff checks passed
- frontend production build passed
- `git diff --check` passed

## Remaining deployment blockers

1. Provision an approved least-privilege PostgreSQL role and verify its grants
   against the real deployment database.
2. Provision HTTPS termination and verify the configured origin and cookie
   behavior through the deployed reverse proxy.
3. Confirm Ollama is reachable only from the private application network.
4. Obtain an owner-approved migration or SSO decision for source plaintext
   credential fields.

Phase 3 and later refactoring are intentionally not started here.
