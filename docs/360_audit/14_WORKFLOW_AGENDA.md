# Workflow and agenda audit

## State machine

| State | Current role | Allowed next actions |
| --- | --- | --- |
| DO_DRAFT | DO | submit_to_nodal |
| SUBMITTED_TO_NO | NO | return_to_do or submit_to_hod |
| RETURNED_TO_DO | DO | submit_to_nodal |
| SUBMITTED_TO_HO | HO | return_to_do, approve, or reject |
| APPROVED | HO | terminal |
| REJECTED | HO | terminal |

The exact allowed-state/action rules are declared in workflow.py transition_agenda.

## Creation rule

create_agenda_from_chat requires a Data Entry Operator, an owned chat session,
at least one message, and an assistant message with non-empty sources. It writes
agenda, agenda_version v1, and a system agenda_message.

## Handoff and evidence

Each valid transition locks and checks the agenda, verifies the current owner,
validates target officer role/activity, updates owner/state, writes a
context_capsule, and writes a HANDOFF agenda_message. Official versions are
stored in agenda_version. Evidence shown for a capsule is derived from AI
messages up to its timestamp.

## Read-only behavior

agenda_detail computes is_read_only when the viewer is not current owner or the
state is terminal. Backend writes independently reject view-only operations.

## Deletion/provenance

Private chats linked to workflow_draft or agenda source_chat_session_id return
409 and cannot be deleted. This preserves official provenance.

## Gaps

- No formal event-sourcing abstraction; current relational history is adequate
  for observed workflow.
- Full concurrent transition/load testing is NOT VERIFIED.
- Notification delivery beyond stored messages is NOT VERIFIED.
- Business sign-off on every state transition is required before external use.

