# Contract: Mock CRM Write-back Adapter

> **Note on syntax**: Python-flavored pseudo-code (`name: Type`) is used for readability across the team. Type-hint syntax is decorative; the authoritative contract is the prose description of operations, inputs, and outputs.

**Module boundary**: FR-033, principle #5 (write-back side)
**Implementation**: `src/opencloser/crm/base.py` (interface) + `src/opencloser/crm/mock.py` (Slice 1 mock)
**Owns**: payload assembly per FR-028 / FR-029 / FR-030, FR-031 per-disposition mapping, FR-032 queue-status mapping
**MUST NOT contain**: persona logic, eligibility logic, transport-event interpretation, session lifecycle management

---

## Public surface

```text
WriteBackAdapter (interface):
    emit_phone_call_activity(payload: PhoneCallActivityPayload) -> None
    emit_queue_status_update(payload: QueueStatusUpdatePayload) -> None
    emit_task(payload: TaskPayload) -> None
```

A second concrete implementation in Slice 2 will satisfy this same interface against the Dataverse SDK without changes to consumer code (FR-016 conceptual-contract requirement).

---

## Behavior

The adapter is invoked by the orchestrator AFTER the orchestrator has decided which payloads are required (via FR-031). The adapter does NOT decide whether to emit — it executes. This keeps disposition-policy decisions in the orchestrator (which already owns idempotency) and keeps the adapter responsible only for payload shape + persistence + export.

For each call:

1. INSERT a row into the corresponding table (`phone_call_activities` / `queue_status_updates` / `task_payloads`) per data-model.md.
2. Append the payload to the in-memory `WriteBack` aggregate for this session.
3. Return.

The Slice 1 mock adapter does NOT export artifacts directly — that's the `ArtifactWriter`'s job (called by the orchestrator at end-of-run). This keeps "persisted" and "exported" cleanly separated per the FR-015 + FR-023 split.

---

## Per-disposition emission map (FR-031, enforced by the orchestrator, mirrored here for reference)

| Final disposition | `emit_phone_call_activity` | `emit_queue_status_update` | `emit_task` (and kind) |
|---|---|---|---|
| `interested_callback_requested` | ✅ | ✅ | ✅ `callback` |
| `interested_email_captured` | ✅ | ✅ | ✅ `callback` |
| `needs_human_review` | ✅ | ✅ | ✅ `review` |
| `not_interested` | ✅ | ✅ | — |
| `call_back_later` | ✅ | ✅ | ✅ `callback` |
| `wrong_number` | ✅ | ✅ | — |
| `no_answer` | ✅ | ✅ | — |
| `voicemail` | ✅ | ✅ | — |
| `do_not_call` | ✅ | ✅ | — |
| `failed` | ✅ | ✅ | — |
| `blocked` | — | ✅ | — |

---

## Per-disposition `new_status` for queue-status payload (FR-032)

| Final disposition | `new_status` |
|---|---|
| `interested_callback_requested` | `ready` |
| `interested_email_captured` | `completed` |
| `call_back_later` | `ready` |
| `not_interested` | `completed` |
| `wrong_number` | `blocked` |
| `no_answer` | `ready` |
| `voicemail` | `ready` |
| `do_not_call` | `dnc` |
| `needs_human_review` | `blocked` |
| `failed` | `ready` |
| `blocked` | unchanged (orchestrator passes `previous_status` as `new_status`) |

The orchestrator computes `new_status` from this table and passes it on the `QueueStatusUpdatePayload`. The adapter does not re-derive.

---

## Payload shapes

See data-model.md for the Pydantic definitions. Brief recap:

```text
PhoneCallActivityPayload (FR-028):
  schema_version, session_id, queue_item_id, mock_provider_call_id,
  persona_version, final_disposition, summary, started_at, ended_at

QueueStatusUpdatePayload (FR-029):
  schema_version, session_id, queue_item_id,
  previous_status, new_status, transition_reason, transition_at

TaskPayload (FR-030):
  schema_version, task_id, session_id, queue_item_id,
  task_kind: "callback" | "review",
  subject,
  reason_code: HumanReviewReason | None   # required for task_kind="review"
  preferred_callback_window: str | None    # required for task_kind="callback" when window was captured
  captured_email: str | None               # populated when verified email accompanies callback (Q5)
  persona_version, created_at
```

---

## FR-018 precedence enforcement

The adapter's `emit_task` MUST be a no-op (return without persisting) if called with a `TaskPayload` whose disposition (looked up from the session) is in the FR-018 exclusion set: `not_interested`, `wrong_number`, `do_not_call`, `failed`, `blocked`. This is belt-and-suspenders — the orchestrator should not call `emit_task` in those cases, but the adapter rejects in case it does.

This makes FR-018's precedence-over-FR-009 invariant testable at the adapter unit-test layer.

---

## Idempotency

The adapter's persistence MUST cooperate with the orchestrator's idempotency-key table. The adapter does NOT compute keys; the orchestrator wraps each `emit_*` call inside an idempotency-key INSERT. If the key already exists, the orchestrator skips the call. Therefore the adapter MAY assume each `emit_*` is a first delivery.

---

## Forward-compat with Dataverse (FR-016, SC-008)

The interface is deliberately three methods over three Pydantic shapes. The Slice 2 Dataverse adapter:

- Implements `emit_phone_call_activity(...)` by POSTing the payload (translated to Dataverse field names) to the Phone Call entity.
- Implements `emit_queue_status_update(...)` by PATCHing the Dataverse-managed queue row.
- Implements `emit_task(...)` by POSTing to the Task entity with `task_kind` mapped to the appropriate Task subtype.

No changes to the Pydantic payload shapes or to the consumer code (orchestrator) should be required at Slice 2 time. The Slice 2 plan-time review verifies this.

---

## Dependencies allowed

- `opencloser.models` — payload Pydantic classes
- `opencloser.state` — INSERT rows in the three write-back tables

## Dependencies forbidden

- `opencloser.transport`, `opencloser.persona`, `opencloser.eligibility`, `opencloser.core`
- Any vendor-specific field name in Slice 1 — the payload field names are the contract, period
- Any business-rule decision (the adapter executes the orchestrator's decisions)
