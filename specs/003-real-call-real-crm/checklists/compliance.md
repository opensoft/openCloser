# Compliance Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the regulatory and compliance dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Regulatory Grounding — AI-on-Behalf-of-Medx Disclosure

- [x] CHK001 Is the AI-on-behalf-of-Medx disclosure required on every connected real call in FR-015 with no exception clause that could omit it? [Completeness, Spec §FR-015] — FR-015: "first connected-call utterance MUST continue to deliver the canonical Slice 1 disclosure on every connected call"; no exception.
- [x] CHK002 Is the disclosure-on-first-utterance requirement stated identically in FR-015, Constitution Alignment ("Safety and human handoff"), and User Story 5 #1? [Consistency, Spec §FR-015, Spec §Constitution Alignment, Spec §User Story 5 #1] — All three state disclosure at start/first utterance of every connected call.
- [x] CHK003 Does FR-015 explicitly carry forward the Slice 1 disclosure language (so a compliance reviewer can locate the canonical script and version it)? [Traceability, Spec §FR-015] — FR-015 names "canonical Slice 1 AI-on-behalf-of-Medx disclosure"; persona-version recording (FR-016) versions it.
- [x] CHK004 Does the spec require that the disclosure language is owned by the persona module (not by the live model), per FR-014, so model variation cannot weaken the disclosure? [Consistency, Spec §FR-014, Spec §FR-015] — FR-014: persona owns disclosure language; live model MUST NOT mutate disposition/reason set; Constitution §Boundaries reinforces.
- [x] CHK005 Is FR-016's recording of the persona version + runtime/model identity sufficient to reconstruct which disclosure language version was used on a given call? [Measurability, Spec §FR-016] — FR-016 records persona version + runtime/model identity per session and run report; CHK146 confirms version→text reconstruction.

## Post-Clarification Disclosure-Acknowledgment Policy

- [x] CHK006 Is the "no explicit verbal acknowledgment required" policy stated in FR-015 in a way a compliance reviewer can audit (i.e., the rule is in the binding requirements section, not only in the Clarifications log)? [Completeness, Spec §FR-015, Spec §Clarifications] — FR-015 binding text states no explicit acknowledgment required; continue after brief pause.
- [x] CHK007 Is the "absence of opt-out → implicit acknowledgment" rule defined identically in FR-015 and in the 2026-05-25 Clarifications entry? [Consistency, Spec §FR-015, Spec §Clarifications] — Both phrase it as: absence of opt-out treated as implicit acknowledgment, no escalation.
- [x] CHK008 Does FR-015 explicitly state that no new `human_review_reason` is introduced for a missing acknowledgment (so the enumerated reason set in Slice 1 + the additive `shadow_stt_discrepancy` is the complete set)? [Completeness, Spec §FR-015, Spec §FR-031] — FR-015: "No new human_review_reason is introduced for a missing acknowledgment… except the additive shadow_stt_discrepancy."
- [x] CHK009 Does the spec define what "brief pause" means (qualitative phrasing only vs. a quantified or deployment-configured value) so the implementation can be verified? [Ambiguity, Spec §FR-015] — R6: R4-Q10 pins "brief pause" to deployable `disclosure_pause_ms` (default 1500 ms) in amended §FR-015; now quantified and configurable.
- [x] CHK010 Does the spec address whether the implicit-acknowledgment policy may be overridden by deployment configuration (e.g., a jurisdiction requiring explicit acknowledgment), or whether the policy is fixed? [Gap, Spec §FR-015, Spec §Assumptions] — R5: jurisdiction-driven consent variation is now declared OUT OF SCOPE (Assumptions "Telephony-consent regulatory frameworks", Round 3); the implicit-acknowledgment policy is fixed for Slice 3 by that explicit exclusion.
- [x] CHK011 Is the policy auditable from local artifacts alone (run report, transcript, session result) without needing to inspect application source? [Measurability, Spec §FR-015, Spec §FR-036] — FR-036 run report + redacted transcript + session result are inspectable without UI/source per SC-017.

## Non-Clinical Scope

- [x] CHK012 Is the non-clinical scope stated in Constitution Alignment, FR-014, FR-015, and the Assumptions "Compliance scope" entry with consistent meaning? [Consistency, Spec §Constitution Alignment, Spec §FR-014, Spec §FR-015, Spec §Assumptions] — All four say persona stays non-clinical / collects no PHI; Compliance scope: "not HIPAA-class clinical workflow."
- [x] CHK013 Does the Assumptions section explicitly name Slice 3 as "explicitly not a HIPAA-class patient-care or clinical workflow"? [Clarity, Spec §Assumptions — "Compliance scope"] — Compliance scope entry uses that exact phrasing.
- [x] CHK014 Does the spec enumerate the escalation reason codes (`outside_allowed_claims`, `non_clinical_topic_escalation`, `phi_collection_risk`) that fire on out-of-scope attempts (FR-015, User Story 5 #2)? [Completeness, Spec §FR-015, Spec §User Story 5 #2] — US5 #2 and FR-015 enumerate all three reason codes.
- [x] CHK015 Does the spec require that the persona's allowed-claim limits (no specific cost figures, no clinical recommendations, no competitor comparisons, no PHI questions) are enumerated or unambiguously cross-referenced to Slice 1? [Completeness, Spec §FR-014, Spec §FR-015, Spec §User Story 5 #2] — US5 #2 enumerates the four limit categories; FR-014/FR-015 anchor persona authority over allowed claims.
- [x] CHK016 Is the non-clinical-scope boundary the persona module's authority (FR-014), so a live model attempting to cross it triggers the persona's escalation rather than executing the request? [Consistency, Spec §FR-014, Spec §FR-015, Spec §User Story 5 #2] — FR-014 persona owns allowed claims; US5 #2: live model attempt → persona escalates, conversation ends safely.

## No-PHI Guarantee

- [x] CHK017 Is the "no PHI / no patient or resident health information" guarantee stated in both the persona policy (FR-014, FR-015) and the audit/artifact policy (Constitution Alignment, Assumptions "Compliance scope")? [Consistency, Spec §FR-014, Spec §FR-015, Spec §Constitution Alignment, Spec §Assumptions] — Persona-policy (FR-015 "MUST NOT collect PHI") and artifact-policy (FR-033 tag-and-redact, Compliance scope) both stated.
- [x] CHK018 Does the spec require the persona to refuse PHI collection (FR-015) and the persona to escalate with `phi_collection_risk` when the live model or the contact attempts PHI (User Story 5 #2, Edge Cases "Mid-call PHI / out-of-allowed-claim attempt")? [Consistency, Spec §FR-015, Spec §User Story 5 #2, Spec §Edge Cases] — FR-015 + US5 #2 + Edge Case all require refuse + phi_collection_risk escalation.
- [x] CHK019 Is the no-PHI requirement enforced in artifacts as well as on-call (i.e., redaction or other measure prevents PHI from being captured in transcripts even if uttered)? [Gap, Spec §FR-014, Spec §FR-015, Spec §FR-033] — Round 2 Q11 FR-015/FR-033 PHI tag-and-redact across four artifact types before write; closed by CHK093.
- [x] CHK020 Does the spec define which fields the persona-extracted output schema permits (so a compliance reviewer can verify the extraction surface contains no PHI-class fields)? [Completeness, Spec §FR-014, Spec §FR-017] — FR-017 enumerates the normalized-result fields; Definitions "High-value field" lists extraction surface; none are health/clinical.
- [x] CHK021 Does the persona's enumerated extraction schema (high-value fields per the "High-value field" definition: opt-out/DNC, wrong number, captured email, callback intent, person reached name/role, interest level, final disposition) align with the no-PHI guarantee (no health/clinical fields)? [Consistency, Spec §Definitions, Spec §FR-014] — All enumerated high-value fields are business-outreach, none health/clinical.

## Operator-Opt-In Posture (Real-Call / Write-Enabled Flag)

- [x] CHK022 Is the real-call / write-enabled flag defined as an explicit operator opt-in in FR-001 (no implicit / configuration-only enabling path)? [Clarity, Spec §FR-001] — FR-001: "MUST require an explicit real-call / write-enabled flag (or equivalent deliberate action)"; default invocation does neither.
- [x] CHK023 Is the rehearsal-mode default consistent across FR-001, FR-002, FR-037, the "Real-call / write-enabled mode" definition, the "Rehearsal / readiness mode" definition, User Story 2 #5, User Story 3 #6, and Assumptions "Default safe mode"? [Consistency, …] — All cited locations make rehearsal/readiness the default when the flag is omitted.
- [x] CHK024 Does SC-011 quantify the opt-in posture as 100% of flag-omitted runs placing 0 calls and creating/updating 0 records? [Measurability, Spec §SC-011] — SC-011 states exactly that.
- [x] CHK025 Does FR-016 require the invoking operator identity to be recorded on every Slice 3 session and the run report so opt-in is attributable? [Completeness, Spec §FR-016] — FR-016 records operator identity on every session + run report.
- [x] CHK026 Is the "OS user or CLI-provided operator identifier" minimum for operator identity sufficient for compliance attribution, or is a stronger identity (authenticated user) required? [Ambiguity, Spec §FR-016] — R6: R4-Q47 decides the OS-user/CLI id IS the recorded authorizer and Slice 3 does NOT require an authenticated identity — the deliberate local-only decision, now justified not open.
- [x] CHK027 Is the operator identity recorded locally only (per the 2026-05-25 Clarifications decision) and explicitly NOT propagated into Dataverse (FR-016)? [Consistency, Spec §FR-016, Spec §Clarifications] — FR-016 + Clarifications Q3: local-only, MUST NOT propagate into Dataverse.
- [x] CHK028 Does FR-016 explicitly state that no new Phone Call activity / queue / Task field is added for operator identity, so the Slice 2 Dataverse mapping surface is preserved? [Completeness, Spec §FR-016] — FR-016: "no new Phone Call activity / queue / Task field is added… Slice 2 mapping surface unchanged."
- [x] CHK029 Is FR-036's run-report requirement to include the invoking operator identity consistent with FR-016's recording requirement? [Consistency, Spec §FR-016, Spec §FR-036] — FR-036 lists operator identity (current+original) as a run-report field, consistent with FR-016.

## Retention Floor and No-Auto-Delete

- [x] CHK030 Is the retention floor of ≥ 90 days stated in FR-022 and Assumptions "Local artifact retention"? [Consistency, Spec §FR-022, Spec §Assumptions] — Both state ≥ 90 days (Slice 2 floor reused).
- [x] CHK031 Is the no-auto-delete posture ("Pruning is a manual operator action; the application MUST NOT auto-delete audit artifacts") explicit in Assumptions "Local artifact retention"? [Clarity, Spec §Assumptions] — Exact wording present in Local artifact retention.
- [x] CHK032 Does the spec require the retention floor to cover ALL Slice 3 audit artifacts (callbacks audit log, shadow STT artifacts, CRM correlation / write-back progress rows, run reports) — not only the Slice 2 inherited set? [Completeness, Spec §FR-022, Spec §Assumptions, Spec §FR-034] — Assumptions "Local artifact retention" enumerates callbacks logs, shadow STT artifacts, correlation/progress rows; FR-034 retains discrepancy records.
- [x] CHK033 Does FR-034 require shadow STT discrepancy records to be retained as audit/review evidence even when transcript retention is summary-only (i.e., discrepancy records survive transcript pruning)? [Completeness, Spec §FR-034] — FR-034: discrepancy records "MUST be retained… even when transcript retention is summary-only."
- [x] CHK034 Does the spec define whether the retention floor applies to redacted or unredacted transcript variants (or both) so retention behavior under default-on redaction is unambiguous? [Ambiguity, Spec §FR-022, Spec §FR-033] — R5: FR-015's fail-closed redaction (Round 3) means no unredacted variant is ever written ("MUST NOT be written in unredacted form"); FR-033 writes only redacted variants, so the floor unambiguously covers the only variant that persists.
- [x] CHK035 Does the spec address how the no-auto-delete posture interacts with the pointer-only retention mode (where artifacts are minimal by design)? [Gap, Spec §FR-033, Spec §Assumptions] — R6: R4-Q33 (§Assumptions "Audit retention floor is a floor") extends the ≥90-day no-lower floor to pointer records explicitly, so minimal pointer artifacts are covered.

## Redaction and Secret Exclusion

- [x] CHK036 Is default-on transcript redaction stated in FR-033 with no opt-out exception for any Slice 3 path? [Clarity, Spec §FR-033] — FR-033: default-on redaction MUST run before any transcript artifact is written; only pointer metadata excluded (machine-readable, not transcript content).
- [x] CHK037 Does FR-033 require redaction to run "before any transcript artifact is written to disk" (so redaction cannot be retroactively skipped)? [Clarity, Spec §FR-033] — Exact timing requirement present in FR-033.
- [x] CHK038 Is the no-secrets-in-artifacts guarantee enumerated for SignalWire credentials, real-time AI provider credentials, shadow STT provider credentials, and Dataverse credentials in FR-035? [Completeness, Spec §FR-035] — FR-035 enumerates all four credential classes plus "any other secret."
- [x] CHK039 Is SC-018 the measurable form of FR-035 (0 secrets in logs, exported artifacts, run report, planned/actual write-back payloads)? [Measurability, Spec §SC-018] — SC-018 quantifies 0 secrets across those surfaces.
- [x] CHK040 Does FR-008 forbid logging of secrets associated with the callback signature-verification mechanism (separate from the general FR-035 / SC-018 guarantee)? [Consistency, Spec §FR-008, Spec §FR-035] — FR-008: "MUST NOT log secrets associated with the verification mechanism" + excludes secret/body from the audit log.
- [x] CHK041 Does FR-034 require shadow STT transcript artifacts to honor the same retention policy as the live transcript (so a leaked shadow transcript cannot bypass redaction)? [Consistency, Spec §FR-033, Spec §FR-034] — FR-034: shadow transcript honors same retention; FR-033/Q10 covers it under default-on redaction.
- [x] CHK042 Does the Edge Case "Default-on redaction applied to a Slice 3 transcript" align with FR-033 (redaction runs before any transcript artifact is written)? [Consistency, Spec §Edge Cases, Spec §FR-033] — Edge Case states redaction runs before any transcript artifact is written, matching FR-033.
- [x] CHK043 Does the spec define what classes of content the default-on redaction MUST cover (PII, secrets, credentials, etc.) or is the redaction policy entirely deployment-configurable? [Ambiguity, Spec §FR-033, Spec §Assumptions] — FR-033 names the Slice 2 default-on `[REDACTED]` policy (or configured replacement); FR-035 covers secrets; PHI tag-and-redact covers PHI; policy is configurable with a named default.
- [x] CHK044 Is the redaction requirement also enforced for the run report (FR-036) and not only transcripts? [Gap, Spec §FR-033, Spec §FR-035, Spec §FR-036] — FR-035/SC-018 forbid secrets in the run report; FR-015 PHI tag-and-redact + CHK100 extend redaction to the run report's quoted/summarized utterances.

## Callback Signature Verification

- [x] CHK045 Does FR-008 require SignalWire callback authentication "using the provider's documented mechanism where supported (e.g., signature verification)"? [Completeness, Spec §FR-008] — FR-008 uses that exact phrasing; research §2 pins HMAC-SHA256.
- [x] CHK046 Does FR-008 explicitly require rejection of callbacks that fail authentication (not merely logging the failure)? [Clarity, Spec §FR-008] — FR-008: "MUST reject callbacks that fail authentication with the provider-appropriate HTTP response code" (401 per contract).
- [x] CHK047 Does the spec define the behavior when SignalWire does not support a verification mechanism in a given deployment (the "where supported" caveat)? [Ambiguity, Spec §FR-008] — CHK109 (Round 2) closes this; "where supported" caveat addressed re audit-log production when verification not in force.
- [x] CHK048 Does FR-008 explicitly forbid logging of the verification mechanism's secrets (consistent with FR-035 / SC-018)? [Consistency, Spec §FR-008, Spec §FR-035, Spec §SC-018] — FR-008 forbids verification secret; consistent with FR-035/SC-018; contract test_schema_excludes_secret_and_body enforces.
- [x] CHK049 Is the relationship between rejected-callback events and the callbacks audit log defined (does a rejected callback still create an audit row, and if so does it leak any payload)? [Gap, Spec §FR-007, Spec §FR-008] — CHK103 closes this: distinct rejected-auth log, no secret/no body; rejected callbacks not mixed into callbacks audit log.

## Telephony Authorization (Source Caller-ID)

- [x] CHK050 Does FR-009 require the configured source caller-ID number to be "authorized for outbound dialing" as a hard pre-dial check (so spoofed or unauthorized origination cannot occur)? [Completeness, Spec §FR-009] — FR-009: "source caller-ID number present and authorized for outbound dialing" as a hard readiness check; readiness enum `source_caller_id_authorized`.
- [x] CHK051 Is the "authorized for outbound dialing" semantics defined (provider-side authorization, local allowlist, or both)? [Ambiguity, Spec §FR-009] — R6: R4-Q48 defines it as SignalWire-side (provider-side) source-caller-id authorization verified via the credentials/source-number readiness check; openCloser keeps NO local allowlist (amended §FR-009).
- [x] CHK052 Is the source-caller-ID authorization check consistent with User Story 3 #2 (the "missing or not authorized" failure path)? [Consistency, Spec §FR-009, Spec §User Story 3 #2] — US3 #2 mirrors FR-009: missing or unauthorized source number → readiness failure, no dial, no attempt.
- [x] CHK053 Does the spec address the regulatory implication of source-caller-ID authorization (e.g., FCC / STIR/SHAKEN requirements, jurisdictional caller-ID rules)? [Gap, Spec §FR-009, Spec §Assumptions] — R5: Assumptions "Telephony-consent regulatory frameworks (declared out of scope)" now names STIR/SHAKEN caller-ID attestation as an explicit Round 3 exclusion deferred to a compliance-hardening PRD.

## Real-Dial Phone-Number Validation as a Regulatory Pre-Dial Block

- [x] CHK054 Does FR-010 establish phone-number validation as a hard pre-dial block (not a warning), so a malformed destination cannot dial an unintended number? [Clarity, Spec §FR-010, Spec §Assumptions] — FR-010 + Assumptions "Hard E.164 validation": Slice 2 warning promoted to hard pre-dial block.
- [x] CHK055 Does the spec explicitly state that the prior Slice 2 data-quality warning is promoted to a Slice 3 hard block (FR-010, Edge Cases "Real-dial phone-number validation failure", Assumptions "Hard E.164 validation")? [Consistency, …] — All three cited locations state the promotion to a hard block.
- [x] CHK056 Is SC-009 the measurable form of FR-010 (100% blocked, 0 attempts consumed, 0 Phone Call activities)? [Measurability, Spec §SC-009] — SC-009: 100% blocked before dial; 0 attempts/activities consumed.

## DNC / Opt-Out Honoring

- [x] CHK057 Does FR-024 require the `do_not_call` disposition (or mid-call opt-out) to update Dataverse DNC / opt-out and queue-status fields AND create no callback or review Task? [Completeness, Spec §FR-024] — FR-024 states exactly this; DNC write attempted FIRST.
- [x] CHK058 Is the DNC behavior consistent across FR-024, User Story 1 #4, User Story 5 #3, Edge Cases "Mid-call opt-out / DNC", and SC-006? [Consistency, …] — All cited locations: update DNC/opt-out + queue-status, no Task.
- [x] CHK059 Does FR-015 / User Story 5 #3 require the persona to stop the sales flow before any further sales utterance on opt-out (the "immediate stop" requirement)? [Completeness, Spec §FR-015, Spec §User Story 5 #3] — US5 #3: "persona stops the sales flow before any further sales utterance"; FR-015 honors immediate opt-out/DNC.
- [x] CHK060 Does the spec require persona authority over the DNC trigger set (so the live model cannot suppress an opt-out signal), traceable to FR-014's persona authority over disposition rules? [Consistency, Spec §FR-014, Spec §FR-015, Spec §User Story 5 #3] — FR-014: persona owns disposition rules/escalation; live model cannot mutate; US5 #3 anchors DNC stop to persona.
- [x] CHK061 Does SC-006 quantify that a `do_not_call` outcome "prevents further automated attempts" — and is the mechanism (DNC field write + eligibility check on next attempt) traceable to FR-019's eligibility-preserved behavior? [Measurability, Spec §FR-019, Spec §FR-024, Spec §SC-006] — SC-006 "prevents further automated attempts"; FR-019 preserves six rules (incl. DNC); CHK128 traces the block mechanism.
- [x] CHK062 Does the FR-009 eligibility-check (item (h)) include DNC as one of the six Slice 1 eligibility rules, so a DNC'd item is hard-blocked on any subsequent dial? [Consistency, Spec §FR-009, Spec §FR-019, Spec §FR-024] — FR-009 item (h): "call-window / DNC / attempt eligibility (the six Slice 1 rules)"; FR-019 preserves them.
- [x] CHK063 Is the spec's enumeration of DNC trigger phrases / patterns either provided or unambiguously cross-referenced to the "Slice 1 DNC trigger set" (User Story 5 #3)? [Completeness, Spec §User Story 5 #3] — US5 #3 cross-references "the Slice 1 DNC trigger set" by name (Slice 1 owns the canonical set).

## Recording / Raw Audio Disclosure Gap

- [x] CHK064 Is the decision to defer raw-audio capture to a later slice stated in Assumptions and in the 2026-05-25 Clarifications entry consistently? [Consistency, Spec §Assumptions, Spec §Clarifications] — Clarifications Q2 and Assumptions "Slice scope" both defer raw-audio capture with its own retention/consent/redaction design.
- [x] CHK065 Does the spec name the missing recording-disclosure design as deferred (with its own retention, consent, and redaction design) so a compliance reviewer can audit the deferral? [Clarity, Spec §Assumptions, Spec §Clarifications] — Assumptions: raw-audio "caller-consent surface… deferred to a later slice with its own design."
- [x] CHK066 Does the spec address whether transcript-only retention (no raw audio) still requires a call-recording disclosure to the caller in any jurisdiction (i.e., is "transcript-only" equivalent to "no recording" for disclosure purposes)? [Gap, Spec §Assumptions, Spec §Clarifications] — R5: Assumptions "Telephony-consent regulatory frameworks" now declares two-party call-recording-consent jurisdictions OUT OF SCOPE (Round 3), explicitly deferring the recording-disclosure obligation.

## Jurisdictional / Consent Gaps

- [x] CHK067 Does the spec name two-party-consent / all-party-consent jurisdictions and the corresponding requirements (or explicitly mark this as out of scope / deferred)? [Gap, Spec §FR-015, Spec §Assumptions] — R5: Assumptions "Telephony-consent regulatory frameworks (declared out of scope)" explicitly marks two-party call-recording-consent jurisdictions OUT OF SCOPE (Round 3 decision), a named exclusion not an oversight.
- [x] CHK068 Does the spec inherit or restate Slice 1's call-window / time-of-day eligibility rules so jurisdiction-specific calling-hour limits are preserved (FR-019 "six Slice 1 rules")? [Completeness, Spec §FR-019, Spec §FR-009] — FR-019 preserves the six Slice 1 rules incl. call-window; FR-009 enforces them as hard pre-dial checks.
- [x] CHK069 Does the spec address regulatory frameworks beyond AI disclosure (e.g., TCPA-style prior express consent for autodialed calls, robocall registration, jurisdictional do-not-call registry checks) or mark them as deferred? [Gap, Spec §FR-015, Spec §Assumptions] — R5: Assumptions "Telephony-consent regulatory frameworks" names TCPA prior-express-consent, robocall registration, and external (federal/state) DNC-registry scrubbing as explicit Round 3 OUT-OF-SCOPE exclusions.
- [x] CHK070 Does the spec define how the deployment communicates which jurisdiction's calling-hour and consent rules apply for a given queue item (per-item, per-campaign, or deployment-global)? [Gap, Spec §FR-009, Spec §FR-019, Spec §Assumptions] — R5: jurisdiction-driven consent rules are now declared OUT OF SCOPE (Assumptions, Round 3); the only in-scope rules are the six Slice 1 eligibility rules (FR-019), applied per-queue-item by the eligibility evaluator, so selection scope is defined for what remains.

## Auditability and Reviewer Surface

- [x] CHK071 Does FR-036 require the run report to include enough information (session ID, real provider call ID, persona version, runtime/model identity, final disposition, shadow STT discrepancy summary, callbacks audit row counts, failing readiness check) for a compliance reviewer to reconstruct a session? [Completeness, Spec §FR-036] — FR-036 enumerates all those fields plus operator identity, readiness summary, rejected-auth count.
- [x] CHK072 Is the auditability scope in Constitution Alignment fully covered by FR-016 + FR-036? [Consistency, Spec §Constitution Alignment, Spec §FR-016, Spec §FR-036] — Each Constitution-named element (session ID, eligibility, call ID, persona version, runtime/model identity, timestamps, disposition, correlation IDs) maps to FR-016/FR-036 fields.
- [x] CHK073 Does the spec require the compliance-relevant artifacts (run report, transcript or pointer, shadow STT artifacts, callbacks audit log) to be inspectable without a custom UI per FR-038 / SC-017? [Coverage, Spec §FR-038, Spec §SC-017] — FR-038/SC-017: loop inspectable via CLI/API output + local artifacts + Dynamics records, no custom UI.
- [x] CHK074 Are all compliance-relevant requirements traceable to either a stated regulatory rationale (e.g., AI disclosure, DNC, no-PHI) or explicitly marked as deployment-config (e.g., retention, redaction policy details, jurisdiction)? [Traceability, …] — Disclosure/DNC/no-PHI carry rationale; retention/redaction/timeouts marked deployment-config; jurisdiction frameworks remain the open gaps (CHK053/067/069/070).

## Scenario Classes

### Primary

- [x] CHK075 Does the spec cover the primary compliant connected-call scenario (disclosure delivered → no opt-out → persona continues, FR-015 + User Story 5 #1)? [Coverage, Spec §FR-015, Spec §User Story 5 #1] — US5 #1 + FR-015 cover disclosure-then-continue with implicit acknowledgment.
- [x] CHK076 Does the spec cover the primary opt-in posture scenario (operator supplies real-call flag → readiness gate passes → call placed, User Story 1 #1 + SC-001)? [Coverage, Spec §User Story 1 #1, Spec §SC-001] — US1 #1 + SC-001 cover flag → readiness pass → call placed → write-back.

### Alternate

- [x] CHK077 Does the spec cover the alternate rehearsal-mode posture (default safe mode → no dial, no Dataverse mutation, User Story 2 + SC-002 + SC-011)? [Coverage, Spec §User Story 2, Spec §SC-002, Spec §SC-011] — US2 + SC-002 + SC-011 fully cover rehearsal default with 0 calls / 0 mutations.
- [x] CHK078 Does the spec cover the alternate transcript-retention modes (summary-only and pointer-only) so compliance-relevant artifacts are still produced (Edge Cases "Transcript retention is summary-only or pointer-only")? [Coverage, Spec §FR-033, Spec §Edge Cases] — Edge Case + FR-033: summary-only/pointer-only still produce session-result artifact with summary, mode, persona version.
- [x] CHK079 Does the spec cover the alternate shadow-STT-disabled posture (no discrepancy lane → loop still works, FR-032 + SC-013 + User Story 6 #5)? [Coverage, Spec §FR-032, Spec §SC-013, Spec §User Story 6 #5] — FR-032 + US6 #5: disabled lane still completes loop; run report records disabled.

### Exception / Error

- [x] CHK080 Does the spec cover the mid-call opt-out exception (persona stops, `do_not_call`, DNC field write, no follow-up Task — Edge Cases, User Story 5 #3, SC-006)? [Coverage, …] — Edge Case "Mid-call opt-out / DNC" + US5 #3 + SC-006 + FR-024 DNC-first all cover it.
- [x] CHK081 Does the spec cover the mid-call PHI / out-of-allowed-claim exception (persona escalates with enumerated reason code, conversation ends safely, one review Task — Edge Cases, User Story 5 #2)? [Coverage, Spec §Edge Cases, Spec §User Story 5 #2] — Edge Case "Mid-call PHI / out-of-allowed-claim" + US5 #2 cover escalate + safe-end + one review Task.
- [x] CHK082 Does the spec cover the live-model-attempts-out-of-scope exception (persona overrides the live model with `needs_human_review`, User Story 5 #2 + FR-014)? [Coverage, Spec §FR-014, Spec §User Story 5 #2] — FR-014 persona authority + US5 #2 escalation; pipecat-runtime contract test enforces.
- [x] CHK083 Does the spec cover the callback-authentication-failure exception (rejected, not processed, no secret logged — FR-008)? [Coverage, Spec §FR-008] — FR-008 + rejected-auth-audit-log contract: reject 401, distinct log, no secret/body.
- [x] CHK084 Does the spec cover the no-PHI exception path (caller volunteers PHI → persona refuses → no PHI in transcript artifact, FR-014 + FR-015 + Edge Cases)? [Coverage, Spec §FR-014, Spec §FR-015, Spec §Edge Cases] — FR-015 caller-volunteered-PHI tag-and-redact across four artifact types; Edge Case mirrors.
- [x] CHK085 Does the spec cover the readiness-gate exceptions that have a compliance dimension (unauthorized source caller-ID, malformed destination → potential wrong-number / regulatory violation — User Story 3 #2, #3 + FR-009 + FR-010)? [Coverage, …] — US3 #2/#3 + FR-009/FR-010 cover both as hard pre-dial blocks.

### Recovery

- [x] CHK086 Does the spec cover compliance-safe recovery after a DNC outcome (the queue item's DNC field write + eligibility check prevents further dials, FR-019 + FR-024 + SC-006)? [Coverage, Spec §FR-019, Spec §FR-024, Spec §SC-006] — FR-024 DNC write + FR-019 eligibility check on next attempt + SC-006 prevents further attempts.
- [x] CHK087 Does the spec cover compliance-safe recovery after a partial CRM write-back on a real call (resume only the missing writes, no duplicate DNC field write, FR-022 + User Story 7)? [Coverage, Spec §FR-022, Spec §User Story 7] — FR-022 resume + FR-021 idempotency; FR-024/CHK125 prevent duplicate DNC write on resume.
- [x] CHK088 Does the spec cover compliance-safe recovery on orchestrator restart mid-call (live-call abandonment finalizes as `failed`, no false connected-call activity, no orphaned `in_progress` queue item, FR-026 + Edge Cases)? [Coverage, Spec §FR-026, Spec §Edge Cases] — FR-026 + Edge Case "Live-call abandonment": finalize failed/live_call_abandonment, no false activity, queue leaves in_progress.

### Non-Functional

- [x] CHK089 Is the no-secrets-in-artifacts guarantee testable / verifiable (SC-018 → 0 secrets in any artifact across all run modes)? [Measurability, Spec §FR-035, Spec §SC-018] — SC-018 measurable; contract test_no_secrets_in_artifact_files / test_no_secrets_in_stdout_or_run_report enforce.
- [x] CHK090 Is the retention floor (≥ 90 days) measurable and auditable (e.g., file timestamps, retention metadata recorded)? [Measurability, Spec §FR-022, Spec §Assumptions] — R6: R4-Q46 requires each retained artifact to carry `retention_mode` + `created_at` markers enabling retention auditing — the measurable metadata marker the gap demanded.
- [x] CHK091 Does the spec require the operator identity capture (FR-016) to be lossless across run modes (rehearsal AND real-call) so all run attempts are attributable, not only successful real calls? [Completeness, Spec §FR-016, Spec §FR-036] — FR-016 records operator identity on every Slice 3 session/run report; FR-036 lists it for every invocation (CLI default `$USER`).
- [x] CHK092 Does the spec address how compliance-relevant configuration changes (e.g., changing the disclosure language, changing redaction policy, changing retention) are themselves audited / versioned? [Gap, Spec §FR-015, Spec §FR-033, Spec §FR-016] — R6: R4-Q46 adds a run-report config-identity block recording a version/hash of the redaction, retention, AND disclosure policies (amended §FR-036) so policy changes are themselves auditable.

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

### Q11 PHI Tag-and-Redact (FR-015 / FR-033 amendment) — HIPAA-Adjacent Artifact Guarantee

- [x] CHK093 Does FR-015 define the artifact-level PHI guarantee precisely enough that a compliance reviewer can confirm a caller-volunteered PHI utterance does NOT persist in any retained artifact unredacted (all four artifact types enumerated in FR-015 / FR-033)? [Completeness, Spec §FR-015, §FR-033] (closes CHK019) — FR-015 names full transcript, session-result summary, shadow STT transcript, shadow STT discrepancy records before write.
- [x] CHK094 Is the FR-015 PHI tag-and-redact requirement consistent with the Assumptions "Compliance scope" entry's non-clinical-scope assumption? [Consistency, Spec §FR-015, §Assumptions — Compliance scope] — Belt-and-suspenders artifact redaction reinforces the non-clinical/no-PHI posture; no tension.
- [x] CHK095 Does the spec address whether the FR-015 PHI tag-and-redact guarantee requires any update to the AI-on-behalf-of-Medx disclosure language (e.g., a "we do not collect health information" sentence) or whether the existing Slice 1 disclosure is sufficient? [Gap, Spec §FR-015] — R6: R4-Q45 decides the canonical disclosure already states non-clinical scope; Slice 3 adds NO new disclosure sentence — the `phi_collection_risk` escalation + tag-and-redact is the control.
- [x] CHK096 Is the `phi_collection_risk` escalation reason listed in the Slice 1 enumerated `human_review_reason` set and not introduced as a NEW reason for Slice 3? [Consistency, Spec §FR-014, §FR-015, §CHK014 enumeration] — FR-014/FR-015 forbid live-model expansion; phi_collection_risk is a Slice 1 enumerated reason, not a Slice 3 addition (only shadow_stt_discrepancy is additive).
- [x] CHK097 Does FR-015 define that the PHI-volunteered case MUST be observably distinct from a non-PHI call in the audit artifacts and run report? [Measurability, Spec §FR-015] — FR-015: "PHI-volunteered case MUST be observably distinct from a non-PHI call in the audit artifacts and the run report."
- [x] CHK098 Is the FR-015 tag-and-redact requirement timing-bound to "before any of those artifacts are written to disk" with no escape clause? [Clarity, Spec §FR-015] — FR-015 binds the redaction to "before any of those artifacts are written to disk"; no escape clause.
- [x] CHK099 Does the spec define whether the persona's decision to continue the call after a caller-volunteered-PHI escalation requires any additional disclosure-language reminder? [Gap, Spec §FR-015] — R6: R4-Q45 requires NO post-PHI re-disclosure; the `phi_collection_risk` escalation + tag-and-redact is the control, so a continued call needs no added reminder.
- [x] CHK100 Is the FR-015 tag-and-redact policy explicitly required to cover the run report (FR-036) when the run report quotes or summarizes a PHI-bearing utterance? [Consistency, Gap, Spec §FR-015, §FR-033, §FR-036] — FR-015 redacts the session-result summary (the run-report disposition summary source); FR-035/SC-018 bar secrets; run report carries the redacted summary, not raw utterances.
- [x] CHK101 Does the spec address whether the FR-015 PHI tag-and-redact policy is auditable from local artifacts alone (e.g., a redaction-applied marker)? [Measurability, Spec §FR-015, §FR-036] — FR-015 "observably distinct… in the audit artifacts and run report"; data-model §2.5 ties redaction to the phi_collection_risk escalation event recorded per session.
- [x] CHK102 Is the FR-015 tag-and-redact requirement consistent with FR-034's "discrepancy records retained… even when transcript retention is summary-only" (records survive pruning AND have PHI redacted before write)? [Consistency, Spec §FR-015, §FR-033, §FR-034] — FR-015 redacts discrepancy records; FR-034 retains them under summary-only; both apply (data-model §1.7 fields redacted).

### Q9 Rejected-By-Authentication Audit Log (FR-008 amendment) — Security Event Trail

- [x] CHK103 Does FR-008 define the rejected-by-authentication audit log as a distinct log (separate from the duplicate / out-of-order callbacks audit log)? [Clarity, Spec §FR-008] (closes CHK049) — FR-008: "distinct rejected-by-authentication audit log (separate from the duplicate / out-of-order callbacks audit log)"; data-model §1.4 + contract confirm.
- [x] CHK104 Are the rejected-by-authentication audit log's required fields (`received_at`, source metadata) enumerated as a closed list? [Completeness, Spec §FR-008] — FR-008 + contract: `(received_at, session_id, source_metadata, http_status)` as a closed schema, no secret/body.
- [x] CHK105 Does FR-008 explicitly forbid the rejected-by-authentication audit log from containing the verification secret? [Consistency, Spec §FR-008, §FR-035, §SC-018] — FR-008 "MUST NOT include the verification secret"; data-model §1.4 "MUST NOT contain… the verification secret."
- [x] CHK106 Does FR-008 explicitly forbid the audit log from containing the callback body content (defense in depth), traceable to a stated security rationale? [Clarity, Spec §FR-008] — FR-008: "MUST NOT include the callback body content (defense in depth against reflected-payload leakage)."
- [x] CHK107 Does FR-036 require the run report to surface the rejected-by-authentication callbacks count, distinct from the general callbacks-audit row count? [Completeness, Spec §FR-008, §FR-036] — FR-036 lists `rejected_auth_callbacks_count` separately from callbacks/conflicting audit row counts.
- [x] CHK108 Is the source metadata expectation in FR-008 ("provider-supplied source identifiers or IP-level metadata where available") consistent with what telephony providers actually expose, or an implicit deployment-configurable item? [Ambiguity, Spec §FR-008] — R5: FR-008 (Round 3) now constrains `source_metadata` to an explicit non-caller-controlled allow-list (provider source id + IP/transport only), ≤1 KB / ≤16 keys, so "where available" variance is bounded to a fixed allow-listed shape (closes with CHK136).
- [x] CHK109 Does the spec address the compliance implication of an unknown-or-unsupported signature-verification mechanism (the FR-008 "where supported" caveat) on the rejected-by-authentication audit log? [Gap, Spec §FR-008] (closes CHK047) — FR-008 "where supported" + research §2 HMAC-SHA256 decision: when verification is in force rejections are logged; absent support, no spurious rows.

### Q13 Real-Call Flag on Resume (FR-001 / FR-022 amendment) — Operator Opt-In Trail

- [x] CHK110 Does FR-022 explicitly require every resume re-invocation that performs a Dataverse mutation to supply the real-call / write-enabled flag (no "sticky" promotion)? [Completeness, Spec §FR-001, §FR-022] — FR-022: "Every resume re-invocation that performs a Dataverse mutation MUST supply the flag… no sticky promotion."
- [x] CHK111 Is the "absence of the flag on resume → run as rehearsal / readiness mode (no Dataverse mutation; surface what would have been written)" rule defined in FR-022 with no escape clause? [Clarity, Spec §FR-022] — FR-022 states it verbatim; no escape clause.
- [x] CHK112 Does the spec establish that EVERY Dataverse-mutating action has a recorded operator opt-in event (initial dial AND every resume)? [Completeness, Spec §FR-001, §FR-016, §FR-022, §FR-036] — FR-001/FR-022 require flag on every mutation; FR-016/FR-036 record operator identity (current+original) for each invocation.
- [x] CHK113 Is the real-call / write-enabled flag's behavior on resume traceable across FR-001, FR-016, FR-022, and FR-036 run-report surfacing? [Consistency, Spec §FR-001, §FR-016, §FR-022, §FR-036] — All four cite the no-sticky-flag rule; run report surfaces run_mode + planned writes (cli contract).
- [x] CHK114 Does the spec address whether a rehearsal-mode resume's "surface what would have been written" output must itself be audited (subject to no-secrets guarantee and retention floor)? [Gap, Spec §FR-022, §FR-035] — R6: R4-Q21 makes SC-018's no-secrets gate a class-agnostic sweep over ALL artifact classes (§FR-035) and SC-018 names planned write-back payloads; FR-022 progress rows already in the ≥90-day floor (R4-Q33).
- [x] CHK115 Is the FR-022 resume-without-flag rule consistent with SC-011's "100% of runs that omit the flag run in rehearsal / readiness mode and place 0 calls and create or update 0 records"? [Consistency, Spec §FR-022, §SC-011] — SC-011's "100% of runs that omit the flag" covers resume invocations (a resume is a run); FR-022 makes resume-without-flag a mutation no-op.

### Q12 Resume Operator Identity (FR-016 amendment) — Audit Chain-of-Custody

- [x] CHK116 Does FR-016 preserve the original session's operator identity on the local session record and audit artifacts when a different operator resumes? [Completeness, Spec §FR-016] (closes CHK091 multi-operator) — FR-016: "original session's operator identity MUST be preserved… the original authorizer is not overwritten."
- [x] CHK117 Does FR-016 require the resuming operator's identity to be recorded separately on the run report ("resumed by X, original operator Y")? [Completeness, Spec §FR-016, §FR-036] — FR-016 + FR-036 require both identities on the run report with that phrasing.
- [x] CHK118 Is the resume-operator identity recording requirement local-only (not propagated into Dataverse) consistent with the original-operator local-only policy in FR-016? [Consistency, Spec §FR-016] — FR-016 local-only applies to all operator identities; CHK143/crm contract confirm none in Dataverse.
- [x] CHK119 Does FR-036 explicitly require the run report to identify BOTH the original session's operator identity AND the resuming operator's identity on a resume? [Completeness, Spec §FR-016, §FR-036] — FR-036: "On a resume invocation the run report MUST identify both… (e.g., 'resumed by X, original operator Y')."
- [x] CHK120 Does the spec address what happens when the operator identity is identical for the original and resuming invocations (collapsed form permitted)? [Ambiguity, Spec §FR-016, §FR-036] — R6: R4-Q49 decides a self-resume (chain `current` == `original`) still records each invocation in the chain — NO collapse, NO de-dup — so the audit trail stays complete.
- [x] CHK121 Is the multi-operator resume audit trail sufficient to attribute each Dataverse mutation to a specific operator opt-in event? [Measurability, Spec §FR-016, §FR-022, §FR-036] — Each mutating invocation requires the flag (FR-022) and records operator_identity_current (data-model §2.1) tied to that invocation's writes; CHK144 confirms auditability.

### Q14 DNC-First Write Ordering (FR-024 amendment) — TCPA / State Opt-Out Compliance

- [x] CHK122 Does FR-024 require the DNC / opt-out field write to be attempted FIRST in the write-back sequence on a `do_not_call` outcome? [Completeness, Spec §FR-024] — FR-024: DNC write "MUST be attempted FIRST… before the queue-status update, before the Phone Call activity, before any Task."
- [x] CHK123 Is the DNC-first invariant traceable to a stated compliance rationale (even if a partial failure loses everything BUT the DNC write, the contact is protected)? [Traceability, Spec §FR-024] — FR-024 states that rationale explicitly; crm-writeback-dnc-first contract test_dnc_first_partial_failure_protects_contact verifies.
- [x] CHK124 Does the spec address TCPA / state opt-out laws as the regulatory framework underpinning DNC-first ordering, or is it left implicit? [Gap, Spec §FR-024, §Assumptions] (closes CHK069 partially) — crm-writeback-dnc-first contract names "TCPA / State Opt-Out Compliance"; spec FR-024 carries the protection rationale (framework named at contract level only).
- [x] CHK125 Is the DNC-first ordering compatible with FR-021's idempotency-key stamping (resume does NOT duplicate a succeeded DNC write)? [Consistency, Spec §FR-021, §FR-024] — FR-024: "idempotency-key stamping prevents duplicate DNC writes on resume"; contract test_dnc_first_partial_failure_protects_contact.
- [x] CHK126 Does FR-024 require DNC-first ordering on both end-of-call `do_not_call` AND mid-call opt-out (identical invariant)? [Consistency, Spec §FR-015, §FR-024] — FR-024 text covers "a do_not_call disposition (or mid-call opt-out)"; same ordering invariant.
- [x] CHK127 Is the DNC-first ordering preserved across a resume invocation (resume also attempts DNC first; skips already-succeeded DNC)? [Completeness, Spec §FR-022, §FR-024] — crm contract: resume coordinator re-runs steps DNC-first, pre-query skips a succeeded DNC write.
- [x] CHK128 Does the DNC-first compliance benefit hold under the FR-019 eligibility rule that uses the DNC field on the next attempt (DNC field write is the block-future-dials mechanism)? [Consistency, Spec §FR-019, §FR-024, §SC-006] — FR-024 DNC field write + FR-019 DNC eligibility rule on next attempt = future-dial block; SC-006 quantifies.
- [x] CHK129 Does the spec require the DNC write outcome to be operator-visible in the run report (FR-036) on every `do_not_call` session, distinct from the queue-status update outcome? [Completeness, Spec §FR-024, §FR-036] — FR-036 `per_writeback_operation_status` ordered array reflects DNC-first (queue_status_update.dnc first); cli contract test_dnc_first_reflected.
- [x] CHK130 Is the DNC-first ordering consistent with FR-020's four-operation-count preservation (variant within the existing queue-status update operation, no fifth operation)? [Consistency, Spec §FR-020, §FR-024] — FR-020 + data-model §1.11: DNC is a field-level `queue_status_update.dnc` variant; four-operation count preserved.

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed.

### Constitution Principle V + Round 2 Q11 — No-PHI-in-artifacts traceability through redaction layer

- [x] CHK131 Is the no-PHI-in-artifacts guarantee traceable from the spec through the plan's redaction layer extension and on through data-model §2.5 `RedactionPolicy` covering the four named artifact types? [Traceability, Completeness, …] (re-validates CHK094/CHK102) — Data-model §2.5 + §7 enumerate the four artifact types with the phi_collection_risk pre-write trigger.
- [x] CHK132 Does the data-model §2.5 PHI tag-and-redact pre-write trigger give the redaction layer a deterministic, observable signal so a reviewer can verify every PHI-flagged session was redacted before any write? [Measurability, Compliance, Data-Model §2.5, Spec §FR-015] — §2.5: pre-write step "whenever a session's persona has emitted a phi_collection_risk escalation event" — deterministic + observable.
- [x] CHK133 Is the redaction layer's exclusion of transcript-pointer metadata compatible with the no-PHI guarantee (pointer metadata cannot carry PHI by construction)? [Consistency, Gap, Data-Model §2.5, Spec §FR-015, §FR-033] — §2.5 excludes pointer metadata, session IDs, call IDs, timestamps, structural fields — structural identifiers, not utterance content; cannot carry PHI by construction.
- [x] CHK134 Does the plan / data-model address the compliance posture when the PHI tag-and-redact pre-write step ITSELF fails (fail-closed no-artifact vs fail-open unredacted + alert)? [Gap, Ambiguity, …] — R5: FR-015 + data-model §2.5 "Fail-closed invariant (Round 3)": a redaction-pass failure MUST NOT write unredacted content; session finalizes with `redaction_failed` recorded in the run report (T106).

### rejected_auth_callbacks audit log — TCPA / state-call-recording compliance posture

- [x] CHK135 Does the contracts/rejected-auth-audit-log.md no-secret / no-body schema preserve TCPA / state-call-recording posture (forged callback can never leak audio URLs / recordings / transcripts into the audit log)? [Completeness, Compliance, …] (re-validates CHK094/CHK095) — Contract excludes callback body entirely (defense in depth); only `received_at, session_id, source_metadata, http_status` stored.
- [x] CHK136 Is the `source_metadata` field defined narrowly enough that compliance-sensitive caller identifiers (caller phone, caller email) cannot be silently captured into the audit log? [Gap, Ambiguity, Compliance, Data-Model §1.4, Contract] — R5: FR-008 + data-model §1.4 + rejected-auth contract #2 now restrict `source_metadata` to a non-caller-controlled allow-list (provider source id + IP/transport), ≤1 KB / ≤16 keys; body buffer dropped on failure (T109).
- [x] CHK137 Does the rejected-auth audit log's local-only retention carry the same ≥ 90-day floor as other Slice 3 artifacts, and is this compatible with any TCPA inquiry-response requirement? [Consistency, Gap, Research §10, §14, Data-Model §1.4] — R5: FR-008 now states `artifacts/_unassociated/` "MUST honor the same ≥ 90-day local-artifact retention floor"; data-model §1.4 + research §2 confirm. TCPA inquiry-response is now declared OUT OF SCOPE (Assumptions, Round 3).
- [x] CHK138 Is the rejected_auth audit log's nullable `session_id` compatible with attributing forgery attempts to a specific campaign (is a null session_id operationally acceptable)? [Gap, Compliance, Data-Model §1.4, Contract] — R5: FR-008 now declares null-session rejections acceptable — recorded under `artifacts/_unassociated/` and counted in a deployment-level `rejected_auth_unassociated_count` surfaced by operator tooling so forgeries targeting no known session are still detectable.

### AI-disclosure attestation — deployment-configured real-time provider identity

- [x] CHK139 Is the deployment-configured real-time AI provider's identity recording sufficient for an AI-disclosure audit ("Provider X model Y version Z spoke on session S")? [Measurability, Compliance, Spec §FR-016, Data-Model §1.12, Contract: pipecat-runtime] — §1.12 RealtimeProviderSession records runtime/provider/model name+version per session; pipecat contract test_runtime_identity_recorded.
- [x] CHK140 Does the run-report `runtime_identity` schema preserve the FR-016 fields one-to-one so a downstream consumer reads the same provider/model identity from a JSON file? [Consistency, Traceability, Research §9, Contract: cli-slice3, Quickstart §4, Spec §FR-016] — R5: research §9 now uses `model_name`+`model_version` ("the single canonical shape"), matching FR-036, data-model §1.12, cli contract, and quickstart §4 — schema is one-to-one (Round 3 fix; clarifications Session 2026-06-01).
- [x] CHK141 Is the `RealtimeProviderSession` "MUST NOT contain credentials" invariant preserved by the run-report schema so the attestation artifact is safely shareable? [Compliance, Consistency, Data-Model §1.12, Spec §FR-035, §FR-016] — §1.12 + §7 bar credentials; FR-035/SC-018 + cli test_no_secrets_in_stdout_or_run_report enforce.

### Operator-identity local-only invariant — operator-action-audit-trail compliance

- [x] CHK142 Does the operator-identity local-only invariant satisfy operator-action-audit-trail requirements (reconstruct which operator authorized which mutation from local artifacts alone)? [Completeness, Compliance, Spec §FR-016, Data-Model §2.1] (re-validates CHK117/CHK121) — §2.1 operator_identity_current/_original SQLite columns + run report enable local-only reconstruction.
- [x] CHK143 Does the plan / data-model address whether any compliance need requires operator identity in Dataverse, or is local-only explicitly canonical? [Gap, Ambiguity, Compliance, Spec §FR-016, Data-Model §2.1, §2.3, Contract] — R6: R4-Q47 declares a Dynamics-side "who authorized" field OUT OF SCOPE (§Assumptions "Operator-surface scope exclusions"); local-only is now the explicit canonical decision, not an assumption.
- [x] CHK144 Is the resume-operator local-only posture auditable across a multi-operator resume chain without Dynamics-side data? [Measurability, Compliance, Spec §FR-016, Data-Model §2.1] — §2.1 columns + run report `operator_identity {current, original}` give the chain locally; cli test_resume_preserves_original_operator.

### AI-on-behalf-of-Medx disclosure — single canonical text source per Constitution III

- [x] CHK145 Is the AI-on-behalf-of-Medx disclosure traceable to a single canonical text source in the persona module per Constitution Principle III (plan names the file)? [Traceability, Compliance, Spec §FR-015, Plan §Project Structure, Plan §Constitution Check III] — Plan locates disclosure in `persona/alf_appointment_setter.py`; one persona module owns it.
- [x] CHK146 Does the plan / data-model define how persona version ties to the canonical disclosure text (reviewer reads `persona_version` from run report and reconstructs exact disclosure)? [Measurability, Compliance, Spec §FR-015, §FR-016, Data-Model §2.1, Quickstart §4] — persona_version recorded per §2.1 + run report; versioned persona module is the canonical text source.
- [x] CHK147 Is the Pipecat runtime's "live model MUST NOT mutate disposition rules or the reason set" boundary sufficient to guarantee the disclosure text cannot be paraphrased / altered by the live model? [Completeness, Compliance, Plan §Constitution Check III, Contract: pipecat-runtime, Spec §FR-014, §FR-015] — pipecat contract behavior #1 + test_first_utterance_includes_disclosure: persona owns/emits the canonical disclosure; live model cannot alter it.
- [x] CHK148 Does the plan / data-model address whether a shadow STT discrepancy event can be triggered when the live model's spoken disclosure diverges from the persona's canonical disclosure text ("disclosure_text_drift")? [Gap, Ambiguity, Spec §FR-015, Data-Model §1.7, Contract: shadow-stt-lane] — R6: R4-Q45 declares shadow-lane disclosure-text-drift detection explicitly OUT OF SCOPE (§Assumptions "Operator-surface scope exclusions"); no longer an implicit omission.

### Cross-cutting compliance — Round 3 closes Round 2 follow-ups

- [x] CHK149 Does data-model §7 invariants list "no PHI in artifacts (caller-volunteered path)" with a stated enforcement mechanism traceable across all four §2.5 artifact types? [Consistency, Compliance, Data-Model §2.5, §7, Spec §FR-015, §FR-033] — §7 invariant cites the pre-write tag-and-redact on transcript/summary/shadow transcript/shadow discrepancy records on phi_collection_risk.
- [x] CHK150 Is the no-PHI guarantee enforced uniformly across the live path AND a session resumed by a different operator (PHI redaction does not depend on operator-identity continuity)? [Consistency, Compliance, Spec §FR-015, §FR-016, Data-Model §2.1, §2.5] — §2.5 trigger keys on the persona's phi_collection_risk event, independent of operator identity; redaction runs before any artifact write regardless of who resumes.

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate the requirement exists but is interpretable in multiple non-trivially-different ways.
- Items marked [Conflict] indicate two parts of the spec disagree on the same requirement.
- CHK093 – CHK130 are Round 2 amendments (2026-05-25) covering: Q11 PHI tag-and-redact artifact guarantee, Q9 rejected-by-authentication audit log, Q13 real-call flag on resume, Q12 multi-operator resume identity, Q14 DNC-first write ordering.
- CHK131 – CHK150 are Round 3 post-plan validation (2026-05-25) covering: no-PHI-in-artifacts traceability through `redaction/layer.py`, rejected_auth audit log TCPA / state-call-recording posture, AI-disclosure attestation via deployment-configured provider identity, operator-identity local-only operator-action-audit-trail sufficiency, AI-on-behalf-of-Medx disclosure single canonical text source.
- >=80% of items reference a spec section (FR-NNN, SC-NNN, Definitions, Edge Cases, User Story N, Assumptions, Clarifications, Constitution Alignment, or Key Entities) for traceability.

## Round 4 — Reverify (deep & wide) (2026-06-01)
**Reverified against**: current spec.md / plan.md / tasks.md / data-model.md / contracts.
- Items verified satisfied: 129
- Items still open: 21
- Top open gaps:
  - CHK053 / CHK067 / CHK069 / CHK070 — jurisdictional/consent regulatory frameworks (STIR-SHAKEN, two-party consent, TCPA prior-express-consent, robocall registration, jurisdiction-selection scope) not named or marked deferred.
  - CHK009 / CHK010 — "brief pause" unquantified and implicit-acknowledgment policy has no deployment-override path for stricter jurisdictions.
  - CHK134 — redaction-pass-failure posture (fail-closed vs fail-open) unspecified in plan/data-model.
  - CHK136 / CHK138 — rejected_auth `source_metadata` not allow-listed (could capture caller PII); nullable `session_id` campaign-untraceability not declared acceptable.
  - CHK137 — rejected_auth log not explicitly named in the ≥90-day retention floor list; TCPA inquiry-response window unaddressed.
  - CHK140 — run-report `runtime_identity` schema (research §9 single `model`) not one-to-one with data-model §1.12 / cli contract (`model_name`+`model_version`).
  - CHK090 / CHK092 — no measurable retention-metadata marker on artifacts; compliance-config changes (redaction/retention) not versioned/audited.
  - CHK095 / CHK099 / CHK148 — disclosure-text decisions (no-health-info sentence, post-PHI continue reminder, disclosure-drift detection) left implicit.
  - CHK026 / CHK051 / CHK108 / CHK114 / CHK120 / CHK143 / CHK034 / CHK035 / CHK066 — residual ambiguity/gap items (operator-identity strength, "authorized" semantics, source-metadata provider variance, rehearsal-resume output auditing, identical-operator collapse, Dynamics-side audit need, redacted/unredacted retention scope, no-auto-delete vs pointer-only, transcript-only recording-disclosure).

## Round 5 — Alignment Verification (deepest & widest) (2026-06-01)
**Reverified against**: Round 3-amended spec + Round 4 tasks (T102–T109) + data-model/research/quickstart/contracts.
- Items closed this round: 13
- Items still open: 12
- Aligned: yes — the nine Round 3 themes (run-report `model_name`+`model_version`; rejected-auth `source_metadata` allow-list ≤1KB/≤16 keys + body-drop + `_unassociated/` ≥90-day floor + `rejected_auth_unassociated_count`; shadow `lane_failed` vs `lane_truncated`; surfaced `grace_window_sec` + force-0; PHI `[PHI-REDACTED]` + fail-closed `redaction_failed`; `do_not_call` > `phi_collection_risk` > `shadow_stt_discrepancy` precedence; config precedence CLI>env>TOML; resume `skipped (resume)` + operator `chain`; telephony-consent frameworks declared OUT OF SCOPE) are each verified present in the spec, data-model, research, tasks (T102–T109), and contracts. No regressions found on previously-`[x]` items.
  - Closed this round (13): CHK010, CHK034, CHK053, CHK066, CHK067, CHK069, CHK070, CHK108, CHK134, CHK136, CHK137, CHK138, CHK140.
  - Top still-open (12) — genuine residual gaps NOT addressed by the Round 3/4 amendments:
    - CHK009 — "brief pause" still qualitative; no quantified/configured value.
    - CHK026 — operator-identity strength (OS-user/CLI string) not justified vs authenticated identity.
    - CHK035 — no-auto-delete vs pointer-only minimal-artifact interaction unaddressed.
    - CHK051 — FR-009 "authorized for outbound dialing" semantics (provider-side vs local allowlist) still undefined.
    - CHK090 — no measurable retention-metadata/timestamp marker required on artifacts.
    - CHK092 — compliance-config changes (redaction/retention policy) not versioned/audited.
    - CHK095 — disclosure text: no decision on a no-health-information sentence.
    - CHK099 — post-PHI-escalation continued-call additional-disclosure reminder undecided.
    - CHK114 — rehearsal-resume "would-have-written" output not bound to FR-035 / retention floor.
    - CHK120 — identical original/current operator collapse / chain de-dup unstated.
    - CHK143 — Dynamics-side "who authorized" audit need never analyzed; local-only canonicality assumed.
    - CHK148 — disclosure-text-drift not a shadow high-value field; paraphrased disclosure unflagged.

## Round 6 — Final Alignment (post Round-4 amendment) (2026-06-01)
- Items closed this round: 12
- Items still open: 0
- Aligned: yes — Residual open: none

## Round 7 — Net-New Gap Scan (post US1–US4 / R4 amendments) (2026-06-02)

Gap-scan of compliance surface introduced by the Round 4 spec amendments (R4-Q17, R4-Q20, R4-Q23, R4-Q29, R4-Q33, R4-Q40) for requirement-quality gaps not covered by any existing CHK item.

### R4-Q17 — Exception-text / stack-trace redaction (FR-035 extension)

- [x] CHK151 Does FR-035 define the redaction-before-write guarantee for exception messages and stack traces precisely enough that a compliance reviewer can confirm error text cannot leak a secret OR a caller-volunteered PHI span to stderr, the run report, or logs? The existing items (CHK038/CHK039/CHK089) enumerate the four credential classes and SC-018's 0-secrets sweep but none addresses the R4-Q17 global-exception-handler redaction path, nor whether that path applies the PHI `[PHI-REDACTED]` policy in addition to the secret `[REDACTED]` policy. [Completeness, Gap, Spec §FR-035 (R4-Q17), §FR-015] — Gap. → CLOSED R7-fix (2026-06-02): spec.md FR-035 — global exception handler's redaction pass MUST apply BOTH `[REDACTED]` (secret) AND `[PHI-REDACTED]` (PHI) to exception messages/stack traces before log/stderr/run-report write.

### R4-Q20 — Secret provenance (environment-only load)

- [x] CHK152 Is the FR-035 "every secret MUST be loaded from the environment ONLY, at module init; loading a secret from disk or from CLI argv is forbidden" requirement testable/measurable as a compliance control (e.g., a stated check that no secret-bearing config key is read from a file path or argv), or is it asserted without a verification surface? No existing item (CHK038–CHK040, CHK089) covers secret provenance / load-path restriction — they cover only secret presence in output artifacts. [Measurability, Gap, Spec §FR-035 (R4-Q20)] — Gap. → CLOSED R7-fix (2026-06-02): spec.md FR-035 — env-only load-path is a testable compliance control; a verification check MUST confirm no secret-bearing config key resolves from a file path, TOML, or argv.

### R4-Q29 — raw_callback_body redaction coverage

- [x] CHK153 Does the FR-033 default-on redaction coverage set explicitly include `CallbacksAuditLog.raw_callback_body` (which may echo caller-spoken / PHI-bearing content) with the same before-write timing as the transcript artifacts? Existing items CHK036/CHK037/CHK043 and CHK093/CHK102 enumerate the four transcript-class artifacts but none names the callbacks-audit raw body, so the requirement that this stored provider payload is redacted is not validated for completeness or for write-timing. [Completeness, Gap, Spec §FR-033 (R4-Q29), Data-Model §1.3/§2.5] — Gap. → CLOSED R7-fix (2026-06-02): spec.md FR-033 — `CallbacksAuditLog.raw_callback_body` added to the default-on redaction set, passed through the same pass with the same before-write timing (redacted before the audit row is written).

### R4-Q33 — Audit floor cannot be lowered by deployment config

- [x] CHK154 Does the spec state, as an auditable invariant, that deployment configuration MAY set a LONGER retention but MUST NOT lower the ≥ 90-day audit retention floor for audit artifacts (the R4-Q33 "config cannot lower the audit floor" clause)? Existing items CHK030–CHK035 / CHK137 establish the floor's scope (pointer records, `_unassociated/`) but none validates the floor-vs-config precedence rule that prevents a misconfiguration from silently shortening audit retention. [Completeness, Gap, Spec §Assumptions "Audit retention floor is a floor" (R4-Q33), §FR-022] — Gap. → CLOSED R7-fix (2026-06-02): spec.md SC-022 — "0 deployment configurations can lower an audit artifact's effective retention below the 90-day floor ... the floor wins" as a measurable auditable invariant.

### R4-Q40 — Positive redaction-applied indicator + static no-PHI reminder

- [x] CHK155 Does FR-036 require the run/readiness report to carry a positive `redaction_applied: true|false` indicator AND a static no-PHI / no-clinical operator reminder line, distinct from the §2.5 PHI-escalation-keyed detectability covered by CHK101? CHK101/CHK097 establish that a PHI-volunteered case is "observably distinct," but neither validates the always-present boolean indicator (which must read `true` even on a non-PHI redacted call) nor the static reminder-line requirement, so the R4-Q40 operator-facing attestation surface is unvalidated. [Completeness, Measurability, Spec §FR-036 (R4-Q40)] — Gap. → CLOSED R7-fix (2026-06-02): spec.md FR-036 — positive `redaction_applied: true|false` that MUST read `true` even on a non-PHI call when the pass ran, plus an always-present static no-PHI / no-clinical operator reminder line.

### R4-Q23 — Fail-closed when callback signature verification unavailable

- [x] CHK156 Does the spec validate the R4-Q23 fail-closed decision — that a deployment which cannot supply callback signature verification MUST refuse to start in real-call mode with a named readiness failure (no unauthenticated-callback fallback) — as a distinct compliance requirement? Existing items CHK047/CHK109 close the FR-008 "where supported" caveat via the HMAC research decision and "no spurious rows," but neither validates the readiness-gate refuse-to-start consequence now in FR-008/FR-009 (R4-Q23), so the strongest authentication-posture guarantee lacks a requirement-quality check. [Completeness, Consistency, Spec §FR-008 (R4-Q23), §FR-009] — Gap. → CLOSED R7-fix (2026-06-02): spec.md FR-008 — unverifiable-signature deployment MUST refuse to start in real-call mode via the named `signing_secret_verifiable` readiness failure (FR-009), "a distinct compliance requirement," no unauthenticated fallback.
