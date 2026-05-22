# Tests Strategy Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of the testing approach defined in `research.md §Tests & CI gates` and the fixture catalog in the project structure. Unit tests for the *test-strategy writing*, not for the tests themselves.

**Created**: 2026-05-19
**Source**: [plan.md](../plan.md) ; [research.md §Tests](../research.md#tests--ci-gates)

## Test Strategy Completeness

- [x] CHK001 - Does the strategy enumerate every test layer (unit per module, integration end-to-end, dependency-direction lint, coverage floor)? [Completeness, Research §Tests]
- [x] CHK002 - Is the per-module unit-test set enumerated (one file per FR-033 boundary)? [Completeness, Plan §Project Structure]
- [x] CHK003 - Is the integration-test set tied to specific user stories (Story 1 → happy path; Story 2 → blocked; Story 3 → duplicates/conflicts)? [Completeness, Plan §Project Structure]
- [x] CHK004 - Is the SC-009 module-isolation gate specified operationally (pytest markers + dependency-direction lint), not just as an aspiration? [Completeness, Research §Tests + Spec §SC-009]
- [x] CHK005 - Are coverage targets specified with a concrete floor (`90%` per research.md) and a covered surface (`src/opencloser/` excluding `__init__.py`)? [Completeness, Research §Tests]

## Fixture Catalog Completeness (SC-003)

- [x] CHK006 - Does the conversation-fixtures directory cover every disposition in FR-013's 11-value enum (one fixture file per disposition)? [Completeness, Plan §Project Structure + Spec §FR-013 + §SC-003]
- [x] CHK007 - Is the captured-email-AND-callback case (Q5 Clarification) covered by a dedicated fixture file? [Coverage, Plan §Project Structure + Spec §Clarifications]
- [x] CHK008 - Is the email-invalid-no-callback downgrade case (FR-036 rule 7) covered by a dedicated fixture (`needs_human_review_email_invalid.json`)? [Coverage, Plan §Project Structure + Spec §FR-036]
- [x] CHK009 - Does the transport-events directory cover every non-connected path (`no_answer`, `voicemail`, `failed`) AND the duplicate-event paths (`duplicate_connected`, `duplicate_callback_requested`) AND the conflicting-late-event path (`conflicting_failed_after_completed`)? [Completeness, Plan §Project Structure + Spec §Story 3]
- [x] CHK010 - Are the queue-item-fixtures sufficient to cover every eligibility-blocking condition (DNC, call-window, max-attempts, missing-phone, missing-timezone, callable-status not `ready`)? [Completeness, Plan §Project Structure + Spec §Story 2]

## Test Strategy Clarity

- [x] CHK011 - Is "module-isolation" defined operationally (when running `test_persona.py`, every other module is stub-replaced)? [Clarity, Research §Tests + Spec §SC-009]
- [x] CHK012 - Is the "dependency-direction lint" specified precisely (which import statements are allowed/forbidden per module)? [Clarity, Research §Tests + Contracts]
- [x] CHK013 - Is "coverage floor 90%" measured by which tool and which configuration (line coverage, branch coverage, exclusion of `__init__.py`)? [Clarity, Research §Tests]
- [x] CHK014 - Is the SC-001 timing measurement strategy specified (CLI emits `wall_time_ms`; integration test asserts < 60000)? [Clarity, Research §Performance + Spec §SC-001]

## Determinism & Idempotency Tests

- [x] CHK015 - Are tests specified that assert FR-019's duplicate-event no-op behavior across every state surface (session, normalized result, attempt count, all three write-back kinds, exported artifacts)? [Completeness, Spec §FR-019 + §SC-005]
- [x] CHK016 - Are tests specified that assert FR-020's conflicting-event audit-only behavior (the audit row exists but no other state changes)? [Completeness, Spec §FR-020]
- [x] CHK017 - Are tests specified that assert FR-021's attempt-count-increment exactly-once semantics per `mock_provider_call_id`? [Completeness, Spec §FR-021]
- [x] CHK018 - Are tests specified that assert deterministic-JSON property (rerunning the same fixture produces byte-identical artifacts)? [Completeness, Research §JSON + Spec §SC-005]

## Edge Case & Failure Path Tests

- [x] CHK019 - Are tests specified for the call-window-expires-mid-call edge case (in-flight call completes, no new call placed)? [Coverage, Spec §Edge Cases]
- [x] CHK020 - Are tests specified for malformed-timezone fallback (default applied; eligibility decision records substitution)? [Coverage, Spec §Edge Cases]
- [x] CHK021 - Are tests specified for unknown-event-type handling (logged, no state mutation)? [Coverage, Spec §Edge Cases]
- [x] CHK022 - Are tests specified for FR-018's belt-and-suspenders behavior in the crm adapter (emit_task no-ops for excluded dispositions)? [Coverage, Spec §FR-018]
- [x] CHK023 - Are tests specified for the disclosure validator (persona refuses if first turn lacks AI+Medx identification)? [Coverage, Contracts §persona.md]

## Forward Compatibility Tests

- [x] CHK024 - Are tests specified for SC-008's interface stability — does some test/check ensure the crm adapter's public method signatures haven't changed since the contract was reviewed? [Coverage, Spec §SC-008]
- [x] CHK025 - Are contract-conformance tests specified (each module's unit tests use only the methods listed in its contracts/*.md file)? [Coverage, Contracts]
