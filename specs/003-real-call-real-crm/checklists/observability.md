# Observability Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the observability dimension (run report, audit artifacts, telemetry) before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Artifact enumeration

- [ ] CHK001 Is every observable artifact produced by a Slice 3 run enumerated as a single closed list — session-result, transcript or transcript pointer, run report, planned/actual write-back payloads, callbacks audit log, shadow STT artifact, shadow STT discrepancy records, conflicting-events audit log, telephony readiness report? [Completeness, Spec §FR-038, Spec §FR-036]
- [ ] CHK002 Is the Run Report defined as a single artifact with a single contract, rather than as scattered fields across the spec? [Consistency, Spec §FR-036, Spec §Key Entities Run Report]
- [ ] CHK003 Is the Telephony Readiness Report defined as a separate artifact from the Run Report, with a clear relationship (e.g., the run report references or embeds the readiness report)? [Clarity, Spec §Key Entities Telephony Readiness Report, Spec §FR-036, Spec §FR-011]
- [ ] CHK004 Is the Callbacks Audit Log defined as a distinct artifact (separate from the conflicting-events audit log) with explicit population rules? [Clarity, Spec §FR-007, Spec §Key Entities Callbacks Audit Log]
- [ ] CHK005 Is the Conflicting Event Audit Record explicitly distinguished from the Callbacks Audit Log, so an inspector can tell when to look in which? [Clarity, Spec §FR-027, Spec §Key Entities Conflicting Event Audit Record, Spec §Key Entities Callbacks Audit Log]
- [ ] CHK006 Is the Shadow STT Lane / Shadow Transcript defined as a distinct artifact from the Shadow STT Discrepancy Record, with explicit population conditions for each? [Clarity, Spec §Key Entities Shadow STT Lane, Spec §Key Entities Shadow STT Discrepancy Record, Spec §FR-028, Spec §FR-030]
- [ ] CHK007 Is the planned-write-back-payload artifact (planned Phone Call activity, planned queue-status update, planned Task) defined as distinct from the actual write-back payload artifact, so a tester can compare planned vs. actual? [Clarity, Spec §FR-002, Spec §US2 AC-2, Spec §FR-038]
- [ ] CHK008 Is the Write-Back Progress Ledger (preserved from Slice 2) explicitly retained as an observable artifact in Slice 3? [Completeness, Spec §FR-022, Spec §Key Entities Preserved Slice 1 / Slice 2 Entities]
- [ ] CHK009 Does the spec specify that raw call audio is NOT a Slice 3 artifact, and that this exclusion is captured in artifact enumeration? [Clarity, Spec §Clarifications Session 2026-05-25 Q2, Spec §Assumptions Slice scope]
- [ ] CHK010 Is the live-call abandonment audit evidence (the recorded `live_call_abandonment` reason and timeout-elapse condition) defined as part of a named artifact (run report? session-result? callbacks audit log?) rather than left implicit? [Gap, Spec §FR-026, Spec §Key Entities Live-Call Abandonment Outcome]

## Required fields per artifact

- [ ] CHK011 Are the Run Report's required fields enumerated as a closed list — run mode, session ID, invoking operator identity, real provider call ID when assigned, persona version, runtime/model identity, final disposition, per-write-back-operation status, shadow STT enabled/disabled and discrepancy summary, callbacks audit / conflicting-callbacks audit row counts, failing readiness check or block reason when applicable? [Completeness, Spec §FR-036]
- [ ] CHK012 Does the Run Report's required-field list match the Key Entities Run Report description (telephony readiness summary is named in Key Entities but not explicitly listed in FR-036's "at minimum" enumeration)? [Conflict, Spec §FR-036, Spec §Key Entities Run Report]
- [ ] CHK013 Are the Callbacks Audit Log's required fields enumerated — receipt timestamp, callback type, the normalized event the transport produced, any conflicting-late-event audit row, and the `(session_id, provider_event_id)` key? [Completeness, Spec §Key Entities Callbacks Audit Log, Spec §FR-007, Spec §FR-021]
- [ ] CHK014 Are the Conflicting Event Audit Record's required fields enumerated — `(session_id, provider_event_id)` key, the conflicting callback's content, and the finalized disposition that was NOT changed? [Gap, Spec §FR-027, Spec §Edge Cases SignalWire status callback delivered after disposition finalized]
- [ ] CHK015 Are the Shadow STT Discrepancy Record's required fields enumerated — session ID, disagreeing field(s), live value, shadow value, discrepancy classification (benign / uncertain), resulting review-task reason code when escalation applied? [Completeness, Spec §Key Entities Shadow STT Discrepancy Record, Spec §FR-030, Spec §FR-031]
- [ ] CHK016 Are the Telephony Readiness Report's required fields enumerated — result of each readiness check (SignalWire credentials, source number, destination phone format, callback URLs, persona/runtime configuration, Dataverse mapping, callback owner mapping, eligibility), failing check name on any failure? [Completeness, Spec §Key Entities Telephony Readiness Report, Spec §FR-009, Spec §FR-011]
- [ ] CHK017 Are the normalized session result's required fields enumerated — session ID, queue-item ID, real provider call ID, persona version, final disposition, summary, transcript or transcript pointer, captured email or `captured_email_unverified`, `callback_requested`, `preferred_callback_window`, `human_review_reason` when applicable, `blocked_reason` when applicable, `started_at`, `ended_at`? [Completeness, Spec §FR-017]
- [ ] CHK018 Does the run report's required field for "any callbacks audit / conflicting-callbacks audit row counts" specify the counting granularity (per session) or leave it ambiguous? [Ambiguity, Spec §FR-036]
- [ ] CHK019 Are the per-write-back-operation status enum values enumerated — planned / completed / resume-needed / blocked — so the run report's field has a closed value set? [Completeness, Spec §FR-036]
- [ ] CHK020 Are the connected-call timestamps (e.g., answered-at, completed-at) that SignalWire status callbacks supply explicitly defined as required fields on the Phone Call activity payload? [Clarity, Spec §FR-020, Spec §US1 AC-6]

## Identity recording (operator / persona / runtime / model)

- [ ] CHK021 Is the persona version required to be recorded on every Slice 3 session and on the run report? [Completeness, Spec §FR-016, Spec §US5 AC-6]
- [ ] CHK022 Is the runtime/model identity (Pipecat runtime + configured real-time AI provider name + model version) required to be recorded on every Slice 3 session and on the run report? [Completeness, Spec §FR-016, Spec §Key Entities Configured Real-time AI Provider]
- [ ] CHK023 Is the model configuration relevant to audit (e.g., model name and version) defined precisely enough to be measurable (i.e., what counts as "relevant to audit")? [Ambiguity, Spec §FR-016]
- [ ] CHK024 Is the invoking operator identity unambiguously defined (at minimum the OS user or a CLI-provided operator identifier) so a tester knows what value to assert? [Clarity, Spec §FR-016, Spec §Clarifications Session 2026-05-25 Q3]
- [ ] CHK025 Is the operator identity's local-only constraint explicitly stated for every Slice 3 artifact (session-result, run report) AND consistently negated for every Dataverse artifact (Phone Call activity, queue, Task)? [Consistency, Spec §FR-016, Spec §FR-036, Spec §Clarifications Session 2026-05-25 Q3]
- [ ] CHK026 Does FR-016's "no new Phone Call activity / queue / Task field is added for operator identity" cover every Dataverse write path, or is there a path (e.g., a free-text notes field) where operator identity could still leak? [Completeness, Spec §FR-016]
- [ ] CHK027 Is the persona version's relationship to the Slice 1 persona policy stable across Slice 3 (i.e., the persona version field is not changed by Slice 3 even though a live model is added)? [Consistency, Spec §FR-014, Spec §FR-016, Spec §Assumptions Persona policy preserved]
- [ ] CHK028 Are secret values explicitly prohibited from the identity fields (model name / version is OK; provider API key / credentials is NOT) — i.e., is the boundary between identity and credentials defined? [Clarity, Spec §FR-016, Spec §FR-035]
- [ ] CHK029 Is the runtime/model identity required on EVERY Slice 3 session including blocked-by-readiness sessions (where no runtime ran), or only on sessions that connected? [Gap, Spec §FR-016, Spec §FR-011]

## Blocked / failure-reason surfacing

- [ ] CHK030 Is the readiness-failure surfacing requirement consistent between the run report (FR-036 "failing readiness check or block reason when applicable") and the readiness report (FR-011 "failing check named")? [Consistency, Spec §FR-036, Spec §FR-011]
- [ ] CHK031 Is the eligibility-blocked outcome's `blocked_reason` field required on the normalized session result AND surfaced in the run report? [Consistency, Spec §FR-017, Spec §FR-036, Spec §FR-019, Spec §US3 AC-5]
- [ ] CHK032 Is the `live_call_abandonment` reason required to appear in the run report and on the normalized session result? [Completeness, Spec §FR-026, Spec §US4 AC-8]
- [ ] CHK033 Is the `script_truncated` `human_review_reason` consistently used across mid-call runtime degradation triggers (FR-013 (c) silence-timeout) AND mid-call hangup without enough signal (US4 AC-5)? [Consistency, Spec §FR-013, Spec §US4 AC-5, Spec §Edge Cases Live model failure or runtime crash mid-call]
- [ ] CHK034 Is the runtime-failure reason set defined (FR-013 names "runtime-failure reason" but does not enumerate distinct codes for provider error vs. runtime crash) — is one code or multiple codes required? [Ambiguity, Spec §FR-013, Spec §US5 AC-5]
- [ ] CHK035 Is the `shadow_stt_discrepancy` reason code defined as additive to the Slice 1 enumerated set, and is the assertion that existing reason codes are not replaced or repurposed testable? [Measurability, Spec §FR-031, Spec §Key Entities Preserved Slice 1 / Slice 2 Entities]
- [ ] CHK036 Is the provider-rejected-dial-failure reason (FR-012) surfaced consistently in both the run report and the queue-status update, so an operator can trace the failure from either artifact? [Consistency, Spec §FR-012, Spec §FR-036]
- [ ] CHK037 Is the conflicting-late callback's audit row content sufficient to root-cause the original disposition that was NOT changed (i.e., does the audit row identify the finalized disposition and the timestamp at which the conflicting callback arrived)? [Completeness, Spec §FR-027, Spec §Edge Cases SignalWire status callback delivered after disposition finalized]
- [ ] CHK038 Is the readiness-failure reason structured (named check + reason code) or free-text — and is that level of structure sufficient for downstream automation? [Ambiguity, Spec §FR-011, Spec §FR-036]
- [ ] CHK039 Does the spec require the run report to identify which acceptance scenario / disposition path was taken, or only the final disposition? [Gap, Spec §FR-036]

## No-secrets guarantee coverage

- [ ] CHK040 Is the no-secrets prohibition applied to every artifact type — logs, exported artifacts, run report, planned/actual write-back payloads, callbacks audit log, conflicting-events audit log, shadow STT artifacts, transcript artifacts, session-result, readiness report? [Coverage, Spec §FR-035, Spec §SC-018]
- [ ] CHK041 Is the credentials-set FR-035 protects unambiguously enumerated — SignalWire credentials, real-time AI provider credentials, shadow STT provider credentials, Dataverse credentials, "or any other secret"? [Completeness, Spec §FR-035, Spec §SC-018]
- [ ] CHK042 Is the no-secrets requirement extended to the callback-authentication mechanism (FR-008 — verification secrets MUST NOT be logged)? [Consistency, Spec §FR-008, Spec §FR-035]
- [ ] CHK043 Is the no-secrets requirement extended to the identity-recording fields (FR-016 — operator identity, persona version, runtime/model identity) so an inspector can confirm the identity strings themselves are not credential material? [Consistency, Spec §FR-016, Spec §FR-035]
- [ ] CHK044 Is the no-secrets requirement testable — i.e., is "secret" defined precisely enough that a static-analysis or scanning tool can enforce SC-018's "0 secrets" claim? [Measurability, Spec §SC-018, Spec §FR-035]
- [ ] CHK045 Is the default-on redaction policy (FR-033) defined as applying to every transcript artifact written to disk, including shadow STT transcripts? [Consistency, Spec §FR-033, Spec §FR-034, Spec §Edge Cases Default-on redaction applied to a Slice 3 transcript]
- [ ] CHK046 Is the no-secrets guarantee preserved when retention is summary-only or pointer-only (FR-033 — no full transcript file is written, but the summary and pointer artifacts still honor the no-secrets rule)? [Coverage, Spec §FR-033, Spec §FR-035, Spec §Edge Cases Transcript retention is summary-only or pointer-only]
- [ ] CHK047 Is the no-secrets requirement applied to the planned write-back artifacts produced by rehearsal / readiness mode (FR-002), since rehearsal artifacts may include payload content destined for Dynamics? [Coverage, Spec §FR-002, Spec §FR-035]

## Retention floor uniformity

- [ ] CHK048 Is the ≥ 90-day audit retention floor (FR-022) applied uniformly to every audit-grade artifact — correlation rows, progress rows, callbacks audit log, conflicting-events audit log, shadow STT artifacts, shadow STT discrepancy records, run report, readiness report? [Coverage, Spec §FR-022, Spec §Assumptions Local artifact retention]
- [ ] CHK049 Is the shadow STT discrepancy record's retention explicitly defined as "audit/review evidence even when transcript retention is summary-only" (FR-034), and is that exception consistent with the ≥ 90-day floor? [Consistency, Spec §FR-034, Spec §FR-022]
- [ ] CHK050 Is the transcript artifact's retention policy (FR-033 — full + redacted, summary-only, pointer-only) explicitly distinguished from the audit-grade artifact retention floor (FR-022)? [Clarity, Spec §FR-033, Spec §FR-022]
- [ ] CHK051 Does the spec specify whether the run report itself is subject to the ≥ 90-day floor, or only the audit logs it summarizes? [Gap, Spec §FR-036, Spec §FR-022, Spec §Assumptions Local artifact retention]
- [ ] CHK052 Is the "MUST NOT auto-delete audit artifacts" rule (Assumptions Local artifact retention) consistent with the FR-022 retention floor (i.e., manual pruning is the only deletion path)? [Consistency, Spec §FR-022, Spec §Assumptions Local artifact retention]
- [ ] CHK053 Is the retention policy for the planned write-back artifacts produced by rehearsal mode defined (do they fall under the ≥ 90-day floor, the transcript retention modes, or neither)? [Gap, Spec §FR-002, Spec §FR-022]
- [ ] CHK054 Is the retention behavior for backwards-compatible pre-Slice-3 artifacts (Assumptions Backwards-compatible call ID correlation) defined relative to the Slice 3 retention floor? [Gap, Spec §Assumptions Backwards-compatible call ID correlation, Spec §FR-022]

## Shadow STT observability completeness

- [ ] CHK055 Is the run report's "shadow STT enabled/disabled and discrepancy summary" field defined precisely enough to be implementable (what is in the discrepancy summary)? [Ambiguity, Spec §FR-036, Spec §FR-032]
- [ ] CHK056 Is the shadow STT discrepancy classification (benign / uncertain) stored on the discrepancy record so an audit reader can replay the decision? [Completeness, Spec §FR-031, Spec §Key Entities Shadow STT Discrepancy Record]
- [ ] CHK057 Is the per-high-value-field comparison record (FR-030's "compare high-value fields... against the live conversation path's transcript/log") defined as a distinct artifact or a sub-field of the shadow transcript? [Ambiguity, Spec §FR-030, Spec §Key Entities Shadow STT Lane]
- [ ] CHK058 Is the shadow-lane failure / timeout case observable in the run report (FR-029 — shadow-lane failure recorded) with enough detail to root-cause (failure type, timestamp)? [Completeness, Spec §FR-029, Spec §US6 AC-6, Spec §Edge Cases Shadow STT lane fails or times out]
- [ ] CHK059 Is the "no shadow STT events independently mutate a CRM record" assertion (SC-013) verifiable via the observability surface (e.g., shadow-lane artifact identifier is never present as the source of a Dataverse write)? [Measurability, Spec §SC-013, Spec §FR-030]

## Scenario classes (release-gate)

- [ ] CHK060 **Primary**: Is the happy-path observability complete (US1 success produces all enumerated artifacts: session-result, transcript or pointer, run report, callbacks audit log, shadow STT artifact when enabled, plus the Dynamics records)? [Coverage, Spec §US1 Independent Test, Spec §FR-036, Spec §FR-038]
- [ ] CHK061 **Alternate**: Is observability defined for every disposition variant (interested_callback_requested, interested_email_captured, not_interested, call_back_later, wrong_number, no_answer, voicemail, do_not_call, needs_human_review, failed, blocked) — does the run report distinguish them clearly? [Coverage, Spec §FR-017, Spec §FR-036]
- [ ] CHK062 **Alternate**: Is observability defined for rehearsal mode (planned write-back artifacts + readiness report + zero-mutation evidence)? [Coverage, Spec §FR-002, Spec §US2 Independent Test, Spec §SC-002]
- [ ] CHK063 **Exception / Error**: Is observability defined for every readiness-failure category (US3 a–h) — does the readiness report name the failing check with a structured reason for each? [Coverage, Spec §US3, Spec §FR-011, Spec §SC-010]
- [ ] CHK064 **Exception / Error**: Is observability defined for live-runtime degradation triggers (FR-013 a/b/c) — does the run report distinguish the three trigger types so root cause is identifiable? [Coverage, Spec §FR-013, Spec §Edge Cases Live model failure or runtime crash mid-call]
- [ ] CHK065 **Exception / Error**: Is observability defined for provider-rejected dial (FR-012) — does the run report contain enough detail to identify which provider response triggered the rejection? [Completeness, Spec §FR-012]
- [ ] CHK066 **Exception / Error**: Is observability defined for the live-call abandonment timeout (FR-026) — does the run report record the timeout value AND the elapse condition, not just the final disposition? [Gap, Spec §FR-026]
- [ ] CHK067 **Recovery**: Does the audit allow root-causing a resume path (FR-022) — i.e., the run report distinguishes per-write-back-operation status (planned / completed / resume-needed / blocked) so an inspector can identify which writes the resume attempted? [Coverage, Spec §FR-022, Spec §FR-036]
- [ ] CHK068 **Recovery**: Does the audit allow root-causing an out-of-order callback recovery (Edge Cases SignalWire status callbacks delivered out of order) — i.e., the run report records the out-of-order delivery and the normalized stream? [Coverage, Spec §FR-005, Spec §FR-027, Spec §US4 AC-2, Spec §Edge Cases SignalWire status callbacks delivered out of order]
- [ ] CHK069 **Recovery**: Does the audit allow root-causing a duplicate-callback recovery — i.e., the callbacks audit log records every duplicate keyed by `(session_id, provider_event_id)` AND identifies the no-op semantics applied? [Coverage, Spec §FR-007, Spec §FR-021, Spec §US4 AC-1]
- [ ] CHK070 **Recovery**: Does the audit allow root-causing a conflicting-late-callback recovery — i.e., the conflicting-events audit log preserves the finalized disposition and the late callback content (FR-027)? [Coverage, Spec §FR-027, Spec §Edge Cases SignalWire status callback delivered after disposition finalized]
- [ ] CHK071 **Recovery**: Does the audit allow root-causing a CRM-conflict recovery — i.e., the CRM-queue-item-changed-by-human case (Edge Cases) produces audit evidence per the Slice 2 conflict-detection behavior, preserved in Slice 3? [Coverage, Spec §Edge Cases CRM queue item changed by a human between claim and write-back]
- [ ] CHK072 **Non-Functional**: Is the observability surface sufficient to verify FR-038's "demo without a custom UI" claim — i.e., the artifacts named in FR-038 cover every operator-visible question? [Completeness, Spec §FR-038, Spec §SC-017]
- [ ] CHK073 **Non-Functional**: Is the run report's "shadow STT enabled/disabled" claim consistently required regardless of shadow STT outcome (enabled-and-agreeing, enabled-and-discrepant, enabled-and-failed, disabled)? [Consistency, Spec §FR-032, Spec §US6 AC-5, Spec §US6 AC-7]
- [ ] CHK074 **Non-Functional**: Is the audit artifact set sufficient to verify SC-008's "100% of duplicate SignalWire callbacks and repeated CLI recovery attempts leave Dynamics with no duplicates" — i.e., per-session counts of Phone Call activities, Tasks, queue-status transitions, attempt-count increments are derivable from the audit surface? [Measurability, Spec §SC-008, Spec §FR-021, Spec §FR-022]
- [ ] CHK075 **Non-Functional**: Is the observability surface sufficient to distinguish a SC-014 "deterministic disposition selected the disposition" result from a "live model alone selected the disposition" result (i.e., audit evidence the deterministic rules ran)? [Measurability, Spec §SC-014, Spec §FR-014]
- [ ] CHK076 **Non-Functional**: Is the observability surface sufficient to verify SC-015's boundary-leak claim — i.e., is there an inspection procedure named in the spec (or is it [Gap])? [Gap, Spec §SC-015]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap] or [Conflict].

### Rejected-by-authentication audit log (Q9 / FR-008)

- [ ] CHK077 Is the rejected-by-authentication audit log enumerated in the spec's artifact list as a DISTINCT artifact, separately identifiable from the Callbacks Audit Log and from the Conflicting Event Audit Record? [Completeness, Spec §FR-008, Spec §FR-036, Spec §Clarifications Session 2026-05-25 Round 2 Q4]
- [ ] CHK078 Are the rejected-by-authentication audit log's required fields enumerated as a closed list — `received_at`, source metadata (e.g., provider-supplied source identifier or IP-level metadata where available) — AND is the prohibited content enumerated (verification secret, callback body content)? [Completeness, Spec §FR-008]
- [ ] CHK079 Is the boundary between the rejected-by-authentication audit log and the callbacks audit log unambiguous (a callback that fails auth is NOT also recorded in the callbacks audit log, OR it is — and the spec states which)? [Ambiguity, Spec §FR-008, Spec §FR-007, Spec §Key Entities Callbacks Audit Log]
- [ ] CHK080 Is the rejected-by-authentication count required as a distinct field on the run report (per-session granularity), separate from the callbacks audit / conflicting-callbacks audit row counts? [Completeness, Spec §FR-008, Spec §FR-036]
- [ ] CHK081 Is the prohibition on logging the callback body content for rejected-by-auth callbacks measurable (i.e., the no-body-content guarantee is enforceable by inspection of the artifact)? [Measurability, Spec §FR-008, Spec §FR-035]
- [ ] CHK082 Is the rejected-by-authentication audit log subject to the same ≥ 90-day retention floor as other audit artifacts (FR-022 / Assumptions Local artifact retention)? [Coverage, Spec §FR-008, Spec §FR-022, Spec §Assumptions Local artifact retention]
- [ ] CHK083 Is the no-secrets guarantee (FR-035) explicitly extended to the rejected-by-authentication audit log content — i.e., the verification secret prohibition is stated in BOTH FR-008 and is consistent with FR-035? [Consistency, Spec §FR-008, Spec §FR-035]

### Resume operator format on run report (Q12 / FR-016 / FR-036)

- [ ] CHK084 Is the "resumed by X, original operator Y" format on the run report defined precisely enough to be implementable (e.g., field names, ordering, or example string)? [Clarity, Spec §FR-016, Spec §FR-036]
- [ ] CHK085 Does the spec define what the run report records when an additional resume invocation is performed on a session that has already been resumed once (i.e., does the format support a chain of resuming operators, or is only the most recent resumer recorded)? [Gap, Spec §FR-016, Spec §FR-036]
- [ ] CHK086 Does the spec define what the run report records when the original session's operator identity is missing or unknown at resume time (e.g., the original session pre-dates Slice 3 operator-identity recording, or the local session record is corrupt)? [Gap, Spec §FR-016, Spec §FR-036]
- [ ] CHK087 Is the resume-operator record required to be present on EVERY resume invocation's run report (not only when the resuming operator differs from the original)? [Ambiguity, Spec §FR-016, Spec §FR-036]
- [ ] CHK088 Is the operator-identity preservation requirement (original identity preserved on local session record and audit artifacts) consistent across audit artifacts AND the run report (i.e., the local session record holds the original; the run report holds BOTH)? [Consistency, Spec §FR-016, Spec §FR-036]
- [ ] CHK089 Are both the original and resuming operator identities subject to the no-secrets guarantee (FR-035) — i.e., neither identity field may carry credential material? [Coverage, Spec §FR-016, Spec §FR-035]
- [ ] CHK090 Does the spec require that operator identity on a resume invocation continues to be local-only (NOT propagated into Dataverse) for BOTH the original and resuming operators? [Consistency, Spec §FR-016]
- [ ] CHK091 Is the resume-operator record observable in the rehearsal-mode case (a resume re-invocation that omits the real-call flag still produces a run report under FR-022, and that report still records original + resuming operator)? [Coverage, Spec §FR-016, Spec §FR-022, Spec §FR-036]

### Shadow-lane truncated post-finalization audit event (Q7 / FR-029)

- [ ] CHK092 Is the `shadow_lane_truncated` audit event defined as a distinct, named event type in the spec's audit-event vocabulary? [Completeness, Spec §FR-029]
- [ ] CHK093 Is the storage artifact for `shadow_lane_truncated` events specified (i.e., are these events written to the Shadow STT Lane / Shadow Transcript artifact, the Shadow STT Discrepancy Record artifact, the callbacks audit log, the conflicting-events audit log, or a distinct new artifact)? [Gap, Spec §FR-029, Spec §Key Entities Shadow STT Lane, Spec §Key Entities Shadow STT Discrepancy Record]
- [ ] CHK094 Are the `shadow_lane_truncated` event's required fields enumerated (e.g., session ID, finalization timestamp, late-arrival timestamp, grace-window value used, the shadow-lane output that was truncated)? [Completeness, Spec §FR-029]
- [ ] CHK095 Does the spec require that the run report surfaces whether a `shadow_lane_truncated` event occurred for the session, so an inspector can detect post-finalization truncation without reading audit logs? [Gap, Spec §FR-029, Spec §FR-036]
- [ ] CHK096 Is the `shadow_lane_truncated` event's MUST-NOT-mutate guarantee (no disposition mutation, no new CRM write-back) testable by inspection of the audit surface (i.e., the audit row identifies that no CRM payload was emitted)? [Measurability, Spec §FR-029, Spec §FR-027]
- [ ] CHK097 Is the relationship between `shadow_lane_truncated` (post-finalization shadow lane output) and conflicting-late callbacks (post-finalization SignalWire callback) consistent — are they recorded in the same audit artifact, or distinct artifacts, and is the distinction clear? [Consistency, Spec §FR-029, Spec §FR-027]
- [ ] CHK098 Is the grace-window value itself (the deployment-configured value that was in effect for the session) required to be recorded on the run report or session-result, so the truncation event is reproducible? [Gap, Spec §FR-029, Spec §FR-036]
- [ ] CHK099 Does the spec require the `shadow_lane_truncated` event count (and/or boolean) to participate in the run report's shadow STT discrepancy summary (FR-036), or is it surfaced separately? [Ambiguity, Spec §FR-036, Spec §FR-029]
- [ ] CHK100 Is the `shadow_lane_truncated` audit event subject to the same ≥ 90-day retention floor as other audit artifacts? [Coverage, Spec §FR-029, Spec §FR-022]

### Telephony readiness summary on run report (FR-036)

- [ ] CHK101 Does FR-036 now explicitly list `telephony_readiness_summary` (each readiness check from FR-009 with its result) as a required run-report field, closing the Round 1 CHK012 [Conflict] between FR-036 and Key Entities Run Report? [Consistency, Spec §FR-036, Spec §Key Entities Run Report, closes CHK012]
- [ ] CHK102 Is `telephony_readiness_summary` defined as the per-check result tuple (check name + result) for every readiness check enumerated in FR-009, so the field has a closed structure? [Completeness, Spec §FR-036, Spec §FR-009]
- [ ] CHK103 Is the relationship between `telephony_readiness_summary` (a run-report field, per FR-036) and the Telephony Readiness Report (a separate Key Entity) defined — i.e., does the run report embed the summary, reference the readiness report by id, or duplicate the content? [Ambiguity, Spec §FR-036, Spec §Key Entities Telephony Readiness Report]
- [ ] CHK104 Is `telephony_readiness_summary` required on EVERY Slice 3 run report, including rehearsal-mode runs and runs blocked before any readiness check could complete? [Coverage, Spec §FR-036, Spec §FR-002, Spec §FR-011]
- [ ] CHK105 Is the run-report rejected-by-authentication callbacks count requirement (per FR-008, surfaced per FR-036) listed in the FR-036 "at minimum" enumeration alongside the existing callbacks audit / conflicting-callbacks audit row counts? [Completeness, Spec §FR-036, Spec §FR-008]
- [ ] CHK106 Does the Round 2 FR-036 amendment preserve every Round 1 required field (run mode, session ID, invoking operator identity, real provider call ID when assigned, persona version, runtime/model identity, final disposition, per-write-back-operation status, shadow STT enabled/disabled + discrepancy summary, callbacks audit / conflicting-callbacks audit row counts, failing readiness check or block reason)? [Consistency, Spec §FR-036]
- [ ] CHK107 Is the FR-036 required-field enumeration now exhaustive (no remaining gaps between the FR-036 list and the Key Entities Run Report description after the Round 2 amendment)? [Completeness, Spec §FR-036, Spec §Key Entities Run Report, closes CHK012]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Run-report schema completeness (Research §9 vs. FR-036)

- [ ] CHK108 Does every required field enumerated in FR-036 (run_mode, session_id, operator_identity {current, original}, real_provider_call_id, persona_version, runtime_identity, final_disposition, per_writeback_operation_status, shadow_stt {enabled, discrepancy_summary, lane_truncated}, telephony_readiness_summary, callbacks_audit_row_count, conflicting_callbacks_audit_row_count, rejected_auth_callbacks_count, started_at, ended_at, failure/blocked reason) appear in the Research §9 run_report.json schema with the correct JSON type? [Consistency, Research §9, Spec §FR-036, closes CHK012/CHK101/CHK107 against plan]
- [ ] CHK109 Is the `operator_identity` schema in Research §9 defined as `{current: string, original: string|null}` (matching the Round 2 Q12 "resumed by X, original operator Y" requirement and the Data-Model §2.1 `operator_identity_original` nullable column)? [Consistency, Research §9, Data-Model §2.1, Spec §FR-016, Spec §Clarifications Round 2 Q12]
- [ ] CHK110 Is the `runtime_identity` schema in Research §9 defined as `{runtime, version, provider, model_name, model_version}` (matching the Data-Model §1.12 `RealtimeProviderSession` columns and the FR-016 audit identity requirement)? [Consistency, Research §9, Data-Model §1.12, Spec §FR-016]
- [ ] CHK111 Is the `telephony_readiness_summary` schema in Research §9 defined as an array of `{check, result, detail}` tuples (matching the Data-Model §1.9 `TelephonyReadinessReport` entity and covering every readiness check from FR-009)? [Consistency, Research §9, Data-Model §1.9, Spec §FR-009, Spec §FR-036]
- [ ] CHK112 Is the `per_writeback_operation_status` schema in Research §9 defined as an ordered array (preserving DNC-first ordering on `do_not_call` per Round 2 Q14 and the Data-Model §1.11 `WriteBackOperation` variant table)? [Consistency, Research §9, Data-Model §1.11, Spec §FR-024, Spec §FR-020]
- [ ] CHK113 Is the `shadow_stt.lane_truncated` boolean in Research §9 derived from / consistent with the Data-Model §1.8 `ShadowLaneTruncatedEvent` entity's presence-or-absence semantics? [Consistency, Research §9, Data-Model §1.8, Spec §FR-029]

### Artifact-file enumeration (Data-Model §4 vs. Quickstart §3 "Expected outputs")

- [ ] CHK114 Are all 11 artifact file types enumerated in Data-Model §4 (run_report.json, transcript.txt, shadow_transcript.txt, callbacks_audit.jsonl, rejected_auth_callbacks.jsonl, conflicting_callbacks_audit.jsonl, shadow_discrepancies.jsonl, shadow_lane_truncated.json, telephony_readiness.json, planned_writeback.json, actual_writeback.json) listed in Quickstart §3 "Expected outputs (real-call mode)"? [Consistency, Data-Model §4, Quickstart §3]
- [ ] CHK115 Is the rehearsal-mode Quickstart §2 "Expected outputs" list (run_report.json + telephony_readiness.json + planned_writeback.json, with the rest excluded because no call was placed) consistent with Data-Model §4's per-artifact conditional notes ("only when ≥1 ... received", "only when shadow STT enabled", etc.)? [Consistency, Quickstart §2, Data-Model §4]
- [ ] CHK116 Does the Quickstart §3 expected-output list distinguish between always-produced artifacts (run_report.json, telephony_readiness.json) and conditionally-produced artifacts (rejected_auth_callbacks.jsonl only when ≥1 rejected, shadow_*.* only when --shadow-stt, conflicting_callbacks_*.* only when ≥1 late), matching the Data-Model §4 conditional notes? [Consistency, Quickstart §3, Data-Model §4]

### JSONL format line-readability / grep / jq compatibility

- [ ] CHK117 Does Research §10 specify that every audit-log file uses one JSON object per line (`.jsonl`) so the file remains line-readable, append-friendly, grep-friendly, and jq-friendly for every audit log (`callbacks_audit.jsonl`, `rejected_auth_callbacks.jsonl`, `shadow_discrepancies.jsonl`, `conflicting_callbacks_audit.jsonl`)? [Completeness, Research §10]
- [ ] CHK118 Is the JSONL line format constrained so that each line is a complete JSON object with no embedded newlines (a critical jq / grep compatibility requirement), and is this constraint pinned in Research §10 or Data-Model §1.3 / §1.4 / §1.5 / §1.7? [Gap, Research §10, Data-Model §1.3, Data-Model §1.4, Data-Model §1.5, Data-Model §1.7]
- [ ] CHK119 Are the non-JSONL artifact formats (`run_report.json` as a single JSON object, `shadow_lane_truncated.json` as a single JSON object, `telephony_readiness.json` as a single JSON object, `transcript.txt` + `shadow_transcript.txt` as plain text) called out in Research §10 / Data-Model §4 so the format-per-file decision is unambiguous? [Consistency, Research §10, Data-Model §4]

### Rejected-auth count surfaced in run_report AND quickstart sample

- [ ] CHK120 Is `rejected_auth_callbacks_count` listed in BOTH the Research §9 run_report.json schema AND the Quickstart §4 sample (`"rejected_auth_callbacks_count": 0`), so the field is documented in both the schema and an example? [Consistency, Research §9, Quickstart §4, Spec §FR-008, Spec §FR-036, closes CHK105 against plan]
- [ ] CHK121 Does the Quickstart §4 sample show `rejected_auth_callbacks_count` as a numeric (not boolean) so the per-FR-008 count semantics (operator sees the number of attempted forgeries) is preserved? [Consistency, Quickstart §4, Spec §FR-008]
- [ ] CHK122 Is the Contract: rejected-auth-audit-log `count_for_session` method consistent with the Research §9 run_report.json `rejected_auth_callbacks_count` field type AND the Data-Model §1.4 / §3 SQLite mirror so the count's source-of-truth is identifiable? [Consistency, Contract: rejected-auth-audit-log, Research §9, Data-Model §1.4, Data-Model §3]

### Resume operator format consistency across plan / contract / quickstart

- [ ] CHK123 Does the resume-operator "resumed by X, original operator Y" format appear consistently in Plan §Constitution Check Post-Design (Round 2 Q13), Contract: cli-slice3 §Resume operator identity, Quickstart §5, and Research §9 run_report.json `operator_identity: {current, original}`? [Consistency, Plan §Constitution Check, Contract: cli-slice3, Quickstart §5, Research §9, Spec §FR-016, Spec §FR-036, Spec §Clarifications Round 2 Q12]
- [ ] CHK124 Is the resume-operator format example string (e.g., "resumed by X, original operator Y") shown literally in at least one plan-side artifact (Contract: cli-slice3 names it explicitly; does Quickstart §5 or the Research §9 schema include a literal example)? [Completeness, Contract: cli-slice3, Quickstart §5, Research §9]
- [ ] CHK125 Is the operator-identity local-only invariant (operator identity MUST NOT propagate to Dataverse per FR-016 / Round 2 Q12) enforced by the Contract: crm-writeback-dnc-first `test_operator_identity_not_in_dataverse` test AND by the Data-Model §2.3 `PhoneCallActivityPayload` note "No Dataverse field is added by Slice 3 for operator identity"? [Consistency, Contract: crm-writeback-dnc-first, Data-Model §2.3, Spec §FR-016]

### DNC-first per-writeback-operation-status ordering invariant

- [ ] CHK126 Is the DNC-first ordering on `do_not_call` outcomes documented consistently in Plan §Summary (Round 2 Q14), Contract: crm-writeback-dnc-first §DNC-first ordering, Quickstart §3 (table row "**`do_not_call`**" with "**DNC FIRST, Round 2 Q14**"), Quickstart §4 (`per_writeback_operation_status[0].operation is queue_status_update.dnc` on do_not_call), and Data-Model §1.11 (WriteBackOperation variant table row "**FIRST** in the write-back sequence on `do_not_call`")? [Consistency, Plan §Summary, Contract: crm-writeback-dnc-first, Quickstart §3, Quickstart §4, Data-Model §1.11, Spec §FR-024]
- [ ] CHK127 Does the Contract: crm-writeback-dnc-first §Per-disposition step ordering table (the row "**`do_not_call`** | **queue_status_update.dnc → phone_call_activity → (no task)**") match the Quickstart §3 disposition table row for `do_not_call` (Phone Call activity created; Queue-status update DNC FIRST; — Task; DNC field updated)? [Consistency, Contract: crm-writeback-dnc-first, Quickstart §3]
- [ ] CHK128 Does the Contract: crm-writeback-dnc-first `test_dnc_first_on_do_not_call` test assert that `assemble_writeback({disposition: do_not_call})[0]` is `QueueStatusUpdateVariant.DNC` (matching the Data-Model §1.11 ordering invariant)? [Consistency, Contract: crm-writeback-dnc-first §Contract test summary, Data-Model §1.11]

### telephony_readiness.json artifact ↔ run_report telephony_readiness_summary

- [ ] CHK129 Is the `telephony_readiness.json` artifact file format (Data-Model §1.9) consistent with the `telephony_readiness_summary` field schema in the Research §9 run_report.json (same per-check tuple shape, same enumerated check names)? [Consistency, Data-Model §1.9, Research §9, Spec §FR-009, Spec §FR-036]
- [ ] CHK130 Does the relationship between the standalone `telephony_readiness.json` artifact and the embedded `run_report.json.telephony_readiness_summary` array clearly resolve whether the run report DUPLICATES the standalone file's content (Data-Model §4 says "always; mirrors the run_report.json summary"), closes CHK103 (Round 2 ambiguity) against the plan? [Consistency, Data-Model §4, Data-Model §1.9, Research §9, closes CHK103]
- [ ] CHK131 Is the `telephony_readiness.json` file required for EVERY Slice 3 invocation including rehearsal-mode (Data-Model §4 says "always") AND including runs that are blocked before all readiness checks complete (closes CHK104 against the plan)? [Consistency, Data-Model §4, Spec §FR-011, Spec §FR-036, closes CHK104]
- [ ] CHK132 Are the 9 readiness check enum values in Data-Model §1.9 (`signalwire_credentials`, `source_caller_id_authorized`, `destination_phone_e164`, `status_callback_url_configured`, `media_callback_url_configured`, `campaign_persona_runtime_mapping`, `dataverse_metadata_verified`, `task_owner_mapping_resolved`, `eligibility`) exhaustive against the readiness-check list in Spec §FR-009 and Quickstart §8 "Common readiness failures"? [Completeness, Data-Model §1.9, Spec §FR-009, Quickstart §8]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- CHK108 – CHK132 are Round 3 amendments (2026-05-25) validating the Phase-1 plan-side artifacts: the run_report.json schema completeness against FR-036, the artifact-file enumeration consistency between Data-Model §4 and Quickstart §3, the JSONL format guarantees in Research §10, the rejected-auth count visibility across run_report.json and Quickstart §4, the resume-operator "resumed by X, original operator Y" format across plan / contract / quickstart, the DNC-first per-writeback-operation-status ordering invariant, and the telephony_readiness.json ↔ run_report.json.telephony_readiness_summary consistency.
- ≥80% of items reference a spec section or a quality marker for traceability.
