# Idempotency & Error Recovery Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for idempotency keys, duplicate-event handling,
bounded retry, and resume-after-failure — for completeness, clarity, consistency, and
coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Idempotency & recovery domain · **Audience**: PR reviewer / spec author

## Idempotency Keys & Correlation

- [ ] CHK001 Is the idempotency-key derivation rule ("the session ID, or a key deterministically derived from it") specified deterministically? [Clarity, Spec §FR-024]
- [ ] CHK002 Does the spec require the idempotency key to be stamped on a metadata-verified Dataverse field, not free text in a description? [Completeness, Spec §FR-024]
- [ ] CHK003 Is a pre-write Dataverse query by the idempotency key required before each create? [Completeness, Spec §FR-024]
- [ ] CHK004 Does the spec define behavior when the pre-write idempotency query itself fails transiently? [Coverage, Gap, Spec §FR-024]
- [ ] CHK005 Are the CRM correlation identifiers required to be recorded both locally and on the CRM record? [Consistency, Spec §FR-024]
- [ ] CHK006 Does the spec define a maximum lifetime or expiry for persisted correlation identifiers used to resume? [Gap]
- [ ] CHK007 Are requirements defined for a retry after the key was stamped on Dataverse but before the local correlation record was persisted? [Coverage, Gap, Spec §FR-024]

## Duplicate Event Handling

- [ ] CHK008 Is duplicate detection specified for each artifact type individually (Phone Call activity, Task, queue-status transition, attempt increment)? [Completeness, Spec §FR-021]
- [ ] CHK009 Is the no-op outcome of a duplicate mock event specified for both local session state and CRM write-back state? [Completeness, Spec §FR-022]
- [ ] CHK010 Does the spec define what constitutes "the same session" across repeated CLI invocations? [Clarity, Spec §FR-021]
- [ ] CHK011 Are requirements defined for a duplicate mock event arriving after the session is already finalized? [Coverage, Spec §FR-022]
- [ ] CHK012 Are requirements defined for a duplicate `callback_requested` mock event for a CRM-backed session (original Task retained)? [Coverage, Spec §Edge Cases]
- [ ] CHK013 Is "duplicate event" defined by event ID, and is the event-ID uniqueness assumption stated? [Clarity, Spec §FR-022]
- [ ] CHK014 Are requirements defined for concurrent duplicate processing (two runs of the same item) even though single-run is the norm? [Coverage, Gap]
- [ ] CHK015 Is re-invocation of the CLI for an already-finalized session required to produce zero new records? [Completeness, Spec §FR-021]

## Retry & Backoff

- [x] CHK016 Are bounded-retry parameters (max attempts, backoff strategy and timing) quantified in the requirements? [Clarity, Gap, Spec §FR-023] — Resolved by FR-023: initial attempt + 3 retries, 1s / 2s / 4s default backoff, capped `Retry-After`.
- [x] CHK017 Is "transient Dataverse error" defined once and used consistently rather than assumed? [Ambiguity, Spec §FR-023] — Resolved by Definitions.
- [x] CHK018 Does the spec distinguish a retryable transient error from a permanent error that must not be retried? [Gap, Spec §FR-023] — Resolved by Definitions + FR-023.
- [ ] CHK019 Is it specified that a retry reuses the existing idempotency key / correlation identifier? [Completeness, Spec §FR-023]
- [ ] CHK020 Are requirements defined for retry behavior on each of the four write-back operations independently? [Coverage, Spec §FR-015]

## Resume After Failure

- [ ] CHK021 Are requirements defined for how partial write-back progress is persisted and read back so a resume run completes "only the missing CRM writes"? [Completeness, Spec §FR-023]
- [ ] CHK022 Does the spec specify whether an exhausted-retry exit uses a failure exit status distinct from a clean completion? [Clarity, Gap, Spec §FR-023]
- [ ] CHK023 Are requirements defined for a resume run that finds the queue item already finalized? [Gap, Coverage]
- [ ] CHK024 Is the mid-write-back partial-failure edge case (activity created, Task fails) backed by explicit recovery requirements? [Traceability, Spec §Edge Cases]
- [ ] CHK025 Is it specified what the operator sees when a run exits for later resume, so the resume is discoverable? [Clarity, Gap, Spec §FR-023]

## Consistency

- [x] CHK026 Is the "exactly one attempt-count increment" requirement reconcilable with the unspecified increment timing in FR-008? [Conflict, Spec §FR-021] — Resolved by the `Attempt consumed` definition and FR-021 timing rule.
- [ ] CHK027 Do FR-021, FR-022, FR-023, and FR-024 form a non-overlapping, non-contradictory set? [Consistency, Spec §FR-021]
- [ ] CHK028 Is idempotency behavior consistent between dry-run and write-enabled modes? [Consistency, Spec §FR-031]
- [ ] CHK029 Is SC-005's "exactly one … at most one Task" measurable and consistent with zero-Task dispositions? [Measurability, Spec §SC-005]
- [ ] CHK030 Are the idempotency requirements consistent with the Slice 1 idempotency keys reused unchanged? [Consistency, Spec §Key Entities]
- [ ] CHK031 Is the local correlation store's role (audit/correlation only, not queue lifecycle) consistent with the source-of-truth assumption? [Consistency, Spec §Assumptions]

## Notes

- Requirements-quality audit only.
- Resolved in this pass: CHK016 (retry parameters), CHK017/CHK018 (transient vs. permanent error), CHK026 (attempt-increment timing).
- Remaining high-signal defects: CHK004/CHK007 (pre-query and stamp-before-persist gaps).
