# Official agenda workflow

**Status: CURRENT SOURCE OF TRUTH**

The product separates a private evidence assistant from the official agenda
record. A private conversation can be used as source material, but it becomes
official only through the agenda APIs and governed ownership transitions.

## Lifecycle

```text
private cited chat
  -> DO creates agenda draft (v1)
  -> DO submits to NO
  -> NO returns to DO or submits to HO
  -> HO approves or rejects
```

Database states are `DO_DRAFT`, `SUBMITTED_TO_NO`, `RETURNED_TO_DO`,
`SUBMITTED_TO_HO`, `APPROVED`, and `REJECTED`. The service validates actor,
current owner, state, and target officer in one transition operation.

## Evidence and versioning

An agenda stores the source private chat reference, versioned draft text,
official messages, and a `context_capsule` snapshot at handoff. AI messages
carry the same page-level source metadata used by private RAG. A revision
increments `editing_version`; the source conversation is not deleted.

## Permission behavior

Participants can view an agenda when authorized by the participant/owner
relationship. If the current owner is another role, the API returns a read-only
snapshot and rejects official-thread AI queries with `409`; the UI should not
pretend that a locked composer is usable. Only the current owner can revise or
transition the agenda.

## Supported API actions

| Action | Route | Result |
| --- | --- | --- |
| Create | `POST /api/v1/workflow/agendas` | Creates a DO draft from a cited private chat. |
| Revise | `POST /api/v1/workflow/agendas/{id}/revisions` | Saves a new official version for the current owner. |
| Transition | `POST /api/v1/workflow/agendas/{id}/transition` | Performs an authorized handoff/approval/rejection. |
| Official AI | `POST /api/v1/workflow/agendas/{id}/query` | Adds a grounded question and answer to an editable official thread. |

## Invalid transitions

Wrong role, wrong owner, wrong state, missing recipient, duplicate transition,
and read-only requests are rejected. The workflow service is the authority;
frontend disabled buttons are only a usability aid.

## Product boundary

Private AI questions may be used to gather evidence without changing an agenda.
Copying evidence or creating an official agenda is an explicit action. This
keeps the audit trail and ownership controls clear.
