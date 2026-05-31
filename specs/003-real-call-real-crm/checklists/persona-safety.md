# Persona Safety Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the ALF appointment-setter persona-safety dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Disclosure (first utterance, acknowledgment, every connected call)

- [ ] CHK001 Is the AI-on-behalf-of-Medx disclosure required on the persona's first connected-call utterance defined unambiguously? [Completeness, Spec §FR-015, Spec §User Story 5 #1]
- [ ] CHK002 Is the disclosure requirement stated to apply to every connected call (no exceptions, no per-campaign waiver) and is that "every connected call" wording consistent between Constitution Alignment, FR-015, and User Story 5? [Consistency, Spec §Constitution Alignment "Safety and human handoff", Spec §FR-015, Spec §User Story 5 #1]
- [ ] CHK003 Is the canonical disclosure text owned by the persona module (not the live model, transport, or runtime) and is that ownership stated in both the Constitution Alignment block and FR-014? [Consistency, Spec §Constitution Alignment "Boundaries", Spec §FR-014]
- [ ] CHK004 Does the spec define what counts as "the persona's first connected-call utterance" for purposes of when the disclosure must be delivered (e.g., immediately on `connected`, before any sales utterance)? [Clarity, Spec §FR-015, Spec §User Story 5 #1]
- [ ] CHK005 Is the post-clarification "no explicit verbal acknowledgment required" behavior stated in FR-015 (continue after a brief pause; absence of opt-out = implicit acknowledgment; no escalation; no new audit flag; no new human-review reason)? [Completeness, Spec §Clarifications Session 2026-05-25 Q1, Spec §FR-015]
- [ ] CHK006 Is the "no new human-review reason for missing acknowledgment" rule stated consistently with the enumerated reason set so a reader cannot infer that silence might introduce a new reason code? [Consistency, Spec §FR-015, Spec §FR-014]
- [ ] CHK007 Is the "brief pause" before continuing after disclosure qualitatively defined or explicitly Deferred to Plan rather than left silently unspecified? [Clarity, Spec §FR-015, Ambiguity]
- [ ] CHK008 Does the spec explicitly state that the disclosure requirement is NOT relaxed by the live model (i.e., the live model cannot suppress or rephrase the disclosure away)? [Completeness, Spec §FR-014, Spec §FR-015, Gap]
- [ ] CHK009 Is the disclosure behavior on non-connected normalized events (`no_answer`, `voicemail`, `failed`) clarified as N/A (because there is no first connected utterance) so the requirement scope is unambiguous? [Clarity, Spec §FR-015, Spec §Edge Cases]
- [ ] CHK010 Does the spec resolve the relationship between the FR-015 "in the absence of a clear opt-out / DNC statement, continue after a brief pause" rule and the opt-out trigger set so a caller's ambiguous response is unambiguously classified as either opt-out or non-opt-out? [Clarity, Spec §FR-015, Spec §User Story 5 #3, Ambiguity]

## Allowed-claim categories

- [ ] CHK011 Is the allowed-claim category set named (or explicitly cross-referenced to the Slice 1 source of truth) so a reader does not have to infer it from the negative list of escalation triggers? [Completeness, Spec §FR-015, Spec §User Story 5 #2, Gap]
- [ ] CHK012 Is the negative list of disallowed claim categories (specific cost figures, clinical recommendations, comparisons to specific competitors, any PHI-related question) stated once and referenced everywhere it applies? [Consistency, Spec §User Story 5 #2, Spec §Edge Cases "Mid-call PHI / out-of-allowed-claim attempt"]
- [ ] CHK013 Is the persona module identified as the owner of the allowed-claim set (and not the live model or runtime) in FR-014 and the Constitution Alignment boundary block? [Consistency, Spec §Constitution Alignment "Boundaries", Spec §FR-014]
- [ ] CHK014 Is the behavior when the live model attempts an out-of-allowed-claim utterance defined (persona escalates, the conversation ends safely, one review Task with the enumerated reason) consistently in User Story 5 #2, FR-015, and the Edge Cases section? [Consistency, Spec §User Story 5 #2, Spec §FR-015, Spec §Edge Cases]
- [ ] CHK015 Is the behavior when the *contact* (not the live model) raises an out-of-allowed-claim topic defined symmetrically to the live-model case? [Completeness, Spec §Edge Cases "Mid-call PHI / out-of-allowed-claim attempt"]
- [ ] CHK016 Is the mapping from each disallowed-claim category to its enumerated escalation reason (`outside_allowed_claims`, `non_clinical_topic_escalation`, `phi_collection_risk`) defined or explicitly delegated to the persona module? [Clarity, Spec §User Story 5 #2, Spec §FR-015]
- [ ] CHK017 Is the persona's "stay non-clinical" obligation stated as a hard rule (not best-effort) in both Constitution Alignment and FR-015? [Consistency, Spec §Constitution Alignment "Safety and human handoff", Spec §FR-015]
- [ ] CHK018 Does the spec define how the persona module observes an out-of-allowed-claim attempt emitted by the live model, or is that mechanism explicitly Deferred to Plan? [Clarity, Spec §Deferred to Implementation Plan "Runtime and live-model details"]

## PHI exclusion

- [ ] CHK019 Is the "no resident/patient PHI collection" rule stated in Constitution Alignment, FR-014/FR-015, and the Compliance scope assumption with consistent wording? [Consistency, Spec §Constitution Alignment "Safety and human handoff", Spec §FR-015, Spec §Assumptions "Compliance scope"]
- [ ] CHK020 Is the PHI-collection-attempt escalation path defined (persona escalates with `phi_collection_risk` reason, conversation ends safely, one review Task created)? [Completeness, Spec §User Story 5 #2, Spec §Edge Cases "Mid-call PHI / out-of-allowed-claim attempt"]
- [ ] CHK021 Is "PHI" qualitatively defined for the persona's purposes (resident/patient health information) so the escalation rule is testable? [Clarity, Spec §Constitution Alignment "Safety and human handoff", Spec §Assumptions "Compliance scope"]
- [ ] CHK022 Is the PHI-exclusion rule stated as non-relaxable by the live model and is that non-relaxation cross-referenced from FR-014's "live model cannot override" rule? [Consistency, Spec §FR-014, Spec §FR-015]
- [ ] CHK023 Does the spec confirm that no transcript or shadow-STT artifact may capture PHI as a side effect, given the no-PHI-collection rule + redaction policy interaction? [Completeness, Spec §FR-033, Spec §Assumptions "Compliance scope", Gap]
- [ ] CHK024 Is the relationship between "no PHI collection" and the existing extraction schema's high-value fields (email, callback window, person reached name/role) explicitly stated so the extraction list cannot be misread as PHI-permissive? [Clarity, Spec §Definitions "High-value field", Spec §FR-014]
- [ ] CHK025 Is the Compliance scope assumption ("non-clinical ALF business-outreach demo, not HIPAA-class patient-care") cross-referenced from the persona-safety section so it is not buried only in Assumptions? [Consistency, Spec §Assumptions "Compliance scope", Gap]

## Opt-out / DNC trigger set

- [ ] CHK026 Is the opt-out / DNC trigger set named (or cross-referenced to the Slice 1 source of truth) so a reader does not have to infer it from acceptance scenarios? [Completeness, Spec §User Story 5 #3, Spec §FR-015, Gap]
- [ ] CHK027 Is the mid-call opt-out behavior (persona stops the sales flow before any further sales utterance; disposition `do_not_call`; Dataverse DNC / opt-out + queue-status fields updated; no callback or review Task) stated consistently between User Story 5 #3, FR-024, the Edge Cases "Mid-call opt-out / DNC" entry, and SC-006? [Consistency, Spec §User Story 5 #3, Spec §FR-024, Spec §Edge Cases, Spec §SC-006]
- [ ] CHK028 Is the "no follow-up Task on `do_not_call`" rule explicit in both FR-024 and SC-006 so the persona-safety stop cannot be accidentally weakened by a write-back addition? [Consistency, Spec §FR-024, Spec §SC-006]
- [ ] CHK029 Does the spec define how the persona distinguishes a "clear opt-out / DNC phrase matching the Slice 1 DNC trigger set" from an ambiguous response covered by the no-acknowledgment-required rule? [Clarity, Spec §User Story 5 #3, Spec §FR-015, Ambiguity]
- [ ] CHK030 Is the opt-out trigger set identified as owned by the persona module (and not modifiable by the live model)? [Consistency, Spec §FR-014, Spec §FR-015]
- [ ] CHK031 Does the spec confirm that the live model cannot introduce a new opt-out keyword that bypasses the persona's enumerated trigger set, or is that explicitly Deferred to Plan? [Completeness, Spec §FR-014, Gap]

## Deterministic disposition precedence authority

- [ ] CHK032 Is the persona's deterministic disposition precedence (the Slice 1 FR-036 rules) named as the authoritative selector for the final disposition in every place a disposition is discussed (FR-014, User Story 5 #4, SC-014, Edge Cases)? [Consistency, Spec §FR-014, Spec §User Story 5 #4, Spec §SC-014]
- [ ] CHK033 Is the SC-014 measurable outcome ("100% of connected real-call sessions use the deterministic Slice 1 FR-036 rules; 0 sessions had a final disposition determined by the live model alone") expressed in a way that can be verified by inspection of the session-result artifact and persona output? [Measurability, Spec §SC-014, Spec §FR-014]
- [ ] CHK034 Is the precedence rule stated as preserved verbatim from Slice 1 with no Slice-3-introduced override hooks (other than the explicitly additive `shadow_stt_discrepancy` escalation)? [Consistency, Spec §FR-014, Spec §FR-031, Spec §Assumptions "Slice 1 / Slice 2 contracts preserved"]
- [ ] CHK035 Does the spec resolve the relationship between the persona's deterministic rules and the orchestrator's discrepancy escalation hook (User Story 6 #4) so it is clear which module makes the final call? [Clarity, Spec §User Story 6 #4, Spec §FR-031, Ambiguity]
- [ ] CHK036 Is the precedence rule stated to apply even on degraded live-runtime paths (FR-013 triggers a/b/c → finalization as `script_truncated` / `failed`) so a degraded run cannot accidentally let the live model pick the disposition? [Completeness, Spec §FR-013, Spec §FR-014, Spec §Edge Cases "Live model failure or runtime crash mid-call"]
- [ ] CHK037 Is the precedence authority stated in both directions: live model MUST NOT pick the disposition AND live model MUST NOT veto a disposition the deterministic rules select? [Completeness, Spec §FR-014, Gap]
- [ ] CHK038 Does FR-014 explicitly bind the precedence authority to the persona module (not to the orchestrator alone) so a future plan cannot move it to the orchestrator and bypass persona ownership? [Clarity, Spec §FR-014, Spec §Constitution Alignment "Boundaries"]

## Human-review reason enumeration

- [ ] CHK039 Is the Slice 1 enumerated `human_review_reason` set (`outside_allowed_claims`, `non_clinical_topic_escalation`, `phi_collection_risk`, `script_truncated`) enumerated in one canonical location and cross-referenced everywhere a reason code is used? [Consistency, Spec §FR-014, Spec §FR-015, Spec §User Story 5 #2, Gap]
- [ ] CHK040 Is the additive `shadow_stt_discrepancy` entry explicitly described as additive (not a replacement) to the Slice 1 reason set in FR-031, FR-015, and the Preserved Slice 1 / Slice 2 Entities block? [Consistency, Spec §FR-031, Spec §FR-015, Spec §Key Entities "Preserved Slice 1 / Slice 2 Entities"]
- [ ] CHK041 Is the rule "existing Slice 1 reason codes MUST NOT be replaced or repurposed" stated in FR-031 and not weakened anywhere else? [Consistency, Spec §FR-031]
- [ ] CHK042 Does each escalation path (out-of-allowed-claim, PHI attempt, non-clinical topic, script truncation, shadow-STT uncertain discrepancy, live-runtime degradation per FR-013) name the exact reason code it produces? [Completeness, Spec §FR-013, Spec §FR-015, Spec §FR-031, Spec §Edge Cases]
- [ ] CHK043 Is the `script_truncated` reason defined for both (i) caller-hangup mid-conversation with insufficient signal (User Story 4 #5) and (ii) live-runtime degradation after connection (FR-013 trigger c, plus a/b after connection) without ambiguity about which trigger applied? [Clarity, Spec §FR-013, Spec §User Story 4 #5, Ambiguity]
- [ ] CHK044 Does the spec confirm that the live model cannot expand the reason set (FR-014) and cannot replace a reason code, in both FR-014 and FR-031 wording? [Consistency, Spec §FR-014, Spec §FR-031]
- [ ] CHK045 Is the SC-005 success criterion ("a human-review reason code drawn from the Slice 1 enumerated set OR `shadow_stt_discrepancy`") aligned exactly with the enumerated set in FR-014 + FR-031? [Consistency, Spec §SC-005, Spec §FR-014, Spec §FR-031]

## Live-model boundary (cannot override)

- [ ] CHK046 Is the live-model-cannot-override rule stated in both directions in FR-014: (a) MUST NOT change which disposition is selected for a given extracted state; (b) MUST NOT expand or replace the human-review reason set? [Completeness, Spec §FR-014]
- [ ] CHK047 Is the live model's permitted scope (produces conversation turns and extraction events) defined positively as well as negatively so a reader knows what the live model IS allowed to do? [Clarity, Spec §FR-014, Spec §User Story 5 "Why this priority"]
- [ ] CHK048 Is the boundary stated to apply even when the live model is the configured real-time AI provider (Key Entities "Configured Real-time AI Provider") so a vendor-specific path cannot smuggle disposition authority back in? [Consistency, Spec §FR-014, Spec §Key Entities "Configured Real-time AI Provider"]
- [ ] CHK049 Is the boundary stated to apply to BOTH the live model AND the Pipecat runtime (i.e., neither runtime nor model may mutate persona authority)? [Completeness, Spec §FR-013, Spec §FR-014, Gap]
- [ ] CHK050 Is the SC-015 boundary success criterion ("0 SignalWire-specific / Pipecat-specific / real-time-AI-provider / shadow-STT specifics in orchestrator, eligibility evaluator, persona module, or Dataverse adapter") aligned with the persona-safety boundary so vendor leakage cannot dilute persona authority? [Consistency, Spec §SC-015, Spec §FR-014]
- [ ] CHK051 Does the spec confirm that the live model cannot suppress disclosure or rewrite the disclosure language away (a direct corollary of FR-014's persona-owned disclosure language)? [Completeness, Spec §FR-014, Spec §FR-015, Gap]
- [ ] CHK052 Is the boundary stated as observable in audit (i.e., a reviewer can read the session-result + run report and confirm that the disposition came from the deterministic rules, not the live model)? [Measurability, Spec §FR-016, Spec §FR-036, Spec §SC-014]

## Persona version / runtime / model identity audit

- [ ] CHK053 Is the requirement to record persona version on every Slice 3 session stated in FR-016 and reflected in the run-report field list (FR-036)? [Consistency, Spec §FR-016, Spec §FR-036]
- [ ] CHK054 Is the requirement to record runtime/model identity (provider name + model version) on every session stated in FR-016 and the "Configured Real-time AI Provider" entity? [Consistency, Spec §FR-016, Spec §Key Entities "Configured Real-time AI Provider"]
- [ ] CHK055 Is the requirement to record model configuration relevant to audit (e.g., model name and version) stated with enough specificity to be testable? [Measurability, Spec §FR-016]
- [ ] CHK056 Is the rule that secrets MUST NOT be recorded stated in FR-016 and reinforced by FR-035 (no-secrets-in-artifacts)? [Consistency, Spec §FR-016, Spec §FR-035, Spec §SC-018]
- [ ] CHK057 Is the operator-identity recording rule (local session + run report only, NOT propagated into Dataverse, no new Dataverse field added) stated unambiguously in FR-016 and FR-036? [Consistency, Spec §FR-016, Spec §FR-036, Spec §Clarifications Session 2026-05-25 Q3]
- [ ] CHK058 Is the SC-017 demo-evidence criterion explicit that a reviewer can read the run report and identify persona version + runtime/model identity without reading source code? [Measurability, Spec §SC-017, Spec §FR-036]
- [ ] CHK059 Does the spec define how the persona version is incremented or pinned across runs so an audit can distinguish two runs that used different persona versions? [Clarity, Spec §FR-016, Gap]
- [ ] CHK060 Is the persona-version audit requirement stated to apply even when the run is rehearsal / readiness mode (so a rehearsal artifact carries the same persona-version provenance as a real-call run)? [Completeness, Spec §FR-002, Spec §FR-016, Gap]

## Persona module ownership of safety-critical surfaces

- [ ] CHK061 Is the persona module identified as the sole owner of disclosure language, allowed claims, extraction schema, deterministic disposition rules, and escalation reasons in both Constitution Alignment and FR-014? [Consistency, Spec §Constitution Alignment "Boundaries", Spec §FR-014]
- [ ] CHK062 Is the persona module identified as preserved across Slice 1 → Slice 3 with no Slice-3-introduced surface changes other than the additive `shadow_stt_discrepancy` reason? [Consistency, Spec §FR-014, Spec §Assumptions "Persona policy preserved", Spec §Key Entities "Preserved Slice 1 / Slice 2 Entities"]
- [ ] CHK063 Is the persona-module / Pipecat-runtime split explicit (Pipecat owns audio bridging; persona owns safety + disposition) so a future plan cannot collapse them and reintroduce vendor leakage? [Consistency, Spec §FR-013, Spec §FR-014, Spec §Key Entities "Pipecat Realtime Audio Runtime"]
- [ ] CHK064 Is the persona's authority over escalation reasons stated to apply even when an escalation is triggered by an orchestrator-level signal (FR-013, FR-031) rather than a persona-observed event? [Completeness, Spec §FR-013, Spec §FR-031, Gap]

## Scenario classes

### Primary

- [ ] CHK065 Is the primary persona-safety scenario (connected call → disclosure → safe sales flow → deterministic disposition) covered end-to-end across User Story 1, User Story 5, and FR-014/FR-015? [Coverage, Spec §User Story 1, Spec §User Story 5, Spec §FR-014, Spec §FR-015]
- [ ] CHK066 Does the spec confirm that the primary path applies the disclosure on every connected call regardless of disposition outcome? [Consistency, Spec §FR-015, Spec §User Story 5 #1]

### Alternate

- [ ] CHK067 Is the alternate path "interested caller verifies email but declines callback" covered with a defined disposition (`interested_email_captured`) and Task behavior? [Coverage, Spec §User Story 1 #2, Spec §FR-017]
- [ ] CHK068 Is the alternate path "interested caller agrees to callback window" covered with a defined disposition (`interested_callback_requested`) and Task behavior? [Coverage, Spec §User Story 1 #1, Spec §SC-003]
- [ ] CHK069 Is the alternate path "caller declines all engagement (not interested)" covered with `not_interested` and the per-disposition write-back behavior? [Coverage, Spec §FR-017, Spec §FR-020]

### Exception / Error

- [ ] CHK070 Is the exception path "live model attempts out-of-allowed-claim utterance" covered with escalation reason mapping (`outside_allowed_claims`)? [Coverage, Spec §User Story 5 #2, Spec §Edge Cases "Mid-call PHI / out-of-allowed-claim attempt"]
- [ ] CHK071 Is the exception path "live model or contact raises PHI question" covered with `phi_collection_risk`? [Coverage, Spec §User Story 5 #2, Spec §Edge Cases]
- [ ] CHK072 Is the exception path "non-clinical topic escalation" covered with `non_clinical_topic_escalation`? [Coverage, Spec §User Story 5 #2, Spec §Edge Cases]
- [ ] CHK073 Is the exception path "clear opt-out / DNC mid-call" covered with `do_not_call` disposition and no follow-up Task? [Coverage, Spec §User Story 5 #3, Spec §FR-024, Spec §Edge Cases "Mid-call opt-out / DNC"]
- [ ] CHK074 Is the exception path "wrong-number response" covered (so a wrong-number contact does not produce a sales callback)? [Coverage, Spec §User Story 5 "Independent Test", Spec §FR-017]
- [ ] CHK075 Is the exception path "ambiguous caller / insufficient signal" covered with `needs_human_review` / `script_truncated`? [Coverage, Spec §User Story 4 #5, Spec §User Story 5 "Independent Test"]

### Recovery

- [ ] CHK076 Is the recovery path "live model failure or runtime crash AFTER connection" finalized as `needs_human_review` / `script_truncated` (preserving safety)? [Coverage, Spec §FR-013, Spec §Edge Cases "Live model failure or runtime crash mid-call"]
- [ ] CHK077 Is the recovery path "live model failure BEFORE connection" finalized as `failed` with a runtime-failure reason and NO false connected-call activity (preserving the disclosure-on-every-connected-call invariant)? [Coverage, Spec §FR-013, Spec §Edge Cases]
- [ ] CHK078 Is the recovery path "silence-after-connection / no-extraction-event timeout" finalized as `needs_human_review` / `script_truncated` (preserving safety and bounding the conversation)? [Coverage, Spec §FR-013, Spec §Edge Cases]
- [ ] CHK079 Is the recovery path "caller hangs up after sufficient signal" finalized via the deterministic disposition rules using available extraction (no live-model override)? [Coverage, Spec §User Story 4 #5, Spec §FR-014]

### Non-Functional

- [ ] CHK080 Is the SC-014 100%-deterministic-disposition criterion expressed as a measurable invariant verifiable from session-result + run-report artifacts? [Measurability, Spec §SC-014, Spec §FR-016]
- [ ] CHK081 Is the persona-version audit requirement expressed as a measurable invariant (every session has a persona version + runtime/model identity recorded)? [Measurability, Spec §FR-016, Spec §FR-036]
- [ ] CHK082 Is the no-secrets-in-artifacts invariant (FR-035, SC-018) expressed as a measurable property and confirmed to apply to persona/runtime identity recording? [Measurability, Spec §FR-035, Spec §SC-018, Spec §FR-016]
- [ ] CHK083 Is the SC-015 boundary invariant (no vendor-specific event shapes in persona module / orchestrator / eligibility evaluator / Dataverse adapter) expressed as inspectable by boundary tests? [Measurability, Spec §SC-015]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendment to FR-015 (caller-volunteered PHI escalation + tag-and-redact pre-write invariant) and the new "Mid-call PHI / out-of-allowed-claim attempt" Edge Case wording. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap] or [Ambiguity].

### Caller-volunteered PHI vs. live-model-attempted PHI (Q11 — FR-015)

- [ ] CHK084 Does the amended FR-015 make the boundary explicit between (a) the persona refusing to ASK for PHI and (b) the caller VOLUNTEERING PHI despite the refusal — i.e., are both cases now covered with distinct escalation wording? [Completeness, Spec §FR-015, §Clarifications Session 2026-05-25 (Round 2) Q6]
- [ ] CHK085 Is the `phi_collection_risk` reason code used CONSISTENTLY for BOTH (a) the live-model-attempts-to-collect case (per FR-015 / Round 1 CHK032) AND (b) the caller-volunteers case (per the Round 2 amendment), without introducing a separate reason code for the volunteered case (preserves the Slice 1 enumerated reason set per FR-014 / FR-031, closes Round 1 CHK020)? [Consistency, Spec §FR-014, §FR-015, §FR-031]
- [ ] CHK086 Is the rule that the Slice 1 `human_review_reason` enumeration is NOT expanded by the Round 2 amendment stated unambiguously (only `shadow_stt_discrepancy` remains the lone additive entry — closes Round 1 CHK040, CHK045)? [Consistency, Spec §FR-014, §FR-015, §FR-031, §Key Entities: Preserved Slice 1 / Slice 2 Entities]
- [ ] CHK087 Does the Edge Cases "Mid-call PHI / out-of-allowed-claim attempt" entry now explicitly cover BOTH triggers (live model attempts to collect PHI AND contact volunteers PHI) with the same escalation reason and the redaction-before-write requirement (closes Round 1 CHK015, CHK032)? [Consistency, Spec §FR-015, §Edge Cases: Mid-call PHI / out-of-allowed-claim attempt]
- [ ] CHK088 Is the "call MAY continue or end per the persona's existing decision rules" qualifier on the PHI-volunteered case stated in FR-015 and cross-referenced from the Edge Cases entry so a reader cannot infer the call MUST end? [Clarity, Spec §FR-015, §Edge Cases]
- [ ] CHK089 Does the spec define how the persona OBSERVES caller-volunteered PHI (vs. live-model-attempted PHI) so the escalation trigger is testable, or is the observation mechanism explicitly Deferred to Plan (parallels Round 1 CHK018)? [Clarity, Spec §FR-015, §Deferred to Implementation Plan "Runtime and live-model details", Gap]

### PHI tag-and-redact pre-write invariant in persona artifacts (Q11 — FR-015 + FR-033)

- [ ] CHK090 Does the amended FR-015 require the default-on redaction policy to tag-and-redact the PHI-bearing utterance in the FULL transcript, the session-result `summary`, the shadow STT transcript, AND the shadow STT discrepancy records before any of those artifacts are written to disk (closes Round 1 CHK023, CHK036)? [Completeness, Spec §FR-015, §FR-033, §Clarifications Session 2026-05-25 (Round 2) Q5]
- [ ] CHK091 Is the redaction-before-write ordering stated as a hard MUST (no PHI-bearing utterance reaches disk in any of the four covered artifact classes) consistent with Round 1 CHK028's hard-ordering rule for default-on redaction generally? [Consistency, Spec §FR-015, §FR-033]
- [ ] CHK092 Is the "tag-and-redact" requirement defined sufficiently to be testable for persona-safety review — i.e., a reviewer can confirm a PHI utterance was both tagged (so PHI-volunteered sessions can be counted / audited) AND redacted (so PHI content does not persist)? [Measurability, Spec §FR-015, Gap]
- [ ] CHK093 Does the spec require that the PHI-volunteered case is OBSERVABLY DISTINCT in the audit artifacts AND the run report from a non-PHI call (per FR-015 final sentence) so an auditor can count PHI-volunteered sessions and validate they were escalated? [Measurability, Spec §FR-015, §FR-036]
- [ ] CHK094 Is the tag-and-redact requirement consistent with the persona module's authority over the extraction schema (FR-014) — i.e., the persona OWNS what is tagged as PHI vs. what is extracted as a high-value field (closes Round 1 CHK024)? [Consistency, Spec §FR-014, §FR-015, §Definitions: High-value field]

### Persona-authority preservation on the PHI-volunteered path (Q11 — FR-014, FR-015)

- [ ] CHK095 Is the "persona escalates `needs_human_review` reason `phi_collection_risk`" rule on the PHI-volunteered path stated as PERSONA-DRIVEN (not orchestrator-driven or model-driven) so Round 1 CHK046 (live-model-cannot-override) is preserved on the new path? [Consistency, Spec §FR-014, §FR-015]
- [ ] CHK096 Does the spec confirm that the live model cannot suppress or relax the PHI escalation on the volunteered-PHI case (parallel to Round 1 CHK033 for the attempt-to-collect case)? [Completeness, Spec §FR-014, §FR-015]
- [ ] CHK097 Is the deterministic disposition precedence (FR-014 / Slice 1 FR-036, Round 1 CHK032–CHK038) preserved when the escalation reason is `phi_collection_risk` regardless of which trigger produced it (live model attempt vs. caller-volunteered)? [Consistency, Spec §FR-014, §FR-015]
- [ ] CHK098 Does the persona's "MAY continue or end per existing decision rules" wording on the volunteered case preserve the deterministic precedence (i.e., the continue-or-end decision still flows through the persona's deterministic rules, not the live model's preference)? [Consistency, Spec §FR-014, §FR-015]

### Disposition-precedence interplay on PHI-volunteered case (Q11 — FR-014, FR-015, FR-024)

- [ ] CHK099 Does the spec resolve the interplay between a PHI-volunteered escalation (`needs_human_review` / `phi_collection_risk`) and a contemporaneous mid-call opt-out (`do_not_call`) — i.e., which disposition wins under the Slice 1 deterministic precedence (parallels Round 1 CHK029 for opt-out vs. ambiguous response)? [Clarity, Spec §FR-014, §FR-015, §FR-024, Ambiguity]
- [ ] CHK100 Is the per-disposition write-back behavior on a PHI-volunteered escalation (`needs_human_review` ⇒ one review Task with `phi_collection_risk` reason) consistent with the Slice 1 / Slice 2 review-task contract (Round 1 CHK020, CHK073, CHK032)? [Consistency, Spec §FR-015, §FR-020, §FR-031]
- [ ] CHK101 Does the spec confirm that the PHI-volunteered escalation produces EXACTLY ONE review Task (not multiple — e.g., not one per PHI utterance) so a single-session-with-multiple-PHI-utterances does not produce duplicate review Tasks (closes a Round 1-style ambiguity parallel to CHK028 for shadow-STT)? [Clarity, Spec §FR-015, §FR-020, Gap]
- [ ] CHK102 Is the persona's escalation behavior on the PHI-volunteered case OPERATOR-VISIBLE via the run report (closes Round 1 CHK038) and visible in the audit artifacts (per the FR-015 "observably distinct" requirement)? [Consistency, Spec §FR-015, §FR-036]

### Shadow-STT discrepancy interplay (Q11 — FR-015, FR-030, FR-031)

- [ ] CHK103 Does the spec require that a PHI-volunteered case detected ONLY by the shadow STT lane (live transcript missed it, shadow caught it) still triggers the `phi_collection_risk` escalation, or is it routed through the `shadow_stt_discrepancy` escalation path — i.e., which reason code wins? [Clarity, Spec §FR-015, §FR-030, §FR-031, Ambiguity]
- [ ] CHK104 Is the redact-before-write invariant for shadow STT transcript + shadow STT discrepancy records (closes Round 1 CHK029, CHK037) stated as applying even when the PHI content is the very thing being compared between live and shadow values (the discrepancy record cannot become a back-channel for unredacted PHI)? [Completeness, Spec §FR-015, §FR-030, §FR-033, §FR-034]

### Cross-cutting Round 2 consistency

- [ ] CHK105 Does the amended FR-015 wording for the PHI-volunteered case preserve the existing first-utterance disclosure requirement (Round 1 CHK001–CHK010) so the disclosure invariant cannot regress on PHI-escalated sessions? [Consistency, Spec §FR-015]
- [ ] CHK106 Is the Compliance scope assumption ("non-clinical ALF business-outreach demo; not HIPAA-class patient-care") cross-referenced from FR-015's PHI-volunteered amendment so the new PHI handling rule cannot be misread as a clinical-workflow concession (closes Round 1 CHK025, CHK035)? [Consistency, Spec §Assumptions "Compliance scope", §FR-015]
- [ ] CHK107 Are the resume-operator format ("resumed by X, original operator Y") additions to FR-016 / FR-036 (Round 2 Q7) consistent with the persona-version + runtime/model identity recording requirements (Round 1 CHK053–CHK060) so a resume run still records persona authority alongside both operators? [Consistency, Spec §FR-016, §FR-036]
- [ ] CHK108 Does the spec confirm that the persona module's surface (disclosure language, allowed claims, extraction schema, deterministic disposition rules, escalation reasons) is unchanged by the Round 2 amendments — only the BEHAVIOR on caller-volunteered PHI is sharpened, not the persona's enumerated reason set (Round 1 CHK061–CHK064)? [Consistency, Spec §FR-014, §FR-015, §Constitution Alignment "Boundaries"]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### PersonaRuntime Protocol signature preserves Slice 1 conceptual contract

- [ ] CHK109 Does the `PersonaRuntime.run(session_context, conversation) → PersonaOutput` signature (Contract: pipecat-runtime) preserve the Slice 1 conceptual contract verbatim — i.e., the input/output types are the same and no Pipecat-specific argument is introduced (re-validates Round 1 persona-contract preservation against the plan)? [Consistency, Contract: pipecat-runtime, Plan §Summary, Spec §FR-013]
- [ ] CHK110 Is the `PersonaRuntime` Protocol stated as the Slice 1 conceptual contract's Slice 3 implementation rather than a parallel surface — so an orchestrator written for Slice 1's persona contract consumes the Pipecat runtime without code changes (boundary preservation per Plan §Constitution Check III)? [Consistency, Contract: pipecat-runtime, Plan §Constitution Check, Spec §FR-013]
- [ ] CHK111 Does the plan place `PersonaRuntime` in `src/opencloser/runtime/base.py` (Plan §Project Structure) parallel to `transport/base.py`, so the runtime abstraction is symmetric with the transport abstraction and the Slice 1 boundaries remain crisp? [Consistency, Plan §Project Structure, Spec §FR-013]

### Deterministic disposition precedence enforced by contract test

- [ ] CHK112 Does the contract test `test_live_model_extraction_does_not_override_disposition` (Contract: pipecat-runtime) enforce FR-014's deterministic-disposition-precedence rule by construction — i.e., a live-model `ExtractionEvent` claiming `disposition=foo` is ignored and the Slice 1 deterministic rules pick the final disposition? [Measurability, Contract: pipecat-runtime, Spec §FR-014]
- [ ] CHK113 Is the persona module's authority over the `human_review_reason` enumeration preserved by the contract test's "MUST NOT be expanded or replaced by the live model" assertion (Contract: pipecat-runtime Required Behavior #2) — and is the lone additive entry (`shadow_stt_discrepancy`, emitted from the shadow lane) reconciled with this assertion (re-validates Round 1 CHK086 against the plan)? [Consistency, Contract: pipecat-runtime, Spec §FR-014, Spec §FR-031]
- [ ] CHK114 Does the contract test surface a scenario where the live model emits BOTH a turn AND an extraction event that disagree on disposition, so the test fixture exercises the precedence in a realistic (not degenerate) way? [Measurability, Contract: pipecat-runtime, Gap]

### Disclosure on every connected call (FR-015) via `test_first_utterance_includes_disclosure`

- [ ] CHK115 Does the contract test `test_first_utterance_includes_disclosure` (Contract: pipecat-runtime) enforce FR-015's "AI-on-behalf-of-Medx disclosure on every connected call" rule for the first connected-call utterance — i.e., the test fails if the first utterance lacks the canonical disclosure? [Measurability, Contract: pipecat-runtime, Spec §FR-015]
- [ ] CHK116 Is the "canonical AI-on-behalf-of-Medx disclosure" language sourced from the persona module (not the runtime) so the Pipecat runtime delegation to the persona for first-utterance content preserves Slice 1 persona authority (re-validates Round 1 disclosure-language ownership against the plan)? [Consistency, Contract: pipecat-runtime, Plan §Project Structure `persona/`, Spec §FR-015]
- [ ] CHK117 Does the contract test cover the case where the call connects but the persona's first utterance is interrupted by an immediate caller opt-out — does the disclosure-on-every-connected-call requirement still apply if the connection lifetime is sub-disclosure (potential edge-case gap)? [Clarity, Contract: pipecat-runtime, Spec §FR-015, Gap]

### No-acknowledgment-required (Round 1 Q1) via `test_no_acknowledgment_required`

- [ ] CHK118 Does the contract test `test_no_acknowledgment_required` (Contract: pipecat-runtime) enforce Round 1 Q1 by asserting that caller silence after disclosure does NOT trigger any escalation and the conversation continues — i.e., the test fails if any silence-after-disclosure escalation is observed? [Measurability, Contract: pipecat-runtime, Spec §FR-015]
- [ ] CHK119 Is the "absence of an opt-out → implicit acknowledgment" rule (Contract: pipecat-runtime Required Behavior in `run()` docstring) stated consistently with FR-015's "no explicit verbal acknowledgment from the caller" wording so the two surfaces cannot diverge? [Consistency, Contract: pipecat-runtime, Spec §FR-015]
- [ ] CHK120 Does the contract test distinguish "caller silence" from "live-runtime silence" — i.e., a brief caller-silence pause is implicit acknowledgment, while a `SilenceAfterConnectionTimeout` elapse is a degradation trigger — so the two paths are not conflated? [Clarity, Contract: pipecat-runtime, Spec §FR-013, Spec §FR-015]

### Caller-volunteered PHI (Round 2 Q11) via `test_caller_volunteered_phi_escalates_and_redacts`

- [ ] CHK121 Does the contract test `test_caller_volunteered_phi_escalates_and_redacts` (Contract: pipecat-runtime) enforce BOTH the `phi_collection_risk` escalation AND the PHI tag-and-redact pass running on all four artifact types BEFORE write (re-validates Round 2 CHK090, CHK105–CHK106 against the plan)? [Measurability, Contract: pipecat-runtime, Spec §FR-015, Spec §FR-033]
- [ ] CHK122 Is the four-artifact-type coverage (full transcript + session-result summary + shadow STT transcript + shadow STT discrepancy records) stated identically in Contract: pipecat-runtime Required Behavior #4 and Data-Model §2.5 so a reader cannot infer one artifact class is exempt? [Consistency, Contract: pipecat-runtime, Data-Model §2.5, Spec §FR-015]
- [ ] CHK123 Does the contract test cover the PHI-volunteered case when shadow STT is DISABLED — i.e., the test still verifies redaction in transcript + summary (the two artifact types still produced) and does NOT spuriously fail on the absent shadow artifacts (re-validates Round 1 disabled-lane behavior against the new contract test)? [Completeness, Contract: pipecat-runtime, Spec §FR-032, Gap]
- [ ] CHK124 Is the PHI-volunteered case's "observably distinct in the audit artifacts and the run report" requirement (Contract: pipecat-runtime Required Behavior #4) testable via the run report's enumerated fields (Research §9) so an auditor can count PHI-volunteered sessions (re-validates Round 2 CHK093 against the run-report schema)? [Measurability, Contract: pipecat-runtime, Research §9]

### Runtime/model identity property (Contract: pipecat-runtime `identity`) ↔ FR-016

- [ ] CHK125 Does the `RealtimeAIProvider.identity` property (Contract: pipecat-runtime) return `{provider_name, model_name, model_version}` consistent with FR-016's recording requirements and Data-Model §1.12's `RealtimeProviderSession` columns — i.e., the property surface and the persisted-row surface align? [Consistency, Contract: pipecat-runtime, Data-Model §1.12, Spec §FR-016]
- [ ] CHK126 Is the `runtime_name` / `runtime_version` pair (Data-Model §1.12) sourced from the `PersonaRuntime` implementation (always `"pipecat"` for Slice 3) rather than the `RealtimeAIProvider.identity` property — i.e., does the plan distinguish runtime identity (the persona runtime layer) from provider identity (the AI provider layer) clearly enough that both are auditable separately? [Clarity, Data-Model §1.12, Contract: pipecat-runtime]
- [ ] CHK127 Does the contract test `test_runtime_identity_recorded_no_credentials` (Contract: pipecat-runtime) cover BOTH the recording of the five-field identity AND the exclusion of credential strings, so FR-016 + FR-035 are jointly enforced by one test? [Measurability, Contract: pipecat-runtime, Spec §FR-016, Spec §FR-035]
- [ ] CHK128 Is the runtime/model identity surface preserved on resume — i.e., `Session.runtime_identity` columns (Data-Model §3) are not overwritten by a resuming invocation's runtime/model identity if they differ (Round 2 Q12 parallel for runtime identity)? [Clarity, Data-Model §3, Spec §FR-016, Gap]

### Live-runtime degradation triggers (Round 1 Q4) ↔ research.md §7 + plan.md `runtime/pipecat/degradation.py`

- [ ] CHK129 Does the live-runtime degradation trigger mapping (Plan §Project Structure `runtime/pipecat/degradation.py` comment, Research §7) enforce the FR-013 Round 1 Q4 three-trigger set — (a) `RealtimeProviderError`, (b) `PipecatRuntimeError`, (c) `SilenceAfterConnectionTimeout` — with the correct pre-connected / post-connected disposition mapping (re-validates Round 1 FR-013 coverage against the plan)? [Completeness, Plan §Project Structure, Research §7, Contract: pipecat-runtime, Spec §FR-013]
- [ ] CHK130 Is the pre-connected disposition mapping (`failed` with runtime-failure reason; no false Phone Call activity) stated consistently in Contract: pipecat-runtime Required Behavior #5, Data-Model §6 state-transition table, and quickstart.md so a reader cannot conclude one says `needs_human_review` while another says `failed`? [Consistency, Contract: pipecat-runtime, Data-Model §6, Spec §FR-013]
- [ ] CHK131 Is the post-connected disposition mapping (`needs_human_review` with reason `script_truncated`) consistent across the three triggers — i.e., (a) and (b) and (c) all map to the SAME post-connected disposition, not three different ones (parallel to Round 1 CHK032)? [Consistency, Contract: pipecat-runtime, Spec §FR-013]
- [ ] CHK132 Does the silence-after-connection trigger (c) only fire AFTER `connected` (Contract: pipecat-runtime, Research §7) — i.e., the silence timer is not running pre-connection, so the pre-connected disposition cannot accidentally be reached via trigger (c) (re-validates Round 1 silence-trigger-after-connect-only against the plan)? [Completeness, Research §7, Contract: pipecat-runtime, Spec §FR-013]
- [ ] CHK133 Does the contract test set (`test_provider_error_pre_connected_yields_failed`, `test_provider_error_post_connected_yields_needs_review`, `test_runtime_crash_post_connected_yields_needs_review`, `test_silence_timeout_yields_needs_review`) cover every (trigger, connect-state) combination required by FR-013, or is any cell missing? [Completeness, Contract: pipecat-runtime, Spec §FR-013, Gap]
- [ ] CHK134 Is the `SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC` default of 30s (Research §7) consistent with the silence-after-connection trigger's intended use as a degradation signal — i.e., is the default chosen so a normal pause-for-thought does not trip it (operationally defensible)? [Clarity, Research §7, Spec §FR-013, Ambiguity]

### Persona module ownership preserved under Pipecat runtime delegation (Constitution V)

- [ ] CHK135 Is the persona module's ownership of disclosure language, allowed claims, extraction schema, disposition rules, and escalation reasons (Plan §Constitution Check III, Plan §Project Structure `persona/`) preserved when the Pipecat runtime delegates to the persona for first-utterance content, extraction-event handling, and disposition selection (re-validates Round 1 persona-authority against the runtime-delegation pattern)? [Consistency, Plan §Constitution Check, Plan §Project Structure, Contract: pipecat-runtime]
- [ ] CHK136 Does the plan keep the persona's `disposition_rules.py` unchanged (Plan §Project Structure comment "disposition_rules.py unchanged") so the deterministic disposition precedence is invariant under the Slice 3 runtime delegation — i.e., the live model produces inputs to the rules, not the rules themselves? [Consistency, Plan §Project Structure, Spec §FR-014]
- [ ] CHK137 Is the `escalation.py` additive `shadow_stt_discrepancy` entry (Plan §Project Structure) the ONLY additive change to the persona's enumerated escalation reasons — and is that single-additive-entry rule cross-referenced from Data-Model §5 ("escalation extends with the additive `shadow_stt_discrepancy` entry") so the rule is asserted in both the plan and the data model? [Consistency, Plan §Project Structure, Data-Model §5, Spec §FR-031]
- [ ] CHK138 Does the persona's `extraction.py` PHI-volunteered handling hook (Plan §Project Structure comment "extraction.py adds PHI-volunteered handling per Round 2 Q11") preserve the Slice 1 extraction schema — i.e., the hook adds detection of caller-volunteered PHI without changing the high-value-field extraction schema (Data-Model §1.7 enumerated `field` set)? [Consistency, Plan §Project Structure, Data-Model §1.7, Spec §FR-014]
- [ ] CHK139 Is the "live model never sets the disposition" rule (Research §5 `PersonaSink` description, Contract: pipecat-runtime Required Behavior #2) preserved at the Pipecat pipeline boundary — i.e., the `PersonaSink` is the single hand-off point and it routes through the persona's deterministic rules, not the live model's preference? [Consistency, Research §5, Contract: pipecat-runtime, Spec §FR-014]

### Cross-cutting plan-side persona-safety consistency

- [ ] CHK140 Is the allowed-claim guardrail (Contract: pipecat-runtime Required Behavior #3) enforced by an explicit contract test (`test_disallowed_claim_escalates`) so the live model attempting an out-of-allowed-claim is observably blocked at the persona-escalation boundary (re-validates Round 1 CHK020 against the plan)? [Measurability, Contract: pipecat-runtime, Spec §FR-015]
- [ ] CHK141 Does the plan reconcile the FR-014 "live model MUST NOT change which disposition is selected" rule with the FR-013 live-runtime degradation triggers — i.e., a degradation trigger CAN change the disposition (to `failed` or `needs_human_review`), but only via the orchestrator-driven finalization path, not via a live-model-emitted extraction event? [Consistency, Contract: pipecat-runtime, Spec §FR-013, Spec §FR-014, Ambiguity]
- [ ] CHK142 Is the persona's "MAY continue or end per the persona's existing decision rules" wording on the PHI-volunteered case (Contract: pipecat-runtime Required Behavior #4) preserved consistent with Round 2 CHK088 — i.e., the continue-or-end decision is persona-deterministic, not live-model-driven? [Consistency, Contract: pipecat-runtime, Spec §FR-015]
- [ ] CHK143 Does the Pipecat runtime's first-utterance disclosure delivery rule (Contract: pipecat-runtime Required Behavior #1) coexist with the FR-013 trigger (b) pre-connected `PipecatRuntimeError` mapping — i.e., a pre-connected runtime crash cannot create a "connected call without a disclosure" anomaly because the pre-connected disposition is `failed` and no Phone Call activity is created? [Consistency, Contract: pipecat-runtime, Spec §FR-013, Spec §FR-015]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate two or more reasonable interpretations are possible and clarification is needed.
- ≥80% of items reference a spec section or a quality marker for traceability.
