# Contract: Dataverse Write-back Adapter

> Python-flavored pseudo-code for readability; the authoritative contract is the prose.

**Module boundary**: spec FR-015, FR-016, FR-021–FR-024; constitution principle III
**Implements**: the **unchanged** Slice 1 `WriteBackAdapter` interface —
`specs/001-mock-call-mock-crm/contracts/crm-writeback.md`
**Implementation**: `src/opencloser/crm/dataverse/adapter.py` (+ `client.py`, `auth.py`,
`mapping.py`, `errors.py`)
**Owns**: translating the Slice 1 `*Payload` shapes to Dataverse Web API requests, the
idempotency pre-query, bounded transient retry, and recording CRM correlation rows
**MUST NOT contain**: persona/eligibility/transport logic, the per-disposition emission
decision, or the `new_status` computation (those stay in the orchestrator — FR-017)

---

## Public surface

`DataverseWriteBackAdapter` implements the Slice 1 `WriteBackAdapter` interface **with no
signature changes** (SC-011):

```text
emit_phone_call_activity(payload: PhoneCallActivityPayload) -> None
emit_queue_status_update(payload: QueueStatusUpdatePayload) -> None
emit_task(payload: TaskPayload) -> None
build_writeback(session_id: str) -> WriteBack
```

The orchestrator consumes this exactly as it consumed the Slice 1 mock adapter — that is the
FR-016 / SC-011 guarantee.

---

## Behavior

For each `emit_*` (write-enabled mode):

1. **Translate** the conceptual payload to Dataverse fields via `DataverseMapping` — only
   `approved_update_field` fields appear in the request body; `preserve_if_present` and
   non-mapped fields are omitted (FR-003).
2. **Idempotency pre-query** (FR-024): `GET {entity}?$filter={idempotency_key_field} eq
   '{session_id}'&$top=1`. A hit ⇒ record/confirm the existing `dataverse_record_id` in
   `crm_correlations` and **return without creating** (no-op).
3. **Write**: POST (activity/Task) or PATCH (queue row) through `DataverseClient`, with the
   session ID stamped on the verified idempotency-key column. Bounded retry on **transient**
   errors (initial + 3 retries, 1s/2s/4s, `Retry-After`≤30s — FR-023); **permanent** errors
   fail without retry.
4. **Record** the result in `crm_correlations` (`write_status` = `confirmed`/`failed`) and
   update `writeback_progress`.
5. On retry-budget exhaustion mid-write-back: raise `WriteBackResumeNeeded`, leaving
   `writeback_progress.run_status = resume_needed` (the resume coordinator handles re-entry).

In **dry-run** mode, `emit_*` performs translation + the planned-payload capture only — zero
GET-for-pre-query mutations are unnecessary and zero POST/PATCH are issued (FR-031).

`emit_task` keeps the Slice 1 FR-018 no-op rule for excluded dispositions, and populates the
Dataverse `ownerid` lookup from `TaskPayload.assigned_to`.

`build_writeback(session_id)` assembles the in-memory `WriteBack` aggregate exactly as
Slice 1 — for the artifact writer.

---

## Per-disposition behavior

The per-disposition emission map and `new_status` table are **inherited unchanged** from
`crm-writeback.md`. The adapter does not re-derive them (SC-011).

---

## Dependencies

- **Allowed**: `opencloser.models`, `opencloser.crm.base`, `opencloser.crm.dataverse.*`,
  `opencloser.state` (correlation/progress rows), `httpx`, stdlib.
- **Forbidden**: `opencloser.transport`, `opencloser.persona`, `opencloser.eligibility`,
  `opencloser.core.orchestrator`; any Dataverse logical name **outside** `crm/dataverse/`
  (SC-010).
