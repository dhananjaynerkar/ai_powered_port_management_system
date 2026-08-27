# GitHub safety inventory

This repository is prepared for source-code version control. The following
items must remain local or be supplied through a private deployment secret
store. The inventory contains names and patterns only; it does not contain any
credential values or tenant data.

## Never commit

- Environment overrides: `.env`, `.env.*`, and other machine-specific config
  files. The only committed environment files are sanitized templates:
  `.env.example` and `.env.acceptance.example`.
- Database connection strings, passwords, API keys, access tokens, session
  secrets, private keys, certificates, and service-account credentials.
- Local database files, SQL dumps, exports, backups, and serialized model or
  dataset files that may contain tenant or operational data.
- Uploaded PDFs, document copies, OCR output, tenant exports, and other raw
  corpus material unless it has been explicitly approved for public release.
- Runtime logs, crash dumps, local test credentials, browser state, caches,
  build output, and generated archives.
- Personal machine paths or configuration that reveal local usernames,
  network details, or internal deployment topology when they are not needed by
  the source code.

## Repository controls

The root `.gitignore` excludes the categories above, including all local
environment files except the two sanitized templates. It also excludes common
credential/certificate extensions, local database and backup formats, private
data directories, runtime state, and generated release archives.

## Safe configuration practice

1. Copy a sanitized template to a local ignored file.
2. Put real database URLs, passwords, tokens, and deployment values only in
   that local file or in the deployment secret store.
3. Review `git status --short` and the staged file list before every push.
4. If a secret is ever committed, revoke or rotate it first, then remove it
   from repository history using an approved repository-maintenance procedure.

## Pre-push evidence

Before publication, the working tree is checked for credential-shaped markers,
private-key blocks, sensitive extensions, ignored local data, and tracked
environment overrides. Secret values are not printed during these checks.
