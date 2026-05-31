# Performance Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the performance dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Latency Targets — Live Conversation Path

- [ ] CHK001 Is an end-to-end turn-latency target defined for the live conversation path (caller audio → SignalWire → Pipecat → configured real-time AI model → audio response)? [Completeness, Gap, Spec §FR-013]
- [ ] CHK002 Is the absence of a quantified live-conversation turn-latency target explicitly acknowledged in the spec (e.g., labelled as a [Gap] or routed to Deferred to Plan) rather than silently omitted? [Completeness, Gap, Spec §Deferred to Implementation Plan]
- [ ] CHK003 Are perceptual-quality requirements (e.g., maximum tolerable inter-turn pause, jitter ceiling, time-to-first-audio after `answered`) defined or marked deferred for the live conversation path? [Completeness, Gap, Spec §FR-013]
- [ ] CHK004 Is the cold-start cost (time from SignalWire `answered` event to first persona utterance) bounded, or explicitly deferred? [Completeness, Gap, Spec §FR-015]
- [ ] CHK005 Is the live-runtime degradation detection latency (how quickly the orchestrator must recognize trigger (a) provider error, (b) Pipecat crash, or (c) silence-after-connection timeout) quantified or marked deferred? [Measurability, Spec §FR-013]
- [ ] CHK006 Is the orchestrator's finalization latency (time from a live-runtime degradation trigger to the session being finalized as `failed` or `needs_human_review`) defined? [Measurability, Gap, Spec §FR-013]

## Latency Targets — Callback Handling

- [ ] CHK007 Is a maximum time-to-acknowledge for an incoming SignalWire status / media callback defined? [Completeness, Gap, Spec §FR-007]
- [ ] CHK008 Is a maximum time-to-finalize after the `completed` normalized event arrives defined? [Completeness, Gap, Spec §FR-017]
- [ ] CHK009 Is the latency between a `do_not_call` opt-out being recognized and the persona stopping the sales flow quantified or marked deferred? [Measurability, Spec §FR-015, §FR-024]
- [ ] CHK010 Is the maximum acceptable time for a duplicate-callback no-op decision (FR-021, FR-027) defined or marked deferred? [Performance, Gap, Spec §FR-021, §FR-027]

## Shadow-Lane Non-Blocking Guarantee

- [ ] CHK011 Is "MUST NOT block live conversation turns" (FR-029) operationalized via a named metric (e.g., maximum added per-turn latency in ms, maximum jitter contribution)? [Measurability, Spec §FR-029]
- [ ] CHK012 Is "no observable slowdown attributable to the shadow lane" (SC-013) defined with a measurable threshold (what counts as "observable") and a stated measurement method? [Measurability, Spec §SC-013]
- [ ] CHK013 Is the test harness, sampling method, or comparison procedure named for verifying SC-013 (e.g., paired runs with shadow STT enabled vs. disabled, statistical comparison criteria)? [Measurability, Gap, Spec §SC-013]
- [ ] CHK014 Is the shadow-lane timeout (beyond which the shadow lane is treated as failed for this session) defined or marked deferred? [Completeness, Gap, Spec §FR-029, §Edge Cases (Shadow STT lane fails or times out)]
- [ ] CHK015 Is the maximum permitted shadow-lane processing delay before discrepancy events for high-value fields are emitted defined? [Measurability, Gap, Spec §FR-030]
- [ ] CHK016 Is "MUST NOT slow the live call path" (FR-029) consistent with the "no observable slowdown" wording in SC-013 (i.e., are the FR's qualitative requirement and the SC's measurable outcome reconcilable)? [Consistency, Spec §FR-029, §SC-013]
- [ ] CHK017 Is the back-pressure / queueing behavior specified when the shadow lane cannot keep up with the live audio rate, in a way that preserves the non-blocking guarantee? [Completeness, Gap, Spec §FR-029]

## Retry Budget Timing

- [ ] CHK018 Is the bounded retry timing schedule (initial + up to 3 retries with 1s / 2s / 4s default backoff) stated as a single canonical schedule and not contradicted elsewhere? [Consistency, Spec §FR-022]
- [ ] CHK019 Is the optional `Retry-After` honoring rule (capped at 30s) consistent across FR-022 and any related requirement, with no ambiguity about whether the 30s cap overrides a smaller default or a larger server hint? [Consistency, Spec §FR-022]
- [ ] CHK020 Is the upper bound on total in-run retry wall time derivable from FR-022 (so a worst-case latency for write-back finalization can be computed)? [Measurability, Spec §FR-022]
- [ ] CHK021 Is the behavior when the bounded retry budget is exhausted (resume-on-re-invocation) defined with no latency claim that contradicts the bounded-retry budget? [Consistency, Spec §FR-022, §User Story 4 Scenario 7]
- [ ] CHK022 Are SignalWire-side callback retries (FR-007 / Story 4 / Story 7) distinguished from the in-run Dataverse write-back retry budget (FR-022), so the two timing schedules cannot be confused? [Clarity, Spec §FR-007, §FR-022]
- [ ] CHK023 Is the retry behavior for provider-rejected dial requests (FR-012, 4xx before placement) defined as no-retry (i.e., is there an explicit statement that 4xx-before-placement does not trigger the FR-022 retry budget)? [Consistency, Spec §FR-012, §FR-022]

## Timeout Configurability

- [ ] CHK024 Is the live-call abandonment timeout (FR-026) defined as deployment-configurable with the requirement on configurability stated, even though the default value is intentionally not pinned? [Completeness, Spec §FR-026, §Definitions (Live-call abandonment), §Deferred to Implementation Plan]
- [ ] CHK025 Is the live-runtime silence-after-connection / no-extraction-event timeout (FR-013 trigger (c)) defined as deployment-configurable, with the configurability stated as the requirement? [Completeness, Spec §FR-013, §Deferred to Implementation Plan]
- [ ] CHK026 Is the SignalWire connect-timeout and ringing-timeout configurability surface stated or routed to Deferred to Plan? [Completeness, Spec §Deferred to Implementation Plan]
- [ ] CHK027 Are the three Slice 3 timeouts (live-call abandonment, live-runtime silence-after-connection, SignalWire connect+ring) consistently described as deployment-configurable across the FR text, the Definitions, the Assumptions, and the Deferred-to-Plan list? [Consistency, Spec §FR-013, §FR-026, §Assumptions (Live-call abandonment timeout), §Deferred to Implementation Plan]
- [ ] CHK028 Is the silence-timeout's start condition unambiguous (does the timer start at the connected normalized event, at the first persona utterance, at the first caller utterance, or at the first extraction event)? [Ambiguity, Spec §FR-013]
- [ ] CHK029 Is it explicit that the silence-after-connection timeout is not applicable before the connected state (i.e., trigger (c) cannot fire pre-connection)? [Clarity, Spec §Edge Cases (Live model failure or runtime crash mid-call)]
- [ ] CHK030 Is the relationship between the live-call abandonment timeout and the silence-after-connection timeout defined (are they independent, ordered, or one is bounded by the other)? [Consistency, Gap, Spec §FR-013, §FR-026]
- [ ] CHK031 Is the configurability of the discrepancy-policy decision latency (when shadow STT escalates to `needs_human_review`) defined, or is it implicit / unstated? [Completeness, Gap, Spec §FR-031]

## Throughput Constraints

- [ ] CHK032 Is "exactly one Dataverse queue item per invocation" (FR-003) stated unambiguously as a hard upper bound on throughput per invocation? [Clarity, Spec §FR-003]
- [ ] CHK033 Is the single-item-per-invocation constraint consistent with the constitution-alignment statement ("Slice 3 processes exactly one Dataverse queue item per invocation")? [Consistency, Spec §Constitution Alignment, §FR-003]
- [ ] CHK034 Is the exclusion of batch calling, schedulers, campaign automation loops, and multi-worker coordination explicit and not contradicted by any performance / throughput statement elsewhere? [Consistency, Spec §FR-003, §Assumptions (Single campaign, single item)]
- [ ] CHK035 Is the concurrent-CLI-invocation behavior (second invocation observes `in_progress` and exits before dial — FR-003 / Edge Cases) defined without an implied performance claim that could conflict with the single-item-per-invocation rule? [Consistency, Spec §FR-003, §Edge Cases (Concurrent CLI invocation)]
- [ ] CHK036 Is there an explicit statement that no Slice 3 SLO is defined for sustained or peak call throughput (because throughput is bounded to one item per invocation)? [Completeness, Gap, Spec §FR-003]

## Callback Storm Tolerance

- [ ] CHK037 Is duplicate-callback tolerance (same provider event id replayed) defined with a stated invariant — no second normalized event, no second attempt increment, no second write-back — but with no implicit latency cap that would conflict with FR-007's "MUST record every callback (including duplicates)"? [Consistency, Spec §FR-007, §FR-021, §Story 4 Scenario 1]
- [ ] CHK038 Is out-of-order callback tolerance (e.g., `completed` before `answered`) defined with a stated invariant of a single coherent disposition, with no implicit performance claim about reordering window size? [Completeness, Spec §FR-005, §Story 4 Scenario 2, §Edge Cases (SignalWire status callbacks delivered out of order)]
- [ ] CHK039 Is the conflicting-late callback behavior (callback after disposition finalized — FR-027) defined with the no-mutation invariant, and is it consistent with the duplicate-callback invariant in FR-021? [Consistency, Spec §FR-021, §FR-027]
- [ ] CHK040 Is the worst-case number of audited callback rows per session (for storage / log-write throughput sizing) bounded or marked deferred? [Completeness, Gap, Spec §FR-007]
- [ ] CHK041 Is the callback-storm behavior under sustained high-rate duplicate or out-of-order delivery (e.g., a misconfigured SignalWire retry loop) defined or explicitly out of scope? [Completeness, Gap, Spec §FR-007, §FR-021]

## Vague-Adjective Audit

- [ ] CHK042 Is the spec free of unquantified performance adjectives ("fast", "quick", "responsive", "snappy", "smooth") used to describe the live conversation path? [Measurability, Spec §FR-013, §User Story 5]
- [ ] CHK043 Is "live" (in "live conversation path", "live model", "live runtime") used only as a path / mode identifier and never as a stand-in for an unstated latency requirement? [Clarity, Spec §Definitions (Live conversation path), §FR-013]
- [ ] CHK044 Is "non-blocking" (FR-029) defined or measurable rather than left as a qualitative adjective? [Measurability, Spec §FR-029]
- [ ] CHK045 Is "lightweight live verification" (FR-009 / FR-020, inherited from Slice 2) accompanied by a measurable bound or an explicit "inherited from Slice 2 with no new Slice 3 quantification" note? [Measurability, Spec §FR-009, §FR-020]
- [ ] CHK046 Is "transient" (in "transient Dataverse error", "transient SignalWire callback delivery failure") consistent with the FR-022 retry budget definition rather than implicitly requiring a separate timing guarantee? [Consistency, Spec §FR-022, §User Story 7]
- [ ] CHK047 Is "promptly", "soon", or any equivalent informal latency word absent from the spec, or — if present — explicitly mapped to a measurable requirement? [Measurability, Spec §entire spec]

## Scenario Class Coverage — Primary

- [ ] CHK048 Does the spec name a performance requirement (or explicit deferral) for the primary happy-path scenario (Story 1: dial → connected → ALF persona conversation → finalize → write-back)? [Completeness, Spec §User Story 1, §FR-013]
- [ ] CHK049 Does the spec name a performance requirement for the primary rehearsal scenario (Story 2: zero dial, zero mutation, readiness report produced)? [Completeness, Gap, Spec §User Story 2]

## Scenario Class Coverage — Alternate

- [ ] CHK050 Does the spec name a performance requirement (or explicit deferral) for an alternate path where shadow STT is enabled (Story 6) vs. disabled (FR-032)? [Completeness, Spec §FR-032, §SC-013]
- [ ] CHK051 Does the spec address performance under each transcript retention mode (full+redacted, summary-only, pointer-only) — e.g., is the redaction-pass latency considered? [Completeness, Gap, Spec §FR-033]

## Scenario Class Coverage — Exception / Error

- [ ] CHK052 Does the spec name a finalization-latency expectation when a live-runtime degradation trigger (FR-013 (a), (b), (c)) fires mid-call? [Completeness, Gap, Spec §FR-013, §Edge Cases (Live model failure or runtime crash mid-call)]
- [ ] CHK053 Does the spec name a maximum time within which a telephony readiness failure must be surfaced to the operator (before dial)? [Completeness, Gap, Spec §FR-011]
- [ ] CHK054 Does the spec name a maximum time within which a provider-rejected dial request (FR-012) is recognized and reported? [Completeness, Gap, Spec §FR-012]
- [ ] CHK055 Does the spec define the maximum acceptable time the queue item may remain in `in_progress` before live-call abandonment fires, expressed in terms of the configurable timeout? [Measurability, Spec §FR-026, §SC-012]

## Scenario Class Coverage — Recovery

- [ ] CHK056 Does the spec name a performance / latency requirement (or explicit deferral) for the resume-on-re-invocation path (FR-022, Story 7)? [Completeness, Gap, Spec §FR-022, §User Story 7]
- [ ] CHK057 Does the spec name how quickly an orchestrator restart between SignalWire's `completed` callback and Dataverse write-back must be resumable? [Completeness, Gap, Spec §User Story 7 Scenario 4, §Edge Cases (Live-call abandonment / orchestrator crash mid-call)]
- [ ] CHK058 Does the spec define a maximum total wall-clock recovery time (sum of in-run retry budget + resume re-invocation), or explicitly leave it deferred? [Completeness, Gap, Spec §FR-022]

## Scenario Class Coverage — Non-Functional

- [ ] CHK059 Are local artifact write-throughput requirements (transcript, callbacks audit log, shadow STT artifacts, run report) defined or marked deferred? [Completeness, Gap, Spec §FR-036, §FR-038]
- [ ] CHK060 Is the maximum acceptable end-to-end wall-clock for a single Slice 3 invocation (rehearsal mode and real-call mode) defined or explicitly deferred? [Completeness, Gap, Spec §SC-001, §SC-002]
- [ ] CHK061 Is the audit log retention floor (≥ 90 days, FR-022 / Assumptions) consistent with any implicit performance claim about log rotation or pruning latency? [Consistency, Spec §FR-022, §Assumptions (Local artifact retention)]
- [ ] CHK062 Is the FR-022 retention floor (≥ 90 days) explicitly described as a retention requirement, not a performance requirement, so it cannot be misread as a latency constraint? [Clarity, Spec §FR-022, §Assumptions (Local artifact retention)]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap]. Many Round 1 latency [Gap]s are now resolved by the new "Performance and latency targets" subsection under Deferred to Implementation Plan; those closures are called out explicitly.

### Deferred-to-Plan Subsection Completeness

- [ ] CHK063 Does the new "Performance and latency targets" subsection under Deferred to Implementation Plan enumerate end-to-end turn latency for the live conversation path as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK001 / CHK002)
- [ ] CHK064 Is time-to-first-audio after `answered` enumerated as a deferred item in the new subsection? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK003 / CHK004)
- [ ] CHK065 Is the live-call abandonment timeout default value enumerated as a deferred item in the new subsection? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK024 — confirms configurability is the requirement and the default is deferred)
- [ ] CHK066 Is the live-runtime silence-after-connection / no-extraction-event timeout default value enumerated as a deferred item in the new subsection? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK025)
- [ ] CHK067 Is the maximum time-to-acknowledge for an incoming SignalWire status / media callback enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK007)
- [ ] CHK068 Is the maximum time-to-finalize after the `completed` normalized event enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK008)
- [ ] CHK069 Is the duplicate-callback no-op decision latency (FR-021, FR-027) enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK010)
- [ ] CHK070 Is the orchestrator finalization latency after a live-runtime degradation trigger (FR-013) fires enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK006 / CHK052)
- [ ] CHK071 Is the shadow-lane processing budget and the threshold beyond which the shadow lane is treated as failed enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK014 / CHK015)
- [ ] CHK072 Is the back-pressure / queueing behavior when the shadow lane cannot keep up enumerated as a deferred item in a way that preserves the FR-029 non-blocking guarantee? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets, §FR-029] (closes CHK017)
- [ ] CHK073 Is the resume-on-re-invocation wall-clock budget (FR-022) enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK056 / CHK057 / CHK058)
- [ ] CHK074 Is the end-to-end wall-clock for a single Slice 3 invocation (rehearsal AND real-call mode) enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK060)
- [ ] CHK075 Are local artifact write-throughput requirements (transcript, callbacks audit log, shadow STT artifacts, run report) enumerated as deferred under each transcript retention mode? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets, §FR-033] (closes CHK051 / CHK059)
- [ ] CHK076 Is the test harness / sampling method / statistical comparison procedure for verifying SC-013's "no observable slowdown" enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets, §SC-013] (closes CHK013)
- [ ] CHK077 Is the maximum time within which a telephony readiness failure must be surfaced to the operator (FR-011) enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK053)
- [ ] CHK078 Is the maximum time within which a provider-rejected dial request (FR-012) is recognized and reported enumerated as a deferred item? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets] (closes CHK054)
- [ ] CHK079 Does the new subsection's leading paragraph explicitly state that the configurability and behavior contracts are stated in the requirements while specific numeric values belong to `/speckit.plan` or deployment configuration, so the deferral is principled rather than a silent omission? [Clarity, Spec §Deferred to Implementation Plan — Performance and latency targets]
- [ ] CHK080 Does the new subsection's closing statement ("Items not on this list … are either resolved in the requirements above, addressed by the preserved Slice 1 / Slice 2 contracts, or are sub-questions of one of the items above") cover every latency concept the Round 2 amendments introduce so no new latency [Gap] is silently left unowned? [Completeness, Spec §Deferred to Implementation Plan — Performance and latency targets]

### Q7 Grace-Window Timing Properties (FR-029 amendment)

- [ ] CHK081 Is the FR-029 post-finalization grace window's unit defined (seconds vs. milliseconds vs. unspecified-but-deployment-configurable)? [Ambiguity, Spec §FR-029]
- [ ] CHK082 Is the FR-029 post-finalization grace window described as deployment-configurable (paralleling the live-call abandonment timeout's configurability posture) and is the configurability the binding requirement? [Completeness, Spec §FR-029]
- [ ] CHK083 Is a maximum bound on the FR-029 grace window stated, or is the upper bound explicitly deferred to deployment configuration? [Completeness, Gap, Spec §FR-029]
- [ ] CHK084 Is the relationship between the FR-029 grace window and the FR-026 live-call abandonment timeout defined (are the two timeouts independent, ordered, or one nested inside the other)? [Consistency, Gap, Spec §FR-026, §FR-029]
- [ ] CHK085 Is the relationship between the FR-029 grace window and the FR-013 silence-after-connection timeout defined (the grace window starts at finalization which is after either the live-runtime degradation trigger or the normalized terminal event — is the ordering explicit)? [Consistency, Gap, Spec §FR-013, §FR-029]
- [ ] CHK086 Is the FR-029 grace window enumerated in the new "Performance and latency targets" deferred subsection (the grace-window value is a latency property introduced in Round 2 — does the deferral list cover it)? [Completeness, Gap, Spec §FR-029, §Deferred to Implementation Plan — Performance and latency targets]
- [ ] CHK087 Is the `shadow_lane_truncated` post-finalization audit-only event defined with a stated emission-latency expectation (or explicitly deferred), so an operator can reason about how long after finalization the event may still appear? [Completeness, Gap, Spec §FR-029]
- [ ] CHK088 Is the FR-029 grace window's effect on the SC-001 / SC-002 end-to-end wall-clock consistent (i.e., does the deferred end-to-end wall-clock target account for the grace window, or is the grace window explicitly outside the SC-001 / SC-002 envelope)? [Consistency, Gap, Spec §FR-029, §SC-001, §SC-002]

### Q11 Redaction-Pass Latency Per Artifact (FR-015 / FR-033 amendment)

- [ ] CHK089 Does the new "Performance and latency targets" deferred subsection's "redaction-pass latency contribution" deferral explicitly cover all four artifacts the Round 2 redaction policy now spans (full transcript, session-result summary, shadow STT transcript, shadow STT discrepancy records)? [Completeness, Gap, Spec §FR-015, §FR-033, §Deferred to Implementation Plan — Performance and latency targets]
- [ ] CHK090 Is the per-artifact redaction-pass latency contribution defined or explicitly deferred for the session-result summary (Round 2 added it to the redaction scope)? [Completeness, Gap, Spec §FR-033]
- [ ] CHK091 Is the per-artifact redaction-pass latency contribution defined or explicitly deferred for the shadow STT transcript (Round 2 added it to the redaction scope)? [Completeness, Gap, Spec §FR-033]
- [ ] CHK092 Is the per-artifact redaction-pass latency contribution defined or explicitly deferred for the shadow STT discrepancy records (Round 2 added it to the redaction scope)? [Completeness, Gap, Spec §FR-033]
- [ ] CHK093 Is the FR-015 PHI tag-and-redact pre-write requirement ("before any of those artifacts are written to disk") consistent with the redaction-pass latency deferral (i.e., the spec does not implicitly impose a hidden latency budget by requiring the tag-and-redact to complete before write)? [Consistency, Spec §FR-015, §FR-033]
- [ ] CHK094 Is the redaction-pass for the transcript pointer explicitly excluded from the latency-contribution envelope (consistent with FR-033's exclusion of pointer metadata from default-on redaction)? [Clarity, Spec §FR-033, §Deferred to Implementation Plan — Performance and latency targets]
- [ ] CHK095 Does the deferred performance bundle cover the cumulative redaction-pass latency (sum across all four redaction-covered artifacts) rather than only the per-artifact contribution? [Completeness, Gap, Spec §FR-033, §Deferred to Implementation Plan — Performance and latency targets]
- [ ] CHK096 Is the redaction-pass latency contribution's interaction with the FR-029 grace window defined (does the redaction-pass run within the grace window or outside it)? [Consistency, Gap, Spec §FR-029, §FR-033]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Research §7 three-timeout defaults (90s / 30s / 3s) defensibility for ALF outbound

- [ ] CHK097 Is the research §7 `SLICE3_ABANDONMENT_TIMEOUT_SEC` default of 90s defensibly chosen for the ALF outbound use case (i.e., is 90 seconds long enough to span typical ring + answer + opening exchange before a non-terminal silence indicates abandonment, and short enough to avoid leaving the queue item in `in_progress` for unacceptable wall-clock durations)? [Measurability, Ambiguity, Research §7, Spec §FR-026]
- [ ] CHK098 Is the research §7 `SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC` default of 30s defensibly chosen for the ALF outbound use case (i.e., does the 30s threshold reflect typical front-desk-staff response latency at an assisted-living facility while still firing quickly enough to escalate `script_truncated` before caller frustration)? [Measurability, Ambiguity, Research §7, Spec §FR-013]
- [ ] CHK099 Is the research §7 `SLICE3_GRACE_WINDOW_SEC` default of 3s defensibly chosen for the ALF outbound use case (i.e., is 3 seconds long enough for a deployment-typical shadow STT lane to deliver its last frame after live-call finalization, and short enough to avoid an operator-visible CRM write-back delay)? [Measurability, Ambiguity, Research §7, Spec §FR-029]

### Three-timeout independence — clear in plan + research + data-model + quickstart

- [ ] CHK100 Is the three-timeout independence (abandonment governs "no terminal event arrival"; silence-after-connection governs "no extraction event arrival AFTER connection"; grace window governs "post-finalization shadow-drain") clearly stated in research §7? [Clarity, Consistency, Research §7]
- [ ] CHK101 Is the same three-timeout independence preserved in data-model §6 state transitions (the abandonment timer fires inside the callback loop pre-finalization; the silence-after-connection timer fires inside the Pipecat pipeline post-connected; the grace window starts at `finalized_at` and is recorded as `grace_window_sec` on `Session`)? [Consistency, Data-Model §2.1, §6, Research §7]
- [ ] CHK102 Is the three-timeout independence preserved in quickstart §1.3 `[timeouts]` config block (each timeout has its own TOML key, its own FR citation, and an operator-readable comment naming the distinct trigger)? [Clarity, Quickstart §1.3, Research §7]
- [ ] CHK103 Does the plan's "Performance / Scale" section name the three timeouts independently and tie each to its FR (FR-026 / FR-013 / FR-029) without collapsing them into a single budget? [Consistency, Plan §Performance / Scale, Research §7]

### FR-029 non-blocking guarantee at boundary values (grace window = 0 and unbounded)

- [ ] CHK104 Does the FR-029 non-blocking guarantee survive a grace-window value of 0 (research §7 says "configurable to 0; write-back immediately; shadow always becomes `shadow_lane_truncated`") — is the data-model §1.8 `ShadowLaneTruncatedEvent` semantics preserved when EVERY connected session produces a truncated event? [Consistency, Gap, Research §7, Data-Model §1.8, Spec §FR-029]
- [ ] CHK105 Does the FR-029 non-blocking guarantee survive an unbounded (very large) grace-window value — is there a stated mechanism that prevents a hung shadow lane (no STT output, no timeout) from indefinitely delaying CRM write-back, or does the spec / plan rely on the shadow STT provider's own timeout? [Gap, Ambiguity, Research §7, Spec §FR-029, Contract: shadow-stt-lane]
- [ ] CHK106 Is the "no spec-mandated maximum" grace-window posture (research §7) consistent with FR-029's "MUST NOT block live-call finalization" requirement, i.e., does the spec / plan ever bound the grace-window's effect on overall invocation wall-clock (the operator's invocation does not return until either grace expires or shadow completes — is this acceptable)? [Consistency, Gap, Research §7, Spec §FR-029, §SC-001]
- [ ] CHK107 Is the boundary between "grace window = 0 always truncates" and "grace window > 0 may not truncate" reflected in the data-model §7 invariants (specifically the "Non-blocking shadow STT at finalization" invariant)? [Consistency, Data-Model §7, Research §7, Spec §FR-029]

### Deferred-to-Plan "Performance and latency targets" — full discharge by Research §7 + Plan

- [ ] CHK108 Is the spec's Deferred-to-Plan "Performance and latency targets" subsection fully discharged by the research §7 timeout decisions + the plan's "Performance / Scale" section's enumerated deferrals (turn latency, time-to-first-audio, abandonment-default, silence-default, callback-ack timing, finalize timing, shadow-lane processing budget, back-pressure behavior, resume wall-clock, artifact write throughput, end-to-end invocation wall-clock)? [Completeness, Spec §Deferred to Implementation Plan, Plan §Performance / Scale, Research §7] (re-validates CHK086/CHK089/CHK095)
- [ ] CHK109 Does the plan's "Performance / Scale" section name each Deferred-to-Plan latency target by name and route it either to a research §7 decision OR to a still-deferred-to-deployment configuration, so no latency target is silently dropped? [Traceability, Completeness, Plan §Performance / Scale, Spec §Deferred to Implementation Plan]
- [ ] CHK110 Are the three deferred latency surfaces NOT covered by research §7 (turn latency, time-to-first-audio, back-pressure behavior) explicitly handed to a deployment / runtime decision rather than a numeric default in `config/slice3.toml`, so the spec's "no numeric targets" posture is preserved? [Consistency, Plan §Performance / Scale, Research §7, §11]
- [ ] CHK111 Does the plan's Performance / Scale enumeration cover the cumulative redaction-pass latency (CHK095 from Round 2) for the four-artifact redaction scope, either by pinning a default or routing to the same deployment-configurable bucket as the timeouts? [Completeness, Gap, Plan §Performance / Scale, Spec §FR-033, Research §7]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- The spec intentionally does not pin a live-conversation turn-latency target (CHK001/CHK002): the most important amendment is either to add a measurable target or to explicitly route it to Deferred to Plan with a named owner.
- SC-013's "no observable slowdown attributable to the shadow lane" (CHK012/CHK013) is the most measurable existing performance claim and warrants a named measurement method.
- Round 2 (2026-05-25) added a "Performance and latency targets" subsection under Deferred to Implementation Plan; CHK063 – CHK080 verify this subsection's completeness and explicitly close many Round 1 latency [Gap]s.
- CHK081 – CHK096 cover NEW latency properties introduced by Round 2 (FR-029 grace window, FR-015 / FR-033 expanded redaction scope) that did not exist in Round 1.
- CHK097 – CHK111 are Round 3 post-plan validation (2026-05-25) covering: defensibility of the three research §7 timeout defaults for the ALF outbound use case, three-timeout independence across plan + research + data-model + quickstart, FR-029 non-blocking guarantee at boundary grace-window values (0 and unbounded), full discharge of the spec's Deferred-to-Plan "Performance and latency targets" subsection by research §7 + plan's "Performance / Scale" section.
- ≥80% of items reference a spec section or a quality marker for traceability.
