# Specification Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — the spec names the governing stack components (SignalWire, Pipecat, Dataverse, configured real-time AI provider, shadow STT) only at the boundary where the constitution / MVP PRD already mandates them; specific SDK choices, webhook shapes, pipeline topology, model names/versions, and CLI flag spellings are explicitly deferred to `/speckit.plan`.
- [x] Focused on user value and business needs — every requirement is grounded in the constitution's CRM-first / thin-slice / safety / auditability principles and the MVP PRD's "one queue item → real call → Dynamics write-back" outcome.
- [x] Written for business stakeholders — requirements are stated in terms of operator behavior, eligibility safety, telephony readiness, persona safety, Dynamics outcomes, audit evidence, and demo posture rather than internal code paths.
- [x] All mandatory sections completed — Constitution Alignment, Definitions, User Scenarios & Testing (with Edge Cases), Requirements (Functional Requirements + Key Entities), Success Criteria, Assumptions, and Deferred to Implementation Plan are all populated.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — the spec uses reasonable defaults sourced from the constitution, MVP PRD, Slice 1, and Slice 2 specs; deployment-configurable values (live-call abandonment timeout, shadow STT discrepancy policy, transcript retention mode, specific provider credentials) are stated as configurability requirements and listed under Deferred to Implementation Plan rather than blocking clarifications.
- [x] Requirements are testable and unambiguous — every FR-NNN is stated as a single MUST / MUST NOT / SHOULD behavior with an observable outcome (Dynamics state, run-report contents, audit-artifact contents, attempt-count semantics, callback-handling behavior). Each user story carries an Independent Test description that names the observable evidence.
- [x] Success criteria are measurable — SC-001 through SC-018 use concrete metrics (exactly-one, 100%, 0 false / duplicate / secret-bearing, "no observable slowdown attributable to the shadow lane", named-check-in-readiness-report, "rehearsal places 0 SignalWire calls and creates or updates 0 Dynamics records").
- [x] Success criteria are technology-agnostic — outcomes are stated in terms of operator-visible behavior, Dynamics records, audit-artifact contents, and run-report contents; SignalWire / Pipecat / shadow STT references are confined to where the constitution / MVP PRD already names them as the in-scope MVP boundary.
- [x] All acceptance scenarios are defined — seven user stories, each with two-to-nine Given/When/Then acceptance scenarios covering happy path, rehearsal, blocked paths, idempotency, persona safety, shadow STT, and recovery.
- [x] Edge cases are identified — the Edge Cases section enumerates SignalWire callback ordering, duplicate callbacks, abandoned calls, mid-call opt-out, PHI/out-of-allowed-claim attempts, runtime failure mid-call, real-dial phone-number validation, credentials suspension mid-run, unreachable callback URLs, provider 4xx on dial, partial CRM write-back, shadow STT mismatch, shadow STT lane failure, transcript retention modes, default-on redaction, metadata drift between rehearsal and real-call run, CRM queue item changed between claim and write-back, and resume with retention disabled.
- [x] Scope is clearly bounded — Constitution Alignment, Definitions, and Assumptions state what Slice 3 adds, what it preserves from Slice 1 and Slice 2 unchanged, and what is explicitly out of scope (Flutter admin app and admin/install UI, multi-provider telephony, app voice/video, clinical workflows, opportunity creation, Dograh-as-required-runtime, distributed job queues, batch processing, automatic sales qualification beyond the approved fields).
- [x] Dependencies and assumptions identified — Assumptions section lists Slice 1 / Slice 2 contract preservation, bench ownership (`py-bench` for Feature 003; Flutter work in Features 004+), single campaign / single item, first-and-only telephony provider (SignalWire), voice runtime path (Pipecat + configured real-time AI provider), persona policy preservation, default safe mode, hard E.164 validation, live-call abandonment timeout configurability, shadow STT toggle + discrepancy policy configurability, transcript retention modes, backwards-compatible call ID correlation, compliance scope, local artifact retention floor, operator surface, and CRM as control plane.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria — the Requirement Coverage Notes map each FR to specific user stories, acceptance scenarios, and SC entries; no FR is orphaned.
- [x] User scenarios cover primary flows — User Story 1 (real call + write-back end-to-end), User Story 2 (rehearsal default), User Story 3 (blocked unsafe dialing), User Story 4 (SignalWire callback / duplicate / failure idempotency), User Story 5 (live Pipecat + persona safety), User Story 6 (shadow STT non-blocking + discrepancy), User Story 7 (transient recovery) collectively cover the MVP PRD's Slice 3 acceptance criteria.
- [x] Feature meets measurable outcomes defined in Success Criteria — SC-001 through SC-018 are sufficient to certify the "smallest independently demonstrable outcome" stated in Constitution Alignment and the MVP PRD: one eligible Dataverse-owned ALF queue item moves from `ready` to a final disposition after a real SignalWire call with the correct Dynamics write-back, with hard pre-dial safety gates, idempotency under duplicate provider callbacks and retries, persona safety preserved, shadow STT non-blocking, and demonstrable evidence without a custom openCloser UI.
- [x] No implementation details leak into specification — SDK choice, webhook shape mapping table, Pipecat pipeline topology, real-time AI model name/version, shadow STT provider, CLI flag spellings, file-naming conventions, and timeout default values are all deferred to `/speckit.plan` via the Deferred to Implementation Plan section.

## Notes

- Validation iteration: 1. All checklist items pass on the first iteration. No `[NEEDS CLARIFICATION]` markers were introduced — the spec relies on already-clarified Slice 1 and Slice 2 contracts and the MVP PRD / Architecture / ALF PRD for any decision that would otherwise need clarification. Open-ended deployment-configurable values (timeouts, discrepancy policy thresholds, retention defaults, provider choices) are stated as configurability requirements and routed to `/speckit.plan`.
- Forward-compatibility check: The spec applies only the name-only changes catalogued in the Slice 1 SC-008 forward-compatibility review (`mock_provider_call_id` → `provider_call_id`, `MockCallEvent` → `CallEvent`, `fixture_id` → `dial_plan`) and one additive entry to the Slice 1 `human_review_reason` enumeration (`shadow_stt_discrepancy`). No Slice 1 / Slice 2 contract is weakened or deleted.
- Bench ownership: Feature 003 is fully owned by `py-bench`. Flutter admin/install/dashboard work is scoped to Features 004+ in `flutterBench` and is explicitly excluded from this spec.
- Items marked incomplete: none.

---

# Cross-Cutting Requirements Quality (Release Gate)

**Appended**: 2026-05-25 — `/speckit-checklist go wide and go deep. max coverage and max depth`
**Depth**: Release gate (maximum coverage, all five scenario classes per applicable domain)
**Scope**: Cross-cutting requirement-quality dimensions — Completeness, Clarity, Consistency, Acceptance Criteria Quality, Dependencies & Assumptions, Ambiguities & Conflicts. Per-domain checklists live alongside this file (api.md, data-model.md, integration.md, ux.md, error-handling.md, idempotency.md, testing-strategy.md, observability.md, performance.md, configuration.md, deployment.md, security.md, persona-safety.md, shadow-stt.md, telephony-readiness.md, compliance.md).
**Domains intentionally excluded**: `accessibility` — Slice 3 has no visual UI (operator surface is CLI / API / Dynamics records / local artifacts) and no caller-side accessibility surface (the persona is a one-way outbound voice conversation with adult ALF staff; TTY / hearing-impairment caller paths are out of scope for the MVP and would require an independent PRD).

## Completeness — global

- [ ] CHK001 Are all functional requirements traceable to at least one user story AND at least one success criterion via the Requirement Coverage Notes? [Completeness, Spec §Requirement Coverage Notes]
- [ ] CHK002 Is every Slice 3 disposition in FR-017 represented by at least one acceptance scenario across User Stories 1–7? [Completeness, Spec §FR-017]
- [ ] CHK003 Is every readiness-check category enumerated in FR-009 also exercised by a User Story 3 acceptance scenario? [Completeness, Spec §FR-009]
- [ ] CHK004 Are the three Slice 3 additions (SignalWire transport, Pipecat runtime, shadow STT lane) each bound by an explicit MUST-NOT-leak boundary rule? [Completeness, Spec §Constitution Alignment]
- [ ] CHK005 Are all six rehearsal-mode acceptance scenarios (Story 2) backed by at least one FR-002 sub-clause? [Completeness, Spec §FR-002]
- [ ] CHK006 Are all Slice 1 / Slice 2 contracts the spec claims to preserve enumerated by name (not just referenced as "Slice 1/2 contracts")? [Completeness, Spec §Assumptions]
- [ ] CHK007 Does the spec enumerate every Dataverse write the Slice 3 adapter may make (Phone Call activity, queue-status update, Task, DNC/opt-out field write, blocked-status field write)? [Completeness, Spec §FR-020 / FR-023 / FR-024]
- [ ] CHK008 Are all artifacts the run produces (run report, session-result, transcript or pointer, planned/actual write-back payloads, callbacks audit log, conflicting-events audit log, shadow STT artifact, discrepancy records, telephony readiness report) enumerated together in one place rather than scattered? [Completeness, Spec §FR-038]
- [ ] CHK009 Are the inputs required for a Slice 3 invocation (campaign selector, queue-item selector, persona/runtime config, SignalWire config, shadow STT toggle, run mode) listed in a single requirement and consistent with the operator-interface section? [Completeness, Spec §FR-037]
- [ ] CHK010 Does the spec state what happens when the configured real-time AI provider is unconfigured at invocation (vs. unreachable mid-call)? [Gap]
- [ ] CHK011 Does the spec state what happens when the shadow STT discrepancy policy file is missing or malformed at invocation? [Gap]
- [ ] CHK012 Does the spec state what happens when the configured persona/runtime mapping resolves to a persona that does not exist? [Gap]
- [ ] CHK013 Does the spec define the live-conversation turn-latency target the live model + Pipecat path must achieve? [Gap, Performance]

## Clarity — vague-adjective audit

- [ ] CHK014 Is "brief pause" in the disclosure-acknowledgment clarification quantified or explicitly left to persona configuration? [Clarity, Ambiguity, Spec §FR-015]
- [ ] CHK015 Is "no observable slowdown attributable to the shadow lane" in SC-013 operationalized (latency-budget delta, p95 turn delay, or a named test harness)? [Measurability, Spec §SC-013]
- [ ] CHK016 Is "high-value field" defined in exactly one place and referenced consistently everywhere the term appears? [Clarity, Consistency, Spec §Definitions / FR-030]
- [ ] CHK017 Is "live-call abandonment timeout" stated as a single named timeout consistently across the Definitions, FR-026, the live-runtime degradation edge case, and Deferred to Plan? [Consistency, Spec §FR-026 / Definitions / Edge Cases]
- [ ] CHK018 Is "silence-after-connection / no-extraction-event timeout" stated as a distinct timeout from "live-call abandonment timeout" everywhere it appears? [Clarity, Spec §FR-013]
- [ ] CHK019 Is "approved blocked-status write" defined or cross-referenced to the Slice 1 / Slice 2 source of truth? [Clarity, Spec §FR-011]
- [ ] CHK020 Is "provider-acceptable" (in "E.164 or a provider-acceptable equivalent") defined or scoped to the SignalWire transport? [Clarity, Spec §FR-010]
- [ ] CHK021 Is "verified Dataverse mapping" (used in FR-009 readiness checks) defined or cross-referenced to the Slice 2 two-phase verification gate? [Clarity, Spec §FR-009]
- [ ] CHK022 Is "operator-visible" (used across FR-011 / FR-036 and Story 3 scenarios) operationalized — is operator visibility CLI stdout, run report file, both, or deployment-configurable? [Clarity, Spec §FR-011 / FR-036]
- [ ] CHK023 Is "configurable timeout" in the live-call abandonment definition explicitly tagged as deployment configuration (vs. CLI flag) anywhere the term is used? [Clarity, Spec §Definitions]

## Consistency — cross-section alignment

- [ ] CHK024 Are the renames (`mock_provider_call_id` → `provider_call_id`, `MockCallEvent` → `CallEvent`, `fixture_id` → `dial_plan`) applied consistently across Definitions, FR-006, FR-018, Key Entities, Assumptions, and the normalized-result shape in FR-017? [Consistency, Spec §FR-018 / Assumptions]
- [ ] CHK025 Is the additive `shadow_stt_discrepancy` reason consistently described as "additive to Slice 1 enumerated set" across FR-031, Assumptions, and Key Entities? [Consistency, Spec §FR-031 / Assumptions]
- [ ] CHK026 Are the per-disposition write-back emission decisions stated only once (by reference to Slice 1 / Slice 2) rather than re-enumerated in Slice 3, to prevent drift? [Consistency, Spec §FR-020]
- [ ] CHK027 Does FR-013's degradation-trigger mapping (connected → `script_truncated`; pre-connected → `failed`) match the corresponding edge case exactly? [Consistency, Spec §FR-013 / Edge Cases]
- [ ] CHK028 Does FR-003's concurrent-claim contract match the new edge-case entry word-for-word on the "no dial / no attempt / no Phone Call activity" assertions? [Consistency, Spec §FR-003 / Edge Cases]
- [ ] CHK029 Is the Slice 2 retention floor ("≥ 90 days") referenced identically in FR-022, Assumptions ("Local artifact retention"), and any audit-log entity definition? [Consistency, Spec §FR-022 / Assumptions]
- [ ] CHK030 Are the FR-009 readiness checks and the Story 3 Independent Test categories one-for-one (no readiness check missing a test category, no test category missing a readiness check)? [Consistency, Spec §FR-009 / Story 3 Independent Test]
- [ ] CHK031 Is the "operator identity" capture rule (local-only, not in Dynamics) consistent between FR-016 and FR-036? [Consistency, Spec §FR-016 / FR-036]

## Acceptance Criteria Quality

- [ ] CHK032 Does every acceptance scenario name an observable evidence source (Dynamics record, run report field, audit-log entry, normalized-result field)? [Acceptance Criteria, Spec §User Scenarios & Testing]
- [ ] CHK033 Does every Success Criterion (SC-001 – SC-018) state a measurable threshold (exact-one, 100%, 0, ≥, named field)? [Acceptance Criteria, Spec §Success Criteria]
- [ ] CHK034 Are "100%" success criteria scoped to a clearly bounded population (e.g., "100% of duplicate SignalWire callbacks" — is "duplicate" defined?)? [Acceptance Criteria, Spec §SC-008]
- [ ] CHK035 Are negative-evidence success criteria (e.g., "0 secrets in logs", "0 false connected-call Phone Call activities") testable by a named artifact-inspection procedure? [Acceptance Criteria, Spec §SC-007 / SC-018]
- [ ] CHK036 Does the spec name a single canonical demo-evidence checklist that the Slice 3 acceptance run can be evaluated against? [Acceptance Criteria, Spec §FR-038 / Deferred to Plan]

## Dependencies & Assumptions

- [ ] CHK037 Is every external dependency (SignalWire, Pipecat, configured real-time AI provider, shadow STT provider, Dynamics / Dataverse) listed under Assumptions with a clear failure-mode plan? [Dependency, Spec §Assumptions]
- [ ] CHK038 Is the assumption "Dataverse is the operational source of truth" called out as a Slice 3 invariant (not just inherited silently from Slice 2)? [Assumption, Spec §Assumptions]
- [ ] CHK039 Are the Slice 1 / Slice 2 contract dependencies listed by name (eligibility decision, normalized session result, per-disposition write-back map, idempotency-key stamping, bounded retry, resume behavior, metadata verification, high-confidence value preservation, owner/team mapping)? [Dependency, Spec §Assumptions]
- [ ] CHK040 Does the spec state which Slice 2 deferred-to-plan items (if any) Slice 3 now requires answered (or explicitly re-defers)? [Dependency, Gap]
- [ ] CHK041 Is the assumption "compliance scope is non-clinical ALF business outreach" stated and tied to the PHI-exclusion guarantee? [Assumption, Spec §Assumptions]

## Ambiguities & Conflicts

- [ ] CHK042 Is there any place where "rehearsal / readiness mode" and "dry-run" are used interchangeably without a definition pointer? [Ambiguity, Spec §Definitions]
- [ ] CHK043 Is there any conflict between FR-022's resume contract and FR-026's live-call abandonment finalization on a session where SignalWire delivered an `answered` callback but never a terminal event? [Conflict, Spec §FR-022 / FR-026]
- [ ] CHK044 Is the persona's authority over disposition (FR-014) stated in a way that cannot be misread as forbidding the live model from emitting extraction events that influence the deterministic precedence inputs? [Ambiguity, Spec §FR-014]
- [ ] CHK045 Is FR-016's "operator identity" definition tight enough to disambiguate OS user vs. a CLI-provided operator id vs. an SSO-derived id? [Ambiguity, Spec §FR-016]
- [ ] CHK046 Is there any conflict between FR-029 ("shadow STT MUST NOT slow the live call") and FR-031 ("uncertain discrepancy escalates to `needs_human_review`") on a session where the shadow lane is still producing comparisons at the moment the orchestrator wants to finalize? [Conflict, Spec §FR-029 / FR-031]
- [ ] CHK047 Are there any Slice 3 requirements that introduce a write to Dataverse outside the four Slice 2 write-back operations (Phone Call activity, queue-status update, Task, write-back assembly)? [Conflict, Spec §FR-020]

## Scenario-class coverage (cross-cutting)

- [ ] CHK048 Is at least one acceptance scenario present for the Primary class (`interested_callback_requested` end-to-end)? [Coverage, Spec §Story 1 #1]
- [ ] CHK049 Is at least one acceptance scenario present for the Alternate class (`interested_email_captured`, `not_interested`, `call_back_later`, `wrong_number`)? [Coverage, Spec §Story 1 #2]
- [ ] CHK050 Is at least one acceptance scenario present for the Exception/Error class (provider 4xx, runtime crash, metadata drift, transient Dataverse error)? [Coverage, Spec §Story 4 / Story 7]
- [ ] CHK051 Is at least one acceptance scenario present for the Recovery class (orchestrator restart mid-call, retry / resume on partial write-back, callback re-delivery after transient failure)? [Coverage, Spec §Story 4 / Story 7]
- [ ] CHK052 Is at least one acceptance scenario present for the Non-Functional class (no-secrets-in-artifacts, shadow STT non-blocking, retention modes honored)? [Coverage, Spec §SC-013 / SC-018 / Edge Cases]
- [ ] CHK053 Is any scenario class missing from any individual user story for which it would apply (e.g., does Story 5 cover its Recovery class via the runtime-degradation scenario)? [Coverage, Spec §User Scenarios & Testing]

## Traceability hygiene

- [ ] CHK054 Does every FR-NNN entry have a Requirement-Coverage-Notes line that maps it to a User Story + an SC? [Traceability, Spec §Requirement Coverage Notes]
- [ ] CHK055 Is the operator-identity addition (FR-016 / FR-036) reflected in the Requirement Coverage Notes (or is the omission deliberate)? [Traceability, Gap]
- [ ] CHK056 Is the concurrent-CLI-invocation addition (FR-003) reflected in the Requirement Coverage Notes? [Traceability, Gap]
- [ ] CHK057 Is the live-runtime degradation-trigger expansion (FR-013) reflected in the Requirement Coverage Notes? [Traceability, Gap]
- [ ] CHK058 Are the Clarifications-session bullets keyed back to the FRs they amended (so a reader can find the change without diffing)? [Traceability, Spec §Clarifications]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap] or [Conflict].

### Round 2 traceability — every Q has both a Clarifications bullet AND an FR update

- [ ] CHK059 Is Q6 (resume on answered-but-no-terminal-event → immediate `failed` / `live_call_abandonment`) reflected in BOTH the Clarifications "Session 2026-05-25 (Round 2)" subblock AND in FR-026? [Traceability, Spec §Clarifications, Spec §FR-026]
- [ ] CHK060 Is Q7 (post-finalization grace window + `shadow_lane_truncated` audit-only event) reflected in BOTH the Clarifications block AND in FR-029? [Traceability, Spec §Clarifications, Spec §FR-029]
- [ ] CHK061 Is Q8 (DNC / blocked / dial-blocked are field-level variants of the existing queue-status update — four-op count preserved) reflected in BOTH the Clarifications block AND in FR-020? [Traceability, Spec §Clarifications, Spec §FR-020]
- [ ] CHK062 Is Q9 (distinct rejected-by-authentication audit log with `(received_at, source metadata)`, no secret, no body; run-report count) reflected in BOTH the Clarifications block AND in FR-008 AND in FR-036? [Traceability, Spec §Clarifications, Spec §FR-008, Spec §FR-036]
- [ ] CHK063 Is Q10 (default-on redaction covers transcript + summary + shadow transcript + shadow discrepancy records; pointer excluded) reflected in BOTH the Clarifications block AND in FR-033? [Traceability, Spec §Clarifications, Spec §FR-033]
- [ ] CHK064 Is Q11 (PHI-volunteered → `phi_collection_risk` + tag-and-redact across the four artifacts BEFORE write) reflected in BOTH the Clarifications block AND in FR-015 AND in FR-033 AND in the Edge Cases entry? [Traceability, Spec §Clarifications, Spec §FR-015, Spec §FR-033, Spec §Edge Cases]
- [ ] CHK065 Is Q12 (resume preserves original operator on session+audit; records resuming operator on run report) reflected in BOTH the Clarifications block AND in FR-016 AND in FR-036? [Traceability, Spec §Clarifications, Spec §FR-016, Spec §FR-036]
- [ ] CHK066 Is Q13 (real-call flag required on every Dataverse-mutating invocation incl. resume; absence on resume → rehearsal mode) reflected in BOTH the Clarifications block AND in FR-001 AND in FR-022? [Traceability, Spec §Clarifications, Spec §FR-001, Spec §FR-022]
- [ ] CHK067 Is Q14 (DNC write attempted FIRST on `do_not_call`; idempotency prevents duplicates on resume) reflected in BOTH the Clarifications block AND in FR-024? [Traceability, Spec §Clarifications, Spec §FR-024]
- [ ] CHK068 Are there any Round 2 FR amendments that lack a matching Clarifications bullet (no FR amendment without a Q entry), and any Q entries that lack a matching FR update (no clarification stranded in the Clarifications block)? [Traceability, Completeness, Spec §Clarifications, Spec §Requirements]

### Round 1 [Conflict] resolution — re-test the four flagged conflicts

- [ ] CHK069 Does FR-022's resume contract now align with FR-026's live-call abandonment finalization on a session that received `answered` but never a terminal event (resume immediately finalizes as `failed` / `live_call_abandonment`), closing CHK043 from Round 1? [Conflict-Resolution, Spec §FR-022, Spec §FR-026]
- [ ] CHK070 Does FR-029's grace-window addition resolve the FR-029 ↔ FR-031 tension on a session with shadow processing still in-flight at finalization (orchestrator finalizes immediately; CRM write-back is held for the grace window so a late shadow event may participate; otherwise write-back proceeds and the late event is `shadow_lane_truncated`), closing CHK046 from Round 1? [Conflict-Resolution, Spec §FR-029, Spec §FR-031]
- [ ] CHK071 Does FR-020's "DNC opt-out / blocked-status / dial-blocked writes are field-level variants of the existing queue-status update operation; four-op count preserved" close the CHK047 Round-1 conflict (whether Slice 3 introduces a write outside the Slice 2 four operations)? [Conflict-Resolution, Spec §FR-020, Spec §FR-024]
- [ ] CHK072 Does the FR-036 amendment (`telephony_readiness_summary` + rejected-by-authentication count + resume operator format) close the Round 1 CHK012 [Conflict] in observability (Run Report Key-Entity field list vs. FR-036 mismatch)? [Conflict-Resolution, Spec §FR-036, Spec §Key Entities > Run Report]
- [ ] CHK073 Do the Round 2 amendments avoid introducing any NEW conflict between FRs (e.g., DNC-first ordering vs. four-op count; PHI tag-and-redact vs. pointer-machine-readability; grace window vs. FR-029 non-blocking)? [Conflict-Free, Spec §FR-020, Spec §FR-024, Spec §FR-015, Spec §FR-033, Spec §FR-029]

### Round 1 [Gap] hotspot closure — sample re-test of performance.md and security.md

- [ ] CHK074 Does the new Deferred-to-Plan "Performance and latency targets" subsection enumerate the live-conversation turn-latency target (caller audio → SignalWire → Pipecat → real-time AI model → audio response), closing the Round 1 performance.md gap on live-call latency? [Gap-Closure, Spec §Deferred to Implementation Plan > Performance and latency targets, Spec §performance.md CHK013]
- [ ] CHK075 Does the Performance and latency targets subsection cover the shadow-lane back-pressure / FR-029 non-blocking enforcement budget, closing the Round 1 performance.md gap on the shadow-lane processing budget? [Gap-Closure, Spec §Deferred to Implementation Plan > Performance and latency targets, Spec §FR-029]
- [ ] CHK076 Does the Performance subsection cover the duplicate-callback no-op decision latency and callback-storm tolerance, closing the Round 1 performance.md gap on idempotency under high-rate callback floods? [Gap-Closure, Spec §Deferred to Implementation Plan > Performance and latency targets, Spec §FR-021, Spec §FR-027]
- [ ] CHK077 Does the Performance subsection cover the resume-on-re-invocation wall-clock budget and the `completed`-to-write-back recovery time, closing the Round 1 performance.md gap on resume timing? [Gap-Closure, Spec §Deferred to Implementation Plan > Performance and latency targets, Spec §FR-022]
- [ ] CHK078 Does the Performance subsection cover the local artifact write-throughput per retention mode AND the redaction-pass latency contribution, closing the Round 1 performance.md gaps on artifact-write performance? [Gap-Closure, Spec §Deferred to Implementation Plan > Performance and latency targets, Spec §FR-033]
- [ ] CHK079 Does FR-008's rejected-by-authentication audit log + run-report count close the Round 1 security.md gap on detectability of attempted callback forgery? [Gap-Closure, Spec §FR-008, Spec §FR-036]
- [ ] CHK080 Does FR-008's explicit "verification secret MUST NOT be logged" + "callback body MUST NOT be recorded" close the Round 1 security.md gap on reflected-payload leakage in audit logs? [Gap-Closure, Spec §FR-008]
- [ ] CHK081 Does FR-015's PHI tag-and-redact obligation across transcript + summary + shadow transcript + shadow discrepancy records close the Round 1 security.md gap on PHI leakage into derived artifacts? [Gap-Closure, Spec §FR-015, Spec §FR-033]
- [ ] CHK082 Does FR-016's "operator identity captured but local-only" combined with the resume operator preservation close the Round 1 security.md gap on operator-identity audit traceability? [Gap-Closure, Spec §FR-016, Spec §FR-036]
- [ ] CHK083 Does FR-024's DNC-write-first ordering close the Round 1 security.md gap on opt-out durability under partial write-back failure? [Gap-Closure, Spec §FR-024, Spec §FR-022]

### Cross-FR consistency for the new Round 2 concepts

- [ ] CHK084 Is the "rejected-by-authentication audit log" terminology used identically across FR-008, FR-036, the Key Entities section, and the Clarifications block (no variant phrasing)? [Consistency, Spec §FR-008, Spec §FR-036, Spec §Clarifications]
- [ ] CHK085 Is the `shadow_lane_truncated` event named identically across FR-029, the Clarifications block, and any other reference (no variant naming, e.g., `shadow_truncated` / `shadow_late_event`)? [Consistency, Spec §FR-029, Spec §Clarifications]
- [ ] CHK086 Is the "post-finalization grace window" defined consistently across FR-029, the Clarifications block, and the Deferred-to-Plan section (where the default value is deferred)? [Consistency, Spec §FR-029, Spec §Clarifications, Spec §Deferred to Implementation Plan]
- [ ] CHK087 Is the DNC-write-first ordering described consistently across FR-024, the Clarifications block, and FR-020 (the four-op count preservation rationale)? [Consistency, Spec §FR-024, Spec §FR-020, Spec §Clarifications]
- [ ] CHK088 Is the resume operator format ("resumed by X, original operator Y") described consistently across FR-016, FR-036, and the Clarifications block? [Consistency, Spec §FR-016, Spec §FR-036, Spec §Clarifications]
- [ ] CHK089 Is the PHI tag-and-redact artifact list (full transcript + summary + shadow transcript + shadow discrepancy records; pointer excluded) identical across FR-015, FR-033, the Edge Cases entry, and the Clarifications block? [Consistency, Spec §FR-015, Spec §FR-033, Spec §Edge Cases, Spec §Clarifications]
- [ ] CHK090 Is the "resume rehearsal-mode fallback on flag absence" rule (FR-022) consistent with the FR-001 "default invocation MUST NOT mutate Dynamics" rule and with the FR-002 rehearsal-mode contract? [Consistency, Spec §FR-001, Spec §FR-002, Spec §FR-022]

### Requirement Coverage Notes freshness

- [ ] CHK091 Are the Requirement Coverage Notes updated to reflect the FR-008 rejected-by-authentication audit log (or are they stale relative to the Round 2 amendments)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-008]
- [ ] CHK092 Are the Requirement Coverage Notes updated to reflect the FR-015 PHI tag-and-redact addition (or stale)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-015]
- [ ] CHK093 Are the Requirement Coverage Notes updated to reflect the FR-016 resume operator format addition (or stale)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-016]
- [ ] CHK094 Are the Requirement Coverage Notes updated to reflect the FR-022 resume-mode rehearsal fallback (or stale)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-022]
- [ ] CHK095 Are the Requirement Coverage Notes updated to reflect the FR-024 DNC-write-first ordering (or stale)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-024]
- [ ] CHK096 Are the Requirement Coverage Notes updated to reflect the FR-026 resume-on-`answered`-but-no-terminal-event behavior (or stale)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-026]
- [ ] CHK097 Are the Requirement Coverage Notes updated to reflect the FR-029 grace-window + `shadow_lane_truncated` addition (or stale)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-029]
- [ ] CHK098 Are the Requirement Coverage Notes updated to reflect the FR-036 `telephony_readiness_summary` + rejected-by-auth count + resume operator format addition (or stale)? [Traceability, Spec §Requirement Coverage Notes, Spec §FR-036]
- [ ] CHK099 Is the new Deferred-to-Plan "Performance and latency targets" subsection referenced from the Requirement Coverage Notes (or from a "Deferred items" cross-link) so a reader knows performance targets are intentionally not pinned? [Traceability, Spec §Requirement Coverage Notes, Spec §Deferred to Implementation Plan > Performance and latency targets]
- [ ] CHK100 Does the spec's "Clarifications" header ordering (Session 2026-05-25 followed by Session 2026-05-25 (Round 2 — checklist-driven)) make clear which decisions are Round 1 vs. Round 2 so future amendments can chain on cleanly? [Clarity, Spec §Clarifications]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Every spec FR has a plan-side artifact entry (Technical Context row, research decision, data-model entity, contract Protocol, or quickstart step)

- [ ] CHK101 Does FR-001 (real-call / write-enabled flag default-off) have at least one plan-side trace (Plan §Technical Context "Run modes" row + Contract: cli-slice3 "Run-mode default" + Quickstart §3 `--real-call` example)? [Traceability, Spec §FR-001, Plan §Technical Context, Contract: cli-slice3, Quickstart §3]
- [ ] CHK102 Does FR-002 (rehearsal / readiness mode as default) have at least one plan-side trace (Plan §Technical Context "Run modes" + Contract: cli-slice3 §Run-mode default + Quickstart §2 rehearsal walkthrough)? [Traceability, Spec §FR-002, Plan §Technical Context, Contract: cli-slice3, Quickstart §2]
- [ ] CHK103 Does FR-003 (single queue item per invocation + concurrent-claim block) have plan-side traces (Contract: cli-slice3 §Single queue item + §Concurrent same-item invocation + Plan §Constraints "Concurrent CLI invocation...")? [Traceability, Spec §FR-003, Contract: cli-slice3, Plan §Constraints]
- [ ] CHK104 Does FR-004 (SignalWire transport satisfying existing call-transport contract) have plan-side traces (Contract: signalwire-transport §Python protocol + Research §1 SignalWire SDK decision + Plan §Project Structure `transport/signalwire/`)? [Traceability, Spec §FR-004, Contract: signalwire-transport, Research §1, Plan §Project Structure]
- [ ] CHK105 Does FR-005 (SignalWire event normalization + out-of-order/duplicate tolerance) have plan-side traces (Contract: signalwire-transport §event_stream + Data-Model §1.2 `CallEvent` + Research §1)? [Traceability, Spec §FR-005, Contract: signalwire-transport, Data-Model §1.2, Research §1]
- [ ] CHK106 Does FR-006 (real provider call ID assignment) have plan-side traces (Data-Model §1.1 SignalWireDial + Data-Model §2.1 Session.provider_call_id + Contract: signalwire-transport §place_call return type)? [Traceability, Spec §FR-006, Data-Model §1.1, Data-Model §2.1, Contract: signalwire-transport]
- [ ] CHK107 Does FR-007 (status + media callback handling + dedup) have plan-side traces (Contract: signalwire-transport §event_stream + Data-Model §1.3 CallbacksAuditLog + Research §10 file format)? [Traceability, Spec §FR-007, Contract: signalwire-transport, Data-Model §1.3, Research §10]
- [ ] CHK108 Does FR-008 (callback signature verification + rejected-auth audit log + run-report count) have plan-side traces (Research §2 + Contract: rejected-auth-audit-log + Data-Model §1.4 RejectedAuthCallbackLog + Plan §Constraints)? [Traceability, Spec §FR-008, Research §2, Contract: rejected-auth-audit-log, Data-Model §1.4]
- [ ] CHK109 Does FR-009 (telephony readiness check) have plan-side traces (Data-Model §1.9 TelephonyReadinessReport + Contract: cli-slice3 §Required readiness checks + Quickstart §8 readiness failures table)? [Traceability, Spec §FR-009, Data-Model §1.9, Contract: cli-slice3, Quickstart §8]
- [ ] CHK110 Does FR-010 (E.164 validation before dial) have plan-side traces (Contract: signalwire-transport §Real-dial E.164 validation + Data-Model §1.1 `destination_phone` validation note)? [Traceability, Spec §FR-010, Contract: signalwire-transport, Data-Model §1.1]
- [ ] CHK111 Does FR-011 (telephony readiness failure exits before dial) have plan-side traces (Contract: cli-slice3 exit code 4 + Data-Model §6 state-transition `[real-call] → readiness check fail → exit`)? [Traceability, Spec §FR-011, Contract: cli-slice3 §Exit codes, Data-Model §6]
- [ ] CHK112 Does FR-012 (provider-rejected dial — no attempt consumed) have plan-side traces (Contract: signalwire-transport §Provider-rejected dial + Contract: cli-slice3 exit code 5 + Data-Model §1.11 dial_blocked variant)? [Traceability, Spec §FR-012, Contract: signalwire-transport, Contract: cli-slice3, Data-Model §1.11]
- [ ] CHK113 Does FR-013 (Pipecat runtime + degradation triggers a/b/c) have plan-side traces (Contract: pipecat-runtime §Live-runtime degradation triggers + Research §3 + Research §7 silence timeout)? [Traceability, Spec §FR-013, Contract: pipecat-runtime, Research §3, Research §7]
- [ ] CHK114 Does FR-014 (persona ownership of disposition / live model does not set disposition) have plan-side traces (Contract: pipecat-runtime §Deterministic disposition precedence preserved + Research §5 PersonaSink)? [Traceability, Spec §FR-014, Contract: pipecat-runtime, Research §5]
- [ ] CHK115 Does FR-015 (disclosure + PHI escalation + tag-and-redact) have plan-side traces (Contract: pipecat-runtime §AI disclosure + §Caller-volunteered PHI + Data-Model §2.5 RedactionPolicy + Plan §Constraints PHI clause)? [Traceability, Spec §FR-015, Contract: pipecat-runtime, Data-Model §2.5, Plan §Constraints]
- [ ] CHK116 Does FR-016 (persona version + runtime/model identity + operator identity recorded) have plan-side traces (Data-Model §1.12 RealtimeProviderSession + Data-Model §2.1 Session.operator_identity_* + Contract: pipecat-runtime §Runtime/model identity recorded)? [Traceability, Spec §FR-016, Data-Model §1.12, Data-Model §2.1, Contract: pipecat-runtime]
- [ ] CHK117 Does FR-017 (Slice 1 normalized result shape preserved) have plan-side traces (Data-Model §2.2 NormalizedResult + Plan §Constitution Check §III boundaries)? [Traceability, Spec §FR-017, Data-Model §2.2, Plan §Constitution Check]
- [ ] CHK118 Does FR-018 (Slice 1 module boundaries preserved) have plan-side traces (Plan §Constitution Check §III + Plan §Project Structure preserving `core/`, `eligibility/`, `persona/` packages unchanged)? [Traceability, Spec §FR-018, Plan §Constitution Check, Plan §Project Structure]
- [ ] CHK119 Does FR-019 (eligibility behavior preserved) have plan-side traces (Plan §Project Structure `eligibility/` unchanged + Research §14 reused Slice 1 / Slice 2 decisions)? [Traceability, Spec §FR-019, Plan §Project Structure, Research §14]
- [ ] CHK120 Does FR-020 (Slice 2 four-op write-back contract preserved + Slice 3 additive variants) have plan-side traces (Contract: crm-writeback-dnc-first §What MUST NOT change + Data-Model §1.11 WriteBackOperation table + Research §14)? [Traceability, Spec §FR-020, Contract: crm-writeback-dnc-first, Data-Model §1.11, Research §14]
- [ ] CHK121 Does FR-021 (idempotency-key stamping reused) have plan-side traces (Contract: crm-writeback-dnc-first §Idempotency on resume + Data-Model §2.4 IdempotencyKey + Research §14)? [Traceability, Spec §FR-021, Contract: crm-writeback-dnc-first, Data-Model §2.4, Research §14]
- [ ] CHK122 Does FR-022 (bounded retry + resume + ≥90d retention) have plan-side traces (Research §14 + Contract: crm-writeback-dnc-first §Required behaviors + Plan §Project Structure `slice3/resume.py`)? [Traceability, Spec §FR-022, Research §14, Contract: crm-writeback-dnc-first, Plan §Project Structure]
- [ ] CHK123 Does FR-023 (blocked-by-eligibility approved writes only) have plan-side traces (Data-Model §1.11 blocked variant + Contract: crm-writeback-dnc-first §Per-disposition step ordering "blocked" row)? [Traceability, Spec §FR-023, Data-Model §1.11, Contract: crm-writeback-dnc-first]
- [ ] CHK124 Does FR-024 (DNC-first on do_not_call) have plan-side traces (Contract: crm-writeback-dnc-first §DNC-first ordering + Data-Model §1.11 DNC variant "FIRST" + Plan §Summary Round 2 Q14 callout + Quickstart §3 disposition table)? [Traceability, Spec §FR-024, Contract: crm-writeback-dnc-first, Data-Model §1.11, Plan §Summary, Quickstart §3]
- [ ] CHK125 Does FR-025 (attempt-count semantics) have plan-side traces (Data-Model §1.11 blocked variant "no increment" + Contract: crm-writeback-dnc-first §Per-disposition step ordering blocked row)? [Traceability, Spec §FR-025, Data-Model §1.11, Contract: crm-writeback-dnc-first]
- [ ] CHK126 Does FR-026 (live-call abandonment) have plan-side traces (Research §7 abandonment timeout + Contract: cli-slice3 exit code 6 + Plan §Project Structure `slice3/resume.py` Q6 callout)? [Traceability, Spec §FR-026, Research §7, Contract: cli-slice3, Plan §Project Structure]
- [ ] CHK127 Does FR-027 (conflicting-late callbacks) have plan-side traces (Data-Model §1.5 ConflictingEventAuditLog + Research §10 conflicting_callbacks_audit.jsonl)? [Traceability, Spec §FR-027, Data-Model §1.5, Research §10]
- [ ] CHK128 Does FR-028–FR-032 (shadow STT) have plan-side traces (Contract: shadow-stt-lane §Python protocol + Research §4 + Research §6 + Data-Model §1.6, §1.7, §1.8)? [Traceability, Spec §FR-028 – FR-032, Contract: shadow-stt-lane, Research §4, Research §6, Data-Model §1.6 – §1.8]
- [ ] CHK129 Does FR-033 (transcript retention + default-on redaction artifact coverage) have plan-side traces (Data-Model §2.5 RedactionPolicy + Plan §Constraints redaction clause + Quickstart §1.3 `[retention]`/`[redaction]` config)? [Traceability, Spec §FR-033, Data-Model §2.5, Plan §Constraints, Quickstart §1.3]
- [ ] CHK130 Does FR-034 (shadow STT retention parity) have plan-side traces (Contract: shadow-stt-lane §Retention parity + Data-Model §1.6 transcript_path)? [Traceability, Spec §FR-034, Contract: shadow-stt-lane, Data-Model §1.6]
- [ ] CHK131 Does FR-035 (no secrets in logs / artifacts) have plan-side traces (Research §11 env-var secrets only + Contract: rejected-auth-audit-log §No secret leakage + Plan §Constraints)? [Traceability, Spec §FR-035, Research §11, Contract: rejected-auth-audit-log, Plan §Constraints]
- [ ] CHK132 Does FR-036 (run report) have plan-side traces (Research §9 run_report.json schema + Contract: cli-slice3 §Run report + Data-Model §1.10 RunReport)? [Traceability, Spec §FR-036, Research §9, Contract: cli-slice3, Data-Model §1.10]
- [ ] CHK133 Does FR-037 (CLI command + run modes) have plan-side traces (Research §8 CLI flag shape + Contract: cli-slice3 §Command shape + Quickstart §2 / §3)? [Traceability, Spec §FR-037, Research §8, Contract: cli-slice3, Quickstart §2, Quickstart §3]
- [ ] CHK134 Does FR-038 (demo without custom UI) have plan-side traces (Research §13 demo-evidence checklist + Quickstart §7 + Contract: cli-slice3 §Demo evidence without a custom UI)? [Traceability, Spec §FR-038, Research §13, Quickstart §7, Contract: cli-slice3]

### Every research.md decision closes a spec Deferred-to-Plan item

- [ ] CHK135 Does Research §1 (SignalWire SDK + SWML + httpx + embedded ASGI receiver) close the spec Deferred-to-Plan item "Specific SignalWire SDK choice, dial-plan / TwiML / SWML representation, ... SignalWire intermediate status names"? [Traceability, Research §1, Spec §Deferred to Implementation Plan > Telephony adapter details]
- [ ] CHK136 Does Research §2 (HMAC-SHA256 + SIGNALWIRE_SIGNING_SECRET env var + distinct rejected_auth_callbacks table) close the spec Deferred-to-Plan item "The webhook signature-verification mechanism choice and the configuration surface for SignalWire credentials, source number, and callback URLs"? [Traceability, Research §2, Spec §Deferred to Implementation Plan > Telephony adapter details]
- [ ] CHK137 Does Research §3 (RealtimeAIProvider 3-method protocol + SLICE3_REALTIME_PROVIDER env var + fake) close the spec Deferred-to-Plan items "The configured real-time AI model provider choice" and "The persona's prompt / extraction / disposition wiring between the deterministic persona module and the live model"? [Traceability, Research §3, Spec §Deferred to Implementation Plan > Runtime and live-model details]
- [ ] CHK138 Does Research §4 (ShadowSTTProvider protocol + SLICE3_SHADOW_STT_PROVIDER env var + config/shadow_stt_discrepancy_policy.json with benign_rules + uncertain_rules) close the spec Deferred-to-Plan items "The shadow STT provider choice and credentials / configuration surface" and "The exact shadow STT discrepancy policy"? [Traceability, Research §4, Spec §Deferred to Implementation Plan > Shadow STT details]
- [ ] CHK139 Does Research §5 (Pipecat single-pipeline topology with SignalWireMediaInput → RealtimeAIProviderBridge → PersonaSink + μ-law 8kHz + VAD with 800ms fallback) close the spec Deferred-to-Plan item "The Pipecat pipeline topology, audio codec, and turn-taking configuration"? [Traceability, Research §5, Spec §Deferred to Implementation Plan > Runtime and live-model details]
- [ ] CHK140 Does Research §6 (tee at SignalWireMediaInput + separate asyncio.Task for shadow lane) close the spec Deferred-to-Plan item "The audio fan-out mechanism that feeds the same caller audio to the shadow lane without affecting the live path"? [Traceability, Research §6, Spec §Deferred to Implementation Plan > Shadow STT details]
- [ ] CHK141 Does Research §7 (3 distinct timeouts: SLICE3_ABANDONMENT_TIMEOUT_SEC=90, SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC=30, SLICE3_GRACE_WINDOW_SEC=3) close the spec Deferred-to-Plan item "The connect-timeout, ringing-timeout, live-call abandonment timeout, and live-runtime silence-after-connection / no-extraction-event timeout default values"? [Traceability, Research §7, Spec §Deferred to Implementation Plan > Telephony adapter details, Spec §Deferred to Implementation Plan > Resume / abandonment edge details]
- [ ] CHK142 Does Research §8 (`opencloser run3` subcommand + Typer + --real-call/--write + --resume + per-invocation flag requirement) close the spec Deferred-to-Plan item "The CLI flag and configuration-file shape that enables real-call / write-enabled mode"? [Traceability, Research §8, Spec §Deferred to Implementation Plan > Telephony adapter details]
- [ ] CHK143 Does Research §9 (one JSON file per session at artifacts/<session_id>/run_report.json with the documented schema) close the spec Deferred-to-Plan item "The run-report file format, JSON schema, file-naming convention, and per-session subdirectory grouping"? [Traceability, Research §9, Spec §Deferred to Implementation Plan > Run-report and artifact layout]
- [ ] CHK144 Does Research §10 (per-artifact JSONL / JSON file format enumeration) close the spec Deferred-to-Plan items "The shadow STT artifact filename pattern and discrepancy-record file format" and "The callbacks-audit-log file format"? [Traceability, Research §10, Spec §Deferred to Implementation Plan > Run-report and artifact layout]
- [ ] CHK145 Does Research §11 (config/slice3.toml + env vars for secrets) close the spec Deferred-to-Plan item "The CLI flag and configuration-file shape" (configuration surface part)? [Traceability, Research §11, Spec §Deferred to Implementation Plan > Telephony adapter details]
- [ ] CHK146 Does Research §12 (contract + integration + unit + manual real-call smoke) close the spec Deferred-to-Plan item "The recommended test harness for Slice 3 (fixture-replay through the SignalWire transport, recorded-audio playback through the Pipecat runtime, real test-call posture against a controlled tenant) and the CI / pre-pilot demo-evidence checklist"? [Traceability, Research §12, Spec §Deferred to Implementation Plan > Test posture for real calls]
- [ ] CHK147 Does Research §13 (docs/slice3/demo-evidence-checklist.md enumeration) close the demo-evidence portion of the spec Deferred-to-Plan "Test posture for real calls" item? [Traceability, Research §13, Spec §Deferred to Implementation Plan > Test posture for real calls]
- [ ] CHK148 Does Research §14 (reused Slice 1 / Slice 2 decisions) explicitly note that no spec Deferred-to-Plan item is closed by re-research, since these items pre-date Slice 3? [Clarity, Research §14, Spec §Assumptions]

### Constitution Check pre/post-design consistency

- [ ] CHK149 Are all five Constitution Check Principle statuses (I–V) marked Pass in BOTH the Plan §Constitution Check initial table AND the Plan §Post-Design Re-Check, with no status change between the two snapshots? [Consistency, Plan §Constitution Check, Plan §Post-Design Re-Check]
- [ ] CHK150 Does the Plan §Post-Design Re-Check section reference each Phase-1 artifact (data-model.md, contracts/, quickstart.md) and link the Round 2 Q-IDs (Q6, Q7, Q9, Q11, Q12, Q13, Q14) to the specific data-model entity / contract behavior that addresses them? [Completeness, Plan §Post-Design Re-Check]
- [ ] CHK151 Is the Plan §Complexity Tracking section explicitly empty (no plan-side decision introduces a constitution violation), with the "(none)" row preserved in the violation table? [Consistency, Plan §Complexity Tracking]

### Research §14 reuse list covers every Slice 1 / Slice 2 contract the spec preserves

- [ ] CHK152 Does Research §14 reuse list (SQLite, httpx + OAuth2, mapping artifact, idempotency-key stamping, bounded retry, resume coordinator, default-on transcript redaction, ≥90d retention floor) cover every Slice 1 / Slice 2 contract enumerated in Spec §Assumptions "Slice 1 / Slice 2 contracts preserved" (queue item, eligibility decision, normalized session result, disposition enum, Phone Call activity payload, queue-status update payload, Task payload, idempotency expectations, module boundaries + Slice 2 Dataverse contracts)? [Coverage, Research §14, Spec §Assumptions]
- [ ] CHK153 Does Research §14 explicitly note the Round 2-driven extensions to Slice 2 contracts (resume coordinator extended per Q6/Q12/Q13, default-on redaction extended per Q10/Q11) so the "reused unchanged" framing is not contradicted by the spec's Round 2 amendments? [Consistency, Research §14, Spec §Clarifications Round 2]

### Data-Model §7 invariants cover spec SC-008/SC-013/SC-014/SC-015/SC-016/SC-018

- [ ] CHK154 Does Data-Model §7 invariant "No duplicate writes" cover SC-008 (100% of duplicate SignalWire callbacks + repeated CLI recovery attempts leave Dynamics with no duplicates)? [Coverage, Data-Model §7, Spec §SC-008]
- [ ] CHK155 Does Data-Model §7 invariant "Non-blocking shadow STT at finalization" cover SC-013 (when shadow STT is enabled, the live conversation path completes with no observable slowdown attributable to the shadow lane)? [Coverage, Data-Model §7, Spec §SC-013]
- [ ] CHK156 Does Data-Model §7 invariant "Shadow lane truncation never mutates disposition" cover SC-013 (0 shadow STT events independently mutate a CRM record or override the persona's final disposition) AND SC-014 (persona's deterministic disposition precedence selects 100% of dispositions)? [Coverage, Data-Model §7, Spec §SC-013, Spec §SC-014]
- [ ] CHK157 Does Data-Model §7 invariant "No PHI in artifacts (caller-volunteered path)" cover the FR-015 / FR-033 caller-volunteered PHI escalation + tag-and-redact requirement? [Coverage, Data-Model §7, Spec §FR-015, Spec §FR-033]
- [ ] CHK158 Does Data-Model §7 invariant "Four write-back operations preserved" cover SC-016 (Slice 1 / Slice 2 per-disposition write-back map preserved unchanged)? [Coverage, Data-Model §7, Spec §SC-016]
- [ ] CHK159 Does Data-Model §7 invariant "DNC-first on do_not_call" cover the FR-024 ordering requirement (and is the SC-006 do_not_call protection consistent with this invariant)? [Coverage, Data-Model §7, Spec §FR-024, Spec §SC-006]
- [ ] CHK160 Does Data-Model §7 invariant "No secrets in artifacts" cover SC-018 (0 secrets appear in logs, exported artifacts, run report, or planned/actual write-back payloads) AND FR-035? [Coverage, Data-Model §7, Spec §SC-018, Spec §FR-035]
- [ ] CHK161 Are the SC-015 boundary invariants (0 vendor specifics in core) covered by Data-Model §7 OR by a separate "what must not leak" trace in each contract file? [Coverage, Data-Model §7, Contract: signalwire-transport, Contract: pipecat-runtime, Contract: shadow-stt-lane, Spec §SC-015]

### 64 contract tests provide at least one assertion per FR

- [ ] CHK162 Are the 64 contract tests across 6 files (10 signalwire-transport + 11 pipecat-runtime + 13 shadow-stt-lane + 11 crm-writeback-dnc-first + 8 rejected-auth-audit-log + 11 cli-slice3) collectively sufficient that no Slice 3 FR (FR-001 through FR-038) is left without a contract-test assertion? [Coverage, Contract: all, Spec §Functional Requirements]
- [ ] CHK163 Is any FR with NO direct contract-test assertion (e.g., a high-level behavioral FR that is verified only by integration tests, not contract tests) called out as such in Research §12 or in the contract files, so a reader knows which FRs depend on integration-test coverage rather than contract-test coverage? [Gap, Research §12, Spec §Functional Requirements]

### Quickstart §7 Demo-Evidence Checklist covers operator-evidence in FR-038

- [ ] CHK164 Does Quickstart §7 demo-evidence checklist cover every category of operator evidence enumerated in FR-038 (CLI / API output, the local run report, local audit artifacts [session-result, transcript or transcript pointer, planned/actual write-back payloads, callbacks audit log, shadow STT artifacts and discrepancy records when enabled, conflicting-events audit log when populated], and the resulting Dynamics records [Dataverse queue item, Phone Call activity, callback or review Task])? [Coverage, Quickstart §7, Spec §FR-038]
- [ ] CHK165 Does Quickstart §7 list explicit "before" and "after" Dataverse queue-item screenshots so the demo can show the state-change (status, attempt count, last_disposition, last_session_id, DNC fields) without operator inference? [Completeness, Quickstart §7, Spec §FR-038]

### SQLite schema additions preserve Slice 2 schema invariants

- [ ] CHK166 Do the Slice 3 SQLite schema additions (Data-Model §3 — new tables `rejected_auth_callbacks`, `shadow_stt_discrepancies`, `shadow_lane_truncated_events`; ALTERed `sessions` columns) avoid breaking the Slice 2 `crm_correlations` and `writeback_progress` table contracts that Research §14 reuses unchanged? [Consistency, Data-Model §3, Research §14]
- [ ] CHK167 Are the SQLite `ALTER TABLE sessions ADD COLUMN` statements (Data-Model §3) safe additive changes that preserve the existing Slice 2 session-row primary key + uniqueness invariants (i.e., are they all nullable / defaulted so existing pre-Slice-3 session rows remain valid)? [Consistency, Data-Model §3]
- [ ] CHK168 Is the `CHECK (http_status = 401)` constraint on `rejected_auth_callbacks` consistent with the Contract: rejected-auth-audit-log `test_http_status_is_401` test AND with FR-008's "provider-appropriate HTTP response code"? [Consistency, Data-Model §3, Contract: rejected-auth-audit-log, Spec §FR-008]
- [ ] CHK169 Are foreign-key references in the new tables (`shadow_stt_discrepancies.session_id` and `shadow_lane_truncated_events.session_id` both `REFERENCES sessions(session_id)`) consistent with Slice 2's existing `crm_correlations.session_id` and `writeback_progress.session_id` foreign-key conventions? [Consistency, Data-Model §3, Research §14]
- [ ] CHK170 Does the index strategy in Data-Model §3 (`idx_rejected_auth_session`, `idx_shadow_disc_session`) provide O(1) or O(log n) `count_for_session` queries the run-report needs (Contract: rejected-auth-audit-log §SQLite mirror notes "O(1) for the run report")? [Measurability, Data-Model §3, Contract: rejected-auth-audit-log, Spec §FR-036]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- CHK101 – CHK170 are Round 3 amendments (2026-05-25) validating the Phase-1 plan-side artifacts: every spec FR has at least one plan-side trace (Technical Context row, research decision, data-model entity, contract Protocol, or quickstart step); every research.md decision (1–14) closes a spec Deferred-to-Plan item; the Constitution Check pre/post-design is consistent (no principle status changed); the Complexity Tracking section is correctly empty; Research §14 covers every Slice 1 / Slice 2 contract the spec preserves; the Data-Model §7 invariants cover SC-008/SC-013/SC-014/SC-015/SC-016/SC-018; the 64 contract tests provide at least one assertion per FR; the Quickstart §7 Demo-Evidence Checklist covers FR-038; and the SQLite schema additions don't break Slice 2 invariants.
- ≥80% of items reference a spec section, plan-side artifact, or quality marker for traceability.
