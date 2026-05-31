# Shadow STT Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the shadow-STT non-blocking lane and discrepancy-logging dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Non-blocking guarantee

- [ ] CHK001 Is the non-blocking guarantee stated in FR-029 in all three required dimensions: (a) MUST NOT block live conversation turns, (b) MUST NOT slow the live call path, (c) lane failure / timeout MUST NOT abort the live call? [Completeness, Spec §FR-029]
- [ ] CHK002 Is the non-blocking guarantee operationalized with a named metric, threshold, or test harness so SC-013 ("no observable slowdown attributable to the shadow lane") can be measured? [Measurability, Spec §SC-013, Spec §FR-029, Gap]
- [ ] CHK003 Is "no observable slowdown" in SC-013 either quantified (e.g., latency budget) or explicitly Deferred to Plan so the criterion is testable rather than aspirational? [Measurability, Spec §SC-013, Ambiguity]
- [ ] CHK004 Is the non-blocking guarantee stated consistently between the Constitution Alignment block, the Definitions ("Shadow STT lane"), FR-029, User Story 6, and SC-013? [Consistency, Spec §Constitution Alignment "Boundaries", Spec §Definitions "Shadow STT lane", Spec §FR-029, Spec §User Story 6, Spec §SC-013]
- [ ] CHK005 Is the audio fan-out mechanism (that supplies the same caller audio to the shadow lane without affecting the live path) either specified or explicitly Deferred to Plan? [Clarity, Spec §Deferred to Implementation Plan "Shadow STT details", Spec §FR-028]
- [ ] CHK006 Does the spec confirm that the non-blocking guarantee applies even on a slow / failing shadow STT provider (i.e., back-pressure cannot reach the live path)? [Completeness, Spec §FR-029, Spec §Edge Cases "Shadow STT lane fails or times out"]
- [ ] CHK007 Is the non-blocking guarantee tied to the SC-015 boundary invariant so a shadow-STT-provider-specific path cannot leak into the orchestrator or the live-call path? [Consistency, Spec §FR-029, Spec §SC-015]

## High-value field enumeration

- [ ] CHK008 Is the high-value field list defined exactly once (in Definitions) and cross-referenced from every place that uses it (FR-030, Shadow STT lane definition, User Story 6, Shadow STT Discrepancy Record entity)? [Consistency, Spec §Definitions "High-value field", Spec §FR-030, Spec §User Story 6, Spec §Key Entities "Shadow STT Discrepancy Record"]
- [ ] CHK009 Does the high-value field list explicitly include all seven: opt-out / DNC, wrong number, captured email, callback intent / preferred callback window, person reached name and role, interest level, and final disposition? [Completeness, Spec §Definitions "High-value field", Spec §FR-030]
- [ ] CHK010 Are the FR-030 wording and the Definitions wording for the high-value field list byte-identical (no drift) so a reader cannot conclude one is authoritative and the other indicative? [Consistency, Spec §Definitions "High-value field", Spec §FR-030]
- [ ] CHK011 Does the spec confirm whether the high-value field list is closed (only these seven fields trigger discrepancy events) or open (deployment can add more) and state which? [Clarity, Spec §FR-030, Ambiguity]
- [ ] CHK012 Is each high-value field defined with enough specificity to be compared (e.g., "preferred callback window" comparison semantics, "interest level" enumeration) or explicitly Deferred to Plan? [Clarity, Spec §FR-030, Spec §Definitions "High-value field", Spec §Deferred to Implementation Plan "Shadow STT details"]
- [ ] CHK013 Does the spec confirm that high-value field comparison happens at session finalization (User Story 6 #3) and not mid-call, so a mid-call divergence cannot prematurely escalate? [Clarity, Spec §User Story 6 #3, Spec §FR-030, Spec §FR-031]
- [ ] CHK014 Is the relationship between high-value fields and the persona's extraction schema (FR-014) defined so a reviewer can confirm the shadow lane compares the same field semantics the persona extracts? [Completeness, Spec §FR-014, Spec §FR-030, Gap]

## Audit-only / no-CRM-write semantics

- [ ] CHK015 Is the audit-only semantics stated in both directions in FR-030: (a) shadow lane MUST NOT independently write a CRM record, (b) shadow lane MUST NOT override the persona's final disposition in the MVP? [Completeness, Spec §FR-030]
- [ ] CHK016 Is the audit-only semantics stated consistently in Constitution Alignment ("MUST NOT block the live call or independently mutate CRM"), Definitions ("never independently writes a CRM record or overrides the persona's final disposition"), FR-030, User Story 6, and SC-013? [Consistency, Spec §Constitution Alignment "Auditability", Spec §Definitions "Shadow STT discrepancy", Spec §FR-030, Spec §User Story 6, Spec §SC-013]
- [ ] CHK017 Is User Story 6 #7 ("any shadow STT outcome ... the shadow lane has not independently created or updated any Dataverse record") aligned with FR-030 with no weakening? [Consistency, Spec §User Story 6 #7, Spec §FR-030]
- [ ] CHK018 Does SC-013 express the no-CRM-mutation and no-disposition-override invariants in quantitative terms ("0 shadow STT events independently mutate a CRM record or override the persona's final disposition")? [Measurability, Spec §SC-013, Spec §FR-030]
- [ ] CHK019 Is the "in the MVP" qualifier on the no-disposition-override rule explicit so a future slice could lift it without a Slice 3 contract break (and is the qualifier stated wherever the rule appears)? [Consistency, Spec §FR-030, Spec §Definitions "Shadow STT discrepancy"]
- [ ] CHK020 Is the audit-only rule stated to apply even to the escalation path (FR-031) so a reader cannot infer that `shadow_stt_discrepancy` escalation is a backdoor write from the shadow lane? [Clarity, Spec §FR-030, Spec §FR-031, Ambiguity]

## Escalation rule (`shadow_stt_discrepancy`)

- [ ] CHK021 Is the `shadow_stt_discrepancy` review reason defined consistently as additive to the Slice 1 `human_review_reason` enumeration in FR-031, FR-015, and the Preserved Slice 1 / Slice 2 Entities block? [Consistency, Spec §FR-031, Spec §FR-015, Spec §Key Entities "Preserved Slice 1 / Slice 2 Entities"]
- [ ] CHK022 Is FR-031 explicit that the orchestrator (not the shadow lane) performs the escalation and that exactly one review Task is created in Dynamics? [Clarity, Spec §FR-031, Spec §User Story 6 #4]
- [ ] CHK023 Is the escalation trigger defined as "the configured shadow STT discrepancy policy classifies a discrepancy as uncertain" (not as any disagreement) so benign differences do not escalate? [Clarity, Spec §FR-031, Spec §User Story 6 #4, Spec §Edge Cases "Shadow STT mismatch on a high-value field"]
- [ ] CHK024 Is the escalation review Task assignment defined (configured review owner) consistently with the Slice 1 / Slice 2 review-Task owner mapping? [Consistency, Spec §FR-031, Spec §FR-020, Spec §Constitution Alignment "Safety and human handoff"]
- [ ] CHK025 Is the rule "existing Slice 1 reason codes MUST NOT be replaced or repurposed" stated in FR-031? [Completeness, Spec §FR-031]
- [ ] CHK026 Does SC-005 align with FR-031 by allowing `shadow_stt_discrepancy` to satisfy the `needs_human_review` reason-code requirement? [Consistency, Spec §SC-005, Spec §FR-031]
- [ ] CHK027 Is the escalation rule stated to flow through the persona's deterministic disposition precedence (not bypass it) so the live-model-cannot-override rule is preserved? [Consistency, Spec §FR-014, Spec §FR-031, Spec §User Story 6 #4]
- [ ] CHK028 Does the spec confirm that exactly one review Task is created per escalated session (not one per discrepant field) so a multi-field discrepancy does not create multiple Tasks? [Clarity, Spec §FR-031, Spec §User Story 6 #4, Gap]

## Retention parity

- [ ] CHK029 Is FR-034's retention-parity rule stated for all three retention modes (full + redacted, summary-only, pointer-only)? [Completeness, Spec §FR-034, Spec §FR-033]
- [ ] CHK030 Is the rule "shadow STT discrepancy records MUST be retained as audit/review evidence even when transcript retention is summary-only" stated in FR-034 and reinforced by the Edge Cases "Transcript retention is summary-only or pointer-only" entry? [Consistency, Spec §FR-034, Spec §Edge Cases "Transcript retention is summary-only or pointer-only"]
- [ ] CHK031 Is the default-on redaction policy (FR-033) explicitly stated to apply to shadow STT transcripts before they are written to disk? [Completeness, Spec §FR-033, Spec §FR-034, Gap]
- [ ] CHK032 Is the shadow STT artifact retention floor (≥ 90 days per the Slice 2 retention floor, or longer when configured) stated consistently with the Local artifact retention assumption? [Consistency, Spec §FR-034, Spec §Assumptions "Local artifact retention"]
- [ ] CHK033 Does the spec confirm that shadow STT transcripts honor the same redaction rules and no-secrets-in-artifacts guarantee (FR-035) as the live transcript? [Consistency, Spec §FR-033, Spec §FR-035, Spec §FR-034]
- [ ] CHK034 Is the retention-parity rule stated as a contract the shadow STT provider configuration cannot opt out of (i.e., a deployment cannot configure a shadow lane that bypasses retention)? [Clarity, Spec §FR-034, Gap]

## Toggle behavior

- [ ] CHK035 Is the shadow STT enable/disable toggle defined as deployment-configurable in FR-032 and the Shadow STT toggle assumption? [Consistency, Spec §FR-032, Spec §Assumptions "Shadow STT toggle and discrepancy policy"]
- [ ] CHK036 Does FR-032 explicitly state that the Slice 3 demonstrable loop MUST complete when shadow STT is disabled (so shadow STT is never on the critical path)? [Completeness, Spec §FR-032, Spec §User Story 6 #5]
- [ ] CHK037 Does FR-032 explicitly state that the run report MUST always include the shadow-STT enable state (regardless of mode)? [Completeness, Spec §FR-032, Spec §FR-036]
- [ ] CHK038 Is the toggle priority (P2) consistent with the "shadow STT is not on the demonstrable loop critical path" framing in User Story 6's "Why this priority"? [Consistency, Spec §User Story 6, Spec §FR-032]
- [ ] CHK039 Does the spec define whether the toggle is per-run, per-deployment, or both? [Clarity, Spec §FR-032, Spec §Assumptions "Shadow STT toggle and discrepancy policy", Ambiguity]
- [ ] CHK040 Is the CLI shadow-STT enable/disable flag (FR-037 "shadow STT enable/disable flag") consistent with the deployment-configurable toggle in FR-032 (i.e., how do per-run flag and deployment config interact)? [Consistency, Spec §FR-037, Spec §FR-032, Ambiguity]
- [ ] CHK041 Does the spec confirm that disabling shadow STT also disables the `shadow_stt_discrepancy` escalation path (no false escalations when the lane is off)? [Completeness, Spec §FR-031, Spec §FR-032, Gap]

## Lane-failure behavior

- [ ] CHK042 Is the lane-failure behavior consistent between FR-029 (failure / timeout MUST NOT abort live call), User Story 6 #6 (live call unaffected; no discrepancy events for the missing-shadow case; run report records the failure), and the Edge Cases "Shadow STT lane fails or times out" entry? [Consistency, Spec §FR-029, Spec §User Story 6 #6, Spec §Edge Cases "Shadow STT lane fails or times out"]
- [ ] CHK043 Is "no discrepancy events emitted for the missing-shadow case" stated in both User Story 6 #6 and the Edge Cases entry so a reader cannot infer that a missing shadow transcript silently becomes an escalation? [Clarity, Spec §User Story 6 #6, Spec §Edge Cases "Shadow STT lane fails or times out"]
- [ ] CHK044 Is the lane-failure run-report field defined (run report MUST record the shadow-lane failure) and consistent with FR-036's run-report contents? [Consistency, Spec §User Story 6 #6, Spec §FR-036, Spec §Edge Cases]
- [ ] CHK045 Does the spec define the shadow-lane timeout (or explicitly Defer to Plan) so a deployment knows when "fails or times out" applies? [Clarity, Spec §FR-029, Spec §Edge Cases, Spec §Deferred to Implementation Plan "Shadow STT details"]
- [ ] CHK046 Is the lane-failure case distinguished from the lane-disabled case so a reader cannot conflate them in the run report? [Clarity, Spec §FR-032, Spec §Edge Cases "Shadow STT lane fails or times out", Ambiguity]
- [ ] CHK047 Does the spec confirm that a shadow-lane failure leaves the live disposition unmodified (no `shadow_stt_discrepancy` reason emitted, persona-deterministic rules unaffected)? [Completeness, Spec §FR-014, Spec §FR-029, Spec §Edge Cases]

## Run-report shadow-STT fields

- [ ] CHK048 Does FR-036 enumerate both the "shadow STT enabled/disabled flag" AND the "discrepancy summary when enabled" fields as required run-report contents? [Completeness, Spec §FR-036]
- [ ] CHK049 Is the run-report shadow-STT field set aligned with the "Run Report" Key Entity ("shadow STT enabled/disabled and discrepancy summary")? [Consistency, Spec §FR-036, Spec §Key Entities "Run Report"]
- [ ] CHK050 Does the spec define what "discrepancy summary" includes (e.g., per-field disagree counts, classification distribution) or explicitly Defer to Plan? [Clarity, Spec §FR-036, Spec §Deferred to Implementation Plan "Run-report and artifact layout", Gap]
- [ ] CHK051 Does the spec confirm that a shadow-lane-failure entry appears in the run report (consistent with User Story 6 #6 and the Edge Cases entry)? [Consistency, Spec §FR-036, Spec §User Story 6 #6, Spec §Edge Cases]
- [ ] CHK052 Is the run-report demo-evidence criterion (SC-017 "the operator can read ... the shadow STT artifact and discrepancy records when shadow STT was enabled") aligned with FR-036's run-report field set? [Consistency, Spec §SC-017, Spec §FR-036]
- [ ] CHK053 Does the spec confirm that the run-report shadow-STT fields are produced even on a disabled run (so the enable state is auditable for every run, not just enabled ones)? [Completeness, Spec §FR-032, Spec §FR-036]

## Discrepancy policy classification

- [ ] CHK054 Is the discrepancy classification scheme (benign vs. uncertain) named in FR-031, User Story 6 #4, and the Shadow STT Discrepancy Record entity? [Consistency, Spec §FR-031, Spec §User Story 6 #4, Spec §Key Entities "Shadow STT Discrepancy Record"]
- [ ] CHK055 Is the discrepancy policy itself (which differences are benign vs. uncertain) explicitly Deferred to Plan rather than left unspecified? [Clarity, Spec §FR-031, Spec §Deferred to Implementation Plan "Shadow STT details", Spec §Assumptions "Shadow STT toggle and discrepancy policy"]
- [ ] CHK056 Is the classification rule stated to be deployment-configurable (in the assumption block) and consistent with FR-031's "configured shadow STT discrepancy policy" wording? [Consistency, Spec §FR-031, Spec §Assumptions "Shadow STT toggle and discrepancy policy"]
- [ ] CHK057 Does the spec confirm that benign differences (e.g., casing / whitespace / phonetic spelling) are recorded as discrepancy events even when they do NOT escalate (User Story 6 #3 vs. #4)? [Clarity, Spec §User Story 6 #3, Spec §User Story 6 #4, Ambiguity]
- [ ] CHK058 Is the contract "no discrepancy event ⇒ no extra review Task" stated unambiguously (User Story 6 #2) so an agreeing-shadow run produces no extra Task? [Clarity, Spec §User Story 6 #2, Spec §FR-031]
- [ ] CHK059 Does the Shadow STT Discrepancy Record entity hold the classification (benign / uncertain) as a recorded field so a reviewer can read it without re-running the classifier? [Completeness, Spec §Key Entities "Shadow STT Discrepancy Record"]
- [ ] CHK060 Is the resulting review-task reason code (`shadow_stt_discrepancy`) recorded on the Discrepancy Record when escalation applies (per the Discrepancy Record entity definition)? [Consistency, Spec §Key Entities "Shadow STT Discrepancy Record", Spec §FR-031]

## Shadow STT entities

- [ ] CHK061 Is the "Shadow STT Lane / Shadow Transcript" entity defined with the optional, non-blocking, session-scoped, retention-parity properties stated? [Completeness, Spec §Key Entities "Shadow STT Lane / Shadow Transcript"]
- [ ] CHK062 Is the "Shadow STT Discrepancy Record" entity defined with session ID, disagreeing field(s), live and shadow values, classification (benign / uncertain), and review-task reason code when escalation applied? [Completeness, Spec §Key Entities "Shadow STT Discrepancy Record"]
- [ ] CHK063 Is the Shadow STT entity set consistent across Constitution Alignment, Definitions, FR-028 – FR-032, FR-034, FR-036, and Key Entities (no entity introduced in one section without backing requirements elsewhere)? [Consistency, Spec §Constitution Alignment "Boundaries", Spec §Definitions, Spec §FR-028, Spec §FR-029, Spec §FR-030, Spec §FR-031, Spec §FR-032, Spec §FR-034, Spec §FR-036, Spec §Key Entities]

## Scenario classes

### Primary

- [ ] CHK064 Is the primary path "shadow STT enabled + live conversation runs unaffected" covered end-to-end in User Story 6 #1 and FR-028 / FR-029? [Coverage, Spec §User Story 6 #1, Spec §FR-028, Spec §FR-029]
- [ ] CHK065 Is the primary path "live and shadow agree on every high-value field ⇒ no discrepancy event, no extra Task" covered in User Story 6 #2? [Coverage, Spec §User Story 6 #2, Spec §FR-030, Spec §FR-031]

### Alternate

- [ ] CHK066 Is the alternate path "shadow STT disabled ⇒ demonstrable loop still completes; run report records disabled" covered in User Story 6 #5 + FR-032? [Coverage, Spec §User Story 6 #5, Spec §FR-032]
- [ ] CHK067 Is the alternate path "live and shadow disagree but classification is benign ⇒ discrepancy event recorded, no escalation" covered in User Story 6 #3? [Coverage, Spec §User Story 6 #3, Spec §FR-031]

### Exception / Error

- [ ] CHK068 Is the exception path "live and shadow disagree, classification is uncertain ⇒ `needs_human_review` + one review Task with `shadow_stt_discrepancy` reason" covered in User Story 6 #4 + FR-031? [Coverage, Spec §User Story 6 #4, Spec §FR-031]
- [ ] CHK069 Is the exception path "shadow STT lane crashes or times out mid-call ⇒ live call unaffected; no discrepancy events emitted for the missing-shadow case; run report records the failure" covered in User Story 6 #6 + FR-029 + Edge Cases? [Coverage, Spec §User Story 6 #6, Spec §FR-029, Spec §Edge Cases "Shadow STT lane fails or times out"]

### Recovery

- [ ] CHK070 Is the recovery path "shadow lane fails ⇒ live call continues to a normalized terminal disposition" covered (i.e., recovery is "live call simply continues"; shadow failure does not start a recovery sub-procedure)? [Coverage, Spec §FR-029, Spec §Edge Cases "Shadow STT lane fails or times out"]
- [ ] CHK071 Is the recovery path "shadow lane discrepancy escalates ⇒ Slice 2 review-task write-back path is reused (idempotent, owner-mapped)" covered in User Story 6 #4 and FR-020 / FR-021? [Coverage, Spec §User Story 6 #4, Spec §FR-020, Spec §FR-021, Spec §FR-031]
- [ ] CHK072 Is the recovery path "session resumes after orchestrator restart ⇒ shadow STT artifacts and discrepancy records remain inspectable (retention parity)" covered in FR-034 + Edge Cases "Resume after a real call when retention policy disables the transcript artifact"? [Coverage, Spec §FR-034, Spec §Edge Cases "Resume after a real call when retention policy disables the transcript artifact"]

### Non-Functional

- [ ] CHK073 Is the SC-013 non-blocking + audit-only invariant expressed as measurable ("no observable slowdown attributable to the shadow lane; 100% of discrepancies recorded; 0 independent CRM mutations or disposition overrides")? [Measurability, Spec §SC-013, Spec §FR-029, Spec §FR-030]
- [ ] CHK074 Is the retention-parity + redaction + no-secrets invariant for shadow STT artifacts expressed as measurable (verifiable by inspecting written shadow artifacts)? [Measurability, Spec §FR-033, Spec §FR-034, Spec §FR-035, Spec §SC-018]
- [ ] CHK075 Is the run-report shadow-STT field invariant (enabled flag + discrepancy summary present on every run) expressed as measurable? [Measurability, Spec §FR-032, Spec §FR-036]
- [ ] CHK076 Is the SC-015 boundary invariant (0 shadow STT provider specifics in orchestrator, eligibility evaluator, persona module, or Dataverse adapter) tied to the shadow-lane boundary so a future plan cannot leak vendor specifics? [Measurability, Spec §SC-015, Spec §Constitution Alignment "Boundaries"]
- [ ] CHK077 Is the shadow-STT retention-floor invariant (≥ 90 days unless configured otherwise) measurable by inspecting the local artifact directory? [Measurability, Spec §FR-034, Spec §Assumptions "Local artifact retention"]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments to FR-029 (grace window + `shadow_lane_truncated` audit-only event), FR-033 (default-on redaction extended to shadow STT transcript + shadow STT discrepancy records), and FR-015 (caller-volunteered PHI tag-and-redact in shadow artifacts). Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap] or [Ambiguity].

### Non-blocking finalization preserved (Q7 — FR-029)

- [ ] CHK078 Does the amended FR-029 explicitly state that the orchestrator MUST NOT delay session finalization to wait for the shadow lane to drain (i.e., finalization is immediate; only write-back may be deferred — closes Round 1 CHK002, CHK006)? [Completeness, Spec §FR-029, §Clarifications Session 2026-05-25 (Round 2) Q2]
- [ ] CHK079 Is the non-blocking-finalization guarantee consistent between FR-029, User Story 6, the Constitution Alignment "Boundaries" block, and SC-013 after the Round 2 amendment (closes Round 1 CHK004)? [Consistency, Spec §FR-029, §User Story 6, §Constitution Alignment "Boundaries", §SC-013]
- [ ] CHK080 Is the distinction between (a) session FINALIZATION (immediate, never delayed) and (b) CRM WRITE-BACK (MAY be held for a grace window) stated so a reader cannot conflate them and infer that the shadow lane can delay finalization? [Clarity, Spec §FR-029]

### Grace window definition (Q7 — FR-029)

- [ ] CHK081 Does the amended FR-029 introduce the post-finalization grace window as a DEPLOYMENT-CONFIGURABLE value (not pinned in the spec) — i.e., the configurability is the requirement, the specific number belongs in `/speckit.plan`? [Completeness, Spec §FR-029, §Deferred to Implementation Plan "Performance and latency targets"]
- [ ] CHK082 Is the grace window's purpose stated unambiguously (allows a late shadow-STT discrepancy event to PARTICIPATE in the disposition per FR-031) so a reader cannot infer it is a generic latency knob? [Clarity, Spec §FR-029, §FR-031]
- [ ] CHK083 Does the spec confirm that the grace window is OPTIONAL behavior (FR-029 says the orchestrator MAY hold write-back) — i.e., a deployment may configure a zero-length grace window and the FR-029 non-blocking guarantee still holds? [Clarity, Spec §FR-029, Ambiguity]
- [ ] CHK084 Is the grace-window-elapsed behavior defined (write-back MUST proceed without the shadow result; subsequent shadow output recorded as audit-only `shadow_lane_truncated`) so a reader knows the deterministic outcome on grace-window expiry? [Completeness, Spec §FR-029]
- [ ] CHK085 Is the grace window's interaction with the FR-031 escalation rule defined — i.e., a discrepancy event that arrives WITHIN the grace window MAY trigger `shadow_stt_discrepancy` escalation; one that arrives AFTER becomes audit-only `shadow_lane_truncated` and does NOT escalate? [Clarity, Spec §FR-029, §FR-031, Ambiguity]
- [ ] CHK086 Is the grace window defined as starting at SESSION FINALIZATION (not at call completion, dial, or any other anchor) so the timing reference is unambiguous? [Clarity, Spec §FR-029, Gap]
- [ ] CHK087 Is the grace window's configurability surface (per-deployment? per-run? both?) defined or explicitly deferred to plan, parallel to Round 1 CHK039 for the shadow STT toggle? [Clarity, Spec §FR-029, §Deferred to Implementation Plan, Ambiguity]

### `shadow_lane_truncated` audit-only event semantics (Q7 — FR-029)

- [ ] CHK088 Does the amended FR-029 introduce `shadow_lane_truncated` as a POST-FINALIZATION AUDIT-ONLY event with explicit "MUST NOT mutate the finalized disposition or emit a new CRM write-back payload" wording? [Completeness, Spec §FR-029, §Clarifications Session 2026-05-25 (Round 2) Q2]
- [ ] CHK089 Is the `shadow_lane_truncated` event's audit-only semantics consistent with FR-030's "shadow lane MUST NOT independently write a CRM record and MUST NOT override the persona's final disposition" rule (closes Round 1 CHK015, CHK016, CHK020)? [Consistency, Spec §FR-029, §FR-030]
- [ ] CHK090 Is the `shadow_lane_truncated` event distinguished from the existing shadow-lane-failure case (Round 1 CHK042–CHK047) — i.e., truncation = late-arrival after grace window vs. failure = lane never produced output / timed out (closes Round 1 CHK046 conflation risk)? [Clarity, Spec §FR-029, §Edge Cases "Shadow STT lane fails or times out", Ambiguity]
- [ ] CHK091 Does the spec require the `shadow_lane_truncated` event to be recorded with enough metadata (e.g., session ID, time-late-relative-to-finalization) so an auditor can detect deployments whose grace window is consistently too short? [Measurability, Spec §FR-029, Gap]
- [ ] CHK092 Is the `shadow_lane_truncated` event surfaced in the run report (consistent with FR-036's run-report contents and Round 1 CHK051) so a reviewer reading the run report can see when shadow output was truncated? [Consistency, Spec §FR-029, §FR-036, Gap]
- [ ] CHK093 Does the spec confirm that a `shadow_lane_truncated` event MUST NOT itself emit a `shadow_stt_discrepancy` review Task (so a late-arrival cannot back-door-trigger the escalation that grace-window expiry was meant to skip)? [Completeness, Spec §FR-029, §FR-031]
- [ ] CHK094 Is the `shadow_lane_truncated` audit-only event's no-CRM-mutation invariant tied to the SC-013 measurable invariant ("0 shadow STT events independently mutate a CRM record or override the persona's final disposition") so the new event class is covered by the existing measurement (closes Round 1 CHK018)? [Consistency, Spec §FR-029, §SC-013]

### Disposition immutability post-finalization (Q7 — FR-029)

- [ ] CHK095 Does the amended FR-029 require that any shadow-lane output produced AFTER the grace window MUST NOT mutate the finalized disposition — even if the shadow lane disagrees on a high-value field? [Completeness, Spec §FR-029]
- [ ] CHK096 Is the post-finalization immutability of the disposition consistent with FR-027 (conflicting-late SignalWire callbacks MUST NOT mutate the finalized disposition) — i.e., both late-shadow and late-callback follow the same post-finalization audit-only pattern? [Consistency, Spec §FR-027, §FR-029]
- [ ] CHK097 Is the post-finalization disposition immutability stated to apply even when the shadow lane's late output would have classified as uncertain under the FR-031 discrepancy policy (so an operator cannot manually "promote" a truncated-event to an escalation)? [Clarity, Spec §FR-029, §FR-031, Gap]

### Default-on redaction extended to shadow STT artifacts (Q10 — FR-033)

- [ ] CHK098 Does the amended FR-033 explicitly include the SHADOW STT TRANSCRIPT in the default-on redaction policy's coverage list (closes Round 1 CHK031)? [Completeness, Spec §FR-033, §FR-034, §Clarifications Session 2026-05-25 (Round 2) Q5]
- [ ] CHK099 Does the amended FR-033 explicitly include the SHADOW STT DISCREPANCY RECORDS in the default-on redaction policy's coverage list (closes Round 1 CHK029)? [Completeness, Spec §FR-033, §FR-030, §Clarifications Session 2026-05-25 (Round 2) Q5]
- [ ] CHK100 Is the redaction scope on the shadow STT discrepancy records defined to cover BOTH the live and shadow values held in the record (per the Discrepancy Record entity in Round 1 CHK062) so a discrepancy record cannot become a side channel for unredacted content? [Completeness, Spec §FR-033, §Key Entities: Shadow STT Discrepancy Record]
- [ ] CHK101 Is the redaction-BEFORE-disk ordering preserved verbatim for both shadow artifact classes (i.e., redaction completes before each artifact is written, not best-effort) so Round 1 CHK028's hard-ordering rule is preserved across the new coverage (closes Round 1 CHK033)? [Consistency, Spec §FR-033, §FR-034]
- [ ] CHK102 Is the redaction extension consistent across all three retention modes — full-with-redaction, summary-only (when shadow summary applies), pointer-only (where the pointed-at artifact is still redacted) — closing Round 1 CHK029 (retention parity) for redaction? [Consistency, Spec §FR-033, §FR-034, §Edge Cases "Transcript retention is summary-only or pointer-only"]
- [ ] CHK103 Is the transcript-pointer-excluded-from-redaction rule stated to apply equally to the live transcript pointer AND the shadow transcript pointer (since shadow has retention parity per FR-034) so a reader cannot infer asymmetric treatment? [Consistency, Spec §FR-033, §FR-034, Gap]
- [ ] CHK104 Is the redaction extension preserved on the resume path — i.e., a resume that produces or rewrites shadow STT transcripts or shadow STT discrepancy records still applies the redaction-before-write ordering (parallel to Round 1 CHK020)? [Consistency, Spec §FR-022, §FR-033, §FR-034, Gap]

### PHI tag-and-redact in shadow artifacts is a hard requirement (Q11 — FR-015)

- [ ] CHK105 Does the amended FR-015 explicitly require that caller-volunteered PHI is tagged-and-redacted in the SHADOW STT TRANSCRIPT before it is written to disk (closes Round 1 CHK037)? [Completeness, Spec §FR-015, §FR-033, §FR-034, §Clarifications Session 2026-05-25 (Round 2) Q6]
- [ ] CHK106 Does the amended FR-015 explicitly require that caller-volunteered PHI is tagged-and-redacted in the SHADOW STT DISCREPANCY RECORDS before they are written to disk? [Completeness, Spec §FR-015, §FR-030, §FR-033, §Clarifications Session 2026-05-25 (Round 2) Q6]
- [ ] CHK107 Is the PHI tag-and-redact requirement on shadow artifacts stated as HARD (MUST), not best-effort, so a deployment cannot opt the shadow lane out of PHI redaction (closes Round 1 CHK034 for the redaction-cannot-be-bypassed angle)? [Completeness, Spec §FR-015, §FR-033, §FR-034]
- [ ] CHK108 Is the PHI redaction in shadow artifacts consistent with the SC-018 no-secrets / no-sensitive-content invariant — i.e., shadow artifacts are now part of the same release-gate measurement? [Consistency, Spec §FR-015, §FR-033, §FR-034, §SC-018]
- [ ] CHK109 Does the spec require that the SHADOW STT lane itself can detect (or accept persona signals about) PHI content so the tag-and-redact requirement is implementable, or is that mechanism explicitly Deferred to Plan (parallels Round 1 CHK014, CHK018)? [Clarity, Spec §FR-015, §Deferred to Implementation Plan "Shadow STT details", Ambiguity]
- [ ] CHK110 Is the redact-before-write requirement on shadow STT discrepancy records preserved EVEN WHEN the discrepancy is the very thing being recorded (i.e., live said one thing, shadow said another — both values redacted if PHI; the discrepancy classification still recorded)? [Completeness, Spec §FR-015, §FR-030, §FR-033, Gap]
- [ ] CHK111 Does the spec confirm that a PHI-tagged shadow discrepancy still flows through the FR-031 discrepancy policy (benign vs. uncertain classification) so the redaction does not bypass the escalation path? [Consistency, Spec §FR-015, §FR-031, Ambiguity]

### Cross-cutting Round 2 consistency

- [ ] CHK112 Is the shadow lane's audit-only / no-CRM-write invariant (Round 1 CHK015–CHK020) preserved verbatim by the new `shadow_lane_truncated` event class (i.e., truncation events are audit-only too, no shadow-driven CRM mutation)? [Consistency, Spec §FR-029, §FR-030]
- [ ] CHK113 Is the SC-015 boundary invariant (0 shadow STT provider specifics in orchestrator / persona / Dataverse adapter, Round 1 CHK076) preserved by the grace window and `shadow_lane_truncated` additions — i.e., grace-window timing and truncation-event emission are orchestrator-level concerns, not shadow-provider specifics? [Consistency, Spec §FR-029, §SC-015]
- [ ] CHK114 Is the grace-window-and-truncation behavior preserved when shadow STT is DISABLED (i.e., disabled-lane skips the grace window entirely; no truncation events can be emitted) consistent with Round 1 CHK041's "disable also disables the escalation path" rule? [Consistency, Spec §FR-029, §FR-032]
- [ ] CHK115 Does the run report's grace-window / truncation surface (per CHK092 above) coexist with the existing run-report shadow-STT field set (Round 1 CHK048–CHK053) without duplicating fields or introducing a separate run-report section? [Consistency, Spec §FR-029, §FR-036]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### `ShadowSTTProvider` 2-method protocol enables provider swap (FR-032 deployment-configurable)

- [ ] CHK116 Does the `ShadowSTTProvider` Protocol's two-method surface (`transcribe(audio_stream) → AsyncIterator[TranscriptSegment]`, `close(session_id)`) (Contract: shadow-stt-lane) define a minimal boundary sufficient to enable provider swap without code changes outside `shadow_stt/` (re-validates Round 1 deployment-configurability against the plan)? [Completeness, Contract: shadow-stt-lane, Research §4, Spec §FR-032]
- [ ] CHK117 Is the provider-swap mechanism stated as env-var-driven (`SLICE3_SHADOW_STT_PROVIDER`, Research §4) consistent with FR-032's "deployment-configurable as enabled or disabled" wording so the swap surface is operator-controllable without recompilation? [Consistency, Research §4, Quickstart §1.2, Spec §FR-032]
- [ ] CHK118 Does the plan locate provider-specific shadow STT code exclusively within `src/opencloser/shadow_stt/` (Plan §Project Structure) so a new provider addition requires no edits to `core/`, `orchestrator/`, `persona/`, or `crm/` (preserves Plan §Constitution Check III boundary separation)? [Consistency, Plan §Project Structure, Plan §Constitution Check, Spec §SC-015]
- [ ] CHK119 Is the `close(session_id)` method's semantics (signal lane completion vs. resource cleanup) defined sufficiently that two different provider implementations cannot interpret it differently in ways that affect the FR-029 non-blocking guarantee? [Clarity, Contract: shadow-stt-lane, Spec §FR-029, Ambiguity]

### `asyncio.Task` tee at `SignalWireMediaInput` (Research §6) enforces FR-029 non-blocking

- [ ] CHK120 Does the `asyncio.Task` tee at the `SignalWireMediaInput` boundary (Research §6, Contract: shadow-stt-lane Required Behavior #1) enforce the FR-029 non-blocking guarantee BY CONSTRUCTION — i.e., the orchestrator MUST NOT `await` the lane's task before finalization (re-validates Round 1 CHK015–CHK020 against the implementation pattern)? [Completeness, Research §6, Contract: shadow-stt-lane, Spec §FR-029]
- [ ] CHK121 Does the contract test `test_lane_runs_in_separate_task` (Contract: shadow-stt-lane) explicitly assert that the lane is started via `asyncio.create_task` AND the orchestrator does not `await` it before finalization — so the by-construction guarantee is measurable, not just declared? [Measurability, Contract: shadow-stt-lane, Spec §FR-029]
- [ ] CHK122 Is the tee-at-transport-boundary rationale (Research §6 "the simplest construction that satisfies FR-028 without coupling the shadow lane to Pipecat internals") preserved by the contract test set — i.e., the test set does not assume any Pipecat-internal hook for the shadow lane? [Consistency, Research §6, Contract: shadow-stt-lane, Spec §FR-028]
- [ ] CHK123 Does the contract test `test_lane_does_not_block_live_turns` (Contract: shadow-stt-lane) quantify the non-blocking guarantee statistically (SC-013) — i.e., the live conversation turn cadence is indistinguishable between shadow-enabled and shadow-disabled runs (re-validates Round 1 CHK022 against the plan)? [Measurability, Contract: shadow-stt-lane, Spec §SC-013]
- [ ] CHK124 Is the tee-at-transport-boundary pattern stated to apply only at `SignalWireMediaInput`, not at a deeper Pipecat frame — so the shadow lane is decoupled from any Pipecat pipeline changes (re-validates SC-015 boundary preservation against the plan)? [Consistency, Research §6, Plan §Project Structure, Spec §SC-015]

### Grace window: default 3s, configurable to 0, configurable unbounded (Research §7, Round 2 Q7)

- [ ] CHK125 Does the `SLICE3_GRACE_WINDOW_SEC` default of 3 (Research §7, Quickstart §1.3) match the FR-029 Round 2 Q7 requirement for a deployment-configurable post-finalization grace window (re-validates Round 2 CHK087 against the plan)? [Consistency, Research §7, Quickstart §1.3, Spec §FR-029]
- [ ] CHK126 Is the "configurable to 0" property (Research §7 "Configurable to 0 (write-back immediately; shadow always becomes `shadow_lane_truncated`)") stated consistently with the FR-029 "MAY hold the CRM write-back" wording — i.e., 0 is a valid value and means "don't hold"? [Consistency, Research §7, Spec §FR-029]
- [ ] CHK127 Is the "configurable unbounded" property (Research §7 "or any positive integer (no spec-mandated maximum; deployment may bound it)") preserved by the plan without introducing a hidden upper bound — and is this rationalized with the FR-029 "MUST NOT delay session finalization" rule (a long grace window delays write-back, not finalization)? [Clarity, Research §7, Spec §FR-029]
- [ ] CHK128 Does the grace window's behavior when set to 0 produce the expected `ShadowLaneTruncatedEvent` for every shadow output (Research §7) — i.e., the 0 case is observably distinct from the disabled-lane case (which produces NO truncated event per Round 2 CHK114)? [Clarity, Research §7, Data-Model §1.8, Spec §FR-029, Spec §FR-032, Ambiguity]
- [ ] CHK129 Is the grace window's per-session value persisted on `Session.grace_window_sec` (Data-Model §2.1, §3) so an audit can reconstruct which grace window was in effect for a given session (re-validates Round 2 CHK091 against the data model)? [Completeness, Data-Model §2.1, Data-Model §3]
- [ ] CHK130 Does the grace window's per-session column coexist with the `cm_writeback_started_at` column (Data-Model §2.1) so the actual elapsed time between `finalized_at` and `cm_writeback_started_at` is auditable and comparable to the configured `grace_window_sec`? [Measurability, Data-Model §2.1]

### `shadow_lane_truncated.json` + SQLite mirror preserve audit-only / no-disposition-mutation invariant

- [ ] CHK131 Does the `shadow_lane_truncated.json` file format (Data-Model §1.8, Research §10) plus the SQLite `shadow_lane_truncated_events` table (Data-Model §3) preserve the audit-only / no-disposition-mutation invariant by construction — i.e., the table has NO foreign key to any disposition or CRM write table (Data-Model §7 explicit invariant; re-validates Round 2 CHK088–CHK094 against the schema)? [Completeness, Data-Model §1.8, Data-Model §3, Data-Model §7, Spec §FR-029]
- [ ] CHK132 Is the `shadow_lane_truncated_events` table's `session_id PRIMARY KEY` constraint (Data-Model §3) sufficient to prevent multiple truncated-event rows per session — i.e., the truncated event is at-most-once per session and cannot be silently duplicated? [Completeness, Data-Model §3]
- [ ] CHK133 Does the `would_have_classified_as` enum column (Data-Model §1.8, §3) with `CHECK (would_have_classified_as IN ('benign', 'uncertain'))` record what the discrepancy policy WOULD have classified the late output as — without itself becoming an escalation trigger (Data-Model §1.8 invariant)? [Consistency, Data-Model §1.8, Data-Model §3, Spec §FR-029]
- [ ] CHK134 Is the `late_output_summary_json` column (Data-Model §3) subject to the same default-on redaction policy as the shadow STT discrepancy records (Data-Model §2.5) so a late-arriving PHI-bearing discrepancy summary cannot be a back-channel? [Consistency, Data-Model §3, Data-Model §2.5, Spec §FR-033, Gap]
- [ ] CHK135 Does the contract test `test_late_shadow_output_yields_truncated_event` (Contract: shadow-stt-lane) enforce the Q7 grace-window-elapsed semantics — i.e., shadow emits a discrepancy AFTER the grace window → `ShadowLaneTruncatedEvent` recorded; disposition unchanged; no new CRM payload (re-validates Round 2 CHK088 against the contract test set)? [Measurability, Contract: shadow-stt-lane, Spec §FR-029]
- [ ] CHK136 Is the truncated-event audit-only invariant testable via an inverse assertion — i.e., does the contract test set include a "no `shadow_stt_discrepancy` review Task created after truncated event" assertion so back-door escalation is caught (re-validates Round 2 CHK093 against the test set)? [Measurability, Contract: shadow-stt-lane, Spec §FR-029, Spec §FR-031, Gap]

### `discrepancy_policy.json` (Research §4) operationalizes FR-030 high-value field comparison

- [ ] CHK137 Does the `config/shadow_stt_discrepancy_policy.json` structure (Research §4: `benign_rules`, `uncertain_rules`) operationalize FR-030's high-value field comparison — i.e., every high-value field enumerated in FR-030 has a corresponding rule path in either `benign_rules` or `uncertain_rules` (re-validates Round 1 CHK006–CHK010 against the plan)? [Completeness, Research §4, Spec §FR-030]
- [ ] CHK138 Are the example rules in Research §4 (`benign_rules`: case-insensitive equality, whitespace normalization, phonetic-spelling tolerance for names; `uncertain_rules`: semantically different emails, callback windows differing by > 1 day, opt-out vs. interest disagreement) covering every Round 1-flagged ambiguity case, or do gaps remain (e.g., person-reached-role disagreement, captured-email casing vs. domain differences)? [Completeness, Research §4, Spec §FR-030, Gap]
- [ ] CHK139 Does the JSON policy file's two-section structure preserve the operator-editable / no-code-changes property (Research §4 rationale) — i.e., a deployment can edit the file without touching `shadow_stt/discrepancy.py`? [Clarity, Research §4, Plan §Project Structure]
- [ ] CHK140 Is the policy file's path defined consistently in Research §4 (`config/shadow_stt_discrepancy_policy.json`) and in slice3.toml's `[shadow_stt].discrepancy_policy_path` (Quickstart §1.3) so the file location cannot drift between research and configuration? [Consistency, Research §4, Quickstart §1.3]
- [ ] CHK141 Does the contract test `test_high_value_fields_enumerated` (Contract: shadow-stt-lane) cross-check the 7-field enumeration in `detect_discrepancies` against FR-030's enumerated set — and does Data-Model §1.7's `field` enum (9 entries including `wrong_number` and `final_disposition`) align with the contract's "7 high-value fields" claim or is there an off-by-two inconsistency? [Conflict, Contract: shadow-stt-lane, Data-Model §1.7, Spec §FR-030]

### PHI tag-and-redact propagation to shadow artifacts (Round 2 Q11) per Data-Model §2.5

- [ ] CHK142 Does the PHI tag-and-redact pre-write pass (Round 2 Q11) propagate correctly to BOTH the shadow STT transcript file AND the shadow STT discrepancy records (Data-Model §2.5, Contract: shadow-stt-lane Required Behavior #8) so a `phi_collection_risk` escalation triggers redaction on all four artifact classes (re-validates Round 2 CHK105–CHK107 against the plan)? [Completeness, Data-Model §2.5, Contract: shadow-stt-lane, Spec §FR-015]
- [ ] CHK143 Does the contract test `test_phi_volunteered_redacts_shadow_artifacts` (Contract: shadow-stt-lane) verify that the PHI utterance is tagged AND redacted in BOTH `shadow_transcript.txt` AND `shadow_discrepancies.jsonl` before write — so the PHI redaction parity with live artifacts is measurable (re-validates Round 2 CHK105 against the test set)? [Measurability, Contract: shadow-stt-lane, Spec §FR-015]
- [ ] CHK144 Is the PHI-detection trigger on the shadow lane defined as "persona emits `phi_collection_risk`" (Contract: shadow-stt-lane Required Behavior #8) rather than an independent shadow-lane PHI classifier — so the trigger ownership stays with the persona module (re-validates Round 2 CHK109 ambiguity against the plan)? [Consistency, Contract: shadow-stt-lane, Plan §Project Structure `persona/extraction.py`]
- [ ] CHK145 Does the contract test `test_default_on_redaction_covers_shadow_artifacts` (Contract: shadow-stt-lane) cover the non-PHI default-on redaction case (sensitive content fixtures appear `[REDACTED]`) separately from the PHI-volunteered case so both default-on (FR-033) and PHI-special-case (FR-015) coverage are independently testable? [Measurability, Contract: shadow-stt-lane, Spec §FR-033]
- [ ] CHK146 Is the redact-before-write ordering for shadow discrepancy records (Contract: shadow-stt-lane Required Behavior #7 + #8) preserved when the discrepancy IS the PHI utterance — i.e., both `live_value` and `shadow_value` are redacted before the JSONL line is appended (re-validates Round 2 CHK110 against the contract)? [Completeness, Contract: shadow-stt-lane, Data-Model §1.7, Spec §FR-015]

### Run-report shadow_stt section (Research §9) captures `{enabled, discrepancy_summary, lane_truncated}`

- [ ] CHK147 Does the run-report `shadow_stt` section (Research §9: `{enabled, discrepancy_summary, lane_truncated}`, Data-Model §1.10) capture the three required surfaces per FR-032 ("MUST always state whether shadow STT was enabled") + FR-031 (discrepancy summary) + Round 2 Q7 (lane_truncated)? [Completeness, Research §9, Data-Model §1.10, Spec §FR-029, Spec §FR-032]
- [ ] CHK148 Is the contract test `test_run_report_states_shadow_enabled_flag` (Contract: shadow-stt-lane) explicit that the `shadow_stt.enabled` field is ALWAYS present (true or false) and that when true, BOTH `discrepancy_summary` AND `lane_truncated` are present — so the schema cannot silently omit a required field? [Measurability, Contract: shadow-stt-lane, Research §9]
- [ ] CHK149 Does the run-report `shadow_stt.discrepancy_summary` field have a defined shape (string summary? structured count?) so two different implementations cannot produce divergent formats — Research §9 shows an example string but no schema-level constraint, potential gap? [Clarity, Research §9, Gap]
- [ ] CHK150 Is the `shadow_stt.lane_truncated` boolean reconciled with the `ShadowLaneTruncatedEvent` SQLite row presence — i.e., `lane_truncated = true` iff a `shadow_lane_truncated_events` row exists for the session, no divergence path? [Consistency, Research §9, Data-Model §3]

### FR-032 "demo loop completes without shadow STT" testable when env unset OR "disabled"

- [ ] CHK151 Is the FR-032 "Slice 3 demonstrable loop completes without it" guarantee testable when `SLICE3_SHADOW_STT_PROVIDER` env var is UNSET (Research §4 "if the env var is unset OR equal to `disabled`, the shadow lane is no-op") — and is the unset-vs-disabled equivalence stated explicitly so an empty-string or whitespace-only value is also handled (re-validates Round 1 CHK039 against the plan)? [Completeness, Research §4, Spec §FR-032]
- [ ] CHK152 Does the contract test `test_disabled_lane_completes_demonstrable_loop` (Contract: shadow-stt-lane) exercise BOTH the unset-env case AND the `"disabled"`-value case, or only one — i.e., is the OR-condition in Research §4 fully covered by the test set? [Measurability, Contract: shadow-stt-lane, Research §4, Gap]
- [ ] CHK153 Is the disabled-lane path defined to produce NO `shadow_transcript.txt`, NO `shadow_discrepancies.jsonl`, and NO `shadow_lane_truncated.json` (Data-Model §4 artifact layout shows these as "only when ... enabled") so the disabled case has a deterministic empty-artifact-set? [Consistency, Data-Model §4, Spec §FR-032]
- [ ] CHK154 Does the run report's `shadow_stt.enabled = false` value (Research §9) coexist with the absence of `discrepancy_summary` and `lane_truncated` so the disabled case is observably distinct from an enabled-but-no-discrepancy case (re-validates Round 1 CHK048 against the plan)? [Clarity, Research §9, Spec §FR-032, Ambiguity]
- [ ] CHK155 Is the disabled-lane path stated to skip the grace window entirely (Round 2 CHK114) — i.e., when shadow STT is disabled, `cm_writeback_started_at = finalized_at` (no grace-window delay) and is this consistency preserved by the plan's data-model and runner flow (Data-Model §6)? [Consistency, Data-Model §2.1, Data-Model §6, Spec §FR-029, Spec §FR-032]

### Cross-cutting plan-side shadow-STT consistency

- [ ] CHK156 Is the SC-015 boundary invariant (0 shadow STT provider specifics in core / orchestrator / persona / Dataverse adapter) preserved by the `shadow_stt/` package structure (Plan §Project Structure) — i.e., the four-module split (`base.py`, `lane.py`, `discrepancy.py`, `truncation.py`) keeps all provider details inside the package (re-validates Round 1 CHK076 against the plan)? [Consistency, Plan §Project Structure, Spec §SC-015]
- [ ] CHK157 Does the plan's `tests/fixtures/shadow_stt/` directory (Plan §Project Structure) cover both shadow transcript fixtures AND discrepancy policy fixtures so the contract tests can exercise the policy classification (`benign` / `uncertain`) without depending on a live provider? [Completeness, Plan §Project Structure, Research §4]
- [ ] CHK158 Is the FR-034 retention-parity rule (Contract: shadow-stt-lane Required Behavior #6) preserved by the same `[retention].mode` configuration value driving both live and shadow transcripts (Quickstart §1.3) — i.e., there is no separate `[shadow_stt].retention_mode` that could diverge from the live retention mode (re-validates Round 1 CHK029 against the plan)? [Consistency, Contract: shadow-stt-lane, Quickstart §1.3, Spec §FR-034]
- [ ] CHK159 Does the lane-failure behavior (Contract: shadow-stt-lane Required Behavior #10) state that the run report records the shadow-lane failure for audit — and is the run-report field for this failure named so an auditor can grep for it (Research §9 lists `shadow_stt.lane_truncated` but does not show a separate `lane_failed` field; gap)? [Clarity, Contract: shadow-stt-lane, Research §9, Gap]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate two or more reasonable interpretations are possible and clarification is needed.
- ≥80% of items reference a spec section or a quality marker for traceability.
