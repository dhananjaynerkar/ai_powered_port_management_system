# Phase 08 — Identity and role model (source-derived)

Status: source inspection completed; live acceptance verification is blocked
until the private `.env.acceptance` configuration is supplied.

This model is derived from `src/portproject_rag/auth.py`,
`src/portproject_rag/workflow.py`, `src/portproject_rag/api.py`,
`src/portproject_rag/retrieval.py`, `src/portproject_rag/database.py`, and
`scripts/acceptance_fixture.py`. No passwords, hashes, cookies, or tokens are
included.

## The important distinction

The application has two separate role dimensions:

1. **Portal role** controls which portal a user signs into and is stored on the
   authenticated `PortalUser` as `authority` or `tenant`.
2. **Workflow role** is the source-system `public.admin_roles.role_id` value
   (`DO`, `NO`, or `HO`) for authority accounts. It is looked up again from the
   database by `authority_identity`; it is not represented by
   `PortalUser.role`.

Therefore, `authority != DO`. An authority portal user can be a DO, NO, or HO,
and a tenant is not assigned a workflow role.

## Identity mapping

| Identity | Portal role | Workflow role | Principal ID | Login/source identity | Allowed domain |
| --- | --- | --- | --- | --- | --- |
| Authority officer | `authority` | Active `DO`, `NO`, or `HO` from `public.admin_roles.role_id` | `authority:<admin_id>` | `public.admin_users.user_name` matched case-insensitively, including the supported username/domain variants | Authority dashboard, tenant registry, authority chat, and workflow routes subject to the resolved workflow role and active-owner checks |
| Tenant | `tenant` | None | `tenant:<applicant_id>` | Exact case-insensitive `public.applicant_registration.username` for an approved/active applicant | Tenant portal, tenant-scoped chat, and authenticated common routes; authority-only routes must reject the user |
| Local application account (legacy/setup path) | `authority` or `tenant` | None unless separately linked to a source officer | `local:<rag.app_user.user_id>` | `rag.app_user.username` | The portal role stored on the local account; the API bootstrap endpoint is currently disabled, and acceptance fixtures use source accounts instead |

### Acceptance fixture principals

The resettable fixture defines these sanitized source identities:

| Fixture login label | Source table | Source role | Principal ID |
| --- | --- | --- | --- |
| `DO_TEST` | `public.admin_users` + active `public.admin_roles` | `DO` | `authority:10001` |
| `NO_TEST` | `public.admin_users` + active `public.admin_roles` | `NO` | `authority:10002` |
| `HO_TEST` | `public.admin_users` + active `public.admin_roles` | `HO` | `authority:10003` |
| `TENANT_TEST` | `public.applicant_registration` | None | `tenant:20001` |
| second tenant fixture | `public.applicant_registration` | None | `tenant:20002` |

The fixture also uses Principal A = `authority:10001` and Principal B =
`tenant:20001` for cross-principal tests. These labels identify synthetic
fixtures; their private passwords remain in the ignored runtime credentials
file and are never documented or printed.

## Authentication and session flow

1. `/api/authority/login` calls `authenticate(..., "authority")`, which joins
   `public.admin_users` to an active `public.admin_roles` row and validates that
   the source role is `DO`, `NO`, or `HO`.
2. `/tenant/api/auth/login` calls `authenticate(..., "tenant")`, which resolves
   an approved/active row in `public.applicant_registration`.
3. Both paths return a `PortalUser` with a portal role and a stable principal
   string. External source identities have `user_id=None` because they are not
   rows in `rag.app_user`.
4. `create_session` generates an opaque random token. The browser receives it
   as the HttpOnly `portproject_session` cookie; only its SHA-256 digest is
   stored in `rag.user_session`, alongside `principal_id`, username, display
   name, portal role, expiry, and idle-access data.
5. `current_user` hashes the cookie presented by the request, validates expiry
   and idle timeout, updates `last_accessed_at`, and reconstructs `PortalUser`.

## Agenda ownership and workflow authorization

`rag.agenda` stores these independent ownership fields:

- `created_by_principal`
- `assigned_do_principal`
- `assigned_nodal_principal`
- `assigned_hod_principal`
- `current_owner_principal`
- `current_owner_role` (`DO`, `NO`, or `HO`)

`authority_identity` first requires the portal role `authority`, then parses the
`authority:<admin_id>` principal and resolves the active source role from
`public.admin_roles`. Agenda listing/detail additionally require the caller's
principal to be one of the agenda participants. Mutations require the caller
to be the `current_owner_principal`; transition rules then enforce the source
workflow role and allowed state.

This means an authority officer can see an agenda because of participant
membership, but cannot edit or hand it off merely because the portal role says
`authority`.

## Chat ownership and privacy boundary

`rag.chat_session.principal_id` is the ownership key. Listing, reading, and
deleting a conversation all filter by the authenticated caller's exact
`principal_id`. A workflow-linked session is additionally protected from
deletion if it is referenced by `workflow_draft` or `agenda.source_chat_session_id`.

The `user_id` column is nullable for external source identities; principal
scoping is therefore the authoritative privacy boundary for the acceptance
fixtures.

## RAG ACL boundary

The retrieval queries pass `PortalUser.role` to the ACL predicate:

```text
cardinality(acl_roles) = 0 OR requested_portal_role = ANY(acl_roles)
```

The acceptance documents therefore use these ACL values:

- empty ACL: public evidence
- `authority`: evidence available to all authority officers (DO/NO/HO)
- `tenant`: evidence available to tenants

`DO`, `NO`, and `HO` are **not** RAG ACL values in the current implementation.
Workflow-role-specific evidence would require a separate, explicitly approved
authorization design; it must not be assumed from the current source code.

## Live-verification items for the next Phase 08 step

Once the private acceptance DSN is available, verify without mutating
`portproject`:

- authority login resolves `role=authority` and the correct workflow title for
  each DO/NO/HO fixture;
- tenant login resolves `role=tenant` and a `tenant:<applicant_id>` principal;
- sessions are principal-bound and cookies are not exposed in reports;
- cross-principal chat read/list/delete attempts are denied;
- authority-only endpoints reject tenant sessions;
- workflow endpoints reject tenants and enforce source-role/owner rules;
- authority retrieval sees authority/public evidence, while tenant retrieval
  sees tenant/public evidence only;
- restricted evidence is absent from retrieved chunks, context, citations, and
  generated answers for the disallowed principal.

These are verification tasks, not claims that have been live-tested in this
blocked turn.
