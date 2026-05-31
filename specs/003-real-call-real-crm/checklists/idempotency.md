# Idempotency Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for de-duplication and exactly-once semantics before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Dedup-Key Definitions

- [ ] CHK001 Is the idempotency key for Phone Call activities defined as a stable session-derived value stamped onto a metadata-verified Dataverse field? [Clarity, Spec §FR-021]
- [ ] CHK002 Is the idempotency key for Tasks defined as a stable session-derived value stamped onto a metadata-verified Dataverse field (same shape as Phone Call activity)? [Clarity, Consistency, Spec §FR-021]
- [ ] CHK003 Is the dedup key for SignalWire callback events defined as `(session_id, provider_event_id)`? [Clarity, Spec §FR-007, Spec §FR-027, Spec §Edge Cases, Spec §Key Entities]
- [ ] CHK004 Is the dedup key for SignalWire status callbacks and media callbacks defined as the same `(session_id, provider_event_id)` tuple (not divergent shapes)? [Consistency, Spec §FR-007, Spec §Edge Cases]
- [ ] CHK005 Is the dedup key for conflicting-late callbacks the same `(session_id, provider_event_id)` tuple as the regular callbacks audit log? [Consistency, Spec §FR-027, Spec §Edge Cases]
- [ ] CHK006 Is the dedup key for queue-claim semantics (concurrent CLI invocation) explicitly defined as the Dataverse queue item identifier observed as not-`ready`? [Clarity, Spec §FR-003, Spec §Clarifications, Spec §Edge Cases]
- [ ] CHK007 Is the dedup key for resume-on-re-invocation defined (session ID + write-back progress ledger so only missing writes execute)? [Clarity, Spec §FR-022, Spec §Story 4 #7, Spec §Story 7 #2]
- [ ] CHK008 Is the dedup key for attempt-count increment defined so that the increment is bound to exactly one successful dial (not to retry attempts or duplicate callbacks)? [Clarity, Spec §FR-025, Spec §Definitions]
- [ ] CHK009 Is the dedup key requirement explicit that the key MUST be backed by a metadata-verified Dataverse field (pre-discovered, not assumed)? [Measurability, Spec §FR-020, Spec §FR-021]
- [ ] CHK010 Is the Slice-3 rename of `mock_provider_call_id` → `provider_call_id` documented as backwards-compatible for replay / audit inspection so pre-Slice-3 correlation keys remain interpretable? [Consistency, Spec §FR-006, Spec §FR-018, Spec §Assumptions]
- [ ] CHK011 Is the dedup key explicitly NOT derived from any value that could change between retries (e.g., timestamps, callback receipt order, retry counter)? [Clarity, Ambiguity, Spec §FR-021, Gap]

## Per-Event-Source Dedup Contracts

- [ ] CHK012 Is the dedup contract for duplicate SignalWire status callbacks specified as a no-op for session state, normalized result, attempt count, and write-back, AND still recorded in the callbacks audit log? [Completeness, Spec §FR-007, Spec §FR-021, Spec §Story 4 #1]
- [ ] CHK013 Is the dedup contract for duplicate SignalWire media callbacks specified (Pipecat wired exactly once; second media callback no-op)? [Completeness, Spec §FR-007, Spec §Edge Cases]
- [ ] CHK014 Is the dedup contract for out-of-order SignalWire status callbacks specified (transport adapter tolerant; orchestrator does not rely on strict ordering; single coherent disposition produced)? [Completeness, Spec §FR-005, Spec §Story 4 #2, Spec §Edge Cases]
- [ ] CHK015 Is the dedup contract for late-after-finalization callbacks specified (no disposition change, no normalized-result mutation, no attempt increment, no new CRM write, recorded in conflicting-events audit log)? [Completeness, Spec §FR-027, Spec §Edge Cases]
- [ ] CHK016 Is the dedup contract for repeated CLI invocation on a fully-finalized session specified (no duplicate Phone Call activity, Task, queue-status transition, or attempt-count increment)? [Completeness, Spec §FR-021, Spec §Story 4 #9]
- [ ] CHK017 Is the dedup contract for repeated CLI invocation on a partially-written session specified (only the missing writes are retried)? [Completeness, Spec §FR-022, Spec §Story 4 #7, Spec §Story 7 #2]
- [ ] CHK018 Is the dedup contract for in-run retry after a transient Dataverse error specified (reuse correlation; no second Phone Call activity / Task)? [Completeness, Spec §FR-022, Spec §Story 4 #6, Spec §Story 7 #1]
- [ ] CHK019 Is the dedup contract for SignalWire provider-side retry of callback delivery specified (second delivery treated as duplicate via provider_event_id; no-op for state)? [Completeness, Spec §Story 7 #3, Spec §FR-021]
- [ ] CHK020 Is the dedup contract for orchestrator restart between dial and write-back specified (resume preserves real provider call ID; only missing writes execute)? [Completeness, Spec §Story 7 #4, Spec §Edge Cases]
- [ ] CHK021 Is the dedup contract for concurrent CLI invocations on the same queue item specified (second invocation observes not-`ready` and exits before dial; no dial, no attempt, no Phone Call, no Task)? [Completeness, Spec §FR-003, Spec §Clarifications, Spec §Edge Cases]
- [ ] CHK022 Is the dedup contract for callback-authentication-rejected events specified (rejected callbacks are not delivered to the orchestrator, do not enter the callbacks audit log as accepted events)? [Completeness, Ambiguity, Spec §FR-008, Gap]
- [ ] CHK023 Is the dedup contract for shadow STT discrepancy events specified so the same discrepancy is not double-emitted, and shadow events never independently create a CRM record? [Completeness, Spec §FR-030, Spec §SC-013, Spec §Story 6 #7]
- [ ] CHK024 Is the dedup contract for the shadow-STT-uncertain → `needs_human_review` escalation specified to create exactly one review Task (not duplicated if the discrepancy is re-evaluated)? [Completeness, Spec §FR-031, Spec §Story 6 #4, Spec §SC-005]
- [ ] CHK025 Is the dedup contract for live-call abandonment finalization specified so a late `completed` callback arriving after timeout does not retroactively create a connected-call Phone Call activity? [Completeness, Spec §FR-026, Spec §FR-027, Spec §Edge Cases]

## Attempt-Count Semantics

- [ ] CHK026 Is "Attempt consumed" defined precisely as: eligibility allows + run-mode checks pass + real-dial validation passes + telephony readiness passes + Dataverse metadata verification passes + SignalWire dial succeeded (real provider call ID assigned)? [Clarity, Measurability, Spec §Definitions, Spec §FR-025]
- [ ] CHK027 Is the "exactly once per session" requirement for attempt-count increment stated explicitly? [Measurability, Spec §FR-025, Spec §SC-008]
- [ ] CHK028 Is every blocked / failed path that MUST NOT increment attempt count enumerated (blocked eligibility, rehearsal/readiness mode, real-call flag absence, telephony readiness failure, real-dial phone-validation failure, Dataverse-unreachable-at-start, malformed dial-plan / persona-runtime configuration, provider-rejected dial)? [Completeness, Spec §FR-025, Spec §Definitions]
- [ ] CHK029 Are duplicate SignalWire callbacks for the same dialed call explicitly listed as a non-incrementing path? [Completeness, Spec §FR-021, Spec §FR-025]
- [ ] CHK030 Are conflicting-late callbacks explicitly listed as a non-incrementing path? [Completeness, Spec §FR-027]
- [ ] CHK031 Are repeated CLI invocations explicitly listed as a non-incrementing path (no duplicate attempt-count increment on resume)? [Completeness, Spec §FR-021, Spec §FR-022, Spec §Story 4 #9, Spec §Story 7 #2]
- [ ] CHK032 Are concurrent CLI invocations explicitly listed as a non-incrementing path for the second invocation? [Completeness, Spec §FR-003, Spec §Clarifications]
- [ ] CHK033 Is orchestrator restart between dial and write-back specified as preserving (not re-incrementing) the attempt count on resume? [Completeness, Spec §Story 7 #4, Spec §FR-022]
- [ ] CHK034 Is live-call abandonment specified as a path where the attempt has already been consumed (because dial succeeded) and is NOT re-incremented on timeout finalization? [Completeness, Ambiguity, Spec §FR-026, Spec §Definitions, Gap]
- [ ] CHK035 Is the relationship between attempt-count increment and Phone Call activity creation explicit (both happen exactly once per successful dial; neither is created on pre-dial failures)? [Consistency, Spec §FR-025, Spec §FR-010, Spec §FR-011, Spec §FR-012]
- [ ] CHK036 Is the requirement explicit that the attempt-count Dataverse field is treated as a metadata-verified write (i.e., the Slice 2 mapping artifact covers it)? [Completeness, Spec §FR-020, Spec §FR-021]
- [ ] CHK037 Is the success criterion for non-incrementing paths measurable (e.g., "0 such failures consume an attempt" in SC-009 / SC-010 / SC-012)? [Measurability, Spec §SC-009, Spec §SC-010, Spec §SC-012]

## Retry Budget & Backoff

- [ ] CHK038 Is the in-run retry budget specified as initial attempt + up to 3 retries? [Measurability, Spec §FR-022]
- [ ] CHK039 Is the backoff sequence specified as 1s / 2s / 4s default? [Measurability, Spec §FR-022]
- [ ] CHK040 Is `Retry-After` handling specified (honored when present, capped at 30s)? [Measurability, Spec §FR-022]
- [ ] CHK041 Is the retry budget scope explicit (per write-back operation, per session, or per write-back attempt) so it cannot be ambiguously expanded? [Clarity, Ambiguity, Spec §FR-022, Gap]
- [ ] CHK042 Is the requirement explicit that retries reuse the same idempotency key (no new correlation per retry)? [Consistency, Spec §FR-021, Spec §FR-022, Spec §Story 4 #6]
- [ ] CHK043 Is the requirement explicit that retry exhaustion leads to resume-on-re-invocation rather than a fresh attempt-count increment? [Consistency, Spec §FR-022, Spec §FR-025, Spec §Story 4 #7]
- [ ] CHK044 Is "transient" defined clearly enough that the retry-vs-abort decision is decidable (per Slice 2 transient-error classification reused)? [Clarity, Ambiguity, Spec §FR-022, Gap]
- [ ] CHK045 Is the retry behavior consistent across all four write-back operations (Phone Call activity, queue-status update, Task, write-back assembly)? [Consistency, Spec §FR-020, Spec §FR-022]
- [ ] CHK046 Is the retry budget explicitly bounded (no infinite retry loop) for every failure mode that triggers retry? [Measurability, Spec §FR-022]

## Resume-on-Re-Invocation Contracts

- [ ] CHK047 Is the resume contract explicit that ONLY missing writes are retried (no replay of already-successful writes)? [Clarity, Spec §FR-022, Spec §Story 4 #7, Spec §Story 7 #2]
- [ ] CHK048 Is the resume contract explicit that the recorded real provider call ID is preserved across re-invocation? [Completeness, Spec §Story 7 #4]
- [ ] CHK049 Is the resume contract explicit that the session ID is preserved across re-invocation (so the dedup key remains stable)? [Completeness, Spec §FR-021, Spec §FR-022]
- [ ] CHK050 Is the resume contract explicit that the persona version, runtime/model identity, and operator identity are preserved (or re-recorded consistently) on resume? [Completeness, Spec §FR-016, Gap]
- [ ] CHK051 Is the resume contract explicit when transcript retention is summary-only or pointer-only (resume from local audit artifacts, missing transcript file is not an error)? [Completeness, Spec §Edge Cases]
- [ ] CHK052 Is the resume trigger explicit (operator re-invokes the CLI; not an automatic watcher) — or is the choice documented as Deferred to Plan? [Clarity, Spec §Deferred to Implementation Plan]
- [ ] CHK053 Is the resume contract explicit that no second attempt-count increment occurs? [Consistency, Spec §FR-021, Spec §FR-025, Spec §Story 4 #9]
- [ ] CHK054 Is the resume contract explicit that no second Phone Call activity is created (idempotency-key pre-query on every create)? [Consistency, Spec §FR-021, Spec §Story 7 #2]
- [ ] CHK055 Is the resume contract explicit that no second Task is created on the `needs_human_review` resume path (e.g., Story 7 scenario 5)? [Completeness, Spec §FR-021, Spec §Story 7 #5]
- [ ] CHK056 Is the resume contract explicit that the local audit artifacts are sufficient to drive resume (correlation rows, progress rows, write-back progress ledger)? [Completeness, Spec §FR-022, Spec §Edge Cases, Spec §Key Entities]
- [ ] CHK057 Is the resume contract explicit that the local audit retention floor (≥ 90 days) supports delayed re-invocation? [Measurability, Spec §FR-022, Spec §Assumptions]

## No-Duplicate Guarantees (Per Record Type)

- [ ] CHK058 Is the no-duplicate-Phone-Call-activity guarantee stated explicitly in FR text (not only in SC-008)? [Consistency, Spec §FR-021, Spec §SC-008]
- [ ] CHK059 Is the no-duplicate-Task guarantee stated explicitly in FR text (not only in SC-008)? [Consistency, Spec §FR-021, Spec §SC-008]
- [ ] CHK060 Is the no-duplicate-queue-status-transition guarantee stated explicitly in FR text (not only in SC-008)? [Consistency, Spec §FR-021, Spec §SC-008]
- [ ] CHK061 Is the no-duplicate-attempt-count-increment guarantee stated explicitly in FR text (not only in SC-008)? [Consistency, Spec §FR-021, Spec §FR-025, Spec §SC-008]
- [ ] CHK062 Is the SC-008 100% measurement decomposable into the four per-record-type guarantees (so each can be independently verified)? [Measurability, Consistency, Spec §SC-008, Spec §FR-021]
- [ ] CHK063 Is the no-duplicate guarantee uniform across all event sources (provider duplicate callback, CLI re-invocation, in-run retry, orchestrator restart, SignalWire provider retry)? [Consistency, Spec §FR-021, Spec §SC-008]
- [ ] CHK064 Is the "no duplicate" requirement explicit for the callbacks audit log itself — duplicates ARE recorded (not deduped at the audit layer)? [Clarity, Spec §FR-007, Spec §FR-021, Spec §Story 4 #1]
- [ ] CHK065 Is the "no duplicate" requirement explicit for the shadow STT discrepancy record (one record per discrepancy, even if the discrepancy is re-evaluated)? [Completeness, Spec §FR-030, Gap]
- [ ] CHK066 Is the "no duplicate review Task on shadow-STT escalation" stated explicitly (exactly one Task per uncertain discrepancy)? [Completeness, Spec §FR-031, Spec §Story 6 #4]
- [ ] CHK067 Is the "no duplicate DNC field update" stated explicitly for repeated DNC callbacks / re-invocations? [Completeness, Ambiguity, Spec §FR-024, Spec §SC-006, Gap]
- [ ] CHK068 Is the no-duplicate guarantee preserved across Slice 3's Phone Call activity additions (real provider call ID, answered-at / completed-at timestamps) — i.e., the additive fields do not introduce a new duplicate-creation path? [Consistency, Spec §FR-020, Spec §Story 1 #6]

## Concurrent-Claim Semantics

- [ ] CHK069 Is the requirement explicit that concurrent CLI invocations REUSE Slice 2 queue-claim semantics (not a new mechanism)? [Consistency, Spec §FR-003, Spec §Clarifications]
- [ ] CHK070 Is the observation predicate for the second invocation precise (queue item observed as not-`ready`, e.g., claimed / `in_progress`)? [Clarity, Measurability, Spec §FR-003, Spec §Edge Cases]
- [ ] CHK071 Is the exit behavior for the second invocation precise (exit before dial with operator-visible blocked-by-claim message; no SignalWire call; no attempt; no Phone Call activity; no Task)? [Completeness, Spec §FR-003, Spec §Clarifications, Spec §Edge Cases]
- [ ] CHK072 Is the requirement explicit that the first invocation is unaffected by the second invocation's exit? [Completeness, Spec §FR-003, Spec §Edge Cases]
- [ ] CHK073 Is the requirement explicit that multi-worker coordination remains OUT of scope, with queue-claim observation being the only Slice 3 concurrency contract? [Clarity, Spec §FR-003, Spec §Edge Cases, Spec §Assumptions]
- [ ] CHK074 Is the boundary between "concurrent claim" (second invocation, blocked) and "resume after retry-budget exhaustion" (re-invocation of the same operator on a non-`ready` item) explicitly distinguishable so resume is not blocked? [Clarity, Ambiguity, Spec §FR-003, Spec §FR-022, Gap]
- [ ] CHK075 Is the requirement explicit that the queue-claim mechanism's dedup key is the Dataverse queue item identifier (not the session ID)? [Clarity, Spec §FR-003, Gap]

## Scenario Classes

- [ ] CHK076 Primary scenario: are idempotency requirements stated for the happy-path single dial + single write-back? [Coverage, Spec §FR-021, Spec §Story 1]
- [ ] CHK077 Alternate scenario: are idempotency requirements stated for each per-disposition write-back variant (callback Task, email Task, review Task, DNC update, blocked-status-only write)? [Coverage, Spec §FR-020, Spec §FR-021, Spec §SC-003 – SC-007]
- [ ] CHK078 Exception/Error scenario: are idempotency requirements stated for every failure path that could trigger replay (transient error, retry, callback duplicate, orchestrator restart, concurrent claim, late callback, callback auth failure)? [Coverage, Spec §FR-021, Spec §FR-022, Spec §FR-027, Spec §Story 4, Spec §Story 7]
- [ ] CHK079 Recovery scenario (with rollback for state mutation): is the no-rollback-needed property explicit (idempotency-key pre-query before create means no rollback of duplicate creates; instead, creates are prevented)? [Coverage, Clarity, Spec §FR-021, Spec §Story 7]
- [ ] CHK080 Non-functional scenario: are non-functional idempotency properties stated (audit retention ≥ 90 days enables delayed resume; no secrets in idempotency keys; shadow lane never independently writes CRM regardless of repetition)? [Coverage, Spec §FR-022, Spec §FR-030, Spec §FR-035, Spec §SC-013, Spec §SC-018]
- [ ] CHK081 Are inapplicable scenario classes explicitly named (e.g., raw-audio idempotency is N/A because raw-audio capture is out of scope for Slice 3)? [Coverage, Clarity, Spec §Assumptions, Spec §Clarifications]
- [ ] CHK082 Is the measurability of the recovery scenario explicit (SC-008 100% no-duplicate, SC-012 100% live-call-abandonment finalization, SC-009 / SC-010 100% block-before-dial)? [Measurability, Spec §SC-008, Spec §SC-009, Spec §SC-010, Spec §SC-012]

## Cross-Cutting Consistency

- [ ] CHK083 Are the four no-duplicate guarantees in SC-008 each backed by an FR (FR-021 covers all four; check that none is asserted only in SC-008)? [Consistency, Traceability, Spec §SC-008, Spec §FR-021]
- [ ] CHK084 Is the additive `shadow_stt_discrepancy` reason code explicit as the ONLY Slice 3 addition to the persona's human-review reason enumeration (no other reasons sneak in via idempotency paths)? [Consistency, Spec §FR-031, Spec §FR-014, Spec §Assumptions]
- [ ] CHK085 Is the requirement explicit that the Slice 3 Phone Call activity additions (real provider call ID, connected-call timestamps) do NOT change the idempotency key derivation? [Consistency, Spec §FR-020, Spec §FR-021, Gap]
- [ ] CHK086 Is the requirement explicit that the shadow STT lane and the live conversation path share a single session ID (so dedup keys collide intentionally on the same session)? [Consistency, Spec §FR-028, Spec §FR-030, Spec §Definitions]
- [ ] CHK087 Is the requirement explicit that conflicting-late callbacks (FR-027) reuse the SAME `(session_id, provider_event_id)` dedup key as the regular callbacks audit log (FR-007) rather than introducing a separate scheme? [Consistency, Spec §FR-007, Spec §FR-027, Spec §Edge Cases]
- [ ] CHK088 Is the relationship between the Slice 2 idempotency-key stamping and the Slice 3 callbacks audit log explicit (different keys for different purposes: idempotency key for CRM creates, provider event ID for callback dedup)? [Clarity, Spec §FR-007, Spec §FR-021, Gap]
- [ ] CHK089 Is the requirement explicit that operator identity (FR-016) is NOT part of any idempotency or dedup key (it is local-only and varies per invocation)? [Consistency, Spec §FR-016, Spec §Clarifications]
- [ ] CHK090 Is the requirement explicit that the `do_not_call` write-back (DNC fields + queue-status) is idempotent across repeated DNC callbacks or re-invocations? [Completeness, Spec §FR-024, Spec §SC-006, Gap]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

### Q6 — Resume idempotency on `answered`-no-terminal session (FR-026)

- [ ] CHK091 Is the idempotency contract explicit that a second resume invocation on a session ALREADY finalized as `failed`/`live_call_abandonment` by a prior resume is a no-op for state, attempt count, and all four CRM write-back operations (re-tests CHK016, CHK033)? [Completeness, Spec §FR-021, Spec §FR-026]
- [ ] CHK092 Is the dedup key for the resume-immediate-finalize path explicit (it MUST use the same session ID / idempotency key as the original session, NOT a new key derived from the resume invocation timestamp)? [Clarity, Consistency, Spec §FR-021, Spec §FR-022, Spec §FR-026, Gap]
- [ ] CHK093 Is the requirement explicit that the resume-immediate-finalize path does NOT re-increment the attempt count (closes CHK034 [Gap] under the new resume rule)? [Consistency, Spec §FR-025, Spec §FR-026, Spec §FR-022]
- [ ] CHK094 Is the idempotency contract explicit that a late `completed` callback arriving AFTER the resume-immediate-finalize does not retroactively create a connected-call Phone Call activity (re-tests CHK025 under the resume-immediate-finalize rule)? [Consistency, Spec §FR-026, Spec §FR-027]

### Q8 — DNC / blocked / dial-blocked as field-level queue-status variants (FR-020)

- [ ] CHK095 Is the requirement explicit that DNC field writes (FR-024), blocked-by-eligibility status field writes (FR-023), and dial-blocked status field writes (FR-012) INHERIT the queue-status-update operation's idempotency key derivation rather than introducing per-variant keys? [Consistency, Spec §FR-020, Spec §FR-021, Spec §FR-023, Spec §FR-024]
- [ ] CHK096 Is the requirement explicit that the FR-020 "operation count remains four" preserves the FR-021 per-operation no-duplicate guarantees — i.e., each field-level variant is governed by the queue-status update operation's single dedup contract, not by a new one? [Consistency, Spec §FR-020, Spec §FR-021]
- [ ] CHK097 Is the no-duplicate-queue-status-transition guarantee (re-tests CHK060) preserved across all three field-level variants on retry / resume / re-invocation paths? [Consistency, Spec §FR-020, Spec §FR-021, Spec §FR-023, Spec §FR-024]

### Q9 — Rejected-by-authentication audit log idempotency (FR-008)

- [ ] CHK098 Is the dedup model for the distinct rejected-by-authentication audit log explicit — is it keyed by `(received_at, source metadata)`, OR is duplicate-rejection acceptance (one row per rejection event, no dedup) the requirement (closes CHK022 [Gap])? [Clarity, Ambiguity, Spec §FR-008, Gap]
- [ ] CHK099 Is the boundary between the rejected-by-authentication audit log and the regular callbacks audit log explicit that rejected callbacks are NOT recorded in the regular callbacks audit log (re-tests CHK022)? [Consistency, Spec §FR-007, Spec §FR-008]
- [ ] CHK100 Is the dedup model explicit that the rejected-by-authentication audit log MUST NOT contain the verification secret or the callback body content (so dedup CANNOT be performed on body-derived hashes — only `(received_at, source metadata)` are available)? [Consistency, Spec §FR-008]
- [ ] CHK101 Is the rejected-by-authentication count surfaced in the run report (FR-036) defined as a per-session count, derived once-and-for-all from the audit log, so retried run-report rendering produces the same count (idempotent reporting)? [Consistency, Spec §FR-008, Spec §FR-036, Gap]

### Q12 — Operator identity preservation on resume (FR-016)

- [ ] CHK102 Is the requirement explicit that the original operator identity on the session record is preserved IDEMPOTENTLY across multiple resume invocations (a second, third, fourth resume by different operators MUST NOT overwrite the original)? [Completeness, Spec §FR-016, Gap]
- [ ] CHK103 Is the requirement explicit that the resuming operator identity recorded on the run report represents the CURRENT invocation only, not a cumulative chain of resumers (or, alternatively, that a cumulative chain is required and uniquely keyed)? [Ambiguity, Spec §FR-016, Spec §FR-036, Gap]
- [ ] CHK104 Is the requirement explicit that operator identity is NOT part of any idempotency or dedup key (re-tests CHK089 under the new resume-by-different-operator scenario)? [Consistency, Spec §FR-016]

### Q13 — Real-call flag absence on resume = idempotent rehearsal (FR-001, FR-022)

- [ ] CHK105 Is the requirement explicit that a resume invocation omitting the real-call / write-enabled flag is an idempotent no-op for all four write-back operations, the attempt count, and the session state (multiple successive flag-omitted resumes produce the same observable result)? [Completeness, Spec §FR-001, Spec §FR-022]
- [ ] CHK106 Is the requirement explicit that a flag-omitted resume MUST NOT consume any progress-ledger entry that a subsequent flag-supplied resume would need (i.e., rehearsal-mode resume is non-destructive against the resume state)? [Consistency, Spec §FR-022, Gap]
- [ ] CHK107 Is the requirement explicit that a flag-omitted resume MUST NOT emit any CRM correlation row, write-back row, or new audit-row side effect that a future resume would need to dedup against? [Consistency, Spec §FR-022, Gap]

### Q14 — DNC-first idempotency on resume (FR-024)

- [ ] CHK108 Is the requirement explicit that when the original DNC write SUCCEEDED but a later write FAILED, the resume invocation MUST NOT create a duplicate DNC write (re-tests CHK067 [Gap])? [Completeness, Spec §FR-024, Spec §FR-021, Spec §FR-022]
- [ ] CHK109 Is the requirement explicit that DNC write idempotency uses the same session-derived idempotency key model as Phone Call activities and Tasks (FR-021), not a separate DNC-specific key model? [Consistency, Spec §FR-021, Spec §FR-024]
- [ ] CHK110 Is the requirement explicit that the resume invocation MUST detect the prior successful DNC write via the existing write-back progress ledger (CHK056) before attempting the next write — i.e., the DNC-first ordering rule applies to the FIRST invocation; resume picks up at the next un-completed step? [Clarity, Spec §FR-022, Spec §FR-024, Gap]
- [ ] CHK111 Is the no-duplicate-DNC-write guarantee uniform across repeated DNC callbacks, retried DNC writes, AND resume re-invocations (single guarantee, three trigger paths)? [Consistency, Spec §FR-021, Spec §FR-024, Spec §SC-006]

### `shadow_lane_truncated` event idempotency (FR-029)

- [ ] CHK112 Is the dedup model for the `shadow_lane_truncated` audit-only event explicit (one event per session per truncated shadow run, or one event per late shadow output beyond the grace window — these are different semantics)? [Ambiguity, Spec §FR-029, Gap]
- [ ] CHK113 Is the requirement explicit that a `shadow_lane_truncated` event MUST NOT emit a new CRM write-back payload, MUST NOT mutate the finalized disposition, and MUST NOT change the attempt count (audit-only)? [Consistency, Spec §FR-029]
- [ ] CHK114 Is the boundary between an in-grace-window shadow discrepancy (may escalate per FR-031, creates a review Task per CHK024) and a post-grace-window `shadow_lane_truncated` event (audit-only, no Task) decidable from observed event timestamps? [Clarity, Spec §FR-029, Spec §FR-031]
- [ ] CHK115 Is the requirement explicit that a `shadow_lane_truncated` event MUST NOT trigger a duplicate review Task even if a shadow discrepancy on the same field was already escalated within the grace window? [Consistency, Spec §FR-029, Spec §FR-031]
- [ ] CHK116 Is the `shadow_lane_truncated` event constrained to NOT participate in any dedup key collision with the regular shadow STT discrepancy record (CHK065 from Round 1) — i.e., they are distinct artifact types? [Consistency, Spec §FR-029, Spec §FR-030, Gap]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Data-model §7 invariants — `(session_id, provider_event_id)` dedup-key schema-level consistency

- [ ] CHK117 Is the `(session_id, provider_event_id)` dedup-key consistency between data-model §1.2 `CallEvent` and §1.3 `CallbacksAuditLog` enforced at the schema level — i.e., does the SQLite mirror schema (data-model §3) prevent orphan rows in `CallbacksAuditLog` whose `(session_id, provider_event_id)` has no corresponding `CallEvent`? [Consistency, Gap, Data-Model §1.2, §1.3, §3, §7]
- [ ] CHK118 Is the `(session_id, provider_event_id)` dedup-key enforced to prevent key collisions across distinct sessions (i.e., is `session_id` always part of the dedup key, never just `provider_event_id` alone, so SignalWire's globally-unique-or-not event ID does not produce false duplicates across sessions)? [Consistency, Data-Model §1.2, §1.3, §7]
- [ ] CHK119 Does the data-model §3 SQLite extension for `CallEvent` (not explicitly shown in the SQL block — only `rejected_auth_callbacks`, `shadow_stt_discrepancies`, `shadow_lane_truncated_events`) define a UNIQUE constraint on `(session_id, provider_event_id)` for the `CallEvent` table OR rely on the orchestrator dedup logic (FR-007 + FR-021), and is the choice operator-defensible? [Gap, Ambiguity, Data-Model §1.2, §3]
- [ ] CHK120 Does the data-model §7 "No duplicate writes" invariant tie the `(session_id, provider_event_id)` dedup-key to the contracts/signalwire-transport.md `event_stream` dedup behavior (the transport marks duplicates `is_duplicate=True` on the second delivery) so the dedup-key contract is enforced at both the transport boundary AND the persistence layer? [Consistency, Traceability, Data-Model §7, Contract: signalwire-transport, Spec §FR-007, §FR-021]

### Idempotency-key stamping pre-query — extension to DNC-first ordering

- [ ] CHK121 Does the idempotency-key stamping pre-query (FR-021, reused from Slice 2 per research §14) extend to the new DNC-first ordering invariant (Round 2 Q14) such that a resume invocation re-running the DNC write FIRST finds the existing row via pre-query and skips? [Consistency, Spec §FR-021, §FR-024, Research §14, Contract: crm-writeback-dnc-first] (re-validates CHK108 from Round 2)
- [ ] CHK122 Does the data-model §2.4 `IdempotencyKey` ("Slice 3 makes no changes — DNC-first writes (Round 2 Q14) reuse the same key shape") explicitly confirm the DNC-first write uses the same session-derived idempotency key, OR does the DNC-first write need a distinct key model because it targets queue-status FIELDS rather than a separate record? [Ambiguity, Data-Model §2.4, Contract: crm-writeback-dnc-first] (re-validates CHK109 from Round 2)
- [ ] CHK123 Is the DNC-first resume idempotency posture (DNC write succeeds; resume runs again; pre-query finds existing write; skips) traceable through the data-model §6 resume-invocation state-transitions block AND the contracts/crm-writeback-dnc-first.md "Idempotency on resume" section? [Traceability, Consistency, Data-Model §6, Contract: crm-writeback-dnc-first]
- [ ] CHK124 Does the data-model / contract define the dedup-key persistence layer for the DNC field write (a Dataverse field update, not a record create) — i.e., does the pre-query look up an existing field value or rely on the `writeback_progress` ledger entry, and is the choice deterministic across resume invocations? [Gap, Ambiguity, Data-Model §2.4, Contract: crm-writeback-dnc-first, Spec §FR-021, §FR-024]

### rejected_auth_callbacks idempotency — SQLite mirror + JSONL file consistency

- [ ] CHK125 Does the rejected_auth_callbacks audit log have its own idempotency model — i.e., are duplicate-rejected callbacks (same forged signature delivered N times) recorded N times (one row per delivery) or deduplicated to one row? [Ambiguity, Gap, Data-Model §1.4, Contract: rejected-auth-audit-log]
- [ ] CHK126 Is the duplicate-rejected-callback recording behavior consistent across the SQLite `rejected_auth_callbacks` table (data-model §3) AND the `artifacts/<session_id>/rejected_auth_callbacks.jsonl` file (research §10) — i.e., is one log append-only with N rows and the other deduplicated, or do both behave the same way? [Consistency, Gap, Data-Model §1.4, §3, Research §10]
- [ ] CHK127 Is the `RejectedAuthCallbackLog.session_id`-nullable column's behavior defined for the idempotency model (does a null `session_id` mean "different rejected callbacks are never duplicates because we can't correlate them" or "we treat them all as one event")? [Ambiguity, Data-Model §1.4, Contract: rejected-auth-audit-log]
- [ ] CHK128 Does the run report's `rejected_auth_callbacks_count` field (FR-036, Round 2 Q9) report the row-count (potentially duplicates) or the distinct-event count (deduplicated), and is the choice consistent with the operator-visible meaning ("attempted forgeries detected")? [Clarity, Consistency, Spec §FR-036, Research §9, Data-Model §1.4]

### Resume operator-identity preservation — idempotency across multiple resume invocations

- [ ] CHK129 Does the resume operator-identity preservation (Round 2 Q12, data-model §2.1 `operator_identity_original` + `operator_identity_current`) produce idempotent results across multiple resume invocations — i.e., operator C resumes after operator B resumed after operator A started: what is the `operator_identity_original` value (always A, the very first invocation's operator, or B because B was the prior invocation)? [Ambiguity, Gap, Data-Model §2.1, Spec §FR-016] (re-validates CHK103 from Round 2)
- [ ] CHK130 Is the `operator_identity_original` invariant (set once on first invocation, never overwritten) traceable through the data-model §2.1 schema (the `operator_identity_original TEXT` column has no constraint preventing overwrite — does the plan rely on application-level logic, and is this idempotency-safe)? [Consistency, Gap, Data-Model §2.1, §3, Spec §FR-016]
- [ ] CHK131 Does the data-model define the "operator_identity_current" semantics across multiple resume invocations — is it always the MOST RECENT resuming operator (B then C), or does it accumulate as a chain (A → B → C) in a separate field? [Ambiguity, Data-Model §2.1, Spec §FR-016, Quickstart §5]
- [ ] CHK132 Is the run report's `operator_identity: {current, original}` shape (research §9, quickstart §4) sufficient for a 3-operator resume chain, or does the chain compress information that an auditor would need (the middle operator B who resumed once is no longer surfaced)? [Gap, Completeness, Research §9, Quickstart §4, §5, Spec §FR-016]

### `shadow_lane_truncated` cardinality — PRIMARY KEY session_id correctness

- [ ] CHK133 Does the data-model §1.8 `ShadowLaneTruncatedEvent` cardinality (PRIMARY KEY `session_id` in the SQLite mirror `shadow_lane_truncated_events` table per §3, enforcing at most one row per session) match the operationally-correct semantics (one truncation event per truncated session, NOT one event per late shadow output beyond grace) — is the choice of cardinality intentional? [Consistency, Data-Model §1.8, §3] (re-validates CHK112 from Round 2)
- [ ] CHK134 Is the PRIMARY KEY `session_id` cardinality consistent with the data-model §1.8 invariant "this event MUST NOT mutate the finalized disposition" (a single per-session event is sufficient for audit; multiple late outputs from the same shadow lane are collapsed into one row's `late_output_summary` JSON)? [Consistency, Data-Model §1.8, Spec §FR-029]
- [ ] CHK135 Is the `late_output_summary` JSON field schema (data-model §1.8: "Per-high-value-field summary of what the shadow lane would have produced") defined enough that a per-session row cannot accidentally accumulate multiple late outputs in a way that violates the implicit "single truncation event" cardinality? [Gap, Ambiguity, Data-Model §1.8]
- [ ] CHK136 Is the PRIMARY KEY `session_id` cardinality consistent with the artifact file convention (`artifacts/<session_id>/shadow_lane_truncated.json` is a single file per session, NOT a JSONL append-log) — does the artifact format match the table cardinality? [Consistency, Data-Model §1.8, Research §10]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate the spec text is open to multiple reasonable interpretations and should be tightened.
- Items marked [Conflict] indicate two sections of the spec disagree.
- CHK117 – CHK136 are Round 3 post-plan validation (2026-05-25) covering: `(session_id, provider_event_id)` dedup-key schema-level consistency between `CallEvent` and `CallbacksAuditLog`, idempotency-key stamping pre-query extension to DNC-first ordering, rejected_auth_callbacks idempotency consistency between SQLite mirror + JSONL file, resume operator-identity preservation idempotency across multiple resume invocations, `shadow_lane_truncated` PRIMARY KEY `session_id` cardinality correctness.
- ≥80% of items reference a spec section or a quality marker for traceability.
