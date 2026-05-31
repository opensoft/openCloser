# Integration Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the external-system integration dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Integration Enumeration & Boundary Definition

- [ ] CHK001 Is every external integration in Slice 3 enumerated by name in the requirements (SignalWire telephony, Pipecat runtime, configured real-time AI model provider, shadow STT provider, Dynamics 365 / Dataverse) so that none is left implicit? [Completeness, Spec §Constitution Alignment / Key Entities]
- [ ] CHK002 For each named integration, is its responsibility scope defined (what it provides to openCloser and what openCloser does NOT delegate to it)? [Clarity, Spec §Constitution Alignment]
- [ ] CHK003 Are the conceptual openCloser contracts that each integration must satisfy explicitly named (call-transport contract for SignalWire, persona conceptual contract for Pipecat, Dataverse adapter contract for Dynamics)? [Completeness, Spec §FR-004, FR-013, FR-020]
- [ ] CHK004 Is the configured real-time AI model provider intentionally left unnamed at spec level with the configurability surface (not the provider identity) treated as the requirement? [Clarity, Spec §FR-013 / Deferred to Implementation Plan]
- [ ] CHK005 Is the shadow STT provider intentionally left unnamed at spec level with the configurability surface treated as the requirement? [Clarity, Spec §FR-032 / Deferred to Implementation Plan]
- [ ] CHK006 Does the spec distinguish between integrations that are required for the demonstrable loop (SignalWire, Pipecat, real-time AI model, Dataverse) and those that are optional (shadow STT)? [Clarity, Spec §FR-032, US6 Priority P2]
- [ ] CHK007 Does the spec name the SignalWire-specific concepts that the transport adapter must encapsulate (dial-plan construction, source caller-ID number, status/media callback registration and authentication, provider-state normalization, real provider call ID assignment)? [Completeness, Spec §Key Entities — SignalWire Telephony Transport]
- [ ] CHK008 Are integration boundaries declared in a way that lets a reader determine — without reading code — which module owns each integration concern? [Clarity, Spec §FR-005, FR-013, FR-018]

## Credentials & Secrets Surface

- [ ] CHK009 Is the credentials surface for each integration documented (SignalWire credentials, real-time AI provider credentials, shadow STT provider credentials, Dataverse credentials)? [Completeness, Spec §FR-035]
- [ ] CHK010 Is there a requirement that NO secrets from any integration appear in logs, exported artifacts, the run report, or planned/actual write-back payloads? [Coverage, Spec §FR-035, SC-018]
- [ ] CHK011 Is "secret" defined or bounded enough (e.g., "SignalWire credentials, real-time AI provider credentials, shadow STT provider credentials, Dataverse credentials, or any other secret") that a reviewer can determine what must not be logged? [Clarity, Spec §FR-035, SC-018]
- [ ] CHK012 Does the spec require that callback authentication secrets (e.g., SignalWire signing key) are not logged even on failed-authentication paths? [Coverage, Spec §FR-008]
- [ ] CHK013 Is the requirement to not log secrets stated as measurable (e.g., "0 secrets … appear in logs")? [Measurability, Spec §SC-018]
- [ ] CHK014 Does the spec address whether real-time AI provider model configuration that is recorded for audit (e.g., model name and version) might include sensitive provider-account identifiers that should be excluded? [Gap, Spec §FR-016]
- [ ] CHK015 Is there a requirement that operator identity recording (FR-016) does NOT capture credentials or tokens belonging to the operator? [Gap, Spec §FR-016]
- [ ] CHK016 Does the spec address how credentials are detected as "present and validatable" at telephony readiness time without leaking them to the readiness report? [Ambiguity, Spec §FR-009]
- [ ] CHK017 Does the spec address credential rotation or revocation mid-deployment (e.g., SignalWire credentials suspended between runs vs. mid-run)? [Edge Case, Spec §Edge Cases — SignalWire credentials or source number unauthorized / suspended mid-run]

## Callback Authentication & Inbound-Trust Surface

- [ ] CHK018 Is there a requirement that SignalWire callback delivery is authenticated using the provider's documented mechanism where supported? [Completeness, Spec §FR-008]
- [ ] CHK019 Does the spec require that callbacks failing authentication MUST be rejected (not merely logged)? [Clarity, Spec §FR-008]
- [ ] CHK020 Is the behavior for rejected callbacks specified (no-op for state, no normalized event emitted, audit entry created)? [Gap, Spec §FR-008]
- [ ] CHK021 Does the spec address what happens if SignalWire signature verification is unsupported in a given deployment ("where supported" qualifier)? [Ambiguity, Spec §FR-008]
- [ ] CHK022 Is callback authentication scope bounded to SignalWire callbacks, or is there a parallel requirement for other inbound integration callbacks (real-time AI provider, shadow STT, Dataverse webhooks)? [Coverage, Spec §FR-008]
- [ ] CHK023 Does the spec address replay-attack protection for SignalWire callbacks beyond duplicate-event-id de-duplication (e.g., time-window enforcement on the signature)? [Gap, Spec §FR-007, FR-008]
- [ ] CHK024 Is the provider event id surface for de-duplication clearly defined (SignalWire-provided identifier used as the de-duplication key under `(session_id, provider_event_id)`)? [Clarity, Spec §FR-007, FR-021]
- [ ] CHK025 Does the spec require that callback authentication failures do NOT consume an attempt or mutate Dataverse? [Gap, Spec §FR-008, FR-025]

## Configuration Surface (Per Integration)

- [ ] CHK026 Is the SignalWire configuration surface enumerated (credentials, source caller-ID number, status callback URL, media callback URL)? [Completeness, Spec §FR-009, FR-037]
- [ ] CHK027 Is the Pipecat / real-time AI runtime configuration surface enumerated (persona/runtime mapping, model identity, silence-after-connection timeout)? [Completeness, Spec §FR-013, FR-037]
- [ ] CHK028 Is the shadow STT configuration surface enumerated (enable/disable toggle, discrepancy policy)? [Completeness, Spec §FR-032, FR-037]
- [ ] CHK029 Is the Dataverse configuration surface inherited from Slice 2 verbatim with no Slice 3 additions called out (i.e., is the "no new Dataverse fields for Slice 3" boundary explicit)? [Consistency, Spec §FR-020, FR-016]
- [ ] CHK030 Are the configuration items that are deferred to plan listed separately from configuration that is binding in spec (e.g., "configurability is the requirement; the default value is deployment configuration")? [Clarity, Spec §FR-013, FR-026, FR-032, FR-033, Deferred to Implementation Plan]
- [ ] CHK031 Does the spec specify whether the real-call / write-enabled flag is per-invocation (CLI flag) vs. environment-level configuration? [Ambiguity, Spec §FR-001, Deferred to Implementation Plan]
- [ ] CHK032 Is the campaign-to-persona/runtime mapping requirement explicit as a configuration surface item (resolvable before dial)? [Completeness, Spec §FR-009]

## Failure-Mode Coverage (Per Integration)

### SignalWire failure modes

- [ ] CHK033 Are SignalWire credential failures (missing, invalid, suspended) covered by the readiness check requirement? [Coverage, Spec §FR-009, US3 Acceptance 2]
- [ ] CHK034 Are SignalWire source-number failures (missing, unauthorized) covered by the readiness check requirement? [Coverage, Spec §FR-009, US3 Acceptance 2]
- [ ] CHK035 Are SignalWire callback-URL failures (missing, unreachable from SignalWire side) covered by the readiness check requirement? [Coverage, Spec §FR-009, US3 Acceptance 4]
- [ ] CHK036 Is the SignalWire provider-rejected dial failure mode (4xx before call placement) specified with explicit no-attempt-consumed / no-Phone-Call-activity / queue-status behavior? [Coverage, Spec §FR-012]
- [ ] CHK037 Are SignalWire mid-run credential/source-number suspensions specified (in-flight calls allowed to complete, next pre-dial check fails)? [Edge Case, Spec §Edge Cases — SignalWire credentials or source number unauthorized / suspended mid-run]
- [ ] CHK038 Is the SignalWire status-callback delivery failure (persistent / transient) specified with live-call-abandonment finalization behavior? [Coverage, Spec §FR-026, Edge Cases — Status / media callback URL unreachable]
- [ ] CHK039 Is the SignalWire duplicate-callback case specified as a state no-op with audit recording? [Coverage, Spec §FR-007, FR-021, US4 Acceptance 1]
- [ ] CHK040 Is the SignalWire out-of-order-callback case specified with explicit tolerance and coherent disposition normalization? [Coverage, Spec §FR-005, US4 Acceptance 2, Edge Cases]
- [ ] CHK041 Is the SignalWire late-after-finalization callback case specified as a no-op for state with audit recording? [Coverage, Spec §FR-027, Edge Cases]
- [ ] CHK042 Is the SignalWire carrier-equivalent failure (busy / canceled / failed) normalization mapping requirement clear? [Clarity, Spec §FR-005, US4 Acceptance 3, Edge Cases]

### Pipecat / real-time AI failure modes

- [ ] CHK043 Is a Pipecat runtime crash mid-call covered with explicit finalization behavior? [Coverage, Spec §FR-013, US5 Acceptance 5, Edge Cases — Live model failure or runtime crash mid-call]
- [ ] CHK044 Is an explicit error from the configured real-time AI model provider covered with explicit finalization behavior? [Coverage, Spec §FR-013, Edge Cases]
- [ ] CHK045 Is the silence-after-connection / no-extraction-event timeout failure mode specified with finalization to `needs_human_review` reason `script_truncated`? [Coverage, Spec §FR-013, Edge Cases]
- [ ] CHK046 Is the distinction specified between live-runtime failure BEFORE connection (finalize `failed` with runtime-failure reason, no false Phone Call activity) vs. AFTER connection (finalize `needs_human_review` reason `script_truncated`)? [Clarity, Spec §FR-013, Edge Cases]
- [ ] CHK047 Is the silence-timeout trigger documented as not-applicable before connection (since the timer only starts after connection)? [Clarity, Spec §Edge Cases — Live model failure or runtime crash mid-call]
- [ ] CHK048 Are Pipecat audio codec / transport mismatch failures addressed at requirement level, or explicitly deferred to plan? [Gap / Dependency, Spec §Deferred to Implementation Plan — Runtime and live-model details]
- [ ] CHK049 Is there a requirement that a live-model attempt to emit an out-of-allowed-claim utterance is detected by the persona module and escalated (not silently passed through)? [Coverage, Spec §FR-014, FR-015, US5 Acceptance 2]
- [ ] CHK050 Is there a requirement that the live model MUST NOT relax the persona's safety gates or expand the `needs_human_review` reason set? [Coverage, Spec §FR-014, FR-015]

### Shadow STT failure modes

- [ ] CHK051 Is a shadow STT lane crash or timeout covered with explicit "live call unaffected" requirement? [Coverage, Spec §FR-029, US6 Acceptance 6, Edge Cases — Shadow STT lane fails or times out]
- [ ] CHK052 Is the shadow STT missing-output case (lane failed before producing a transcript) specified to NOT emit discrepancy events? [Coverage, Spec §Edge Cases — Shadow STT lane fails or times out]
- [ ] CHK053 Is the shadow STT enabled/disabled toggle case covered (when disabled, the demonstrable loop completes; run report records the disabled flag)? [Coverage, Spec §FR-032, US6 Acceptance 5]
- [ ] CHK054 Is the shadow STT discrepancy-on-high-value-field case specified to record audit evidence without writing CRM independently or overriding the final disposition? [Coverage, Spec §FR-030, US6 Acceptance 3, Edge Cases]
- [ ] CHK055 Is the shadow STT uncertain-discrepancy case specified to escalate to `needs_human_review` with `shadow_stt_discrepancy` review-task reason via the orchestrator's normal write-back path? [Coverage, Spec §FR-031, US6 Acceptance 4]

### Dataverse / Dynamics failure modes

- [ ] CHK056 Are Dataverse metadata-verification failures at run start specified to block before dial without consuming an attempt? [Coverage, Spec §FR-009, US3 Acceptance 1, Edge Cases — Dataverse metadata drift]
- [ ] CHK057 Are transient Dataverse write failures specified to use bounded in-run retry (Slice 2 reused unchanged)? [Coverage, Spec §FR-022, US7 Acceptance 1]
- [ ] CHK058 Is the exhausted-retry-budget case specified to resume on operator re-invocation without duplicating CRM records? [Coverage, Spec §FR-022, US4 Acceptance 7, US7 Acceptance 2]
- [ ] CHK059 Is the Dataverse partial write-back case (Phone Call activity succeeded, Task failed) specified with the resume path applying? [Coverage, Spec §US7 Independent Test, US7 Acceptance 5]
- [ ] CHK060 Is the human-conflict case (CRM queue item changed between claim and write-back) specified to preserve high-confidence values and stop write-back before the final status update? [Coverage, Spec §Edge Cases — CRM queue item changed by a human]
- [ ] CHK061 Is the concurrent-CLI-invocation case (two invocations on the same Dataverse queue item) specified to use Slice 2 queue-claim semantics with the second invocation exiting before dial? [Coverage, Spec §FR-003, Clarifications, Edge Cases — Concurrent CLI invocation]

### Cross-integration failure modes

- [ ] CHK062 Is the orchestrator-restart-mid-call case specified with finalization via live-call-abandonment timeout and resume path for partial write-back? [Coverage, Spec §FR-026, US4 Acceptance 8, Edge Cases]
- [ ] CHK063 Is the "Dataverse-unreachable-at-start" case specified to block before dial without consuming an attempt? [Coverage, Spec §FR-025]

## Protocol-Boundary Leak Prevention

- [ ] CHK064 Is there an explicit requirement that SignalWire-specific event shapes MUST NOT leak into the orchestrator, eligibility evaluator, persona, or Dataverse adapter? [Coverage, Spec §FR-005, SC-015]
- [ ] CHK065 Is there an explicit requirement that Pipecat-specific pipeline shapes MUST NOT leak into the orchestrator, eligibility evaluator, transport, persona module (beyond its existing inputs/outputs), or Dataverse adapter? [Coverage, Spec §FR-013, SC-015]
- [ ] CHK066 Is there an explicit requirement that the real-time AI model provider's streaming protocol details MUST NOT leak outside the Pipecat runtime adapter? [Coverage, Spec §FR-013, SC-015]
- [ ] CHK067 Is there an explicit requirement that shadow STT provider details MUST NOT leak outside the shadow STT lane? [Coverage, Spec §SC-015]
- [ ] CHK068 Is the leak-prevention requirement measurable (e.g., "0 SignalWire-specific event shapes ... in the orchestrator, eligibility evaluator, persona module, and Dataverse adapter")? [Measurability, Spec §SC-015]
- [ ] CHK069 Is the leak-prevention requirement verifiable by inspection / boundary test as called out in the success criteria? [Measurability, Spec §SC-015]
- [ ] CHK070 Are the only sanctioned name-level changes at the Slice 1 → Slice 3 boundary enumerated explicitly (`mock_provider_call_id` → `provider_call_id`, `MockCallEvent` → `CallEvent`, `fixture_id` → `dial_plan`)? [Completeness, Spec §FR-018, Assumptions]
- [ ] CHK071 Is the additive entry `shadow_stt_discrepancy` to the human-review reason enumeration explicitly the ONLY additive change to that enumeration in Slice 3? [Clarity, Spec §FR-014, FR-031, Assumptions]
- [ ] CHK072 Is the normalized openCloser event set enumerated (`connected`, `no_answer`, `voicemail`, `failed`, `completed`, `callback_requested`) at the level where vendor-event mapping is specified? [Completeness, Spec §FR-005, Definitions — Normalized call event]
- [ ] CHK073 Is the requirement that the live model MUST NOT mutate the deterministic disposition rules or the human-review reason set stated explicitly (not just implicit in persona authority)? [Clarity, Spec §FR-014, SC-014]

## Slice 1 / Slice 2 Contract Preservation

- [ ] CHK074 Is there an explicit requirement that the Slice 1 module boundaries (orchestrator, eligibility evaluator, call transport, persona module, CRM write-back adapter) are preserved unchanged? [Coverage, Spec §FR-018]
- [ ] CHK075 Is there an explicit requirement that the Slice 1 normalized-result shape is reused unchanged (with only the documented field rename)? [Coverage, Spec §FR-017, SC-016]
- [ ] CHK076 Is there an explicit requirement that the Slice 1 eligibility behavior (six rules, `blocked` disposition, `blocked_reason`) is preserved unchanged? [Coverage, Spec §FR-019]
- [ ] CHK077 Is there an explicit requirement that the Slice 1 disposition enumeration is preserved unchanged (no new dispositions in Slice 3)? [Coverage, Spec §FR-017]
- [ ] CHK078 Is there an explicit requirement that the Slice 1 persona policy (disclosure, non-clinical scope, no PHI, opt-out / DNC stop, allowed-claim limits, enumerated `needs_human_review` reasons, deterministic disposition precedence) is preserved unchanged? [Coverage, Spec §FR-014, FR-015, Assumptions]
- [ ] CHK079 Is there an explicit requirement that the Slice 2 Dataverse write-back adapter, per-disposition emission decisions, and per-disposition `new_status` mapping are reused unchanged? [Coverage, Spec §FR-020, SC-016]
- [ ] CHK080 Is there an explicit requirement that Slice 2 Dataverse metadata two-phase verification, mapping artifact, owner/team mapping, and high-confidence value preservation are reused unchanged? [Coverage, Spec §FR-020, SC-016]
- [ ] CHK081 Is there an explicit requirement that Slice 2 idempotency-key stamping behavior is reused unchanged? [Coverage, Spec §FR-021, SC-016]
- [ ] CHK082 Is there an explicit requirement that Slice 2 bounded in-run retry (initial + 3 retries, 1s/2s/4s default, `Retry-After` honored capped at 30s) is reused unchanged? [Coverage, Spec §FR-022]
- [ ] CHK083 Is there an explicit requirement that Slice 2 resume-on-re-invocation behavior is reused unchanged? [Coverage, Spec §FR-022, US4 Acceptance 7, US7 Acceptance 2]
- [ ] CHK084 Is there an explicit requirement that Slice 2 dry-run / readiness default behavior is reused (and extended so the same flag controls SignalWire dialing)? [Coverage, Spec §FR-001, FR-002, Definitions]
- [ ] CHK085 Is there an explicit requirement that Slice 2 local-audit retention floor (≥90 days) is reused for Slice 3 audit artifacts? [Coverage, Spec §FR-022, Assumptions]
- [ ] CHK086 Is there an explicit requirement that no Slice 1 / Slice 2 contract is weakened or deleted? [Coverage, Spec §FR-020, Assumptions]
- [ ] CHK087 Is contract preservation called out as verifiable by contract tests / boundary inspection (not merely a code-author convention)? [Measurability, Spec §SC-016]
- [ ] CHK088 Is the backwards-compatible call-ID correlation requirement explicit (pre-Slice-3 session artifacts and CRM correlations remain interpretable after the rename)? [Coverage, Spec §FR-006, Assumptions]
- [ ] CHK089 Is the requirement that Slice 3 adds NO new Dataverse fields (only the real provider call ID and connected-call timestamps on the existing Phone Call activity payload) explicit? [Clarity, Spec §FR-020, FR-016]

## Integration-Lifecycle States (Misconfigured at Invocation vs. Mid-Call vs. Suspended)

- [ ] CHK090 Is the "integration misconfigured at invocation" path covered (telephony readiness check exits before dial, no attempt consumed, no Phone Call activity)? [Scenario Class — Exception, Spec §FR-009, FR-011]
- [ ] CHK091 Is the "integration fails mid-call" path covered for SignalWire (callback delivery failure → live-call abandonment timeout)? [Scenario Class — Exception, Spec §FR-026]
- [ ] CHK092 Is the "integration fails mid-call" path covered for Pipecat / real-time AI (runtime crash, model provider error)? [Scenario Class — Exception, Spec §FR-013]
- [ ] CHK093 Is the "integration fails mid-call" path covered for shadow STT (lane crash or timeout → live call unaffected)? [Scenario Class — Exception, Spec §FR-029]
- [ ] CHK094 Is the "integration fails mid-call" path covered for Dataverse (transient error → bounded retry → resume)? [Scenario Class — Exception / Recovery, Spec §FR-022]
- [ ] CHK095 Is the "integration suspended mid-run" path covered (SignalWire credentials/source-number suspended mid-run; in-flight calls allowed to complete)? [Scenario Class — Edge Case, Spec §Edge Cases — SignalWire credentials or source number unauthorized / suspended mid-run]
- [ ] CHK096 Is the live-call-abandonment timeout governance specified as a deployment-configured value with the configurability as the requirement? [Clarity, Spec §FR-026, Assumptions]
- [ ] CHK097 Is the silence-after-connection / no-extraction-event timeout governance specified as a deployment-configured value with the configurability as the requirement? [Clarity, Spec §FR-013, Assumptions]
- [ ] CHK098 Is the orchestrator behavior on a NEW invocation after a finalized session specified to be a no-op for CRM (no duplicate Phone Call activity / Task / queue-status transition / attempt-count increment)? [Recovery, Spec §US4 Acceptance 9]
- [ ] CHK099 Is the dial-plan / persona-runtime malformed-configuration case specified to NOT consume an attempt? [Recovery, Spec §FR-025]

## Provider Event ID & Idempotency Across Integrations

- [ ] CHK100 Is the de-duplication key for SignalWire callbacks specified as `(session_id, provider_event_id)`? [Clarity, Spec §FR-007, FR-021]
- [ ] CHK101 Is idempotency required for: duplicate SignalWire status callbacks, duplicate SignalWire media callbacks, repeated CLI invocations for the same session, and Dataverse write-back retries? [Coverage, Spec §FR-021, US4 Independent Test]
- [ ] CHK102 Is the idempotency requirement measurable (100% of duplicates and recovery attempts produce no duplicate Phone Call activities / Tasks / queue-status transitions / attempt-count increments)? [Measurability, Spec §SC-008]
- [ ] CHK103 Is the requirement explicit that a duplicate SignalWire callback IS still recorded in the local callbacks audit log even though it is a state no-op? [Clarity, Spec §FR-021, US4 Acceptance 1]
- [ ] CHK104 Is the conflicting-late-callback case (e.g., `failed` after `completed`) specified to record an audit entry without mutating the finalized disposition? [Coverage, Spec §FR-027, Edge Cases]
- [ ] CHK105 Is the provider event id requirement clear that the SignalWire-assigned identifier is what is used (not an openCloser-generated id)? [Clarity, Spec §FR-007, Definitions]

## Scenario Classes (Per Integration)

### Primary

- [ ] CHK106 Is a primary-path requirement defined for SignalWire (outbound dial, real provider call ID assigned, normalized event stream)? [Primary, Spec §FR-004, US1]
- [ ] CHK107 Is a primary-path requirement defined for Pipecat / real-time AI (connected-call audio bridged, persona-driven turns, extraction events emitted)? [Primary, Spec §FR-013, US5]
- [ ] CHK108 Is a primary-path requirement defined for Dataverse write-back (Phone Call activity + queue-status update + Task per the per-disposition map)? [Primary, Spec §FR-020, US1]
- [ ] CHK109 Is a primary-path requirement defined for shadow STT when enabled (independent transcript, high-value-field comparison, discrepancy events)? [Primary, Spec §FR-028, FR-030, US6]

### Alternate

- [ ] CHK110 Is an alternate-path requirement defined for SignalWire `no_answer` / `voicemail` outcomes (sane normalized outcome, no false connected-call Phone Call activity)? [Alternate, Spec §US1 Acceptance 5, US4 Acceptance 4, SC-007]
- [ ] CHK111 Is an alternate-path requirement defined for caller hang-up mid-conversation (deterministic disposition rules applied to available extraction)? [Alternate, Spec §US4 Acceptance 5]
- [ ] CHK112 Is an alternate-path requirement defined for an interested-caller-without-callback flow (email captured, single Task with email)? [Alternate, Spec §US1 Acceptance 2, SC-004]
- [ ] CHK113 Is an alternate-path requirement defined for shadow STT disabled (loop still completes, run report records disabled)? [Alternate, Spec §FR-032, US6 Acceptance 5]
- [ ] CHK114 Is an alternate-path requirement defined for rehearsal / readiness mode (zero SignalWire calls, zero Dataverse mutations, planned write-back artifacts)? [Alternate, Spec §FR-002, US2, SC-002]

### Exception / Error

- [ ] CHK115 Is an exception-path requirement defined for SignalWire credentials missing / unauthorized? [Exception, Spec §FR-009, US3 Acceptance 2]
- [ ] CHK116 Is an exception-path requirement defined for SignalWire provider-rejected dial (4xx)? [Exception, Spec §FR-012, Edge Cases]
- [ ] CHK117 Is an exception-path requirement defined for a malformed / missing destination phone number? [Exception, Spec §FR-010, US3 Acceptance 3, Edge Cases]
- [ ] CHK118 Is an exception-path requirement defined for a missing / unreachable status or media callback URL? [Exception, Spec §FR-009, US3 Acceptance 4]
- [ ] CHK119 Is an exception-path requirement defined for a Pipecat runtime crash / real-time AI model provider error? [Exception, Spec §FR-013, US5 Acceptance 5, Edge Cases]
- [ ] CHK120 Is an exception-path requirement defined for shadow STT lane crash / timeout? [Exception, Spec §FR-029, US6 Acceptance 6, Edge Cases]
- [ ] CHK121 Is an exception-path requirement defined for Dataverse unreachable at start? [Exception, Spec §FR-025]
- [ ] CHK122 Is an exception-path requirement defined for a callback that fails SignalWire signature authentication? [Exception, Spec §FR-008]
- [ ] CHK123 Is an exception-path requirement defined for the live model attempting to emit an out-of-allowed-claim utterance? [Exception, Spec §FR-014, FR-015, US5 Acceptance 2]
- [ ] CHK124 Is an exception-path requirement defined for a mid-call PHI or out-of-scope topic attempt? [Exception, Spec §Edge Cases — Mid-call PHI / out-of-allowed-claim attempt]

### Recovery (with rollback consideration where state mutates)

- [ ] CHK125 Is a recovery-path requirement defined for transient Dataverse error → bounded retry within the same run? [Recovery, Spec §FR-022, US7 Acceptance 1]
- [ ] CHK126 Is a recovery-path requirement defined for retry-budget exhausted → operator re-invocation resumes only the missing writes? [Recovery, Spec §FR-022, US4 Acceptance 7, US7 Acceptance 2]
- [ ] CHK127 Is a recovery-path requirement defined for SignalWire callback redelivery after a transient failure? [Recovery, Spec §US7 Acceptance 3]
- [ ] CHK128 Is a recovery-path requirement defined for orchestrator restart between `completed` callback and Dataverse write-back, including preservation of the recorded real provider call ID? [Recovery, Spec §US7 Acceptance 4]
- [ ] CHK129 Is a recovery-path requirement defined for live-call abandonment (placed call without normalized terminal event within timeout finalized as `failed` with `live_call_abandonment` reason, queue item leaves `in_progress`)? [Recovery, Spec §FR-026, US4 Acceptance 8, Edge Cases]
- [ ] CHK130 Is the rollback / non-mutation guarantee explicit on all pre-dial failure paths (no Phone Call activity created, no attempt consumed, queue unchanged beyond approved blocked-status write)? [Recovery, Spec §FR-011, FR-012, FR-025]
- [ ] CHK131 Is the recovery path for a partial Dataverse write-back (Phone Call activity succeeded, Task failed transiently) specified to converge to exactly one Task with the correct reason code on retry? [Recovery, Spec §US7 Acceptance 5]
- [ ] CHK132 Is the absence-of-transcript-file case on resume specified as a non-error (audit artifacts and write-back progress rows are authoritative for resume)? [Recovery, Spec §Edge Cases — Resume after a real call when retention policy disables the transcript artifact]

### Non-Functional

- [ ] CHK133 Is the non-functional requirement that shadow STT MUST NOT slow the live call path explicit? [Non-Functional, Spec §FR-029, SC-013]
- [ ] CHK134 Is the non-functional requirement that the live conversation path completes with no observable slowdown attributable to the shadow lane measurable? [Measurability / Non-Functional, Spec §SC-013]
- [ ] CHK135 Is the non-functional requirement that Slice 3 processes exactly one Dataverse queue item per invocation (no batch / no scheduler / no multi-worker) explicit and enumerable? [Non-Functional, Spec §FR-003, Assumptions]
- [ ] CHK136 Is the non-functional requirement that local audit retention is ≥90 days (Slice 2 floor reused) explicit? [Non-Functional, Spec §FR-022, Assumptions]
- [ ] CHK137 Is the non-functional requirement that no auto-deletion of audit artifacts occurs (operator-only manual pruning) explicit? [Non-Functional, Spec §Assumptions]
- [ ] CHK138 Is the non-functional requirement of authentication for inbound callbacks bounded to "where provider supports it" explicit? [Non-Functional, Spec §FR-008]
- [ ] CHK139 Is the non-functional requirement that ANY of three independent triggers (provider error / runtime crash / silence timeout) MUST cause live-runtime degradation finalization explicit and measurable? [Non-Functional / Coverage, Spec §FR-013, Clarifications]
- [ ] CHK140 Is the constitutional auditability guarantee (every processed queue item produces a traceable session ID, eligibility decision, real provider call ID when dialed, persona version, runtime/model identity, started/ended timestamps, final disposition, and CRM correlation identifiers) restated in functional requirements? [Coverage / Traceability, Spec §Constitution Alignment — Auditability, FR-016, FR-036]

## Cross-Cutting Integration Concerns

- [ ] CHK141 Is the spec consistent between the readiness check definition (Definitions section) and the FR-009 enumeration of readiness checks? [Consistency, Spec §Definitions — Telephony readiness check, FR-009]
- [ ] CHK142 Is the spec consistent between FR-010 (real-dial phone-number validation) and the Edge Cases / Definitions phrasings of the same gate? [Consistency, Spec §FR-010, Definitions — Real-dial phone-number validation, Edge Cases]
- [ ] CHK143 Is the spec consistent between FR-025 (attempt-count semantics) and the various FRs that say "no attempt consumed" (FR-011, FR-012, FR-021)? [Consistency, Spec §FR-011, FR-012, FR-021, FR-025]
- [ ] CHK144 Is the spec consistent between FR-007 / FR-021 (callback de-duplication) and FR-027 (conflicting-late callback handling)? [Consistency, Spec §FR-007, FR-021, FR-027]
- [ ] CHK145 Is the spec consistent between FR-013 / Clarifications (three live-runtime degradation triggers) and the Edge Cases description of pre-connection vs. post-connection finalization? [Consistency, Spec §FR-013, Clarifications, Edge Cases — Live model failure or runtime crash mid-call]
- [ ] CHK146 Is the spec consistent between the "raw audio is out of scope" assumption and the FR-028 / FR-030 description of shadow STT consuming the same caller audio (i.e., the audio fan-out does not imply raw-audio persistence)? [Consistency, Spec §Assumptions, FR-028, Edge Cases]
- [ ] CHK147 Is the spec free of conflict between Pipecat being "the only Slice 3 voice runtime" and the persona module retaining authority (i.e., persona authority does not contradict Pipecat ownership of audio bridging)? [Consistency, Spec §FR-013, FR-014, Assumptions]
- [ ] CHK148 Are integration dependencies explicit (e.g., Pipecat depends on a connected SignalWire call; shadow STT depends on the same caller audio; Dataverse write-back depends on a real provider call ID being assigned before Phone Call activity creation)? [Dependency, Spec §FR-013, FR-020, FR-028]
- [ ] CHK149 Is the assumption that "first and only telephony provider is SignalWire" stated, with multi-provider abstraction explicitly out of scope? [Assumption, Spec §Assumptions]
- [ ] CHK150 Is the assumption that "Pipecat is the only Slice 3 voice runtime" stated, with modular STT→LLM→TTS chains out of scope as primary live path? [Assumption, Spec §Assumptions]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

- [ ] CHK151 Is the integration contract with SignalWire's signature-verification mechanism stated clearly enough that a deployment can choose a specific verification method (e.g., HMAC signature header, SDK-provided verifier) without re-amending the spec? [Clarity, Spec §FR-008, Spec §Deferred to Implementation Plan > Telephony adapter details]
- [ ] CHK152 Is the integration between the rejected-by-authentication audit log and the run report (FR-036) well-defined — does the run report read a derived count from the audit log, or is the count incremented independently? [Clarity, Spec §FR-008, Spec §FR-036]
- [ ] CHK153 Is the no-secret / no-body invariant on the rejected-by-authentication audit log enforceable at the SignalWire transport boundary (i.e., the rejection path runs inside the transport, never marshaling the secret or body across the boundary)? [Boundary, Spec §FR-008, Spec §Constitution Alignment > Boundaries]
- [ ] CHK154 Is the integration relationship between the rejected-by-authentication audit log and the existing Callbacks Audit Log defined (separate file? separate table? separate index? shared file with a discriminator?) so an operator can locate forgery evidence without scanning the duplicate-callbacks log? [Clarity, Spec §FR-008, Spec §Key Entities > Callbacks Audit Log]
- [ ] CHK155 Is the post-finalization grace-window integration with the shadow STT provider well-defined — does the orchestrator subscribe to a shadow-lane "drain" signal, or does it poll until the deadline, and does the spec require either approach? [Completeness, Spec §FR-029]
- [ ] CHK156 Is the grace-window integration with the Dataverse adapter clearly bounded — does the orchestrator hold the write-back call entirely, or is the gate inside the adapter? [Boundary, Spec §FR-029, Spec §FR-020]
- [ ] CHK157 Does the grace-window-elapsed handoff to the Dataverse adapter preserve the Slice 2 bounded retry budget (FR-022) — i.e., grace-window wall-clock time is separate from retry-budget time? [Consistency, Spec §FR-029, Spec §FR-022]
- [ ] CHK158 Is the PHI tag-and-redact integration defined as a single point (one redaction pipeline that runs over transcript + summary + shadow transcript + shadow discrepancy records before any write) or as distributed enforcement (each writer applies redaction independently) — is the integration shape pinned? [Clarity, Spec §FR-015, Spec §FR-033]
- [ ] CHK159 Is the PHI tag-and-redact pipeline integration with the live transcript writer, the shadow transcript writer, and the discrepancy-record writer ordered such that NO artifact is written to disk before redaction completes (FR-015 "BEFORE any of those artifacts are written to disk")? [Consistency, Spec §FR-015, Spec §FR-033]
- [ ] CHK160 Is the operator identity propagation across resume invocations clearly defined — the original operator is preserved on the local session record and audit artifacts, AND the resuming operator is recorded on the run report only? [Consistency, Spec §FR-016, Spec §FR-036]
- [ ] CHK161 Is the operator-identity propagation contract clear about which audit artifacts receive the original operator vs. the resuming operator (e.g., callbacks audit log, conflicting-events audit log, write-back progress ledger, shadow STT discrepancy records)? [Completeness, Spec §FR-016]
- [ ] CHK162 Is the DNC-first integration with the Dataverse adapter defined as a hard-coded ordering invariant of the adapter, or as a parameter the orchestrator passes — does the spec pin which? [Clarity, Spec §FR-024, Spec §FR-020]
- [ ] CHK163 Is the DNC-first ordering compatible with the Slice 2 idempotency-key stamping integration — i.e., the idempotency-key stamping on the DNC write prevents duplicate DNC writes on resume even when DNC is the first field-write in the queue-status update operation? [Consistency, Spec §FR-024, Spec §FR-021]
- [ ] CHK164 Is the integration between the resume-on-`answered`-but-no-terminal-event behavior (FR-026) and the SignalWire transport defined as no-reconnect / no-rewire (the resume invocation does not subscribe to further SignalWire callbacks for the in-flight call and does not attempt to re-attach the media stream)? [Boundary, Spec §FR-026]
- [ ] CHK165 Is the integration between the resume invocation and the real-call / write-enabled flag enforcement defined (FR-001 + FR-022) such that a resume without the flag runs in rehearsal mode through the same code path — no sticky promotion? [Consistency, Spec §FR-001, Spec §FR-016, Spec §FR-022]
- [ ] CHK166 Is the rejected-by-authentication audit log's integration with the local-artifact retention floor (≥90 days, per FR-022 / Assumptions > Local artifact retention) stated explicitly so an inspector knows forgery evidence is retained on the same floor? [Completeness, Spec §FR-008, Spec §FR-022]
- [ ] CHK167 Is the `shadow_lane_truncated` event's integration with the conflicting-events audit log (FR-027) defined — does a post-finalization shadow event also go to the conflicting-events audit log, or is `shadow_lane_truncated` a distinct audit channel? [Clarity, Spec §FR-029, Spec §FR-027]
- [ ] CHK168 Is the integration between FR-015 PHI tag-and-redact and FR-034 shadow-transcript retention defined consistently — i.e., when shadow STT is enabled the redaction applies to the shadow transcript and the discrepancy records before they are written under the retention policy? [Consistency, Spec §FR-015, Spec §FR-034]
- [ ] CHK169 Is the rejected-by-authentication count surfaced on the run report (FR-036) integrated as a first-class run-report field (not buried inside the callbacks audit summary), so an operator can detect attempted forgeries at a glance? [Completeness, Spec §FR-008, Spec §FR-036]
- [ ] CHK170 Is the integration between the resume operator format ("resumed by X, original operator Y", FR-036) and downstream readers (e.g., the demo evidence in FR-038) defined enough that the operator-readable Run Report carries the human-readable phrasing? [Clarity, Spec §FR-036, Spec §FR-038]
- [ ] CHK171 Does the spec define the integration behavior when the grace window elapses concurrently with a Dataverse write attempt — i.e., the write-back proceeds without the late shadow result and the late shadow result is recorded as `shadow_lane_truncated` (no race-condition ambiguity)? [Consistency, Spec §FR-029] (Resolves CHK046 [Conflict] from requirements.md.)
- [ ] CHK172 Does the spec define the integration with the SignalWire signature-verification configuration surface (where the verification secret lives, how it is rotated) at the spec level, or is it explicitly deferred to plan? [Clarity, Spec §FR-008, Spec §Deferred to Implementation Plan > Telephony adapter details]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

- [ ] CHK173 Does the research.md §1 SignalWire SDK decision (`signalwire>=2.0,<3.0` for outbound dial + SWML, `httpx` for signature verification) trace back to a spec requirement (FR-004 for the dial, FR-008 for the signature verification) — and does the version pin's upper bound (<3.0) protect against a breaking SDK upgrade? [Completeness, Research §1, Spec §FR-004, Spec §FR-008]
- [ ] CHK174 Does the research.md §1 "embedded ASGI callback receiver (FastAPI/uvicorn) bound only in real-call mode" decision align with the spec FR-001 / FR-002 "rehearsal mode does not place a SignalWire call" rule — i.e., rehearsal mode genuinely needs no port binding? [Consistency, Research §1, Spec §FR-001, Spec §FR-002]
- [ ] CHK175 Is the research.md §1 alternative-rejected list ("raw `httpx`", "separate webhook receiver", "Twilio / multi-provider abstraction") consistent with the constitution's "MUST avoid multiple telephony providers" AND with the spec's "SignalWire is the only Slice 3 telephony provider" assumption? [Consistency, Research §1, Spec §Assumptions, Plan §Constitution Check]
- [ ] CHK176 Does research.md §2's HMAC-SHA256 verification mechanism choice trace to FR-008's "provider's documented mechanism where supported" requirement, with the rejected-auth audit-log columns matching Round 2 Q9 verbatim? [Consistency, Research §2, Spec §FR-008, Spec §Clarifications Round 2 Q9]
- [ ] CHK177 Is the research.md §3 `RealtimeAIProvider` Protocol's three-method shape (`start_session`, `stream_audio`, `end_session`) sufficient to satisfy FR-013's "bridge connected-call audio to and from the configured real-time AI model provider as the primary live conversation path" — does the protocol cover both audio directions AND extraction-event emission? [Completeness, Research §3, Spec §FR-013, Contract: pipecat-runtime.md]
- [ ] CHK178 Does the research.md §3 "first development/CI fake at `runtime/pipecat/provider_fake.py`" decision enable contract tests to run without burning real-provider tokens, matching the research.md §12 testing strategy "no fakes (bad ergonomics)" rejection? [Consistency, Research §3, Research §12]
- [ ] CHK179 Does the research.md §4 `ShadowSTTProvider` Protocol's "if env var unset OR equal to `\"disabled\"`, the shadow lane is no-op" decision satisfy FR-032's "deployment-configurable as enabled or disabled" + "Slice 3 demonstrable loop MUST still complete without it" requirement? [Consistency, Research §4, Spec §FR-032]
- [ ] CHK180 Is the research.md §4 discrepancy-policy file structure (`benign_rules` vs. `uncertain_rules`) consistent with FR-031's "uncertain (rather than a benign formatting / casing difference)" classification — i.e., do the two rule sections map cleanly to the spec's two classifications? [Consistency, Research §4, Spec §FR-031]
- [ ] CHK181 Does the research.md §5 single-pipeline topology with three Pipecat FrameProcessor stages (`SignalWireMediaInput` → `RealtimeAIProviderBridge` → `PersonaSink`) fit FR-013's boundary constraints AND match the `pipecat-runtime.md` "What MUST NOT leak past this boundary" list (Pipecat FrameProcessor / Pipeline types confined to runtime)? [Consistency, Research §5, Spec §FR-013, Contract: pipecat-runtime.md]
- [ ] CHK182 Does the research.md §5 audio-codec decision (μ-law 8 kHz matching SignalWire's default voice codec) align with the SignalWire transport boundary — i.e., codec choice lives in the runtime/transport adapters and does not leak to the orchestrator/persona/Dataverse? [Boundary, Research §5, Spec §SC-015]
- [ ] CHK183 Does the research.md §6 shadow-lane "tee at SignalWireMediaInput" + separate asyncio.Task topology satisfy FR-029's "shadow lane MUST NOT block live conversation turns" guarantee by construction (separate asyncio.Task means no shared awaitable with the live pipeline)? [Consistency, Research §6, Spec §FR-029, Contract: shadow-stt-lane.md]
- [ ] CHK184 Are the research.md §7 three timeout decisions (abandonment 90s, silence-after-connection 30s, grace-window 3s) each independently configurable via distinct env vars / config keys, matching the spec's "three distinct, deployment-configurable timeouts" statement and FR-013 / FR-026 / FR-029? [Completeness, Research §7, Spec §FR-013, Spec §FR-026, Spec §FR-029]
- [ ] CHK185 Does the research.md §7 grace-window-of-`0` option correctly model the "write-back immediately; shadow always becomes `shadow_lane_truncated`" boundary case, consistent with FR-029's "if the grace window elapses without a discrepancy event, the write-back MUST proceed without it"? [Consistency, Research §7, Spec §FR-029]
- [ ] CHK186 Is the research.md §8 CLI shape (`opencloser run3`) consistent with the existing Slice 1 / Slice 2 CLI style (`opencloser run`, `opencloser run2`) AND with `cli-slice3.md`'s exit-code enumeration (0-7)? [Consistency, Research §8, Contract: cli-slice3.md]
- [ ] CHK187 Does the research.md §11 env-var enumeration (SIGNALWIRE_*, SLICE3_REALTIME_*, SLICE3_SHADOW_STT_*, DATAVERSE_*) cover every secret that any contract surface needs, with NO secret accidentally placed in `config/slice3.toml`? [Completeness, Research §11, Spec §FR-035]
- [ ] CHK188 Is the research.md §11 "Slice 2 vars reused" claim for the four DATAVERSE_* env vars consistent with the Slice 2 plan AND with the Slice 3 "Slice 2 Dataverse adapter reused unchanged" decision in plan.md §Technical Context? [Consistency, Research §11, Plan §Technical Context, Plan §Constitution Check]
- [ ] CHK189 Are the contract-test enumerations in `signalwire-transport.md` (`test_signature_verification_does_not_log_secret_or_body`, `test_no_signalwire_specifics_leak`) enforceable by an automated test — i.e., the tests can verify FR-008 / FR-035 / SC-015 / SC-018 via inspection of the recorded artifact and the consumed event stream? [Completeness, Contract: signalwire-transport.md, Spec §FR-008, Spec §FR-035, Spec §SC-015, Spec §SC-018]
- [ ] CHK190 Are the contract-test enumerations in `pipecat-runtime.md` (`test_no_pipecat_specifics_leak`, `test_runtime_identity_recorded_no_credentials`) enforceable by an automated test — i.e., the tests verify SC-015's "0 Pipecat-specific pipeline references" in the consumed PersonaOutput? [Completeness, Contract: pipecat-runtime.md, Spec §SC-015, Spec §FR-016]
- [ ] CHK191 Are the contract-test enumerations in `shadow-stt-lane.md` (`test_lane_does_not_block_live_turns`, `test_lane_does_not_write_crm`) enforceable by an automated test — i.e., the tests verify SC-013's "no observable slowdown" guarantee and FR-030's "MUST NOT independently write a CRM record"? [Completeness, Contract: shadow-stt-lane.md, Spec §SC-013, Spec §FR-030]
- [ ] CHK192 Does the research.md §12 testing-strategy "fixture-replay through the SignalWire transport + recorded-audio playback through the Pipecat runtime" approach match the spec's Deferred-to-Plan "Test posture for real calls" requirement? [Consistency, Research §12, Spec §Deferred to Implementation Plan > Test posture for real calls]
- [ ] CHK193 Does the research.md §12 "Real-call posture (not in CI): `make slice3-real-call-smoke`" decision align with the spec's "real call is expensive, regulated, and operator-visible" rationale from User Story 2's "Why this priority" paragraph? [Consistency, Research §12, Spec §User Story 2]
- [ ] CHK194 Does the research.md §13 demo-evidence checklist enumerate the same artifact set as the quickstart.md §7 demo-evidence checklist, with no artifact appearing in one place but not the other? [Consistency, Research §13, Quickstart §7]
- [ ] CHK195 Does the research.md §14 "reused Slice 1 / Slice 2 decisions (no re-research)" list correctly omit decisions that Slice 3 actually changes (e.g., transcript redaction extended in Round 2 Q10/Q11; resume coordinator extended in Round 2 Q6/Q12/Q13) — confirming no extended decision is mis-listed as reused-unchanged? [Consistency, Research §14, Spec §FR-022, Spec §FR-033]
- [ ] CHK196 Is the quickstart.md §1.2 secrets enumeration (SignalWire, real-time AI provider, shadow STT, Dataverse) consistent with research.md §11's env-var list — exactly the same env-var names, no drift? [Consistency, Quickstart §1.2, Research §11]
- [ ] CHK197 Does the quickstart.md §1.3 `[timeouts]` TOML section default values (abandonment 90, silence-after-connection 30, grace-window 3) match research.md §7's defaults exactly, with no drift between the operator-facing example and the deferred-to-plan defaults? [Consistency, Quickstart §1.3, Research §7]
- [ ] CHK198 Does the quickstart.md §3 expected-Dynamics-records table's `do_not_call` row ("Queue-status update: updated (DNC FIRST, Round 2 Q14)") align with the `crm-writeback-dnc-first.md` `assemble_writeback` Protocol's documented step ordering AND with `data-model.md §1.11`'s "FIRST in the write-back sequence on `do_not_call`" rule? [Consistency, Quickstart §3, Contract: crm-writeback-dnc-first.md, Data-Model §1.11]
- [ ] CHK199 Does the integration of the `RealtimeAIProvider.identity` property (returning `{provider_name, model_name, model_version}`) with the `data-model.md §1.12 RealtimeProviderSession` columns enable a deployment to swap providers (openai-realtime → google-realtime, etc.) without changing the data-model schema — preserving FR-013's "deployment-configurable" requirement? [Boundary, Contract: pipecat-runtime.md, Data-Model §1.12, Spec §FR-013]
- [ ] CHK200 Re-validating CHK154 from Round 2: does the integration between the rejected-auth audit log and the existing CallbacksAuditLog use distinct files (`rejected_auth_callbacks.jsonl` vs. `callbacks_audit.jsonl`), distinct SQLite tables (`rejected_auth_callbacks` vs. signalwire-callbacks), AND distinct entity definitions (data-model §1.3 vs. §1.4) — so the Round 2 Q9 "distinct" decision is enforced at three levels? [Consistency, Research §10, Data-Model §1.3, Data-Model §1.4, Spec §Clarifications Round 2 Q9]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] / [Conflict] indicate clarifying language is needed.
- Items marked [Assumption] / [Dependency] indicate where a contract relies on a stated assumption or an upstream integration state.
- ≥80% of items reference a spec section or a quality marker for traceability.
