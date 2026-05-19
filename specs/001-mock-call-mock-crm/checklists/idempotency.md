# Idempotency & Duplicate-Event Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of duplicate-event handling, conflicting late events, attempt-count semantics, and idempotency-key requirements. Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [ ] CHK001 - Is the exact composition of an idempotency key specified (provider event identity + session ID + write-back kind, or another precise combination)? [Gap, Spec §Assumptions] → **RESOLVED-BY-FR-019 (tuple `(session_id, mock_provider_call_id, event_id, write_back_kind)`)**
- [ ] CHK002 - Are the categories of state that idempotency MUST protect enumerated exhaustively (session row, event rows, normalized result, attempt count, Phone Call-like activity payloads, queue-status update payloads, task payloads, exported artifacts)? [Completeness, Spec §FR-019 + §FR-023]
- [ ] CHK003 - Are the duplicate-event variants of every event type (`connected`, `no_answer`, `voicemail`, `failed`, `completed`, `callback_requested`) specified as values the mock transport MUST be able to emit? [Completeness, Spec §FR-006]
- [ ] CHK004 - Is the audit record for a conflicting late event specified with its required fields (received timestamp, conflicting event payload, the finalized disposition that was preserved, the conflicting event's identity)? [Completeness, Spec §FR-020]
- [ ] CHK005 - Is the de-duplication scope (per-session and per-write-back-kind) explicit, and are the implications for cross-session duplicates stated (allowed or out-of-scope)? [Completeness, Spec §Assumptions]
- [ ] CHK006 - Is the requirement that exported artifacts (FR-023) are also idempotent — same content, same filename, or skip rewrite — explicitly stated? [Gap, Spec §FR-019 + §FR-023]

## Requirement Clarity

- [ ] CHK007 - Is "event identity" defined precisely (a transport-supplied unique ID, a content hash, a composite key, or "any stable identifier the transport chooses")? [Ambiguity, Spec §FR-019]
- [ ] CHK008 - Is "finalized" defined precisely for a session — which dispositions count as finalized (all of FR-013's enum?), and at what wall-clock event does finalization occur? [Clarity, Spec §FR-020]
- [ ] CHK009 - Is "unique call attempt" defined for attempt-count purposes (one `mock_provider_call_id`, one `connected` event, one transport-initiated event sequence, or another anchor)? [Clarity, Spec §FR-021 + §Clarifications]
- [ ] CHK010 - Is "no-op with respect to state, normalized result, attempt count, Phone Call-like activities, queue-status updates, and task payloads" precise enough to allow a deterministic byte-level equality check before and after redelivery? [Clarity, Spec §FR-019]

## Requirement Consistency

- [ ] CHK011 - Does the spec consistently state that duplicate events are no-ops across state, normalized result, attempt count, all three write-back payload kinds, and exported artifacts (i.e., no carve-outs)? [Consistency, Spec §FR-019 + §FR-023]
- [ ] CHK012 - Is the per-attempt attempt-count increment rule (Clarifications Q1 + FR-021) consistent with the Story 3 duplicate-event acceptance scenarios, including the "duplicate callback requested" scenario? [Consistency, Spec §Clarifications + §Story 3]
- [ ] CHK013 - Is FR-020's prohibition on overwriting finalized dispositions consistent with the Edge Case "Late conflicting event" wording, and are both consistent about what is recorded vs. what is rejected? [Consistency, Spec §FR-020 + §Edge Cases]
- [ ] CHK014 - Is the "MUST treat provider-style events idempotently keyed on the event identity" requirement (Constitution Alignment) consistent with FR-019 (which uses similar language)? [Consistency, Spec §Constitution Alignment + §FR-019]
- [ ] CHK015 - Are Story 3 acceptance scenarios 4 and 5 (duplicate connected/completed event; duplicate callback-requested event) consistent in stating that no second activity, no second task, and no attempt-count increment occur? [Consistency, Spec §Story 3]

## Acceptance Criteria Quality

- [ ] CHK016 - Can SC-005's "100% of duplicate mock provider events redelivered for the same session leave state, normalized result, attempt count, Phone Call-like activities, queue-status updates, and task payloads unchanged" be tested as a deterministic fixture-driven property check? [Measurability, Spec §SC-005]
- [ ] CHK017 - Is SC-006's "0 false connected-call activities" observable from exported artifacts alone (without running the test instrumentation)? [Measurability, Spec §SC-006]
- [ ] CHK018 - Is the audit record for conflicting late events specified precisely enough that "the conflicting event was recorded" can be verified by reading the persisted state alone? [Measurability, Spec §FR-020]

## Scenario Coverage

- [ ] CHK019 - Are requirements specified for a duplicate event arriving BEFORE the first event of that identity is fully processed (race during session creation)? [Coverage, Gap]
- [ ] CHK020 - Are requirements specified for redelivered events arriving across separate command invocations of the same queue item (cross-invocation duplicate handling, in addition to in-process duplicate handling)? [Coverage, Gap]
- [ ] CHK021 - Are requirements specified for out-of-order event sequences (e.g., `completed` arrives before `connected`)? [Coverage, Gap]
- [ ] CHK022 - Are requirements specified for the duplicate `callback_requested` event when the session has not yet finalized (vs. the Story 3 case where the session is already finalized as `interested_callback_requested`)? [Coverage, Spec §Story 3]
- [ ] CHK023 - Are requirements specified for redelivery of a `failed` event after a `no_answer` event finalized the session (or vice versa, across different non-terminal-conflict pairings)? [Coverage, Gap]
- [ ] CHK024 - Are requirements specified for whether `voicemail` after `no_answer` is a conflict, a continuation, or both? [Coverage, Gap]

## Edge Case Coverage

- [ ] CHK025 - Is the "unknown event type" handling (log, no state mutation, no crash) specified precisely enough to write a fixture for? [Edge Case, Spec §Edge Cases]
- [ ] CHK026 - Are requirements specified for a `failed` event arriving for a session that never had a `connected` event (failure before pickup — what is the disposition, does it consume an attempt)? [Edge Case, Gap]
- [ ] CHK027 - Are requirements specified for two distinct semantic events sharing the same `event_id` by accident (idempotency-key collision — does the second event silently no-op, raise an audit warning, or fail loudly)? [Edge Case, Gap]
- [ ] CHK028 - Are requirements specified for handling of a malformed event payload (missing event-identity field, unknown disposition value in payload)? [Edge Case, Gap]

## Non-Functional Requirements

- [ ] CHK029 - Are requirements specified for the persistence of idempotency keys across process restarts (must survive a crash, must be durable before write-back, etc.)? [Gap, Spec §FR-022]
- [ ] CHK030 - Are requirements specified for the observability of duplicate-event no-ops (logged at what level, surfaced in the CLI, recorded in the audit trail)? [Gap, Spec §FR-027]

## Dependencies & Assumptions

- [ ] CHK031 - Is the assumption that idempotency-key scope is "per session and per write-back kind" (no cross-session dedup) documented as a hard Slice 1 boundary and aligned with all duplicate-handling FRs? [Assumption, Spec §Assumptions]
- [ ] CHK032 - Is the assumption that mock provider events ALWAYS carry an event identity stated as a precondition the transport MUST satisfy (not a hope)? [Assumption, Spec §FR-019]

## Ambiguities & Conflicts

- [ ] CHK033 - Is the precedence between FR-019 (duplicates are no-ops) and FR-020 (conflicting events are recorded for audit) explicit when a duplicate event is ALSO a conflicting event (e.g., a redelivered `failed` after `completed` — is it a duplicate of an earlier `failed`, a conflicting new event, or both)? [Conflict, Spec §FR-019 + §FR-020]
- [ ] CHK034 - Is the relationship between "the conflicting event MUST be recorded for audit" (FR-020) and "duplicate events MUST be no-ops with respect to state" (FR-019) precise about whether recording the audit event counts as a state mutation? [Ambiguity, Spec §FR-019 + §FR-020]
- [ ] CHK035 - Is the per-attempt-count anchor for `attempt_count` reconciled across FR-021 ("tied to a unique call attempt") and the Clarifications log ("every initiated mock call attempt MUST increment exactly once") — i.e., what specific event triggers the increment? [Ambiguity, Spec §FR-021 + §Clarifications]

---

## Addendum 2026-05-19 — Post-Remediation Coverage (FR-019/020/021 reformulation + Conflicting Event Audit Record entity)

The remediation reformulated FR-019 to pin the idempotency-key composition, tightened FR-020 to make the audit channel explicit, and tightened FR-021 to anchor the attempt-count increment. A new entity (Conflicting Event Audit Record) was added. The items below validate the tightened text.

- [ ] CHK036 - Is FR-019's idempotency-key tuple `(session_id, mock_provider_call_id, event_id, write_back_kind)` complete? Are there state mutations not keyable by this tuple (e.g., the conflicting-event audit row, which is keyed differently per the Phase 1 decision)? [Completeness, Spec §FR-019]
- [ ] CHK037 - Is FR-019's `write_back_kind` enumeration (`session_state`, `normalized_result`, `attempt_count`, `phone_call_activity`, `queue_status_update`, `task_payload`, `exported_artifact`) exhaustive? Does it cover every place a state mutation can occur? [Completeness, Spec §FR-019]
- [ ] CHK038 - Is FR-020's clarified precedence rule ("when a single event is BOTH a duplicate AND a conflicting late event, FR-019 wins") consistent with the Clarifications session decision? [Consistency, Spec §FR-020 + §Clarifications]
- [ ] CHK039 - Is the Conflicting Event Audit Record entity's field set (audit_id, session_id, event_id, conflicting_event_type, received_at, full_event_payload, preserved_disposition) complete for the FR-020 audit purpose? [Completeness, Spec §Key Entities]
- [ ] CHK040 - Is the Conflicting Event Audit Record's "separate persistence channel" claim (Spec §Key Entities) consistent with the data-model's table-level separation (`conflicting_event_audit_records` table, no FK to idempotency_keys)? [Consistency, Spec §Key Entities + Plan §data-model.md]
- [ ] CHK041 - Is FR-021's anchor ("incremented at the moment the mock transport emits its first event for a new `mock_provider_call_id`") precise about what counts as "first event" when events arrive out of order (e.g., `failed` before `connected`)? [Edge Case, Spec §FR-021]
