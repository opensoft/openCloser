# Idempotency & Error Recovery Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for idempotency keys, duplicate-event handling,
bounded retry, and resume-after-failure — for completeness, clarity, consistency, and
coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-24 against `plan.md`, `research.md`, `data-model.md`, `contracts/` (post-`45a2356` audit pass; see `reverification.md`)
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Idempotency & recovery domain · **Audience**: PR reviewer / spec author

## Idempotency Keys & Correlation

- [x] CHK001 Is the idempotency-key derivation rule ("the session ID, or a key deterministically derived from it") specified deterministically? [Clarity, Spec §FR-024] — Resolved: FR-024 + research §7 (the session ID is the key).
- [x] CHK002 Does the spec require the idempotency key to be stamped on a metadata-verified Dataverse field, not free text in a description? [Completeness, Spec §FR-024] — Resolved: FR-024.
- [x] CHK003 Is a pre-write Dataverse query by the idempotency key required before each create? [Completeness, Spec §FR-024] — Resolved: FR-024 ("MUST pre-query Dataverse by that key before each create").
- [x] CHK004 Does the spec define behavior when the pre-write idempotency query itself fails transiently? [Coverage, Gap, Spec §FR-024] — Resolved: research §6 + contracts/dataverse-adapter.md — the pre-query is a `DataverseClient` call, so the bounded transient-retry policy applies to it.
- [x] CHK005 Are the CRM correlation identifiers required to be recorded both locally and on the CRM record? [Consistency, Spec §FR-024] — Resolved: FR-024 + Key Entities §CRM Correlation Identifier + data-model §1 (`crm_correlations`).
- [x] CHK006 Does the spec define a maximum lifetime or expiry for persisted correlation identifiers used to resume? [Gap] — Resolved: FR-023 and §Assumptions require CRM correlation/write-back progress records to be retained for at least 90 days or until local audit-artifact retention expires, whichever is longer, unless configured longer.
- [x] CHK007 Are requirements defined for a retry after the key was stamped on Dataverse but before the local correlation record was persisted? [Coverage, Gap, Spec §FR-024] — Resolved: research §7 + contracts/dataverse-adapter.md — the Dataverse pre-query is authoritative, so a missing local correlation row is reconciled on the next pre-query.

## Duplicate Event Handling

- [x] CHK008 Is duplicate detection specified for each artifact type individually (Phone Call activity, Task, queue-status transition, attempt increment)? [Completeness, Spec §FR-021] — Resolved: FR-021 enumerates all four record types.
- [x] CHK009 Is the no-op outcome of a duplicate mock event specified for both local session state and CRM write-back state? [Completeness, Spec §FR-022] — Resolved: FR-022.
- [x] CHK010 Does the spec define what constitutes "the same session" across repeated CLI invocations? [Clarity, Spec §FR-021] — Resolved: session ID is the identity; the queue item's last-session-ID field links a re-invocation to the prior session (contracts/cli-slice2.md resume).
- [x] CHK011 Are requirements defined for a duplicate mock event arriving after the session is already finalized? [Coverage, Spec §FR-022] — Resolved: FR-022 + US4 scenario 4.
- [x] CHK012 Are requirements defined for a duplicate `callback_requested` mock event for a CRM-backed session (original Task retained)? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases (duplicate `callback_requested`).
- [x] CHK013 Is "duplicate event" defined by event ID, and is the event-ID uniqueness assumption stated? [Clarity, Spec §FR-022] — Resolved: FR-022 ("same event ID") + specs/001/contracts/transport.md (event_id uniqueness model).
- [x] CHK014 Are requirements defined for concurrent duplicate processing (two runs of the same item) even though single-run is the norm? [Coverage, Gap] — Resolved: §Assumptions §Single campaign, single item — concurrent claims are explicitly out of scope.
- [x] CHK015 Is re-invocation of the CLI for an already-finalized session required to produce zero new records? [Completeness, Spec §FR-021] — Resolved: FR-021 + US4 scenario 4.

## Retry & Backoff

- [x] CHK016 Are bounded-retry parameters (max attempts, backoff strategy and timing) quantified in the requirements? [Clarity, Gap, Spec §FR-023] — Resolved by FR-023: initial attempt + 3 retries, 1s / 2s / 4s default backoff, capped `Retry-After`.
- [x] CHK017 Is "transient Dataverse error" defined once and used consistently rather than assumed? [Ambiguity, Spec §FR-023] — Resolved by Definitions.
- [x] CHK018 Does the spec distinguish a retryable transient error from a permanent error that must not be retried? [Gap, Spec §FR-023] — Resolved by Definitions + FR-023.
- [x] CHK019 Is it specified that a retry reuses the existing idempotency key / correlation identifier? [Completeness, Spec §FR-023] — Resolved: FR-023 ("Retries MUST reuse the existing idempotency key / CRM correlation identifier").
- [x] CHK020 Are requirements defined for retry behavior on each of the four write-back operations independently? [Coverage, Spec §FR-015] — Resolved: FR-023 ("bounded in-run retries per write operation"); research §6.

## Resume After Failure

- [x] CHK021 Are requirements defined for how partial write-back progress is persisted and read back so a resume run completes "only the missing CRM writes"? [Completeness, Spec §FR-023] — Resolved: FR-023 + data-model §1 (`writeback_progress`) + contracts/cli-slice2.md resume coordinator.
- [x] CHK022 Does the spec specify whether an exhausted-retry exit uses a failure exit status distinct from a clean completion? [Clarity, Gap, Spec §FR-023] — Resolved: FR-023 ("resume-needed status") + contracts/cli-slice2.md exit-status table.
- [x] CHK023 Are requirements defined for a resume run that finds the queue item already finalized? [Gap, Coverage] — Resolved: US4 scenario 4 + contracts/cli-slice2.md (re-invocation for a completed session is a clean no-op).
- [x] CHK024 Is the mid-write-back partial-failure edge case (activity created, Task fails) backed by explicit recovery requirements? [Traceability, Spec §Edge Cases] — Resolved: §Edge Cases + FR-023 + US4 scenario 3.
- [x] CHK025 Is it specified what the operator sees when a run exits for later resume, so the resume is discoverable? [Clarity, Gap, Spec §FR-023] — Resolved: Definitions §Operator-visible ("retry/resume state") + contracts/cli-slice2.md + quickstart §7.

## Consistency

- [x] CHK026 Is the "exactly one attempt-count increment" requirement reconcilable with the unspecified increment timing in FR-008? [Conflict, Spec §FR-021] — Resolved by the `Attempt consumed` definition and FR-021 timing rule.
- [x] CHK027 Do FR-021, FR-022, FR-023, and FR-024 form a non-overlapping, non-contradictory set? [Consistency, Spec §FR-021] — Resolved: re-verified — FR-021 (no duplicates + attempt timing), FR-022 (duplicate-event no-op), FR-023 (retry/resume), FR-024 (idempotency key) are delineated with no contradiction.
- [x] CHK028 Is idempotency behavior consistent between dry-run and write-enabled modes? [Consistency, Spec §FR-031] — Resolved: FR-031 + contracts/dataverse-adapter.md (dry-run issues zero writes, so idempotency is moot and consistent).
- [x] CHK029 Is SC-005's "exactly one … at most one Task" measurable and consistent with zero-Task dispositions? [Measurability, Spec §SC-005] — Resolved: SC-005 "at most one Task" accommodates zero-Task dispositions.
- [x] CHK030 Are the idempotency requirements consistent with the Slice 1 idempotency keys reused unchanged? [Consistency, Spec §Key Entities] — Resolved: Key Entities §Preserved Slice 1 Entities + data-model §4.
- [x] CHK031 Is the local correlation store's role (audit/correlation only, not queue lifecycle) consistent with the source-of-truth assumption? [Consistency, Spec §Assumptions] — Resolved: §Assumptions §Source of truth + data-model §1.

## Mid-Run CRM-State Conflict (T045 — added 2026-05-24)

- [x] CHK032 Are mid-run CRM-state conflict-detection requirements (T045) defined as the FR-003/FR-021 interplay — re-read mapped queue fields + `preserve_if_present` set immediately before the final write, stop on detected human change, preserve already-completed writes, persist partial `writeback_progress`, surface an operator-visible conflict? [Coverage, Spec §Edge Cases, T045] — Resolved: spec §Edge Cases "Dataverse queue item changed by a human between claim and write-back" + T045 task description; FR-003 (preserve high-confidence values) + FR-021 (no duplicate records on re-invocation) compose the conflict-stop contract. The resume coordinator (T032) re-performs the same conflict re-read on resume.

## Notes

- Requirements-quality audit only.
- **Re-verification result: 32/32 resolved.** The plan's retry/resume design, `crm_correlations` + `writeback_progress` tables, adapter pre-query, 90-day minimum retention, and T045 conflict-stop contract close every item.
