# Contract: Interaction Core / Orchestrator

**Module boundary**: FR-033, principle #5
**Implementation**: `src/opencloser/core/orchestrator.py`
**Owns**: session lifecycle, idempotency-key application (FR-019), attempt-count increments (FR-021), call sequencing into the four boundary modules
**MUST NOT contain**: persona language, eligibility-rule logic, transport-event interpretation, or vendor-shaped payload assembly

---

## Public surface

```text
process_one_queue_item(
    queue_item_id: str,
    config: SliceConfig,
    state: StateStore,
    eligibility: EligibilityEvaluator,
    transport: CallTransport,
    persona: Persona,
    crm: WriteBackAdapter,
    artifacts: ArtifactWriter,
    clock: Clock = SystemClock(),
) -> RunReport
```

`RunReport` (CLI/test surface, NOT exported as JSON):

```text
RunReport {
    session_id: str
    final_disposition: Disposition
    mock_provider_call_id: str | None
    artifact_dir: str
    wall_time_ms: int
    eligibility_outcome: "allow" | "block"
}
```

---

## Behavior (high-level sequence)

1. Read `queue_items[queue_item_id]`. If absent, raise `QueueItemNotFound`.
2. Call `eligibility.evaluate(queue_item, config) → EligibilityDecision`.
3. Create a session row (FR-005). `state='created'`, `started_at=now()`.
4. If `decision.outcome == 'block'`:
    - Set `session.state='blocked'`, `final_disposition='blocked'`, `blocked_reason=decision.failing_rules`, `ended_at=now()`.
    - Apply `crm.emit_queue_status_update(...)` with `new_status=queue_item.callable_status` (no transition) and `transition_reason="blocked_by_eligibility: <comma-joined rules>"`.
    - Emit artifacts: `session-result.json`, `writeback.json` (queue-status-only), `eligibility-decision.json`.
    - Return.
5. Else (allowed):
    - Set `session.state='eligibility_evaluated'`.
    - Call `transport.place_call(queue_item) → mock_provider_call_id`. Record on session.
    - Increment `queue_items.attempt_count` exactly once for this `mock_provider_call_id` (FR-021 anchor).
    - Set `session.state='in_flight'`.
    - For each event in `transport.event_stream()`:
        - Compute the FR-019 idempotency key. If present in `idempotency_keys`, skip (no-op).
        - If `session.state == 'finalized'` AND event would change disposition: record into `conflicting_event_audit_records`. No state change, no write-back.
        - Else: INSERT into `mock_call_events`, route to the persona if event is `connected`, otherwise update session state.
    - When the event stream terminates OR a finalizing event is processed:
        - Read `persona.run(...)` result (already produced incrementally during the connected event).
        - Build the `NormalizedResult` from the persona output + session metadata.
        - Apply FR-031 to decide which write-back payloads to emit; apply FR-032 to compute `new_status`.
        - Call `crm.emit_phone_call_activity(...)`, `crm.emit_queue_status_update(...)`, and optionally `crm.emit_task(...)`.
        - Set `session.state='finalized'`, `ended_at=now()`.
6. Always emit the artifacts (FR-023) via `artifacts.write_session(session_id, ...)`.
7. Return `RunReport`.

---

## Idempotency contract (FR-019, FR-020, FR-021)

- The orchestrator is the SOLE owner of the `idempotency_keys` table.
- Every state-mutating step computes the FR-019 key `(session_id, mock_provider_call_id, event_id, write_back_kind)` and INSERTs it atomically with the state mutation in one transaction. UNIQUE-constraint violation → no-op.
- Attempt-count increment uses `write_back_kind='attempt_count'` with `event_id=None` and is keyed solely on `(session_id, mock_provider_call_id)`.
- FR-020 audit-record writes are NOT gated by the idempotency table (per Clarifications). They are gated by their own `(session_id, event_id)` PK to avoid duplicate audit rows when the same conflicting event is redelivered.

---

## Dependencies allowed

- `opencloser.models` — Pydantic entities
- `opencloser.state` — StateStore DAO
- `opencloser.eligibility` — EligibilityEvaluator interface
- `opencloser.transport` — CallTransport interface
- `opencloser.persona` — Persona interface
- `opencloser.crm` — WriteBackAdapter interface
- `opencloser.artifacts` — ArtifactWriter

## Dependencies forbidden

- Any concrete persona language (e.g., disclosure templates) — must come from `persona`
- Any vendor-specific payload field name (e.g., Dataverse field names) — must come from `crm`
- Any eligibility-rule logic (the orchestrator only reads `decision.outcome` and `decision.failing_rules`)
- Any conversation interpretation — the orchestrator passes the event stream through, never inspects content
