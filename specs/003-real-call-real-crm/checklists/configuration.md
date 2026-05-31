# Configuration Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the configuration / deployment-configurable surface dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Configurable-Knob Enumeration

- [ ] CHK001 Is the real-call / write-enabled flag enumerated as a configurable knob (CLI flag or equivalent deliberate action)? [Completeness, Spec §FR-001, §FR-037, §Definitions (Real-call / write-enabled mode)]
- [ ] CHK002 Is the rehearsal / readiness mode toggle enumerated as a configurable knob with its default behavior (no flag = rehearsal) explicitly stated? [Completeness, Spec §FR-002, §FR-037]
- [ ] CHK003 Are the three transcript retention modes (full-transcript-with-redaction, summary-only, pointer-only) enumerated as a configurable knob? [Completeness, Spec §FR-033, §Assumptions (Transcript retention modes)]
- [ ] CHK004 Is the shadow STT enable/disable toggle enumerated as a configurable knob? [Completeness, Spec §FR-028, §FR-032, §FR-037, §Assumptions (Shadow STT toggle and discrepancy policy)]
- [ ] CHK005 Is the shadow STT discrepancy policy (which differences are benign vs. uncertain) enumerated as a configurable knob? [Completeness, Spec §FR-030, §FR-031, §Assumptions (Shadow STT toggle and discrepancy policy), §Deferred to Implementation Plan (Shadow STT details)]
- [ ] CHK006 Is the live-call abandonment timeout enumerated as a configurable knob? [Completeness, Spec §FR-026, §Definitions (Live-call abandonment), §Assumptions (Live-call abandonment timeout), §Deferred to Implementation Plan]
- [ ] CHK007 Is the live-runtime silence-after-connection / no-extraction-event timeout enumerated as a configurable knob? [Completeness, Spec §FR-013, §Deferred to Implementation Plan]
- [ ] CHK008 Is the SignalWire connect-timeout and ringing-timeout enumerated as configurable knobs (or explicitly out of scope)? [Completeness, Gap, Spec §Deferred to Implementation Plan]
- [ ] CHK009 Are SignalWire account / credentials enumerated as configurable knobs? [Completeness, Spec §FR-008, §FR-009, §Definitions (Telephony readiness check)]
- [ ] CHK010 Is the source caller-ID number enumerated as a configurable knob (with the "authorized for outbound dialing" requirement attached)? [Completeness, Spec §FR-009, §Definitions (Telephony readiness check)]
- [ ] CHK011 Are the SignalWire status callback URL and media callback URL enumerated as configurable knobs? [Completeness, Spec §FR-007, §FR-009, §Definitions (Telephony readiness check)]
- [ ] CHK012 Is the persona/runtime configuration (campaign-to-persona/runtime mapping) enumerated as a configurable knob? [Completeness, Spec §FR-009, §FR-037, §Definitions (Telephony readiness check)]
- [ ] CHK013 Are the configured real-time AI model provider identity (provider name, model name, model version) and its credentials enumerated as configurable knobs? [Completeness, Spec §FR-013, §FR-016, §Key Entities (Configured Real-time AI Provider), §Deferred to Implementation Plan (Runtime and live-model details)]
- [ ] CHK014 Are the shadow STT provider identity and credentials enumerated as configurable knobs? [Completeness, Spec §FR-028, §FR-035, §Deferred to Implementation Plan (Shadow STT details)]
- [ ] CHK015 Are Dataverse credentials enumerated as a configurable knob? [Completeness, Spec §FR-020, §FR-035]
- [ ] CHK016 Is the Dataverse field-mapping artifact (the Slice 2 verified mapping) enumerated as a configurable / deployment artifact? [Completeness, Spec §FR-020, §FR-009, §Key Entities (Preserved Slice 1 / Slice 2 Entities: CRM Field Mapping Artifact)]
- [ ] CHK017 Are the callback Task owner/team and the review Task owner/team mappings enumerated as configurable knobs? [Completeness, Spec §FR-009, §FR-020, §Definitions (Telephony readiness check)]
- [ ] CHK018 Is the redaction policy (default-on `[REDACTED]` or its configured replacement) enumerated as a configurable knob? [Completeness, Spec §FR-033, §FR-035]
- [ ] CHK019 Is the local audit retention floor (≥ 90 days, or longer when configured) enumerated as a configurable knob (with the ≥ 90-day floor stated as a hard minimum)? [Completeness, Spec §FR-022, §Assumptions (Local artifact retention)]
- [ ] CHK020 Are the campaign selector and the queue-item selector enumerated as required operator inputs (per-invocation configuration)? [Completeness, Spec §FR-003, §FR-037]
- [ ] CHK021 Is the invoking operator identity (OS user or CLI-provided operator identifier) enumerated as captured-but-not-Dataverse-propagated configuration / context? [Completeness, Spec §FR-016, §FR-036]

## Defaults vs Deployment-Configuration

- [ ] CHK022 Is the rehearsal / readiness mode default (FR-002, FR-037) stated unambiguously as the default when the real-call / write-enabled flag is omitted? [Clarity, Spec §FR-002, §FR-037, §SC-011]
- [ ] CHK023 Is the default-on redaction policy (FR-033) stated as default-on with the configurable-replacement allowance explicit? [Clarity, Spec §FR-033]
- [ ] CHK024 Is the bounded retry default (1s / 2s / 4s, plus 3 retries) stated as a default that can be overridden or as a fixed schedule? (Slice 2 inherited — the spec describes it as a default.) [Ambiguity, Spec §FR-022]
- [ ] CHK025 Is the optional `Retry-After` cap of 30s stated as a default cap that can be overridden, or as a fixed cap? [Ambiguity, Spec §FR-022]
- [ ] CHK026 For each knob whose default value is intentionally not pinned in the spec (live-call abandonment timeout, silence-after-connection timeout, SignalWire connect/ring timeouts, shadow STT discrepancy policy, real-time AI provider choice, shadow STT provider choice), is the "deployment configuration" status explicit so the absence of a default is not silently ambiguous? [Completeness, Spec §FR-013, §FR-026, §Assumptions, §Deferred to Implementation Plan]
- [ ] CHK027 Is the local audit retention floor's "≥ 90 days" default vs. "longer when configured" override path described unambiguously? [Clarity, Spec §FR-022, §Assumptions (Local artifact retention)]
- [ ] CHK028 Is the shadow STT default state (enabled vs. disabled out of the box) stated, or explicitly left to deployment configuration with no default? [Completeness, Gap, Spec §FR-028, §FR-032]
- [ ] CHK029 Is the transcript retention default mode (full+redacted vs. summary-only vs. pointer-only) stated, or explicitly left to deployment configuration with no default? [Completeness, Gap, Spec §FR-033]

## Required vs Optional Configuration

- [ ] CHK030 Is each configurable knob's required-vs-optional status unambiguous (e.g., SignalWire credentials = required for any real-call run; shadow STT = optional / off-able)? [Clarity, Spec §FR-009, §FR-028, §FR-032]
- [ ] CHK031 Is it explicit that SignalWire credentials, source caller-ID number, destination phone, callback URLs, persona/runtime mapping, verified Dataverse mapping, callback/review Task owner mapping, and call-window/DNC/attempt eligibility are ALL required for the telephony readiness check to pass? [Completeness, Spec §FR-009, §Definitions (Telephony readiness check)]
- [ ] CHK032 Is the Slice 2 verified-mapping requirement explicit as a prerequisite (i.e., the mapping must be verified, not merely present)? [Completeness, Spec §FR-009, §FR-020]
- [ ] CHK033 Is it explicit which knobs are per-invocation operator inputs (campaign selector, queue-item selector, run mode, shadow STT enable/disable flag) vs. per-deployment configuration (SignalWire credentials, Dataverse credentials, owner mappings, retention modes)? [Clarity, Spec §FR-003, §FR-037]
- [ ] CHK034 Is the shadow STT enable/disable knob's level (per-invocation flag vs. per-deployment configuration vs. both) consistent across FR-032 and FR-037? [Consistency, Spec §FR-032, §FR-037]

## Credentials Surface

- [ ] CHK035 Are SignalWire credentials, real-time AI provider credentials, shadow STT provider credentials, and Dataverse credentials each enumerated as configurable, with the no-secrets-in-artifacts requirement attached? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK036 Is the SignalWire callback authentication mechanism (e.g., signature verification per FR-008) enumerated as a configurable surface, with its secret material explicitly excluded from logs? [Completeness, Spec §FR-008, §FR-035]
- [ ] CHK037 Is the "MUST NOT log secrets associated with the verification mechanism" requirement (FR-008) consistent with the broader no-secrets-in-artifacts requirement (FR-035, SC-018)? [Consistency, Spec §FR-008, §FR-035, §SC-018]
- [ ] CHK038 Is the credentials-rotation / credentials-suspension behavior (FR-009 readiness re-check on next pre-dial; mid-run in-flight calls allowed to complete per Edge Cases) defined in a way that does not contradict the credentials-required configuration model? [Consistency, Spec §FR-009, §Edge Cases (SignalWire credentials or source number unauthorized / suspended mid-run)]
- [ ] CHK039 Is the credentials surface for the real-time AI model provider distinct from the credentials surface for the shadow STT provider, so they cannot be confused for one set of credentials? [Clarity, Spec §FR-013, §FR-028, §Key Entities (Configured Real-time AI Provider)]

## Mapping & Owner Configuration

- [ ] CHK040 Is the Dataverse field-mapping artifact (Slice 2 mapping artifact) enumerated as a deployment artifact that MUST be verified before any real-call / write-enabled run? [Completeness, Spec §FR-009, §FR-020]
- [ ] CHK041 Is the callback Task owner/team mapping enumerated separately from the review Task owner/team mapping (or, if combined, is the combination explicit)? [Clarity, Spec §FR-009, §FR-020, §SC-003, §SC-005]
- [ ] CHK042 Is the behavior when callback owner / review owner mapping is missing or invalid (telephony readiness failure exits before dial, no Phone Call activity, no attempt consumed) stated consistently across FR-009, FR-011, and SC-010? [Consistency, Spec §FR-009, §FR-011, §SC-010]
- [ ] CHK043 Is the campaign-to-persona/runtime mapping configurable surface enumerated, including how it links a campaign selector input to a persona version and a runtime/model identity? [Completeness, Spec §FR-009, §FR-013, §FR-016]
- [ ] CHK044 Is the relationship between the persona version, the runtime/model identity, and the configured real-time AI provider clear in the configuration model? [Clarity, Spec §FR-013, §FR-016, §Key Entities (Pipecat Realtime Audio Runtime), §Key Entities (Configured Real-time AI Provider)]

## Toggle Behavior (Real-Call / Shadow STT / Retention)

- [ ] CHK045 Is the real-call / write-enabled toggle's behavior reversible across invocations (i.e., the same operator can run rehearsal then real-call against the same item) without state leakage between modes? [Completeness, Gap, Spec §FR-001, §FR-002, §User Story 2]
- [ ] CHK046 Is it explicit that the real-call / write-enabled flag unblocks BOTH SignalWire dialing AND Dataverse mutation (FR-001), not one without the other? [Clarity, Spec §FR-001, §Definitions (Real-call / write-enabled mode)]
- [ ] CHK047 Is the shadow STT toggle's effect on the run report (FR-032: "MUST always state whether shadow STT was enabled") consistent with the run-report content requirement in FR-036? [Consistency, Spec §FR-032, §FR-036]
- [ ] CHK048 When shadow STT is disabled, is it explicit that the Slice 3 demonstrable loop still completes (FR-032)? [Completeness, Spec §FR-032, §User Story 6 Scenario 5]
- [ ] CHK049 Is the transcript retention toggle's effect on artifact emission (no full transcript file when summary-only is configured per FR-033) consistent with the no-secrets-in-artifacts requirement (FR-035) and the redaction-runs-first requirement (FR-033)? [Consistency, Spec §FR-033, §FR-035]
- [ ] CHK050 Is the retention toggle's effect on the shadow STT artifact (FR-034: same retention policy as live transcript; discrepancy records retained even when transcript retention is summary-only) consistent and unambiguous? [Consistency, Spec §FR-033, §FR-034]
- [ ] CHK051 Is the resume-after-real-call behavior when transcript retention disables the transcript artifact (Edge Cases: "the absence of a transcript file is not an error") consistent with the configuration model? [Consistency, Spec §Edge Cases (Resume after a real call when retention policy disables the transcript artifact), §FR-033]

## Consistency with Deferred-to-Plan

- [ ] CHK052 Does every "deployment-configurable" claim in the FR text have either a stated default or a corresponding entry in the Deferred to Implementation Plan section? [Consistency, Spec §FR-013, §FR-026, §FR-028, §FR-030, §FR-031, §FR-032, §FR-033, §Deferred to Implementation Plan]
- [ ] CHK053 Are all knobs the spec marks as "deployment configuration" with no pinned default actually listed in the Deferred to Implementation Plan section, with no orphans? [Consistency, Spec §Deferred to Implementation Plan]
- [ ] CHK054 Is the Deferred-to-Plan entry for "the connect-timeout, ringing-timeout, live-call abandonment timeout, and live-runtime silence-after-connection / no-extraction-event timeout default values" complete and unambiguous about which knobs are configurable surface vs. fixed-in-spec? [Clarity, Spec §Deferred to Implementation Plan]
- [ ] CHK055 Is the "CLI flag and configuration-file shape that enables real-call / write-enabled mode" Deferred-to-Plan entry consistent with the FR-001 / FR-037 requirement that an explicit flag is REQUIRED (i.e., the SHAPE is deferred, not the requirement itself)? [Consistency, Spec §FR-001, §FR-037, §Deferred to Implementation Plan]
- [ ] CHK056 Is the Deferred-to-Plan entry for the shadow STT provider choice, credentials surface, and discrepancy policy aligned with the FR-028 / FR-030 / FR-031 / FR-032 configurability requirements (no contradiction about what's locked in spec vs. deferred)? [Consistency, Spec §FR-028, §FR-030, §FR-031, §FR-032, §Deferred to Implementation Plan (Shadow STT details)]
- [ ] CHK057 Is the Deferred-to-Plan entry for the real-time AI model provider choice and credentials surface aligned with FR-013 / FR-016 (provider IDENTITY is recorded as an audit field; the CHOICE of provider is deferred)? [Consistency, Spec §FR-013, §FR-016, §Deferred to Implementation Plan (Runtime and live-model details)]
- [ ] CHK058 Is the run-report file format / schema / naming Deferred-to-Plan entry consistent with FR-036's required run-report content (the WHAT is fixed; the HOW is deferred)? [Consistency, Spec §FR-036, §Deferred to Implementation Plan (Run-report and artifact layout)]
- [ ] CHK059 Are there any knobs implied by the FR text (e.g., the shadow STT timeout per FR-029 / Edge Cases) that are NOT listed in Deferred to Plan and ALSO have no default in the spec? [Gap, Spec §FR-029, §Edge Cases (Shadow STT lane fails or times out), §Deferred to Implementation Plan]
- [ ] CHK060 Is the configurability surface consistent between the Functional Requirements section, the Definitions section, the Assumptions section, and the Deferred to Implementation Plan section (no knob is described differently in two places)? [Consistency, Spec §Definitions, §Requirements, §Assumptions, §Deferred to Implementation Plan]

## Scenario Class Coverage — Primary

- [ ] CHK061 Is the configuration model complete enough to execute the primary real-call / write-enabled run (Story 1) without referring to undocumented configuration? [Completeness, Spec §User Story 1, §FR-009, §FR-037]
- [ ] CHK062 Is the configuration model complete enough to execute the primary rehearsal run (Story 2) without referring to undocumented configuration? [Completeness, Spec §User Story 2, §FR-002, §FR-037]

## Scenario Class Coverage — Alternate

- [ ] CHK063 Is the configuration model complete for the alternate "shadow STT enabled" path (Story 6) and the alternate "shadow STT disabled" path (FR-032)? [Completeness, Spec §FR-028, §FR-032, §User Story 6]
- [ ] CHK064 Is the configuration model complete for each transcript retention mode (full+redacted, summary-only, pointer-only)? [Completeness, Spec §FR-033]
- [ ] CHK065 Is the configuration model complete for the alternate "fixture-replay debugging in Slice 3" path (Slice 1 / Slice 2 fixtures usable for debugging per Key Entities note)? [Completeness, Gap, Spec §Key Entities (Preserved Slice 1 / Slice 2 Entities)]

## Scenario Class Coverage — Exception / Error (Behavior When Required Config Is Missing)

- [ ] CHK066 Is the behavior defined when SignalWire credentials are missing (telephony readiness failure, no dial, no attempt consumed, no Phone Call activity per FR-011 / SC-010 / Story 3 Scenario 2)? [Completeness, Spec §FR-009, §FR-011, §SC-010, §User Story 3 Scenario 2]
- [ ] CHK067 Is the behavior defined when the source caller-ID number is missing or unauthorized (Story 3 Scenario 2 / Edge Cases)? [Completeness, Spec §FR-009, §FR-011, §Edge Cases (SignalWire credentials or source number unauthorized / suspended mid-run)]
- [ ] CHK068 Is the behavior defined when the destination phone is missing / blank / non-E.164 (FR-010 hard pre-dial block / Story 3 Scenario 3)? [Completeness, Spec §FR-010, §SC-009, §User Story 3 Scenario 3]
- [ ] CHK069 Is the behavior defined when the SignalWire status or media callback URL is missing or unreachable (Story 3 Scenario 4)? [Completeness, Spec §FR-009, §FR-011, §User Story 3 Scenario 4]
- [ ] CHK070 Is the behavior defined when the campaign-to-persona/runtime mapping is missing (Story 3 / FR-009)? [Completeness, Spec §FR-009, §FR-011, §User Story 3]
- [ ] CHK071 Is the behavior defined when the Dataverse mapping is unverified or incomplete (Story 3 Scenario 1 / FR-009 / FR-020)? [Completeness, Spec §FR-009, §FR-020, §User Story 3 Scenario 1]
- [ ] CHK072 Is the behavior defined when the callback Task owner mapping is missing or invalid (Story 3 / FR-009)? [Completeness, Spec §FR-009, §FR-011, §SC-010]
- [ ] CHK073 Is the behavior defined when the real-time AI provider credentials are missing (does this fall under telephony readiness, persona/runtime configuration check, or a separate gate)? [Completeness, Gap, Spec §FR-009, §FR-013]
- [ ] CHK074 Is the behavior defined when the shadow STT provider credentials are missing while shadow STT is enabled? [Completeness, Gap, Spec §FR-028, §FR-032]
- [ ] CHK075 Is the behavior defined when the redaction policy configuration is malformed or missing (does the run fall back to default-on, or fail closed)? [Completeness, Gap, Spec §FR-033, §FR-035]
- [ ] CHK076 Is the behavior defined when the live-call abandonment timeout or silence-after-connection timeout is unconfigured (does the run use an in-spec default, fail closed, or fail open)? [Completeness, Gap, Spec §FR-013, §FR-026]

## Scenario Class Coverage — Recovery

- [ ] CHK077 Is the configuration model consistent with the resume-on-re-invocation path (FR-022): the same configuration values must be present at resume as at the original invocation? [Consistency, Spec §FR-022, §User Story 7]
- [ ] CHK078 Is the credentials-suspended-mid-run recovery path (Edge Cases) consistent with the readiness-check model — i.e., a re-check on the next pre-dial without disrupting an in-flight connected call? [Consistency, Spec §Edge Cases (SignalWire credentials or source number unauthorized / suspended mid-run), §FR-009]
- [ ] CHK079 Is the Dataverse-metadata-drift-between-rehearsal-and-real-call recovery (Edge Cases) consistent with the verified-mapping configuration model (Slice 2 lightweight live verification re-checks)? [Consistency, Spec §Edge Cases (Dataverse metadata drift detected between rehearsal and real-call run), §FR-009, §FR-020]

## Scenario Class Coverage — Non-Functional

- [ ] CHK080 Is the no-secrets-in-artifacts requirement enumerated for EVERY configurable credentials surface (SignalWire, real-time AI provider, shadow STT provider, Dataverse, callback verification mechanism)? [Completeness, Spec §FR-008, §FR-035, §SC-018]
- [ ] CHK081 Is the operator-identity capture (FR-016) explicit about NOT being a Dataverse-side configurable field (so the configurability rule is "local-only, never propagated to Dynamics")? [Clarity, Spec §FR-016, §FR-036]
- [ ] CHK082 Is the run-report's required content (FR-036) covered by the configuration model (every required field — run mode, session ID, operator identity, real provider call ID, persona version, runtime/model identity, final disposition, per-write-back-operation status, shadow STT flag & discrepancy summary, callbacks audit row counts — has a configurable / observable source)? [Completeness, Spec §FR-036]
- [ ] CHK083 Is the local artifact retention floor (≥ 90 days) consistent with the configuration model's expectation that retention is configurable upward but not downward? [Consistency, Spec §FR-022, §Assumptions (Local artifact retention)]
- [ ] CHK084 Is the auto-deletion ban (Assumptions: "Pruning is a manual operator action; the application MUST NOT auto-delete audit artifacts") consistent with the retention-knob configurability model? [Consistency, Spec §Assumptions (Local artifact retention)]
- [ ] CHK085 Is the deployment-configuration scope explicit that NO Slice-3-specific Dataverse field is added (FR-016: operator identity is local-only; FR-020: Slice 2 mapping surface unchanged)? [Consistency, Spec §FR-016, §FR-020]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

### Q7 — Post-finalization grace window for shadow STT write-back (FR-029)

- [ ] CHK086 Is the post-finalization grace window for CRM write-back enumerated as a new deployment-configurable knob (added to the configurable-knob inventory alongside CHK005–CHK008)? [Completeness, Spec §FR-029]
- [ ] CHK087 Is the grace window's default value explicitly stated in the spec OR explicitly deferred to the Implementation Plan / deployment configuration (no silent ambiguity, per the CHK026 pattern)? [Completeness, Clarity, Spec §FR-029, Spec §Deferred to Implementation Plan, Gap]
- [ ] CHK088 Is the grace window's unit (seconds / milliseconds / other) defined, so configuration values are unambiguous? [Clarity, Measurability, Spec §FR-029, Gap]
- [ ] CHK089 Is the grace window's minimum value defined (in particular, is 0 an allowed value with the documented semantics that write-back proceeds immediately and any later shadow output becomes `shadow_lane_truncated`)? [Completeness, Ambiguity, Spec §FR-029, Gap]
- [ ] CHK090 Is the grace window's maximum value defined (is unbounded allowed, or is there a cap to prevent indefinite write-back delay)? [Completeness, Ambiguity, Spec §FR-029, Gap]
- [ ] CHK091 Is the grace window enumerated in the Deferred-to-Plan "Resume / abandonment edge details" or "Performance and latency targets" section so it is not orphaned (no knob without a corresponding deferred-to-plan entry, per CHK059 pattern)? [Consistency, Spec §FR-029, Spec §Deferred to Implementation Plan]
- [ ] CHK092 Is the grace window's per-deployment vs. per-invocation configurability level defined (deployment-only, or also overridable per CLI invocation, per CHK033 pattern)? [Clarity, Spec §FR-029, Gap]

### Q10 — Redaction scope expansion (FR-033)

- [ ] CHK093 Is the expanded redaction artifact list (full transcript + session-result summary + shadow STT transcript + shadow STT discrepancy records) enumerated as the configurable redaction surface (re-tests / refines CHK023)? [Completeness, Spec §FR-033]
- [ ] CHK094 Is the pointer-metadata-exclusion rule (transcript pointer and its metadata are excluded from default-on redaction because pointers MUST remain machine-readable for resume / inspection) explicitly stated as hardcoded (NOT deployment-configurable)? [Clarity, Spec §FR-033]
- [ ] CHK095 Is the redaction-runs-before-write invariant restated for each of the four covered artifacts, so deployments cannot configure a partial-coverage redaction policy that misses one artifact (consistency check against CHK049)? [Consistency, Spec §FR-033, Spec §FR-015]
- [ ] CHK096 Is the interaction between the redaction scope and the three retention modes (full+redacted, summary-only, pointer-only per CHK003) explicit — e.g., under summary-only, the summary is still subject to default-on redaction; under pointer-only, neither transcript nor summary file exists so the redaction surface degenerates to the shadow artifacts? [Consistency, Spec §FR-033, Spec §FR-034]
- [ ] CHK097 Is the shadow STT discrepancy record's retention-when-summary-only behavior (FR-034: discrepancy records retained even when transcript retention is summary-only) consistent with the expanded redaction scope (the retained discrepancy records MUST still be redacted, not bypass redaction)? [Consistency, Spec §FR-033, Spec §FR-034]

### Q11 — PHI tag-and-redact policy (FR-015)

- [ ] CHK098 Is the PHI tag-and-redact policy itself (the tagging mechanism and the redact-before-disk guarantee) enumerated as deployment-configurable OR explicitly hardcoded (so the choice between policy-configurability and policy-hardcoding is not silently ambiguous)? [Completeness, Ambiguity, Spec §FR-015, Gap]
- [ ] CHK099 Is the PHI tag-and-redact policy's interaction with the configured redaction layer (CHK018) explicit — is PHI tag-and-redact a separate sub-policy of the redaction layer, or is it inseparable from the default-on `[REDACTED]` policy? [Clarity, Spec §FR-015, Spec §FR-033, Gap]
- [ ] CHK100 Is the requirement explicit that the PHI tag-and-redact policy applies to the SAME four artifacts as FR-033's expanded redaction scope (full transcript + summary + shadow transcript + shadow discrepancy records), with no divergence in scope? [Consistency, Spec §FR-015, Spec §FR-033]
- [ ] CHK101 Is the observability of a PHI-volunteered escalation in audit artifacts and the run report (per FR-015 "MUST be observably distinct") configurable in any way (e.g., a redaction tag string), or is it hardcoded? [Completeness, Ambiguity, Spec §FR-015, Spec §FR-036, Gap]

### Q9 — Rejected-by-authentication audit log (FR-008)

- [ ] CHK102 Is the rejected-by-authentication audit log's file format / on-disk layout enumerated in the run-report and artifact-layout Deferred-to-Plan section (alongside CHK058's run-report format deferral)? [Completeness, Spec §FR-008, Spec §Deferred to Implementation Plan]
- [ ] CHK103 Is the rejected-by-authentication audit log's retention enumerated as inheriting the local audit retention floor (≥ 90 days, CHK019, CHK083) and NOT having a separate retention knob? [Consistency, Spec §FR-008, Spec §FR-022, Spec §Assumptions]
- [ ] CHK104 Is the rejected-by-authentication count rendering in the run report (per FR-036) enumerated as a fixed run-report field (no configurability on whether the count appears), or is its presence deployment-configurable? [Clarity, Spec §FR-008, Spec §FR-036, Gap]
- [ ] CHK105 Is the "MUST NOT include the verification secret and MUST NOT include the callback body content" requirement consistent with the broader no-secrets-in-artifacts requirement (CHK035, CHK037, CHK080) and explicitly enumerated for the rejected-by-authentication audit log? [Consistency, Spec §FR-008, Spec §FR-035, Spec §SC-018]
- [ ] CHK106 Is the source-metadata content (e.g., provider-supplied source identifiers, IP-level metadata where available) enumerated such that deployments can determine WHICH metadata fields are captured (so deployments can satisfy local privacy obligations)? [Clarity, Completeness, Spec §FR-008, Gap]

### Performance and latency targets — Deferred-to-Plan subsection acknowledgment

- [ ] CHK107 Does the spec's new "Performance and latency targets" Deferred-to-Plan subsection explicitly enumerate numeric latency targets as deferred (so the absence of in-spec numbers is not a [Gap] — it is an intentional deferral)? [Consistency, Spec §Deferred to Implementation Plan]
- [ ] CHK108 Is the "Performance and latency targets" subsection consistent with FR-029 (the grace window is a behavior contract, not a latency target) and with FR-013 (the silence-timeout is a configurability contract, not a latency target) — i.e., the configurability surface and the latency surface are explicitly separated? [Consistency, Spec §FR-013, Spec §FR-029, Spec §Deferred to Implementation Plan]
- [ ] CHK109 Is the deferral of performance and latency targets enumerated in a way that does NOT contradict the per-knob defaults questions (CHK022–CHK029) — i.e., the deferred-to-plan latency surface and the deferred-to-plan default-value surface are NOT the same deferral? [Consistency, Spec §Deferred to Implementation Plan, Gap]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### `config/slice3.toml` structure enumeration (Research §11, Quickstart §1.3)

- [ ] CHK110 Does the `config/slice3.toml` file structure define exactly the six sections enumerated in Research §11 (`[signalwire]`, `[realtime_ai]`, `[shadow_stt]`, `[timeouts]`, `[retention]`, `[redaction]`) — no extra section silently added and no enumerated section silently dropped? [Coverage, Research §11, Quickstart §1.3]
- [ ] CHK111 Is the `[signalwire]` section's required key set (source_caller_id, status_callback_url_template, media_callback_url_template) consistent between Research §11 and the Quickstart §1.3 example? [Consistency, Research §11, Quickstart §1.3]
- [ ] CHK112 Is the `[realtime_ai]` section's key set (provider_name, model_name, model_version) consistent between Research §11 and the Quickstart §1.3 example, and aligned with the runtime_identity recorded on every session per FR-016? [Consistency, Research §11, Quickstart §1.3, Spec §FR-016, Data-Model §1.12]
- [ ] CHK113 Is the `[shadow_stt]` section's key set (enabled_default, discrepancy_policy_path) consistent across Research §11, Quickstart §1.3, and the CLI contract's `[shadow_stt].enabled_default` reference? [Consistency, Research §11, Quickstart §1.3, Contract: cli-slice3.md]
- [ ] CHK114 Is the `[timeouts]` section's key set (abandonment_sec, silence_after_connection_sec, grace_window_sec) consistent across Research §7, Research §11, and the Quickstart §1.3 example? [Consistency, Research §7, Research §11, Quickstart §1.3]
- [ ] CHK115 Are the `[retention]` and `[redaction]` sections each defined with at least one required key (retention.mode, redaction.policy) so an operator knows the minimum non-secret config surface? [Coverage, Quickstart §1.3, Spec §FR-033]

### Required env var consistency (Research §11 ↔ Quickstart §1.2)

- [ ] CHK116 Is the SignalWire env-var triple (`SIGNALWIRE_PROJECT_ID`, `SIGNALWIRE_API_TOKEN`, `SIGNALWIRE_SIGNING_SECRET`) named identically between Research §11 and Quickstart §1.2 — no casing or prefix drift? [Consistency, Research §11, Quickstart §1.2]
- [ ] CHK117 Is the real-time AI provider env-var pair (`SLICE3_REALTIME_PROVIDER`, `SLICE3_REALTIME_API_KEY`) named identically between Research §3, Research §11, and Quickstart §1.2? [Consistency, Research §3, Research §11, Quickstart §1.2]
- [ ] CHK118 Is the shadow STT env-var pair (`SLICE3_SHADOW_STT_PROVIDER`, `SLICE3_SHADOW_STT_API_KEY`) named identically between Research §4, Research §11, and Quickstart §1.2? [Consistency, Research §4, Research §11, Quickstart §1.2]
- [ ] CHK119 Are the Dataverse env vars carried forward from Slice 2 (`DATAVERSE_TENANT_ID`, `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`, `DATAVERSE_ENV_URL`) listed identically between Research §11 and Quickstart §1.2 with no Slice 3-specific rename? [Consistency, Research §11, Quickstart §1.2]
- [ ] CHK120 Is the operator's `$USER` env var (used as the default for `--operator-id` per Research §8) documented in the env-var setup section of the quickstart as an operator-influenced value? [Gap, Research §8, Quickstart §1.2, Contract: cli-slice3.md]

### Timeout default consistency (plan.md ↔ research.md ↔ quickstart.md ↔ data-model.md)

- [ ] CHK121 Does the abandonment timeout default (90 seconds) appear consistently across Research §7 (`SLICE3_ABANDONMENT_TIMEOUT_SEC` default `90`), Quickstart §1.3 (`abandonment_sec = 90`), and Data-Model §2.1 (`grace_window_sec` field present, abandonment governed by Session lifecycle) with no value mismatch? [Consistency, Research §7, Quickstart §1.3, Data-Model §2.1]
- [ ] CHK122 Does the silence-after-connection timeout default (30 seconds) appear consistently across Research §7 (`SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC` default `30`) and Quickstart §1.3 (`silence_after_connection_sec = 30`)? [Consistency, Research §7, Quickstart §1.3]
- [ ] CHK123 Does the grace-window timeout default (3 seconds) appear consistently across Research §7 (`SLICE3_GRACE_WINDOW_SEC` default `3`), Quickstart §1.3 (`grace_window_sec = 3`), and Data-Model §1.8 / §2.1 (grace_window_sec column on `Session`)? [Consistency, Research §7, Quickstart §1.3, Data-Model §1.8, Data-Model §2.1]
- [ ] CHK124 Is the SLICE3_* env var naming pattern (e.g., `SLICE3_ABANDONMENT_TIMEOUT_SEC`, `SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC`, `SLICE3_GRACE_WINDOW_SEC`) consistent across Research §7 and quickstart, and is the CLI / config code path documented to honor the same names? [Consistency, Research §7, Quickstart §1.3, Gap]
- [ ] CHK125 Is the relationship between the env-var timeouts (Research §7) and the `config/slice3.toml [timeouts]` section keys (Quickstart §1.3) defined — which wins on conflict, env var or TOML? [Ambiguity, Research §7, Research §11, Quickstart §1.3, Gap]

### Redaction policy default value (Quickstart §1.3 ↔ Spec FR-033)

- [ ] CHK126 Is the `[redaction].policy = "default"` value in Quickstart §1.3 unambiguous about what "default" means (i.e., does the documentation cite the FR-033 / Round 2 Q10 default-on coverage of full transcript + summary + shadow transcript + shadow discrepancy records)? [Clarity, Quickstart §1.3, Spec §FR-033]
- [ ] CHK127 Is the `[retention].mode` default value documented unambiguously in Quickstart §1.3 (the example shows `"full_with_redaction"`, the alternates `"summary_only"` / `"pointer_only"` — is one designated the default if omitted)? [Ambiguity, Quickstart §1.3, Spec §FR-033]

### Shadow STT default-on vs. FR-032 demo-loop-without-shadow-STT reconciliation

- [ ] CHK128 Is the `[shadow_stt].enabled_default = true` setting in Quickstart §1.3 reconciled with FR-032's "demonstrable loop completes without shadow STT" guarantee — i.e., is it clear that enabled_default = true is a deployment posture and disabling the lane (`--no-shadow-stt` or `SLICE3_SHADOW_STT_PROVIDER=disabled`) MUST still complete the loop? [Conflict, Quickstart §1.3, Spec §FR-032, Research §4]
- [ ] CHK129 Is the operator-visible interaction between the env-var disable (`SLICE3_SHADOW_STT_PROVIDER="disabled"`, Research §4) and the TOML default (`enabled_default = true`, Quickstart §1.3) defined — does env-var-disable override the TOML default, and is that documented? [Ambiguity, Research §4, Quickstart §1.3]
- [ ] CHK130 Is the deployment configuration aligned so the SLICE3 demo / CI loop never has shadow STT as a hard dependency — the demonstrable loop runs with shadow STT disabled per FR-032 regardless of the TOML default? [Consistency, Spec §FR-032, Research §4, Quickstart §1.3]

### Shadow-STT discrepancy policy file path (Research §4 ↔ Quickstart §1.3)

- [ ] CHK131 Does the `shadow_stt_discrepancy_policy.json` file path appear in BOTH Research §4 (`config/shadow_stt_discrepancy_policy.json`) and Quickstart §1.3 (`[shadow_stt].discrepancy_policy_path = "config/shadow_stt_discrepancy_policy.json"`) with the same path? [Consistency, Research §4, Quickstart §1.3]
- [ ] CHK132 Is the discrepancy policy JSON file's two-section structure (`benign_rules`, `uncertain_rules`) documented in the configuration surface so an operator can edit it without reading the implementation? [Coverage, Research §4, Quickstart §1.3, Gap]
- [ ] CHK133 Is the deployment behavior defined when the discrepancy policy file referenced by `discrepancy_policy_path` does not exist or is malformed — does the shadow lane refuse to start, default to all-benign, or default to all-uncertain? [Gap, Research §4, Quickstart §1.3]

### SignalWire callback URL templating (Quickstart §1.3 ↔ Research §1)

- [ ] CHK134 Are the SignalWire callback URL templates (`status_callback_url_template`, `media_callback_url_template`) defined to be parameterizable by `{session_id}` consistently — Quickstart §1.3 shows `{session_id}` placeholders, and Research §1 specifies an in-process ASGI receiver bound only in real-call mode? [Consistency, Quickstart §1.3, Research §1]
- [ ] CHK135 Is the URL template substitution rule defined so an operator knows exactly which placeholders are honored (only `{session_id}`? what about `{queue_item_id}`, `{campaign_id}`?) — and is the failure mode defined when a template contains an unknown placeholder? [Ambiguity, Quickstart §1.3, Gap]
- [ ] CHK136 Is the reachability requirement on the callback URL templates aligned between the readiness check (Contract cli-slice3.md `status_callback_url_configured` / `media_callback_url_configured`) and the configuration surface (Quickstart §1.3)? [Consistency, Contract: cli-slice3.md, Quickstart §1.3, Data-Model §1.9]

### Configuration deferral consistency across plan-side artifacts

- [ ] CHK137 Are the deployment-configurable provider choices (real-time AI provider, shadow STT provider) consistent across Plan §Technical Context, Research §3 / §4, Quickstart §1.2 / §1.3 — no spec-level commitment to a specific vendor leaked? [Consistency, Plan §Technical Context, Research §3, Research §4, Quickstart §1.2]
- [ ] CHK138 Is the no-secrets-in-TOML invariant enforced by the configuration surface (only env vars hold credentials, per Research §11; the example `config/slice3.toml` in Quickstart §1.3 contains zero secret keys)? [Consistency, Research §11, Quickstart §1.3, Spec §FR-035]
- [ ] CHK139 Is the configuration loading order documented (e.g., env vars override TOML, CLI flags override both) so an operator can predict the effective value of any configurable knob from inspection alone? [Gap, Research §11, Contract: cli-slice3.md]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- The most consequential gaps are: (a) whether the shadow STT default state is enabled or disabled (CHK028), (b) whether the transcript retention default mode is full+redacted, summary-only, or pointer-only (CHK029), and (c) the missing-required-config behavior for the real-time AI provider credentials and the shadow STT provider credentials (CHK073, CHK074).
- The configurability surface MUST be enumerated identically across the Definitions, Requirements, Assumptions, and Deferred-to-Plan sections (CHK060) — divergence is the most common source of operator-visible configuration bugs.
- ≥80% of items reference a spec section or a quality marker for traceability.
