# Mock Call Transport Requirements Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of requirements for the mock call transport (FR-006 / FR-007 / FR-008). Unit tests for the *requirements*, not for the implementation.

**Created**: 2026-05-19
**Feature**: [spec.md](../spec.md) ; [contracts/transport.md](../contracts/transport.md)

## Requirement Completeness

- [x] CHK001 - Is the full set of event types the transport MUST emit enumerated (`connected`, `no_answer`, `voicemail`, `failed`, `completed`, `callback_requested`)? [Completeness, Spec §FR-006]
- [x] CHK002 - Are the duplicate-event variants specified for EVERY event type (not just connected/callback)? [Completeness, Spec §FR-006]
- [x] CHK003 - Is the `mock_provider_call_id` uniqueness scope specified (globally unique across all sessions per FR-007)? [Completeness, Spec §FR-007]
- [x] CHK004 - Is the FR-008 "only path" invariant specified precisely enough to gate code review (e.g., the orchestrator MUST receive call-level events only from this interface)? [Completeness, Spec §FR-008]
- [x] CHK005 - Are the event payload fields enumerated per event type (e.g., `voicemail` carries voicemail-length; `failed` carries failure reason)? [Gap, Spec §FR-006 + §Key Entities]
- [x] CHK006 - Are the transport's responsibilities at the boundary specified (allocate `mock_provider_call_id`, emit events, do NOT mutate session state)? [Completeness, Spec §FR-008]

## Requirement Clarity

- [x] CHK007 - Is "fixture- or script-driven" defined precisely (one fixture per scenario, mapped to a queue-item ID)? [Ambiguity, Spec §FR-006]
- [x] CHK008 - Is "event identity" (the FR-019 idempotency anchor) defined precisely as a transport-supplied unique ID within the scope of one `mock_provider_call_id`? [Clarity, Spec §FR-019]
- [x] CHK009 - Is "the same conceptual contract that the future SignalWire transport will satisfy" defined operationally (a named interface, a method-list document, a reviewer-judgment phrase)? [Ambiguity, Spec §FR-008]
- [x] CHK010 - Is the timing relationship between `place_call` returning and the first event arriving specified (synchronous return → event stream begins immediately; or async)? [Clarity, Gap]

## Requirement Consistency

- [x] CHK011 - Does the transport's event-type list (FR-006) align exactly with the Mock Call Event entity's `event_type` CHECK constraint (data-model.md)? [Consistency, Spec §FR-006 + §Key Entities]
- [x] CHK012 - Is the transport's role consistent across FR-006 (emits events), FR-007 (assigns mock_provider_call_id), FR-008 (only path for events), and the Constitution Alignment's "no business rule, persona language, or vendor-shape detail may leak"? [Consistency, Spec §Constitution Alignment + §FR-006 / §FR-007 / §FR-008]
- [x] CHK013 - Is the transport's idempotency contribution (event_id) consistent with FR-019's idempotency-key composition that names `event_id` as the per-call anchor? [Consistency, Spec §FR-019]
- [x] CHK014 - Are the Story 3 acceptance-scenario event types (`no_answer`, `voicemail`, `failed`, duplicate `callback_requested`) consistent with FR-006's emission list and with the data-model `event_type` CHECK? [Consistency, Spec §Story 3 + §FR-006]

## Acceptance Criteria Quality

- [x] CHK015 - Is "the transport is the only path through which call-level events enter the Interaction Core" testable by static code inspection (e.g., dependency-direction lint) rather than runtime behavior alone? [Measurability, Spec §FR-008]
- [x] CHK016 - Is the requirement for `mock_provider_call_id` global uniqueness verifiable by a SQLite UNIQUE constraint or equivalent? [Measurability, Spec §FR-007]
- [x] CHK017 - Is the requirement that "duplicate-event variants" be emittable testable by a fixture file containing repeated `event_id` values? [Measurability, Spec §FR-006]

## Scenario Coverage

- [x] CHK018 - Are requirements specified for the case where `place_call` is invoked but no events ever arrive (transport-level timeout)? [Coverage, Gap]
- [x] CHK019 - Are requirements specified for an event sequence that ends without a finalizing event (open-ended stream)? [Coverage, Gap]
- [x] CHK020 - Are requirements specified for an out-of-order event sequence (e.g., `completed` before `connected`)? [Coverage, Gap]
- [x] CHK021 - Are requirements specified for emitting `callback_requested` mid-stream BEFORE the session has finalized (Story 3's duplicate-callback case implies a non-finalized callback_requested can also occur)? [Coverage, Spec §Story 3]
- [x] CHK022 - Are requirements specified for the case where the fixture contains a `connected` event followed by another `connected` event (illegal sequence or duplicate)? [Coverage, Gap]

## Edge Case Coverage

- [x] CHK023 - Is the "unknown event type" handling (log, no state mutation, no crash) specified at the transport boundary or only at the orchestrator? [Edge Case, Spec §Edge Cases]
- [x] CHK024 - Are requirements specified for malformed event payloads (missing event_id, unknown event_type, malformed timestamp)? [Edge Case, Gap]
- [x] CHK025 - Are requirements specified for the case where the fixture file is missing or unreadable (transport-side failure mode)? [Edge Case, Gap]
- [x] CHK026 - Are requirements specified for the `mock_provider_call_id` allocation strategy under collision (extremely unlikely with UUIDs but still policy)? [Edge Case, Gap]

## Non-Functional Requirements

- [x] CHK027 - Are requirements specified for the transport's deterministic event ordering across runs of the same fixture (no race conditions, no async reordering)? [Gap, Spec §SC-005]
- [x] CHK028 - Are requirements specified for the transport's read-only property (it MUST NOT write to the state store or to the queue item)? [Gap, Spec §FR-008]

## Dependencies & Assumptions

- [x] CHK029 - Is the assumption that the future SignalWire transport will satisfy the SAME conceptual contract (no shape changes; only name changes like `mock_provider_call_id` → `provider_call_id`) explicit? [Assumption, Spec §FR-008 + §SC-008]
- [x] CHK030 - Is the assumption that mock provider events ALWAYS carry an event_id stated as a precondition the transport interface enforces (not a hope)? [Assumption, Spec §FR-019]

## Ambiguities & Conflicts

- [x] CHK031 - Is the boundary between Transport and Persona reconciled — when a `connected` event arrives, does the transport hand off conversation control to the persona via the orchestrator, or does the persona pull from the transport directly? [Ambiguity, Spec §Constitution Alignment + §FR-008 + §FR-009]
- [x] CHK032 - Is FR-006's "fixture- or script-driven" reconciled with the plan's pick of "fixture only" (research.md §Mock transport fixture format)? [Consistency, Spec §FR-006 + Plan §research.md]
