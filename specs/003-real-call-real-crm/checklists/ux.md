# Operator UX Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the operator-CLI UX dimension (no visual UI) before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

> Note: Slice 3 has NO visual openCloser UI. The operator surface is the CLI / developer command, the local run report, local audit artifacts, and the resulting Dynamics records. Visual-UI accessibility items are intentionally excluded; see CHK001.

## Surface Scope

- [ ] CHK001 Does the spec explicitly state that Slice 3 has no custom openCloser UI and that operator evidence comes from CLI / API output + local run report + local audit artifacts + Dynamics records — so that visual-UI accessibility requirements are out of scope by exclusion? [Coverage, Spec §FR-038, Assumptions — Operator surface]
- [ ] CHK002 Does the spec name every operator-facing surface component (CLI command, run report, local audit artifacts enumerated, Dynamics records)? [Completeness, Spec §FR-036, FR-038, Key Entities — Run Report]
- [ ] CHK003 Is the boundary between "operator-visible" and "internal-only" outputs unambiguous (e.g., operator identity is recorded on the local session and run report only and MUST NOT appear in Dynamics)? [Clarity, Spec §FR-016, Clarifications, FR-036]
- [ ] CHK004 Is the spec consistent that the demonstrable loop is exercisable WITHOUT a custom openCloser UI (FR-038) and that the Slice 3 demo path uses CLI / API output + local artifacts + Dynamics records (Assumptions — Operator surface)? [Consistency, Spec §FR-038, Assumptions]

## CLI Invocation Surface

- [ ] CHK005 Is the existence of a CLI / developer command specified as a requirement (not implied)? [Completeness, Spec §FR-037]
- [ ] CHK006 Is the requirement that the CLI processes exactly one Dataverse queue item per invocation explicit? [Clarity, Spec §FR-003, FR-037]
- [ ] CHK007 Are the two supported run modes (rehearsal / readiness as default; real-call / write-enabled requiring an explicit flag) explicitly named? [Completeness, Spec §FR-001, FR-002, FR-037]
- [ ] CHK008 Is it explicit that the default invocation (no flags) MUST NOT place a SignalWire call and MUST NOT mutate Dynamics? [Clarity, Spec §FR-001, FR-037, US3 Acceptance 6, SC-011]
- [ ] CHK009 Is the requirement that the real-call / write-enabled flag (or equivalent deliberate action) is required before any SignalWire dial OR any Dataverse mutation explicit? [Clarity, Spec §FR-001, Definitions]
- [ ] CHK010 Is the exact CLI flag / configuration-file shape for the real-call / write-enabled flag intentionally deferred to plan rather than under-specified at spec level? [Clarity / Dependency, Spec §Deferred to Implementation Plan — Telephony adapter details]
- [ ] CHK011 Is the requirement that the same flag controls BOTH SignalWire dialing AND Dataverse mutation (so an operator cannot accidentally enable only one) explicit? [Clarity, Spec §FR-001, Definitions — Real-call / write-enabled mode]
- [ ] CHK012 Does the spec address the CLI exit-code contract for blocked / unready / failed / completed runs at requirement level, or is this explicitly deferred to plan? [Gap, Spec §FR-011, FR-012, FR-036]
- [ ] CHK013 Does the spec address whether the CLI may be invoked from non-interactive shells (e.g., CI / scheduled context) or whether interactive confirmation is required for real-call mode? [Gap, Spec §FR-001, FR-037]

## Required Operator Inputs

- [ ] CHK014 Are the required operator inputs enumerated (campaign selector, queue-item selector, SignalWire configuration, persona/runtime configuration, shadow STT enable/disable flag, run mode)? [Completeness, Spec §FR-003, FR-037]
- [ ] CHK015 Is the spec consistent between FR-003 ("campaign selector, queue-item selector, persona/runtime configuration, SignalWire configuration, run mode") and FR-037 (which adds "shadow STT enable/disable flag") on required operator inputs? [Consistency, Spec §FR-003, FR-037]
- [ ] CHK016 Is the requirement that the operator must select a single Dataverse queue item per invocation (no implicit selection) explicit? [Clarity, Spec §FR-003]
- [ ] CHK017 Is it explicit that the operator MUST select a campaign (single-campaign, single-item)? [Clarity, Spec §Assumptions — Single campaign, single item]
- [ ] CHK018 Is the requirement that the operator identity is recorded on the local session and run report (at minimum OS user or a CLI-provided operator identifier) explicit? [Completeness, Spec §FR-016, Clarifications]
- [ ] CHK019 Is the requirement that operator identity MUST NOT propagate into Dataverse explicit (no new Dataverse field for operator identity)? [Clarity, Spec §FR-016, Clarifications]
- [ ] CHK020 Is the SignalWire configuration input bounded (e.g., credentials, source caller-ID number, callback URLs) or left unbounded? [Completeness / Ambiguity, Spec §FR-009, FR-037]
- [ ] CHK021 Is the persona/runtime configuration input bounded (e.g., persona version, real-time AI model identity, silence-timeout configuration) at requirement level, or is the exact shape deferred to plan? [Clarity, Spec §FR-013, FR-016, Deferred to Implementation Plan]

## Run Modes & Default-Safe Behavior

- [ ] CHK022 Is rehearsal / readiness mode defined with explicit semantics (verifies mapping, telephony readiness, phone format, persona/runtime configuration, eligibility, planned dial plan, planned write-back payloads; produces readiness report; places zero SignalWire calls; creates or updates zero Dataverse records beyond approved dry-run behavior)? [Completeness, Spec §FR-002, Definitions — Rehearsal / readiness mode]
- [ ] CHK023 Is real-call / write-enabled mode defined with explicit semantics (SignalWire dial permitted, Dataverse mutations performed, reuses Slice 2 write-enabled semantics)? [Completeness, Spec §FR-001, Definitions — Real-call / write-enabled mode]
- [ ] CHK024 Is the "default is rehearsal" requirement testable / measurable (e.g., SC-011: 100% of runs that omit the flag run in rehearsal / readiness mode and place 0 calls and create / update 0 Dynamics records)? [Measurability, Spec §SC-011]
- [ ] CHK025 Is the requirement that rehearsal mode surfaces mapping / telephony-readiness / phone-format gaps in the readiness report (does not silently pass) explicit? [Coverage, Spec §FR-002, US2 Acceptance 3, US2 Acceptance 4]
- [ ] CHK026 Is rehearsal-mode behavior explicit that the planned write-back artifacts match what a real-call / write-enabled run would have sent, with the real provider call ID field marked as not-yet-assigned? [Clarity, Spec §US2 Acceptance 2]
- [ ] CHK027 Is the spec consistent between FR-001 ("default invocation MUST NOT place a SignalWire call and MUST NOT mutate Dynamics"), FR-002 ("rehearsal / readiness mode MUST be the default"), and FR-037 ("rehearsal / readiness (default)")? [Consistency, Spec §FR-001, FR-002, FR-037]
- [ ] CHK028 Is the requirement that rehearsal mode can be exercised against a production tenant without operator's explicit real-call consent stated as the design intent? [Clarity, Spec §US2 Priority rationale]

## Run-Report Content & Readability

- [ ] CHK029 Is the run report required on every Slice 3 invocation (not only on success)? [Completeness, Spec §FR-036]
- [ ] CHK030 Are the minimum run-report fields enumerated (run mode, session ID, invoking operator identity, real provider call ID when assigned, persona version, runtime/model identity, final disposition, per-write-back-operation status, shadow STT enabled/disabled flag and discrepancy summary when enabled, callbacks audit / conflicting-callbacks audit row counts)? [Completeness, Spec §FR-036]
- [ ] CHK031 Is the per-write-back-operation status enumeration explicit (planned / completed / resume-needed / blocked)? [Clarity, Spec §FR-036]
- [ ] CHK032 Is the requirement that the run report identifies the failing readiness check or block reason when applicable explicit? [Coverage, Spec §FR-036]
- [ ] CHK033 Is the requirement that the run report records the telephony readiness summary on every run (including real-call runs) explicit? [Coverage, Spec §Key Entities — Telephony Readiness Report, FR-036]
- [ ] CHK034 Is the requirement that the run report records whether shadow STT was enabled / disabled for the run explicit (so a reviewer can interpret the absence of discrepancy events)? [Clarity, Spec §FR-032, US6 Acceptance 5]
- [ ] CHK035 Is the run-report file format / schema / naming convention deferred to plan (not under-specified at spec level)? [Clarity / Dependency, Spec §Deferred to Implementation Plan — Run-report and artifact layout]
- [ ] CHK036 Is the run report required to be operator-readable (a human can interpret it without source-code access)? [Clarity, Spec §FR-036, SC-017]
- [ ] CHK037 Is the readability requirement testable (SC-017: the operator can read the artifacts and explain the outcome without reading source code)? [Measurability, Spec §SC-017]
- [ ] CHK038 Is the run report required to record the live-runtime degradation reason (provider error / runtime crash / silence-timeout) when the path applied? [Gap / Coverage, Spec §FR-013, Clarifications]
- [ ] CHK039 Is the run report required to record the live-call abandonment reason when finalization used the abandonment timeout? [Gap / Coverage, Spec §FR-026]
- [ ] CHK040 Is the run report required to record the conflicting-late-callback audit row count (so reviewers can detect late-after-finalization deliveries)? [Coverage, Spec §FR-027, FR-036]
- [ ] CHK041 Is the run report required to record whether default-on transcript redaction ran on the transcript artifact? [Gap, Spec §FR-033, Edge Cases — Default-on redaction]
- [ ] CHK042 Is the requirement that the run report MUST NOT contain secrets (SignalWire / real-time AI provider / shadow STT / Dataverse credentials) explicit? [Coverage, Spec §FR-035, SC-018]
- [ ] CHK043 Is the requirement that the operator identity captured on the run report does NOT include secrets or tokens explicit? [Gap, Spec §FR-016]

## Demo-Evidence Enumeration (No Custom UI)

- [ ] CHK044 Are the local audit artifacts that constitute demo evidence enumerated (session-result, transcript or transcript pointer, planned/actual write-back payloads, callbacks audit log, shadow STT artifacts and discrepancy records when enabled, conflicting-events audit log when populated)? [Completeness, Spec §FR-038]
- [ ] CHK045 Are the Dynamics records that constitute demo evidence enumerated (Dataverse queue item, Phone Call activity when applicable, callback or review Task when applicable)? [Completeness, Spec §FR-038]
- [ ] CHK046 Is the demo-evidence requirement testable end-to-end (operator can explain the outcome from the enumerated artifacts and Dynamics records alone)? [Measurability, Spec §SC-017]
- [ ] CHK047 Is the requirement that the local audit artifacts retain a callbacks-audit-row count compatible with the duplicate-callback case explicit (duplicates are recorded, not dropped)? [Coverage, Spec §FR-007, FR-021, FR-036]
- [ ] CHK048 Is the requirement that the conflicting-events audit log is populated only when conflicting-late callbacks arrive explicit? [Clarity, Spec §FR-027, FR-036]
- [ ] CHK049 Is the demo-evidence requirement explicit that no custom openCloser dashboard, campaign UI, transcript review console, or task queue UI is part of Slice 3 evidence? [Coverage, Spec §Constitution Alignment, Assumptions]
- [ ] CHK050 Is the requirement explicit that local artifacts and Dynamics records together MUST be sufficient to explain the outcome without reading source code? [Measurability, Spec §SC-017]
- [ ] CHK051 Is the requirement that shadow STT artifacts and discrepancy records are evidence ONLY when shadow STT was enabled for the run explicit? [Clarity, Spec §FR-032, FR-038]
- [ ] CHK052 Does the spec address transcript-evidence behavior when retention is summary-only or pointer-only (no full transcript file written; session-result still carries summary)? [Coverage, Spec §FR-033, Edge Cases — Transcript retention is summary-only or pointer-only]
- [ ] CHK053 Does the spec address transcript-evidence behavior when shadow STT retention is summary-only (shadow discrepancy records are still retained as audit evidence)? [Coverage, Spec §FR-034]

## Operator-Visible Error / Block Messaging

- [ ] CHK054 Is the requirement that telephony readiness failures surface an operator-visible message naming the failing check explicit? [Completeness, Spec §FR-011, US3 Independent Test, US3 Acceptance 2]
- [ ] CHK055 Is the requirement that the real-dial phone-number validation failure is surfaced in the readiness report with the phone-format failure named explicit? [Coverage, Spec §FR-010, US3 Acceptance 3, US2 Acceptance 4]
- [ ] CHK056 Is the requirement that a SignalWire provider-rejected dial (4xx) is recorded in the run report as a provider-rejected-dial failure explicit? [Coverage, Spec §FR-012, Edge Cases]
- [ ] CHK057 Is the requirement that a Dataverse metadata-verification block surfaces the same metadata-verification block behavior proven in Slice 2 explicit? [Coverage, Spec §US3 Acceptance 1]
- [ ] CHK058 Is the requirement that a concurrent CLI invocation on the same queue item exits with an operator-visible blocked-by-claim message explicit? [Completeness, Spec §FR-003, Clarifications, Edge Cases — Concurrent CLI invocation]
- [ ] CHK059 Is the requirement that a `blocked_reason` is populated on the normalized session result when the path is blocked by eligibility explicit? [Coverage, Spec §FR-017, FR-019]
- [ ] CHK060 Is the requirement that a `human_review_reason` is populated on the normalized session result when applicable explicit? [Coverage, Spec §FR-017]
- [ ] CHK061 Is the requirement that operator-visible error messages MUST NOT contain secrets explicit? [Coverage, Spec §FR-035, SC-018]
- [ ] CHK062 Does the spec address whether operator-visible error messages must distinguish between "config issue" vs. "transient provider failure" vs. "queue-item ineligible" so the operator knows which remediation path applies? [Gap / Clarity, Spec §FR-011, FR-012]
- [ ] CHK063 Is the requirement that live-call abandonment surfaces a `live_call_abandonment` reason on the run report explicit? [Coverage, Spec §FR-026, Edge Cases]
- [ ] CHK064 Is the requirement that live-runtime degradation (provider error / runtime crash / silence timeout) surfaces a runtime-failure or `script_truncated` indication on the run report explicit? [Gap / Coverage, Spec §FR-013, Clarifications]
- [ ] CHK065 Is the operator-visible behavior on shadow STT lane failure specified (run report records the shadow-lane failure; live call unaffected)? [Coverage, Spec §FR-029, US6 Acceptance 6]
- [ ] CHK066 Is the operator-visible behavior on a conflicting-late SignalWire callback specified (audit row recorded; finalized disposition unchanged; no new CRM payload emitted)? [Coverage, Spec §FR-027]

## Readiness Report (Pre-Dial UX)

- [ ] CHK067 Is the readiness report defined as the local artifact produced by rehearsal / readiness mode AND recorded on every real-call / write-enabled run? [Completeness, Spec §Key Entities — Telephony Readiness Report]
- [ ] CHK068 Are the readiness checks the report covers enumerated (SignalWire credentials, source number, destination phone format, callback URLs, persona/runtime configuration, Dataverse mapping, callback owner mapping, eligibility)? [Completeness, Spec §FR-009, Key Entities — Telephony Readiness Report]
- [ ] CHK069 Is the requirement that the readiness report surfaces the failing check name on any readiness failure explicit? [Clarity, Spec §FR-011, Key Entities — Telephony Readiness Report]
- [ ] CHK070 Is the rehearsal-mode readiness report required to include the planned write-back artifacts (planned Phone Call activity, planned queue-status update, planned Task) alongside the readiness check results? [Coverage, Spec §FR-002, US2 Acceptance 1]
- [ ] CHK071 Does the spec address whether a real-call / write-enabled run's readiness summary is part of the run report, the readiness report, or both? [Ambiguity, Spec §Key Entities — Telephony Readiness Report, Key Entities — Run Report]

## Persona / Disclosure / Caller-Facing UX (CLI-Initiated, Live-Call Side)

- [ ] CHK072 Is the requirement that the persona's first connected-call utterance delivers the AI-on-behalf-of-Medx disclosure explicit (this IS caller-facing UX even though it is not visual)? [Coverage, Spec §FR-015, US5 Acceptance 1]
- [ ] CHK073 Is the requirement that the disclosure does NOT require explicit verbal acknowledgment from the caller, and that absence-of-opt-out is implicit acknowledgment, explicit? [Clarity, Spec §FR-015, Clarifications]
- [ ] CHK074 Is the requirement that no new `human_review_reason` is introduced for missing disclosure acknowledgment explicit? [Clarity, Spec §FR-015, Clarifications]
- [ ] CHK075 Is the caller-facing behavior on opt-out (persona stops the sales flow before any further sales utterance) explicit? [Coverage, Spec §US5 Acceptance 3, Edge Cases — Mid-call opt-out / DNC]
- [ ] CHK076 Is the caller-facing behavior on mid-call PHI / out-of-allowed-claim attempts (persona escalates safely with the appropriate enumerated reason; conversation ends safely) explicit? [Coverage, Spec §FR-015, US5 Acceptance 2, Edge Cases]

## Run-Report Audit / Reproducibility Surface

- [ ] CHK077 Is the requirement that the run report enables a run to be reproducible (records persona version, runtime/model identity, model configuration relevant to audit) explicit? [Completeness, Spec §FR-016]
- [ ] CHK078 Is the requirement that the recorded model configuration includes at minimum model name and version explicit? [Clarity, Spec §FR-016]
- [ ] CHK079 Is the requirement that the recorded operator identity uses at minimum the OS user or a CLI-provided operator identifier explicit? [Clarity, Spec §FR-016]
- [ ] CHK080 Is the requirement that the run report records the planned-vs-actual write-back deltas (so a reviewer can detect partial write-back) explicit? [Coverage, Spec §FR-036, FR-038]

## Scenario Classes (Operator UX)

### Primary

- [ ] CHK081 Is the primary operator path defined (CLI in real-call / write-enabled mode against a `ready` queue item with verified telephony readiness produces a real call, Dynamics write-back, run report, and local artifacts)? [Primary, Spec §US1, SC-001]
- [ ] CHK082 Is the primary rehearsal path defined (CLI in rehearsal / readiness mode produces readiness report + planned write-back artifacts; zero calls; zero Dynamics mutations)? [Primary, Spec §US2, SC-002]

### Alternate

- [ ] CHK083 Is the alternate operator path defined for shadow STT enabled (run report records the shadow STT enabled flag and discrepancy summary)? [Alternate, Spec §FR-032, US6 Acceptance 5]
- [ ] CHK084 Is the alternate operator path defined for shadow STT disabled (Slice 3 demonstrable loop still completes; run report records disabled)? [Alternate, Spec §FR-032, US6 Acceptance 5]
- [ ] CHK085 Is the alternate operator path defined for re-invocation of the CLI for the same session after a partial write-back (resume runs only the missing writes)? [Alternate, Spec §FR-022, US4 Acceptance 7]
- [ ] CHK086 Is the alternate operator path defined for re-invocation of the CLI for an already-finalized session (no-op for CRM)? [Alternate, Spec §US4 Acceptance 9]

### Exception / Error

- [ ] CHK087 Is the exception operator path defined for a missing real-call / write-enabled flag (system runs in rehearsal mode as default; no call placed)? [Exception, Spec §US3 Acceptance 6, SC-011]
- [ ] CHK088 Is the exception operator path defined for a missing destination phone number (run exits before dial with phone-format failure named in the readiness report)? [Exception, Spec §FR-010, US3 Acceptance 3, US2 Acceptance 4]
- [ ] CHK089 Is the exception operator path defined for missing SignalWire credentials / unauthorized source number (run exits before dial with readiness failure named)? [Exception, Spec §FR-009, US3 Acceptance 2]
- [ ] CHK090 Is the exception operator path defined for a missing / unreachable callback URL (run exits before dial with callback-URL readiness failure)? [Exception, Spec §FR-009, US3 Acceptance 4]
- [ ] CHK091 Is the exception operator path defined for a missing campaign-to-persona/runtime mapping (run exits before dial with the missing mapping named)? [Exception, Spec §FR-009, US3 Independent Test]
- [ ] CHK092 Is the exception operator path defined for a missing callback owner mapping (run exits before dial with the missing mapping named)? [Exception, Spec §FR-009, US3 Independent Test]
- [ ] CHK093 Is the exception operator path defined for an incomplete Dataverse mapping (run exits before dial with the metadata-verification block)? [Exception, Spec §US3 Acceptance 1]
- [ ] CHK094 Is the exception operator path defined for a concurrent CLI invocation on the same queue item (second invocation exits before dial with blocked-by-claim message; no call placed; no attempt consumed)? [Exception, Spec §FR-003, Clarifications]
- [ ] CHK095 Is the exception operator path defined for a SignalWire provider-rejected dial (4xx) (run exits with provider-rejected-dial failure in run report; no attempt consumed)? [Exception, Spec §FR-012]
- [ ] CHK096 Is the exception operator path defined for an eligibility block (system records `disposition='blocked'` with failing rule names; only approved blocked/status/error fields written; no call placed; no Phone Call activity)? [Exception, Spec §US3 Acceptance 5, FR-019, FR-023]

### Recovery

- [ ] CHK097 Is the recovery operator path defined for a transient Dataverse error mid-write-back (in-run retry succeeds; no duplicate records)? [Recovery, Spec §FR-022, US7 Acceptance 1]
- [ ] CHK098 Is the recovery operator path defined for a retry-budget-exhausted case (operator re-invokes CLI; only missing writes are retried)? [Recovery, Spec §FR-022, US4 Acceptance 7, US7 Acceptance 2]
- [ ] CHK099 Is the recovery operator path defined for orchestrator restart mid-call (live-call abandonment timeout finalizes session; resume path applies for partial write-back)? [Recovery, Spec §FR-026, US4 Acceptance 8]
- [ ] CHK100 Is the recovery operator path defined for orchestrator restart between `completed` callback and write-back (re-invocation resumes only missing writes; preserves recorded real provider call ID)? [Recovery, Spec §US7 Acceptance 4]
- [ ] CHK101 Is the recovery operator path defined for resume when transcript retention is summary-only or pointer-only (absence of transcript file is not an error)? [Recovery, Spec §Edge Cases — Resume after a real call when retention policy disables the transcript artifact]

### Non-Functional

- [ ] CHK102 Is the non-functional requirement that the run report identifies the recovery path taken (so the operator knows what recovery happened) explicit? [Non-Functional / Coverage, Spec §US7 Independent Test, FR-036]
- [ ] CHK103 Is the non-functional requirement that the run report retains at least 90 days (Slice 2 floor reused) explicit? [Non-Functional, Spec §FR-022, Assumptions]
- [ ] CHK104 Is the non-functional requirement that audit artifacts are NOT auto-deleted by the application (operator-only manual pruning) explicit? [Non-Functional, Spec §Assumptions — Local artifact retention]
- [ ] CHK105 Is the non-functional requirement that the CLI surface fits a single CLI / developer command (not a multi-binary tool, not a daemon) explicit? [Non-Functional, Spec §FR-037, FR-038]
- [ ] CHK106 Is the non-functional requirement that the operator surface excludes any custom openCloser visual UI, dashboard, transcript review console, or replacement task queue UI explicit? [Non-Functional, Spec §Constitution Alignment, Assumptions]

## Cross-Cutting UX Concerns

- [ ] CHK107 Is the spec consistent about how the run mode is selected (CLI flag vs. configuration) — i.e., does FR-001's "explicit flag or equivalent deliberate action" leave ambiguity that the plan must resolve? [Ambiguity, Spec §FR-001, Deferred to Implementation Plan]
- [ ] CHK108 Is the spec consistent that the shadow STT enable/disable surface is both a CLI input (FR-037) and a deployment-configurable toggle (FR-032)? [Consistency, Spec §FR-032, FR-037]
- [ ] CHK109 Is the spec free of conflict between "operator identity is captured on the local session and run report" and "operator identity MUST NOT be propagated into Dynamics"? [Consistency, Spec §FR-016, Clarifications]
- [ ] CHK110 Is the spec consistent between Slice 1 / Slice 2 demo evidence (run report, local audit artifacts, Dynamics records) and Slice 3's superset (adds callbacks audit log, conflicting-events audit log, shadow STT artifacts and discrepancy records when enabled)? [Consistency, Spec §FR-038, Assumptions]
- [ ] CHK111 Does the spec address whether the CLI run produces stdout / stderr output suitable for piping to other tools, or whether file-only output is the contract? [Gap, Spec §FR-037, FR-038]
- [ ] CHK112 Does the spec address localization or language of operator-visible messages / run report content? [Gap, Spec §FR-036]
- [ ] CHK113 Does the spec address the operator UX for retention-mode disclosure (e.g., that the session-result artifact MUST include the retention mode the operator can read)? [Coverage, Spec §FR-033]
- [ ] CHK114 Does the spec address an explicit "no clinical workflows / no PHI collection" operator-visible reminder in the run report or readiness report? [Gap, Spec §Constitution Alignment, Assumptions — Compliance scope]
- [ ] CHK115 Is the requirement that the run report names a single final disposition per session (from the Slice 1 disposition enum) explicit? [Clarity, Spec §FR-017, FR-036]
- [ ] CHK116 Is the requirement that any "callback or review Task created" reference in the run report aligns 1:1 with the per-disposition write-back map (no Task created for `do_not_call`, `no_answer`, `voicemail`, `failed`) explicit? [Coverage / Consistency, Spec §FR-024, US1 Acceptance 5, Edge Cases — Mid-call opt-out / DNC]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap] or [Ambiguity].

### Resume operator format on the operator-readable run report (Q12 / FR-016 / FR-036)

- [ ] CHK117 Is the "resumed by X, original operator Y" run-report format defined precisely enough that an operator reading the artifact can unambiguously identify which identity is which (e.g., explicit labels rather than positional order)? [Clarity, Spec §FR-016, Spec §FR-036]
- [ ] CHK118 Is the format unambiguous when the resuming operator and the original operator are the SAME person (e.g., does the report still emit both labels, or does it collapse to a single identity to avoid implying a handoff)? [Gap, Spec §FR-016, Spec §FR-036]
- [ ] CHK119 Is the format readable when there is a CHAIN of resumes by different operators (e.g., original operator A, first resumer B, second resumer C) — does the spec define whether the chain is preserved on the run report or only the most recent resumer is shown? [Gap, Spec §FR-016, Spec §FR-036]
- [ ] CHK120 Does the spec define the operator-visible behavior when the original operator identity is missing or unknown on a resume invocation (e.g., a placeholder string the operator can recognize, not a silently-blank field)? [Gap, Spec §FR-016, Spec §FR-036]
- [ ] CHK121 Is the run-report resume-operator format required on EVERY resume invocation, including rehearsal-mode resumes (resume without the real-call flag), so the operator surface is consistent regardless of run mode? [Coverage, Spec §FR-016, Spec §FR-022, Spec §FR-036]
- [ ] CHK122 Does the spec confirm the resume-operator format is local-only on the run report and MUST NOT appear on any Dataverse record, closing the Round 1 CHK109 consistency check for the resume case? [Consistency, Spec §FR-016, Spec §FR-036, closes CHK109]

### Real-call flag absence on resume — operator-visible mode disclosure (Q13 / FR-022)

- [ ] CHK123 Does the spec require that an operator who omits the real-call flag on a resume invocation sees a clear operator-visible message indicating the resume is running in rehearsal mode (so the operator cannot mistake the no-op for a successful mutation)? [Completeness, Spec §FR-001, Spec §FR-022, Spec §FR-037]
- [ ] CHK124 Is the rehearsal-resume operator-visible disclosure required in BOTH the CLI output and the run report (so an operator looking at either surface knows the mutation did not happen)? [Coverage, Spec §FR-022, Spec §FR-036, Spec §FR-037]
- [ ] CHK125 Does the spec define the precise wording principle or required content of the rehearsal-resume disclosure (e.g., must name "rehearsal mode", must name "no Dataverse mutation", must list the writes that WOULD have been performed)? [Ambiguity, Spec §FR-022, Spec §FR-036]
- [ ] CHK126 Is the operator-visible distinction between a rehearsal-resume run report and a real-call-resume run report readable at a glance (e.g., a distinct run-mode field value, not a buried sub-field), closing the Round 1 CHK010 [Gap] on rehearsal-on-resume? [Clarity, Spec §FR-022, Spec §FR-036, closes deployment CHK010]
- [ ] CHK127 Does the spec require that the rehearsal-resume run report enumerates which writes the resume WOULD have performed (so the operator can re-invoke with the flag and know what is pending)? [Completeness, Spec §FR-022, Spec §FR-002, Spec §FR-036]
- [ ] CHK128 Is the operator-ergonomics risk of a forgotten flag mitigated in spec wording (e.g., explicit safety property that an operator who forgot the flag MUST NOT think the Dataverse write succeeded)? [Measurability, Spec §FR-022, Spec §FR-001]
- [ ] CHK129 Does the spec address whether the rehearsal-resume disclosure MUST also appear on a non-interactive (CI / scripted) invocation, given CHK013's open question about non-interactive invocation behavior? [Gap, Spec §FR-022, Spec §FR-037]

### Rejected-by-auth count surfacing on the run report (Q9 / FR-008 / FR-036)

- [ ] CHK130 Is the rejected-by-authentication callbacks count required on the run report as a distinct, operator-readable field (not buried inside a generic callbacks count)? [Clarity, Spec §FR-008, Spec §FR-036]
- [ ] CHK131 Is the rejected-by-authentication count visually / structurally distinct from the duplicate / out-of-order callbacks audit row count on the run report (so an operator can tell forged-callback attempts apart from provider retries)? [Clarity, Spec §FR-008, Spec §FR-036]
- [ ] CHK132 Does the spec define what the operator should do when the rejected-by-authentication count is non-zero on a session (e.g., is there a recommended investigation surface, or is the count purely informational)? [Gap, Spec §FR-008, Spec §FR-036]
- [ ] CHK133 Is the rejected-by-authentication count required on EVERY run report including rehearsal-mode runs and blocked-before-dial runs (where no callbacks could have been received), so the field's absence-vs-zero distinction is unambiguous? [Coverage, Spec §FR-008, Spec §FR-036]

### Grace-window surfacing on the run report (Q7 / FR-029)

- [ ] CHK134 Does the run report identify whether the grace window was used for the session (i.e., did the orchestrator hold the write-back for the shadow lane to drain, or did it write through immediately)? [Completeness, Spec §FR-029, Spec §FR-036]
- [ ] CHK135 Does the run report identify whether the shadow lane PARTICIPATED in the disposition within the grace window (vs. timed out and triggered a `shadow_lane_truncated` event)? [Completeness, Spec §FR-029, Spec §FR-036]
- [ ] CHK136 Is the grace-window value used for the session readable on the run report (so an operator can reproduce or tune the behavior)? [Clarity, Spec §FR-029, Spec §FR-036]
- [ ] CHK137 Is the `shadow_lane_truncated` event count (or boolean) operator-visible on the run report, so an operator can detect post-finalization truncation without inspecting audit logs? [Coverage, Spec §FR-029, Spec §FR-036]
- [ ] CHK138 Is the grace-window surfacing required regardless of shadow STT outcome (enabled-and-participated, enabled-and-truncated, enabled-and-failed, disabled), so the operator can distinguish each case from the run report alone? [Consistency, Spec §FR-029, Spec §FR-032, Spec §FR-036]

### PHI redaction surfacing — operator sees "PHI redacted" without seeing the PHI (Q11 / FR-015 / FR-033)

- [ ] CHK139 Does the spec require an operator-visible indication on the run report (and/or session-result artifact) that a `phi_collection_risk` escalation occurred AND that the tag-and-redact pass ran, without the run report itself exposing the PHI? [Completeness, Spec §FR-015, Spec §FR-033, Spec §FR-036]
- [ ] CHK140 Is the operator-visible PHI-redacted indicator distinct from the generic default-on redaction indicator (CHK041), so an operator can see that a PHI-specific event occurred? [Clarity, Spec §FR-015, Spec §FR-033, Spec §FR-036]
- [ ] CHK141 Does the spec prohibit the operator-visible PHI-redacted indicator from including the redacted text, the utterance location, or any other content that would defeat the redaction guarantee? [Coverage, Spec §FR-015, Spec §FR-035]
- [ ] CHK142 Is the redacted-summary readability requirement explicit (the summary, after redaction, is still operator-readable enough to explain the outcome per SC-017, even though PHI tokens are replaced with `[REDACTED]` or equivalent)? [Measurability, Spec §FR-015, Spec §FR-033, Spec §SC-017]
- [ ] CHK143 Does the spec address operator-visible behavior on the shadow STT transcript and discrepancy records when PHI redaction has run (i.e., the operator reviewing a shadow discrepancy sees the redacted form, not the PHI, even though the shadow lane independently transcribed the same audio)? [Coverage, Spec §FR-015, Spec §FR-034]

### DNC-first ordering surfacing on the run report (Q14 / FR-024 / FR-036)

- [ ] CHK144 Does the run report's per-write-back-operation status (FR-036) reflect the DNC-first ordering for `do_not_call` outcomes — i.e., on a `do_not_call` session, the DNC field write status is reported BEFORE the queue-status update, Phone Call activity, and Task statuses? [Clarity, Spec §FR-024, Spec §FR-036]
- [ ] CHK145 Is the DNC-first status surfaced as a distinct per-operation row (or equivalent structured representation) on the run report, rather than merged into the queue-status update row (since FR-020 treats DNC as a field-level variant of queue-status update but FR-024 requires it to be sequenced first)? [Ambiguity, Spec §FR-024, Spec §FR-020, Spec §FR-036]
- [ ] CHK146 Does the spec require an operator-visible "contact is protected" indicator on the run report when the DNC-first write succeeds even if a later write in the sequence fails (so the operator can confirm DNC safety from the artifact)? [Completeness, Spec §FR-024, Spec §FR-036]
- [ ] CHK147 Is the operator-visible behavior defined when the DNC-first write itself fails on a real-call `do_not_call` outcome (e.g., an alarming surface on the run report, not a buried sub-field) — so the operator knows the contact may not be protected? [Gap, Spec §FR-024, Spec §FR-036]
- [ ] CHK148 Is the DNC-first ordering preserved and surfaced consistently for mid-call opt-out (persona terminates mid-call) AND end-of-call `do_not_call` disposition, so the operator sees the same ordering regardless of how the disposition was reached? [Consistency, Spec §FR-024, Spec §FR-015, Spec §FR-036]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### `opencloser run3` CLI option clarity (Contract cli-slice3.md)

- [ ] CHK149 Is the purpose of each of the seven `opencloser run3` options (`--campaign-id`, `--queue-item-id`, `--real-call`/`--write`, `--shadow-stt`/`--no-shadow-stt`, `--operator-id`, `--resume`, `--config`) documented unambiguously in the CLI contract with required-vs-optional, default value, and operator-visible effect? [Clarity, Contract: cli-slice3.md, Research §8]
- [ ] CHK150 Is the equivalence of `--real-call` and `--write` (same flag, two spellings) stated unambiguously in the CLI contract so an operator reading either name reaches the same default-safe-mode behavior? [Ambiguity, Contract: cli-slice3.md, Quickstart §3]
- [ ] CHK151 Is the precedence between `--shadow-stt` / `--no-shadow-stt` and the `config/slice3.toml` `[shadow_stt].enabled_default` value defined so an operator can predict the shadow lane state from inspecting the CLI invocation alone? [Clarity, Contract: cli-slice3.md, Research §11, Quickstart §6]
- [ ] CHK152 Is the `--operator-id` default behavior (`$USER` env var) documented in the CLI contract AND surfaced to the operator at invocation time (e.g., echoed in stdout / the run report) so an operator can confirm which identity was captured? [Completeness, Contract: cli-slice3.md, Research §8, Spec §FR-016]
- [ ] CHK153 Is the CLI's behavior with `--resume <session_id>` against a session that does not exist in local state defined for the operator (rejected with which exit code, what message, no Dataverse touch)? [Gap, Contract: cli-slice3.md]
- [ ] CHK154 Is the CLI's behavior defined when BOTH `--campaign-id` / `--queue-item-id` AND `--resume` are supplied — does resume override the campaign/queue selectors, do they have to match, or is it an error? [Ambiguity, Contract: cli-slice3.md, Gap]
- [ ] CHK155 Is the `--config <path>` option's precedence over env vars defined so an operator can predict which source wins when both supply the same key? [Clarity, Contract: cli-slice3.md, Research §11]

### Rehearsal-mode default vs. real-call-mode opt-in clarity to a first-time operator (Quickstart §2-§3)

- [ ] CHK156 Does Quickstart §2 make rehearsal mode unmistakably the default path (e.g., explicit `Note: no --real-call / --write flag → rehearsal mode` callout) so a first-time operator does not need to read the spec to understand the default? [Clarity, Quickstart §2, Spec §FR-002]
- [ ] CHK157 Is the rehearsal-mode-first instruction ("ALWAYS start with a rehearsal run against the same queue item") prominent enough that a first-time operator cannot reasonably skip it? [Clarity, Quickstart §2]
- [ ] CHK158 Does Quickstart §3 explicitly state that `--real-call` is REQUIRED on every Dataverse-mutating invocation including resume (Round 2 Q13), so a first-time operator does not inherit a sticky promotion mental model? [Consistency, Quickstart §3, Contract: cli-slice3.md, Spec §FR-001]

### Exit-code coverage mapping (Contract cli-slice3.md ↔ Quickstart §8)

- [ ] CHK159 Are each of the eight exit codes (0-7) each mapped to a specific named outcome in the CLI contract? [Coverage, Contract: cli-slice3.md]
- [ ] CHK160 Does every non-zero exit code (1-7) appear in BOTH the CLI contract's exit-code table AND a readiness/remedies surface in quickstart (§2 expected-codes table OR §8 common-readiness-failures table) so an operator never sees a code without a referenceable remediation? [Consistency, Contract: cli-slice3.md, Quickstart §2, Quickstart §8, Gap]
- [ ] CHK161 Does Quickstart §8's common-readiness-failures table cover every readiness-check name enumerated in Contract cli-slice3.md (signalwire_credentials, source_caller_id_authorized, destination_phone_e164, status_callback_url_configured, media_callback_url_configured, campaign_persona_runtime_mapping, dataverse_metadata_verified, task_owner_mapping_resolved, eligibility) with a "Likely cause" + "Remedy" pair? [Coverage, Quickstart §8, Contract: cli-slice3.md, Data-Model §1.9]
- [ ] CHK162 Are exit codes 1 (unexpected error) and 2 (bad CLI usage) — which are NOT mapped to a readiness check — defined for the operator with a clear next-step instruction (e.g., "check stderr" / "see usage")? [Clarity, Contract: cli-slice3.md]
- [ ] CHK163 Is exit code 7 (Dataverse-unreachable-at-start) referenced from a quickstart troubleshooting surface so an operator hitting it has an entry point to fix it? [Gap, Contract: cli-slice3.md, Quickstart §2]

### Resume operator format in the run report (Quickstart §4-§5)

- [ ] CHK164 Does the example `run_report.json` in Quickstart §4 (or §5) include the human-readable "resumed by X, original operator Y" string format documented in Contract cli-slice3.md and Spec Round 2 Q12 — not only the structured `operator_identity: {current, original}` object? [Gap, Quickstart §4, Quickstart §5, Contract: cli-slice3.md]
- [ ] CHK165 Is the example run report's `operator_identity.original` field shown both as `null` (first invocation, Quickstart §4) AND as a non-null value (resume by different operator, Quickstart §5) so the operator can visually confirm the resume-path shape? [Completeness, Quickstart §4, Quickstart §5, Data-Model §2.1]
- [ ] CHK166 Is the resume operator format consistent between the CLI contract's "human-readable 'resumed by X, original operator Y' string" wording (Contract cli-slice3.md §Resume operator identity) and the example run report shown in Quickstart? [Consistency, Contract: cli-slice3.md, Quickstart §4]

### Planned vs. actual write-back artifact distinctions (Data-Model §4 ↔ Quickstart §2/§3)

- [ ] CHK167 Does the artifacts directory layout make the planned/actual distinction unambiguous — `planned_writeback.json` appears in BOTH rehearsal-mode AND real-call-mode outputs, while `actual_writeback.json` appears ONLY in real-call mode? [Clarity, Data-Model §4, Quickstart §2, Quickstart §3]
- [ ] CHK168 Are the contents of `planned_writeback.json` in rehearsal mode required to match the contents of `actual_writeback.json` in real-call mode for the same disposition (modulo the real_provider_call_id and connected-call timestamps) so an operator can use rehearsal as a true preview? [Consistency, Quickstart §2, Quickstart §3, Spec §FR-002]
- [ ] CHK169 Does the operator-visible UX define how to inspect the diff between `planned_writeback.json` and `actual_writeback.json` after a real-call run so they can confirm "what was planned == what was emitted"? [Gap, Data-Model §4, Quickstart §3]

### Shadow-STT toggle effect on the artifacts directory layout (Data-Model §4 ↔ Quickstart §6)

- [ ] CHK170 Does the artifacts directory documentation make it unambiguous which files appear only when shadow STT is enabled (`shadow_transcript.txt`, `shadow_discrepancies.jsonl`, `shadow_lane_truncated.json`) vs. always present (`run_report.json`, `telephony_readiness.json`)? [Clarity, Data-Model §4, Quickstart §3]
- [ ] CHK171 Is the operator-facing behavior of the run report's `shadow_stt.enabled` field defined for both enabled and disabled states (Quickstart §6 says the loop completes with shadow STT disabled — does the report explicitly reflect that)? [Coverage, Quickstart §6, Spec §FR-032, Contract: cli-slice3.md]
- [ ] CHK172 Is the absence of `shadow_transcript.txt`, `shadow_discrepancies.jsonl`, and `shadow_lane_truncated.json` from the artifacts directory when shadow STT is disabled documented as an expected outcome (not an error) so an operator does not file a false bug? [Gap, Data-Model §4, Quickstart §6]
- [ ] CHK173 Are the conditional artifacts whose presence depends on session-internal outcomes (`rejected_auth_callbacks.jsonl` if any forged callbacks; `conflicting_callbacks_audit.jsonl` if any late callbacks; `shadow_discrepancies.jsonl` if any discrepancies; `shadow_lane_truncated.json` if the lane was truncated) ENUMERATED in Quickstart §3's directory layout with their conditional appearance noted? [Coverage, Quickstart §3, Data-Model §4]
- [ ] CHK174 Is the operator-visible relationship between the `--shadow-stt` / `--no-shadow-stt` CLI flag and the resulting `run_report.json` `shadow_stt` block (enabled state, discrepancy summary, lane_truncated) defined so an operator can verify their intended toggle took effect? [Clarity, Quickstart §4, Quickstart §6, Contract: cli-slice3.md]

### Run-report field consistency across plan-side artifacts

- [ ] CHK175 Are the run-report fields enumerated in Contract cli-slice3.md (§Run report) identical to the example shown in Quickstart §4 — no field appears in one and is missing from the other? [Consistency, Contract: cli-slice3.md, Quickstart §4, Data-Model §1.10]
- [ ] CHK176 Is the `per_writeback_operation_status` ordering on a `do_not_call` outcome (DNC variant first per Round 2 Q14) demonstrated in BOTH the Quickstart §3 expected-records table AND the example run report in Quickstart §4 so an operator can verify it without cross-referencing the contracts? [Consistency, Quickstart §3, Quickstart §4, Contract: crm-writeback-dnc-first.md]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] / [Conflict] indicate clarifying language is needed.
- Items marked [Assumption] / [Dependency] indicate where the operator surface relies on a stated assumption or an upstream configuration state.
- ≥80% of items reference a spec section or a quality marker for traceability.
- Visual-UI accessibility items are intentionally excluded because Slice 3 has no visual openCloser UI (see CHK001).
