# Error-Handling Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the error-handling, failure, exception, and recovery dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Failure-Mode Enumeration

- [ ] CHK001 Are all distinct pre-dial failure modes enumerated (missing SignalWire credentials, unauthorized source caller-ID, missing/blank/malformed destination phone, missing/unreachable callback URLs, missing campaign-to-persona/runtime mapping, unverified Dataverse mapping, missing/invalid callback owner mapping, eligibility block)? [Completeness, Spec §FR-009, Spec §Story 3]
- [ ] CHK002 Are all distinct dial-time failure modes enumerated (provider 4xx / invalid / blocked / unauthorized number on the dial request)? [Completeness, Spec §FR-012, Spec §Edge Cases]
- [ ] CHK003 Are all distinct mid-call failure modes enumerated (real-time AI model provider error, Pipecat runtime crash, silence-after-connection / no-extraction-event timeout)? [Completeness, Spec §FR-013, Spec §Clarifications, Spec §Edge Cases]
- [ ] CHK004 Are all distinct provider-callback failure modes enumerated (duplicate status callback, duplicate media callback, out-of-order callbacks, late-after-finalization callback, persistently failing callback delivery)? [Completeness, Spec §FR-007, Spec §FR-027, Spec §Edge Cases]
- [ ] CHK005 Are all distinct CRM write-back failure modes enumerated (transient Dataverse error mid-write-back, partial write-back where Phone Call succeeded but Task creation failed, retry-budget exhaustion, metadata-drift block)? [Completeness, Spec §FR-022, Spec §Story 7, Spec §Edge Cases]
- [ ] CHK006 Are all distinct orchestrator/runtime lifecycle failure modes enumerated (orchestrator restart mid-call, orchestrator restart between successful dial and write-back, live-call abandonment timeout)? [Completeness, Spec §FR-026, Spec §Story 4 #8, Spec §Story 7 #4, Spec §Edge Cases]
- [ ] CHK007 Are all distinct shadow STT failure modes enumerated (shadow lane crash, shadow lane timeout, shadow disabled at run time)? [Completeness, Spec §FR-029, Spec §FR-032, Spec §Story 6 #6, Spec §Edge Cases]
- [ ] CHK008 Are mid-run SignalWire credentials / source-number suspension failures explicitly distinguished from pre-dial readiness failures? [Completeness, Clarity, Spec §Edge Cases]
- [ ] CHK009 Is CRM-queue-item human modification between claim and write-back enumerated as a recoverable conflict failure mode? [Completeness, Spec §Edge Cases]
- [ ] CHK010 Is Dataverse metadata drift between rehearsal and real-call run enumerated as a distinct pre-dial failure mode (versus generic mapping-unverified)? [Completeness, Clarity, Spec §Edge Cases, Spec §Story 4 #6]
- [ ] CHK011 Are concurrent CLI invocations on the same queue item enumerated as a distinct blocked-by-claim failure mode rather than an unknown error? [Completeness, Spec §FR-003, Spec §Clarifications, Spec §Edge Cases]
- [ ] CHK012 Are callback authentication failures (signature verification failing) enumerated as a distinct rejected-callback failure mode? [Completeness, Spec §FR-008, Gap]
- [ ] CHK013 Does the spec name a residual / catch-all failure bucket for unanticipated runtime exceptions outside the enumerated triggers, or does it explicitly assert the enumeration is exhaustive? [Completeness, Ambiguity, Spec §FR-013, Gap]

## Disposition + Reason Mapping Per Failure

- [ ] CHK014 Is the final disposition specified for every pre-dial readiness failure (e.g., `blocked` with `blocked_reason`, or no disposition write at all for non-eligibility failures)? [Consistency, Spec §FR-011, Spec §Story 3 #5, Spec §FR-019]
- [ ] CHK015 Is the final disposition specified for a provider-rejected dial request (FR-012) — is it `failed`, `blocked`, or another value, and is the per-disposition `new_status` unambiguous? [Clarity, Ambiguity, Spec §FR-012, Spec §FR-020, Gap]
- [ ] CHK016 Is the disposition specified for live model / Pipecat runtime errors BEFORE the connected state (`failed` with runtime-failure reason)? [Clarity, Spec §FR-013, Spec §Edge Cases]
- [ ] CHK017 Is the disposition specified for live model / Pipecat runtime errors AFTER the connected state (`needs_human_review` with `script_truncated`)? [Clarity, Spec §FR-013, Spec §Story 5 #5, Spec §Edge Cases]
- [ ] CHK018 Is the disposition specified for silence-after-connection / no-extraction-event timeout (always `needs_human_review` with `script_truncated`, because timer only starts after connection)? [Clarity, Spec §FR-013, Spec §Edge Cases]
- [ ] CHK019 Is the disposition + reason specified for live-call abandonment (`failed` with `live_call_abandonment` reason)? [Clarity, Spec §FR-026, Spec §Story 4 #8, Spec §Definitions]
- [ ] CHK020 Is the disposition specified for shadow STT uncertain discrepancy escalation (`needs_human_review` with `shadow_stt_discrepancy` reason)? [Clarity, Spec §FR-031, Spec §Story 6 #4]
- [ ] CHK021 Is the disposition specified for mid-call PHI / out-of-allowed-claim attempts (`needs_human_review` with `phi_collection_risk`, `non_clinical_topic_escalation`, or `outside_allowed_claims`)? [Clarity, Spec §FR-015, Spec §Story 5 #2, Spec §Edge Cases]
- [ ] CHK022 Is the disposition specified for mid-call opt-out / DNC (`do_not_call` with associated DNC / queue-status write and no Task)? [Clarity, Spec §FR-024, Spec §Story 5 #3, Spec §Edge Cases]
- [ ] CHK023 Is the disposition specified for caller hangup mid-conversation with sufficient signal (deterministic disposition per FR-036) vs. insufficient signal (`needs_human_review` with `script_truncated`)? [Clarity, Spec §Story 4 #5]
- [ ] CHK024 Is the disposition specified for SignalWire `busy` / `canceled` mapping (mapped to `no_answer` per transport adapter) consistent with the normalized event set? [Consistency, Spec §FR-005, Spec §Story 4 #3]
- [ ] CHK025 Is the disposition specified for transient Dataverse error after exhausted in-run retry vs. successful retry (does the run-level disposition stay the assembled persona outcome, or is `failed` emitted)? [Ambiguity, Spec §FR-022, Gap]
- [ ] CHK026 Is the disposition specified for CRM-queue-item human-conflict detection mid-write-back (stop-before-final-status, conflict reported) — is the run finalized as `needs_human_review`, `failed`, or kept open? [Ambiguity, Spec §Edge Cases, Gap]
- [ ] CHK027 Is the disposition specified for Dataverse metadata drift detected at the live-verification gate (does it count as a readiness failure with no disposition, or `blocked`)? [Ambiguity, Spec §Edge Cases, Spec §FR-009]
- [ ] CHK028 Are all `needs_human_review` reason codes used by Slice 3 enumerated and traceable back to the Slice 1 enumeration plus the additive `shadow_stt_discrepancy` entry (no new reasons sneaking in via failure paths)? [Consistency, Spec §FR-014, Spec §FR-015, Spec §FR-031]
- [ ] CHK029 Is the reason code for callback authentication rejection specified (does it produce a disposition, an audit-only event, or a silent drop)? [Ambiguity, Spec §FR-008, Gap]
- [ ] CHK030 Is the reason for a missing-disclosure-acknowledgment scenario specified as NOT a failure (implicit acknowledgment, no escalation, no new reason)? [Consistency, Spec §FR-015, Spec §Clarifications]

## Recovery & Resume Contracts

- [ ] CHK031 Is the recovery path defined for transient Dataverse error within the in-run retry budget (initial + 3 retries, 1s/2s/4s backoff, optional Retry-After ≤ 30s)? [Completeness, Measurability, Spec §FR-022, Spec §Story 4 #6, Spec §Story 7 #1]
- [ ] CHK032 Is the recovery path defined for retry-budget exhaustion (operator re-invokes CLI for the same session; only missing writes are resumed)? [Completeness, Spec §FR-022, Spec §Story 4 #7, Spec §Story 7 #2]
- [ ] CHK033 Is the recovery path defined for orchestrator restart between successful dial and write-back (resume preserves real provider call ID; only missing writes are retried)? [Completeness, Spec §Story 7 #4, Spec §Edge Cases]
- [ ] CHK034 Is the recovery path defined for orchestrator restart mid-call (live-call abandonment timeout finalizes; resume applies for partial write-back)? [Completeness, Spec §FR-026, Spec §Story 4 #8, Spec §Edge Cases]
- [ ] CHK035 Is the recovery path defined for persistent SignalWire callback delivery failure (live-call abandonment timeout finalizes)? [Completeness, Spec §FR-026, Spec §Edge Cases]
- [ ] CHK036 Is the recovery path defined for partial CRM write-back when Phone Call succeeded but Task failed (re-invocation creates only the missing Task, no duplicate)? [Completeness, Spec §Story 7 #5, Spec §Edge Cases]
- [ ] CHK037 Is the recovery path defined for a session already finalized and fully written back (re-invocation is a no-op for all four record types)? [Completeness, Spec §Story 4 #9]
- [ ] CHK038 Is the recovery path defined for shadow STT lane crash/timeout (live call unaffected, run report records shadow-lane failure, no discrepancy event)? [Completeness, Spec §FR-029, Spec §Story 6 #6, Spec §Edge Cases]
- [ ] CHK039 Is the recovery path defined for mid-run SignalWire credentials / source-number suspension (in-flight call allowed to complete; suspension applies to next pre-dial check)? [Completeness, Spec §Edge Cases]
- [ ] CHK040 Is the recovery path defined for resume when transcript retention is summary-only or pointer-only (resume runs from local audit artifacts; missing transcript file is not an error)? [Completeness, Spec §Edge Cases]
- [ ] CHK041 Is the recovery path defined for Dataverse metadata drift caught at the live verification gate (exit before dial; no attempt consumed; no resume needed because no mutation occurred)? [Completeness, Spec §Edge Cases]
- [ ] CHK042 Is the recovery path defined for CRM-queue-item human-conflict (preserve high-confidence values, stop write-back before final status, report for human review)? [Completeness, Spec §Edge Cases]
- [ ] CHK043 Is the resume contract explicitly defined to be triggered by the operator (re-invocation) rather than an automatic watcher process, or is the choice deferred to plan? [Clarity, Spec §Deferred to Implementation Plan]
- [ ] CHK044 Is the configurability of the live-call abandonment timeout stated as a requirement (default value deferred to deployment), with no ambiguity about whether the configurability itself is in scope? [Clarity, Measurability, Spec §FR-026, Spec §Assumptions]
- [ ] CHK045 Is the configurability of the silence-after-connection / no-extraction-event timeout stated as a requirement (default value deferred to deployment)? [Clarity, Measurability, Spec §FR-013, Spec §Deferred to Implementation Plan]
- [ ] CHK046 Are the retry budget bounds (initial + 3 retries, 1s/2s/4s backoff, Retry-After cap ≤ 30s) explicitly stated as MUST requirements rather than guidelines? [Measurability, Spec §FR-022]
- [ ] CHK047 Is the local audit retention floor for recovery-relevant artifacts (correlation rows, progress rows, ≥ 90 days) stated as a MUST requirement so recovery from a delayed re-invocation remains possible? [Measurability, Spec §FR-022, Spec §Assumptions]

## "MUST NOT" Uniformity Across Failure Classes

- [ ] CHK048 Is the "no attempt consumed" guarantee stated uniformly across every blocked / failed pre-dial path (eligibility block, run-mode flag absence, telephony readiness failure, real-dial phone-number validation failure, Dataverse-unreachable-at-start, provider-rejected dial, malformed dial-plan / persona-runtime configuration)? [Consistency, Spec §FR-025, Spec §Definitions]
- [ ] CHK049 Is the "no Phone Call activity created" guarantee stated uniformly across every non-connected and pre-dial failure path? [Consistency, Spec §FR-010, Spec §FR-011, Spec §FR-012, Spec §FR-026, Spec §Story 1 #5, Spec §Story 3, Spec §Story 4]
- [ ] CHK050 Is the "no duplicate Task" guarantee stated uniformly across every recovery / retry / re-invocation path? [Consistency, Spec §FR-021, Spec §SC-008, Spec §Story 7]
- [ ] CHK051 Is the "no duplicate queue-status transition" guarantee stated uniformly across every recovery / retry / re-invocation path? [Consistency, Spec §FR-021, Spec §SC-008]
- [ ] CHK052 Is the "no duplicate attempt-count increment" guarantee stated uniformly across every recovery / retry / duplicate-callback path? [Consistency, Spec §FR-021, Spec §FR-025, Spec §SC-008]
- [ ] CHK053 Is the "no false connected-call Phone Call activity" guarantee stated uniformly across `no_answer`, `voicemail`, `failed`, `busy`/`canceled`, live-call abandonment, and pre-connected runtime failure? [Consistency, Spec §FR-026, Spec §Story 1 #5, Spec §Story 4 #3, Spec §Story 4 #4, Spec §Story 5 #5]
- [ ] CHK054 Is the "no callback or review Task on DNC outcomes" guarantee stated uniformly across `do_not_call` from mid-call opt-out, persona-detected DNC, and any other DNC path? [Consistency, Spec §FR-024, Spec §SC-006, Spec §Edge Cases]
- [ ] CHK055 Is the "queue item MUST NOT remain in `in_progress` indefinitely" guarantee stated for every mid-call failure path (live-call abandonment, runtime crash, persistent callback delivery failure)? [Consistency, Measurability, Spec §FR-026, Spec §Edge Cases, Spec §SC-012]
- [ ] CHK056 Is the "Dataverse queue MUST NOT advance beyond the approved blocked-status write" guarantee stated for every readiness failure consistently? [Consistency, Spec §FR-011, Spec §Story 3]
- [ ] CHK057 Is the "no shadow-lane independent CRM write" guarantee stated uniformly across every shadow STT failure outcome (agreeing, discrepant, uncertain, lane-crashed, disabled)? [Consistency, Spec §FR-030, Spec §SC-013, Spec §Story 6 #7]
- [ ] CHK058 Is the "secrets MUST NOT appear in logs / artifacts / run report" guarantee stated uniformly across every failure-path error message and run-report field? [Consistency, Spec §FR-008, Spec §FR-035, Spec §SC-018]
- [ ] CHK059 Is the "finalized disposition MUST NOT change" guarantee stated uniformly across every late-arriving event class (late status callback, late media callback, duplicate callback after finalization)? [Consistency, Spec §FR-027, Spec §Edge Cases]
- [ ] CHK060 Is the "live model MUST NOT override deterministic disposition" guarantee stated uniformly across every failure-path that might tempt model override (ambiguous extraction, runtime degradation, shadow STT discrepancy)? [Consistency, Spec §FR-014, Spec §SC-014]
- [ ] CHK061 Is the "operator identity MUST NOT propagate into Dataverse" guarantee stated uniformly across error-path artifacts (run report, callbacks audit log, conflicting-events audit log)? [Consistency, Spec §FR-016, Spec §FR-036, Spec §Clarifications]

## Boundary Failures: Mid-Call vs. Pre-Dial

- [ ] CHK062 Is the boundary between pre-dial readiness failure and dial-time provider rejection unambiguous (FR-009 readiness vs. FR-012 4xx)? [Clarity, Spec §FR-009, Spec §FR-012]
- [ ] CHK063 Is the boundary between dial-time provider rejection (no real provider call ID, no attempt consumed) and dial-time success followed by immediate `failed` callback (real provider call ID assigned, attempt consumed) unambiguous? [Clarity, Spec §FR-006, Spec §FR-025, Gap]
- [ ] CHK064 Is the boundary between pre-connected runtime failure (`failed` + runtime-failure reason, no false Phone Call activity) and post-connected runtime failure (`needs_human_review` + `script_truncated`) unambiguous? [Clarity, Spec §FR-013, Spec §Edge Cases]
- [ ] CHK065 Is "connected normalized state" defined consistently across the abandonment, runtime-failure, and disposition-mapping branches so the pre/post boundary is decidable from observed events? [Clarity, Ambiguity, Spec §FR-013, Spec §FR-026, Gap]
- [ ] CHK066 Is the silence-after-connection timer's start condition unambiguous (starts only after connection; not applicable pre-connection per FR-013 Edge Cases)? [Clarity, Spec §FR-013, Spec §Edge Cases]
- [ ] CHK067 Is the boundary between concurrent-claim blocking (second invocation, no failure) and live-call abandonment (first invocation timed out, then re-invoked) defined so the re-invocation is not misread as a concurrent claim? [Clarity, Spec §FR-003, Spec §FR-026, Gap]
- [ ] CHK068 Is the boundary between transient Dataverse error (retried in-run) and metadata-drift block (exits before further writes) defined? [Clarity, Spec §FR-022, Spec §Edge Cases]
- [ ] CHK069 Is the boundary between callback-authentication-rejection (callback dropped, not delivered to orchestrator) and out-of-order-but-authentic callback (delivered, normalized) defined? [Clarity, Spec §FR-007, Spec §FR-008, Gap]
- [ ] CHK070 Is the boundary between shadow STT discrepancy (recorded, may escalate) and shadow STT lane failure (recorded as lane failure, no discrepancy emitted) defined? [Clarity, Spec §FR-029, Spec §FR-030, Spec §Story 6 #6]
- [ ] CHK071 Is the boundary between PHI / out-of-allowed-claim attempt by the LIVE MODEL (persona escalates) and the same attempt by the CONTACT (persona escalates) consistent in disposition and reason? [Consistency, Spec §FR-015, Spec §Edge Cases]
- [ ] CHK072 Is the boundary between rehearsal-mode telephony readiness failure (no write at all) and real-call-mode readiness failure (approved blocked-status write only) explicitly distinguished? [Clarity, Spec §FR-002, Spec §FR-011]

## Scenario Classes

- [ ] CHK073 Primary scenario: are requirements present for a happy-path real call that ends in any of the connected dispositions with full successful write-back? [Coverage, Spec §Story 1, Spec §SC-001]
- [ ] CHK074 Alternate scenario: are requirements present for connected calls reaching each of the alternate dispositions (`interested_email_captured`, `not_interested`, `call_back_later`, `wrong_number`, `do_not_call`, `needs_human_review`) with their per-disposition write-back behavior? [Coverage, Spec §FR-017, Spec §Story 1, Spec §Story 5]
- [ ] CHK075 Exception/Error scenario: are requirements present for every failure mode enumerated in CHK001–CHK013 with a stated disposition + reason + write-back behavior? [Coverage, Spec §Story 3, Spec §Story 4, Spec §Story 5, Spec §Story 7]
- [ ] CHK076 Recovery scenario (with rollback for state mutation): is the resume contract specified for every state-mutating step (Phone Call activity, queue-status update, Task, attempt-count increment) with rollback / no-duplicate guarantees? [Coverage, Spec §FR-021, Spec §FR-022, Spec §SC-008, Spec §Story 7]
- [ ] CHK077 Non-functional scenario: are non-functional failure properties specified (no secrets in artifacts, audit retention ≥ 90 days, no shadow-lane slowdown of live call, idempotency across recovery)? [Coverage, Spec §FR-029, Spec §FR-035, Spec §SC-013, Spec §SC-018]
- [ ] CHK078 Are scenario classes that are explicitly inapplicable named as such (e.g., raw-audio recovery is N/A because raw-audio capture is out of scope for Slice 3)? [Coverage, Clarity, Spec §Assumptions, Spec §Clarifications]
- [ ] CHK079 Is the "no manual intervention during the run" success criterion measurable for the primary recovery scenario (in-run retry succeeds without operator action)? [Measurability, Spec §SC-001, Spec §FR-022]
- [ ] CHK080 Is the "100% of duplicates and recovery attempts leave Dynamics with no duplicate" success criterion (SC-008) decomposed into measurable per-record-type guarantees in the FRs? [Measurability, Consistency, Spec §SC-008, Spec §FR-021]

## Run-Report and Operator-Visibility of Errors

- [ ] CHK081 Are run-report contents enumerated for every failure mode (which check failed, which retry exhausted, which callback rejected, which discrepancy escalated)? [Completeness, Spec §FR-036, Spec §SC-017]
- [ ] CHK082 Is the requirement explicit that every failure produces an operator-visible message naming the failing check / reason (not a silent failure)? [Clarity, Measurability, Spec §FR-011, Spec §Story 3]
- [ ] CHK083 Is the callbacks audit log requirement explicit that duplicates AND failed/rejected callbacks are recorded (not only successful ones)? [Completeness, Spec §FR-007, Spec §FR-021, Spec §Key Entities]
- [ ] CHK084 Is the conflicting-events audit log requirement explicit for late-after-finalization callbacks (recorded but no state change)? [Completeness, Spec §FR-027, Spec §Edge Cases, Spec §Key Entities]
- [ ] CHK085 Is the run report required to record shadow-lane failure separately from shadow-lane disagreement? [Clarity, Spec §FR-029, Spec §Story 6 #6, Spec §FR-036]
- [ ] CHK086 Is the run report required to record the recovery path taken (in-run retry succeeded / resume on re-invocation / live-call abandonment timeout)? [Completeness, Spec §Story 7, Spec §FR-036]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

### Q6 — Resume on `answered`-but-no-terminal (FR-026)

- [ ] CHK087 Does the spec state that a resume invocation on a session that received SignalWire `answered` but no normalized terminal event MUST finalize immediately as `failed` with reason `live_call_abandonment`, with no waiting period for further callbacks? [Clarity, Spec §FR-026]
- [ ] CHK088 Is the "MUST NOT wait for further SignalWire callbacks for the in-flight call" invariant on resume stated explicitly and unambiguously (re-tests CHK034)? [Clarity, Consistency, Spec §FR-026]
- [ ] CHK089 Is the "MUST NOT attempt to reconnect to the provider's media stream" invariant on resume stated explicitly (closes the media-reconnect ambiguity surfaced in Round 1)? [Clarity, Spec §FR-026]
- [ ] CHK090 Does the spec define how the immediate-finalize-on-resume rule interacts with the configurable live-call abandonment timeout when the timeout has ALREADY elapsed before the operator re-invokes (i.e., does the resume bypass the timeout entirely, or is timeout-elapsed a precondition for the immediate finalize)? [Ambiguity, Spec §FR-026, Gap]
- [ ] CHK091 Is the resume-on-`answered`-no-terminal rule consistent with FR-027 (conflicting-late callback behavior) — i.e., a `completed` callback arriving AFTER the resume has finalized as `live_call_abandonment` is handled as a conflicting-late event with no disposition mutation? [Consistency, Spec §FR-026, Spec §FR-027]
- [ ] CHK092 Is the disposition+reason produced by the resume-immediate-finalize path explicitly the same `(failed, live_call_abandonment)` pair used by the timeout-elapses path (no second variant)? [Consistency, Spec §FR-026, Spec §Definitions]

### Q7 — Post-finalization grace window for shadow STT (FR-029)

- [ ] CHK093 Does the spec state the "orchestrator MUST NOT delay session finalization to wait for the shadow lane" invariant explicitly and separately from the grace-window allowance for CRM write-back? [Clarity, Spec §FR-029]
- [ ] CHK094 Does the spec define the failure mode when the shadow lane crashes DURING the grace window (does write-back proceed at crash-detect, at grace-window expiry, or does the crash itself terminate the window early)? [Ambiguity, Spec §FR-029, Gap]
- [ ] CHK095 Does the spec define the behavior when the grace window is configured to 0 (immediate write-back, late shadow output always becomes `shadow_lane_truncated`)? [Completeness, Ambiguity, Spec §FR-029, Gap]
- [ ] CHK096 Does the spec define an upper bound or fail-closed behavior for an unbounded / pathologically-large grace window (e.g., is "unbounded" allowed, or is there an implicit cap)? [Completeness, Ambiguity, Spec §FR-029, Gap]
- [ ] CHK097 Does the spec define behavior when the shadow lane emits a discrepancy AFTER CRM write-back is already complete but BEFORE the grace window would have elapsed (e.g., write-back finished early on a fast Dataverse round-trip)? [Ambiguity, Spec §FR-029, Spec §FR-031, Gap]
- [ ] CHK098 Is the `shadow_lane_truncated` event explicitly defined as audit-only — no disposition mutation, no new CRM write-back payload, no new attempt-count change? [Clarity, Spec §FR-029]
- [ ] CHK099 Is the boundary between an in-window shadow-STT discrepancy (may escalate per FR-031) and a `shadow_lane_truncated` post-finalization event (audit-only) decidable from observed timestamps? [Clarity, Spec §FR-029, Spec §FR-031]
- [ ] CHK100 Is the run-report contract explicit that a `shadow_lane_truncated` occurrence appears in the run report distinctly from a normal shadow-lane failure (CHK085) and a normal shadow-lane disagreement? [Completeness, Spec §FR-029, Spec §FR-036]

### Q11 — PHI volunteered mid-call (FR-015, FR-033)

- [ ] CHK101 Does the spec define `phi_collection_risk` as a `needs_human_review` reason that interacts cleanly with the deterministic disposition precedence (i.e., does PHI-volunteered escalation override an otherwise-`interested_callback_requested` outcome, and on what precedence rank)? [Clarity, Ambiguity, Spec §FR-015, Spec §FR-014, Gap]
- [ ] CHK102 Is the requirement explicit that PHI tag-and-redact MUST occur BEFORE any of the four covered artifacts (full transcript, summary, shadow transcript, shadow discrepancy records) is written to disk (no race where an unredacted artifact briefly exists on disk)? [Clarity, Measurability, Spec §FR-015, Spec §FR-033]
- [ ] CHK103 Does the spec define the persona's mid-call decision (continue vs. end the call) on PHI-volunteered events with enough precision that the disposition path is decidable (versus left to runtime discretion)? [Ambiguity, Spec §FR-015, Gap]
- [ ] CHK104 Is the PHI-volunteered escalation observably distinct in audit artifacts and the run report from a non-PHI `needs_human_review` escalation (so reviewers can find PHI-bearing sessions without reading every transcript)? [Clarity, Measurability, Spec §FR-015]
- [ ] CHK105 Is the boundary between PHI-volunteered-by-CONTACT (FR-015 escalation + redaction) and PHI-attempt-by-LIVE-MODEL (FR-015 escalation only) re-validated to confirm the redact-before-write rule applies to BOTH paths or only the contact path (re-tests CHK071)? [Consistency, Ambiguity, Spec §FR-015, Gap]

### Q13 — Real-call flag required on every mutation incl. resume (FR-001, FR-022)

- [ ] CHK106 Does the spec state that the real-call / write-enabled flag MUST be supplied on EVERY Dataverse-mutating invocation, with resume invocations explicitly included (no "sticky" or session-inherited promotion)? [Clarity, Spec §FR-001, Spec §FR-022, Spec §FR-016]
- [ ] CHK107 Is the no-op behavior of a resume invocation that OMITS the flag specified completely (no state mutation, no Dataverse write, no attempt-count change, no CRM correlation row creation)? [Completeness, Spec §FR-022]
- [ ] CHK108 Is the run-report content for a resume-omitted-flag run specified (e.g., does the run report identify what WOULD have been written so the operator can see whether to re-run with the flag)? [Completeness, Clarity, Spec §FR-022, Spec §FR-036, Gap]
- [ ] CHK109 Is the operator-visible message for a resume-omitted-flag run specified to make the mode shift unambiguous (the operator INTENDED real-call mode but forgot the flag — they MUST be able to detect this without inspecting Dataverse)? [Clarity, Measurability, Spec §FR-001, Spec §FR-022, Gap]
- [ ] CHK110 Is the boundary between "resume in rehearsal mode" (FR-022 omitted-flag path) and "first-invocation rehearsal mode" (FR-002 default) defined so the run report distinguishes the two? [Clarity, Spec §FR-002, Spec §FR-022, Gap]

### Q14 — DNC field write FIRST in write-back sequence (FR-024)

- [ ] CHK111 Does the spec state that on a `do_not_call` outcome the DNC / opt-out field write MUST be attempted FIRST in the write-back sequence — before queue-status update, Phone Call activity, and any Task? [Clarity, Spec §FR-024]
- [ ] CHK112 Does the spec define behavior when the DNC write SUCCEEDS but the queue-status update FAILS within the retry budget (contact protected; remaining writes resumed on re-invocation)? [Completeness, Spec §FR-024, Spec §FR-022]
- [ ] CHK113 Does the spec define behavior when the DNC write SUCCEEDS but the Phone Call activity creation FAILS within the retry budget? [Completeness, Spec §FR-024, Spec §FR-022, Gap]
- [ ] CHK114 Does the spec define behavior when the DNC write itself FAILS within the retry budget (does the rest of the write-back sequence proceed, or does the entire write-back halt on DNC failure)? [Ambiguity, Spec §FR-024, Spec §FR-022, Gap]
- [ ] CHK115 Is the idempotency contract for DNC writes on resume explicit (DNC write succeeded originally; resume re-invocation MUST NOT create a duplicate DNC write — re-tests CHK090 from idempotency.md from Round 1 perspective)? [Consistency, Spec §FR-024, Spec §FR-021, Spec §FR-022]
- [ ] CHK116 Is the FR-020 "operation count remains four" assertion consistent with the DNC-first ordering — i.e., DNC ordering is an intra-operation sequencing rule, not a fifth operation? [Consistency, Spec §FR-020, Spec §FR-024]
- [ ] CHK117 Does the spec define the disposition + write-back interaction for a DNC outcome that ALSO triggered a PHI-volunteered escalation (FR-015 vs. FR-024 priority — does `do_not_call` override `needs_human_review` per the deterministic disposition precedence)? [Consistency, Ambiguity, Spec §FR-014, Spec §FR-015, Spec §FR-024, Gap]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Exit codes 0-7 — mapping to data-model state transitions + quickstart expected-exit-codes tables

- [ ] CHK118 Is each contracts/cli-slice3.md exit code (0 success, 1 unexpected error, 2 bad CLI usage, 3 concurrent-claim block, 4 telephony readiness failure, 5 provider-rejected dial, 6 live-call abandonment, 7 Dataverse-unreachable-at-start) mapped to a specific named failure mode in the data-model §6 end-to-end state-transitions diagram (rehearsal-mode block, real-call mode block, resume block)? [Completeness, Traceability, Contract: cli-slice3, Data-Model §6]
- [ ] CHK119 Does the quickstart §2 expected-exit-codes table (rehearsal mode: 0, 3, 4, 7) have one row per applicable exit code AND is each row's "Meaning" wording consistent with the contracts/cli-slice3.md exit-codes table? [Consistency, Quickstart §2, Contract: cli-slice3]
- [ ] CHK120 Does the quickstart §3 expected-exit-codes table (real-call mode: same as §2 plus 5 and 6) have one row per applicable exit code AND name the additional codes (5 provider-rejected, 6 live-call abandonment) consistently with the contracts/cli-slice3.md exit-codes table? [Consistency, Quickstart §3, Contract: cli-slice3]
- [ ] CHK121 Is exit code 1 ("Unexpected error / uncaught exception; check stderr") defined as a fallback for failure modes that escape the explicit 2-7 mapping, and does the plan / data-model enumerate any specific failure modes that MUST map to code 1 rather than a more-specific code (e.g., SQLite corruption, redaction-library exception)? [Gap, Ambiguity, Contract: cli-slice3, Plan §Project Structure]
- [ ] CHK122 Is exit code 2 ("Bad CLI usage / missing required arg / conflicting flags") specified completely enough that an operator can determine, from stdout/stderr alone, which argument was missing or which flags conflicted (Typer-default behavior may suffice — is this stated)? [Completeness, Clarity, Contract: cli-slice3]

### contracts/signalwire-transport.md exception hierarchy vs. FR-009/010/011/012 failure modes

- [ ] CHK123 Does the contracts/signalwire-transport.md exception hierarchy (`TelephonyReadinessError`, `ProviderRejectedDialError`, `RealDialPhoneValidationError`) cover every FR-009 readiness-failure category (the nine data-model §1.9 enum values) — i.e., does each readiness category raise the same `TelephonyReadinessError` with a discriminator, or does the plan need additional exception types? [Completeness, Gap, Spec §FR-009, Contract: signalwire-transport, Data-Model §1.9]
- [ ] CHK124 Does the `RealDialPhoneValidationError` exception map cleanly to FR-010 (real-dial phone-number validation) and to exit code 4 (per the readiness-failure category), or is it a separate failure mode with its own exit code? [Ambiguity, Spec §FR-010, Contract: signalwire-transport, Contract: cli-slice3]
- [ ] CHK125 Does the `ProviderRejectedDialError` (FR-012) exception's "MUST NOT consume an attempt" invariant align with the data-model §1.11 `WriteBackOperation.queue_status_update.dial_blocked` variant and with contracts/cli-slice3.md exit code 5? [Consistency, Spec §FR-012, Data-Model §1.11, Contract: signalwire-transport, Contract: cli-slice3]
- [ ] CHK126 Does the contracts/signalwire-transport.md exception set address FR-011 (the requirement that any telephony-readiness failure exits before dial with the failing check named), or does the exception hierarchy only cover the failure-detection side and rely on the CLI layer to surface the failing-check name? [Consistency, Gap, Spec §FR-011, Contract: signalwire-transport, Contract: cli-slice3]

### contracts/pipecat-runtime.md exception set vs. FR-013 Round 1 Q4 three triggers

- [ ] CHK127 Does the contracts/pipecat-runtime.md exception set (`RealtimeProviderError`, `PipecatRuntimeError`, `SilenceAfterConnectionTimeout`) cover the FR-013 Round 1 Q4 three triggers one-to-one (provider error from configured real-time AI model → `RealtimeProviderError`; Pipecat runtime crash → `PipecatRuntimeError`; silence-after-connection / no-extraction-event timeout → `SilenceAfterConnectionTimeout`)? [Completeness, Traceability, Spec §FR-013, Contract: pipecat-runtime]
- [ ] CHK128 Does the plan / data-model define which of the three Q4 triggers leads to which final disposition: pre-connected → `failed`/runtime-failure (triggers a + b only; trigger c only fires post-connected), post-connected → `needs_human_review`/`script_truncated` (all three triggers)? [Consistency, Clarity, Spec §FR-013, Data-Model §6, Contract: pipecat-runtime]
- [ ] CHK129 Is the `SilenceAfterConnectionTimeout` exception's "fires only AFTER `connected`" semantics (research §7) reflected in the contracts/pipecat-runtime.md required-behaviors section so the runtime cannot raise it before the normalized `connected` event? [Consistency, Research §7, Contract: pipecat-runtime, Data-Model §6]
- [ ] CHK130 Does the contracts/pipecat-runtime.md exception set distinguish a `RealtimeProviderError` from a transient provider error (which may be retried) vs. a terminal provider error (which finalizes the session), or is every provider error treated as terminal? [Gap, Ambiguity, Contract: pipecat-runtime, Spec §FR-013]

### Live-call abandonment exit code 6 — consistency with FR-026 + Round 2 Q6

- [ ] CHK131 Is the contracts/cli-slice3.md exit code 6 mapping ("Live-call abandonment per FR-026 / Round 2 Q6") consistent with the resume path's "session that previously received `answered` but no terminal event finalizes immediately as `failed` / `live_call_abandonment`" behavior — i.e., does a resume invocation that detects this state also exit with code 6, or does it exit with code 0 because the resume itself completed successfully? [Ambiguity, Gap, Contract: cli-slice3, Spec §FR-022, §FR-026, Data-Model §6]
- [ ] CHK132 Is the FR-026 live-call abandonment failure observably distinct in the run report's `final_disposition` (`failed`) + `human_review_reason` / blocked-reason field from a non-abandonment `failed` outcome (provider 4xx, runtime crash pre-connected)? [Measurability, Spec §FR-026, §FR-036, Contract: cli-slice3]
- [ ] CHK133 Does the data-model §6 resume-path branch explicitly state which exit code the resume invocation produces when it detects the `answered`-but-no-terminal state and immediately finalizes (exit code 0 because the resume completed, or exit code 6 because the original session abandoned)? [Gap, Ambiguity, Data-Model §6, Contract: cli-slice3]

### Live-call abandonment vs. silence-after-connection — observability in the run report

- [ ] CHK134 Is the live-call abandonment failure (FR-026, normalized event stream silent for `SLICE3_ABANDONMENT_TIMEOUT_SEC`) observably distinct from the silence-after-connection failure (FR-013 / Round 1 Q4 trigger c, no extraction event for `SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC` AFTER connected) in the run report's failure / blocked reason field — i.e., does the run report carry a discriminator (`live_call_abandonment` vs. `silence_after_connection_timeout`) so an operator can tell which timeout fired? [Measurability, Clarity, Spec §FR-013, §FR-026, §FR-036, Research §7]
- [ ] CHK135 Is the disposition difference between live-call abandonment (`failed`/`live_call_abandonment`) and silence-after-connection-after-connected (`needs_human_review`/`script_truncated`) traceable through the data-model §6 state-transitions diagram so an operator reading the diagram can predict which outcome each timeout produces? [Clarity, Consistency, Data-Model §6, Spec §FR-013, §FR-026]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate the spec text is open to multiple reasonable interpretations and should be tightened.
- Items marked [Conflict] indicate two sections of the spec disagree.
- CHK118 – CHK135 are Round 3 post-plan validation (2026-05-25) covering: contracts/cli-slice3.md exit codes 0-7 mapping to data-model §6 state transitions AND to quickstart §2/§3 expected-exit-codes tables, contracts/signalwire-transport.md exception hierarchy vs. FR-009/010/011/012 failure modes, contracts/pipecat-runtime.md exception set vs. FR-013 Round 1 Q4 three triggers, live-call abandonment exit code 6 consistency with FR-026 + Round 2 Q6, live-call abandonment vs. silence-after-connection observability in the run report.
- ≥80% of items reference a spec section or a quality marker for traceability.
