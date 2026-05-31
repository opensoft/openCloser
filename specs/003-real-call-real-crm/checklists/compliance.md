# Compliance Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the regulatory and compliance dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Regulatory Grounding — AI-on-Behalf-of-Medx Disclosure

- [ ] CHK001 Is the AI-on-behalf-of-Medx disclosure required on every connected real call in FR-015 with no exception clause that could omit it? [Completeness, Spec §FR-015]
- [ ] CHK002 Is the disclosure-on-first-utterance requirement stated identically in FR-015, Constitution Alignment ("Safety and human handoff"), and User Story 5 #1? [Consistency, Spec §FR-015, Spec §Constitution Alignment, Spec §User Story 5 #1]
- [ ] CHK003 Does FR-015 explicitly carry forward the Slice 1 disclosure language (so a compliance reviewer can locate the canonical script and version it)? [Traceability, Spec §FR-015]
- [ ] CHK004 Does the spec require that the disclosure language is owned by the persona module (not by the live model), per FR-014, so model variation cannot weaken the disclosure? [Consistency, Spec §FR-014, Spec §FR-015]
- [ ] CHK005 Is FR-016's recording of the persona version + runtime/model identity sufficient to reconstruct which disclosure language version was used on a given call? [Measurability, Spec §FR-016]

## Post-Clarification Disclosure-Acknowledgment Policy

- [ ] CHK006 Is the "no explicit verbal acknowledgment required" policy stated in FR-015 in a way a compliance reviewer can audit (i.e., the rule is in the binding requirements section, not only in the Clarifications log)? [Completeness, Spec §FR-015, Spec §Clarifications]
- [ ] CHK007 Is the "absence of opt-out → implicit acknowledgment" rule defined identically in FR-015 and in the 2026-05-25 Clarifications entry? [Consistency, Spec §FR-015, Spec §Clarifications]
- [ ] CHK008 Does FR-015 explicitly state that no new `human_review_reason` is introduced for a missing acknowledgment (so the enumerated reason set in Slice 1 + the additive `shadow_stt_discrepancy` is the complete set)? [Completeness, Spec §FR-015, Spec §FR-031]
- [ ] CHK009 Does the spec define what "brief pause" means (qualitative phrasing only vs. a quantified or deployment-configured value) so the implementation can be verified? [Ambiguity, Spec §FR-015]
- [ ] CHK010 Does the spec address whether the implicit-acknowledgment policy may be overridden by deployment configuration (e.g., a jurisdiction requiring explicit acknowledgment), or whether the policy is fixed? [Gap, Spec §FR-015, Spec §Assumptions]
- [ ] CHK011 Is the policy auditable from local artifacts alone (run report, transcript, session result) without needing to inspect application source? [Measurability, Spec §FR-015, Spec §FR-036]

## Non-Clinical Scope

- [ ] CHK012 Is the non-clinical scope stated in Constitution Alignment, FR-014, FR-015, and the Assumptions "Compliance scope" entry with consistent meaning? [Consistency, Spec §Constitution Alignment, Spec §FR-014, Spec §FR-015, Spec §Assumptions]
- [ ] CHK013 Does the Assumptions section explicitly name Slice 3 as "explicitly not a HIPAA-class patient-care or clinical workflow"? [Clarity, Spec §Assumptions — "Compliance scope"]
- [ ] CHK014 Does the spec enumerate the escalation reason codes (`outside_allowed_claims`, `non_clinical_topic_escalation`, `phi_collection_risk`) that fire on out-of-scope attempts (FR-015, User Story 5 #2)? [Completeness, Spec §FR-015, Spec §User Story 5 #2]
- [ ] CHK015 Does the spec require that the persona's allowed-claim limits (no specific cost figures, no clinical recommendations, no competitor comparisons, no PHI questions) are enumerated or unambiguously cross-referenced to Slice 1? [Completeness, Spec §FR-014, Spec §FR-015, Spec §User Story 5 #2]
- [ ] CHK016 Is the non-clinical-scope boundary the persona module's authority (FR-014), so a live model attempting to cross it triggers the persona's escalation rather than executing the request? [Consistency, Spec §FR-014, Spec §FR-015, Spec §User Story 5 #2]

## No-PHI Guarantee

- [ ] CHK017 Is the "no PHI / no patient or resident health information" guarantee stated in both the persona policy (FR-014, FR-015) and the audit/artifact policy (Constitution Alignment, Assumptions "Compliance scope")? [Consistency, Spec §FR-014, Spec §FR-015, Spec §Constitution Alignment, Spec §Assumptions]
- [ ] CHK018 Does the spec require the persona to refuse PHI collection (FR-015) and the persona to escalate with `phi_collection_risk` when the live model or the contact attempts PHI (User Story 5 #2, Edge Cases "Mid-call PHI / out-of-allowed-claim attempt")? [Consistency, Spec §FR-015, Spec §User Story 5 #2, Spec §Edge Cases]
- [ ] CHK019 Is the no-PHI requirement enforced in artifacts as well as on-call (i.e., redaction or other measure prevents PHI from being captured in transcripts even if uttered)? [Gap, Spec §FR-014, Spec §FR-015, Spec §FR-033]
- [ ] CHK020 Does the spec define which fields the persona-extracted output schema permits (so a compliance reviewer can verify the extraction surface contains no PHI-class fields)? [Completeness, Spec §FR-014, Spec §FR-017]
- [ ] CHK021 Does the persona's enumerated extraction schema (high-value fields per the "High-value field" definition: opt-out/DNC, wrong number, captured email, callback intent, person reached name/role, interest level, final disposition) align with the no-PHI guarantee (no health/clinical fields)? [Consistency, Spec §Definitions, Spec §FR-014]

## Operator-Opt-In Posture (Real-Call / Write-Enabled Flag)

- [ ] CHK022 Is the real-call / write-enabled flag defined as an explicit operator opt-in in FR-001 (no implicit / configuration-only enabling path)? [Clarity, Spec §FR-001]
- [ ] CHK023 Is the rehearsal-mode default consistent across FR-001, FR-002, FR-037, the "Real-call / write-enabled mode" definition, the "Rehearsal / readiness mode" definition, User Story 2 #5, User Story 3 #6, and Assumptions "Default safe mode"? [Consistency, Spec §FR-001, Spec §FR-002, Spec §FR-037, Spec §Definitions, Spec §User Story 2 #5, Spec §User Story 3 #6, Spec §Assumptions]
- [ ] CHK024 Does SC-011 quantify the opt-in posture as 100% of flag-omitted runs placing 0 calls and creating/updating 0 records? [Measurability, Spec §SC-011]
- [ ] CHK025 Does FR-016 require the invoking operator identity to be recorded on every Slice 3 session and the run report so opt-in is attributable? [Completeness, Spec §FR-016]
- [ ] CHK026 Is the "OS user or CLI-provided operator identifier" minimum for operator identity sufficient for compliance attribution, or is a stronger identity (authenticated user) required? [Ambiguity, Spec §FR-016]
- [ ] CHK027 Is the operator identity recorded locally only (per the 2026-05-25 Clarifications decision) and explicitly NOT propagated into Dataverse (FR-016)? [Consistency, Spec §FR-016, Spec §Clarifications]
- [ ] CHK028 Does FR-016 explicitly state that no new Phone Call activity / queue / Task field is added for operator identity, so the Slice 2 Dataverse mapping surface is preserved? [Completeness, Spec §FR-016]
- [ ] CHK029 Is FR-036's run-report requirement to include the invoking operator identity consistent with FR-016's recording requirement? [Consistency, Spec §FR-016, Spec §FR-036]

## Retention Floor and No-Auto-Delete

- [ ] CHK030 Is the retention floor of ≥ 90 days stated in FR-022 and Assumptions "Local artifact retention"? [Consistency, Spec §FR-022, Spec §Assumptions]
- [ ] CHK031 Is the no-auto-delete posture ("Pruning is a manual operator action; the application MUST NOT auto-delete audit artifacts") explicit in Assumptions "Local artifact retention"? [Clarity, Spec §Assumptions]
- [ ] CHK032 Does the spec require the retention floor to cover ALL Slice 3 audit artifacts (callbacks audit log, shadow STT artifacts, CRM correlation / write-back progress rows, run reports) — not only the Slice 2 inherited set? [Completeness, Spec §FR-022, Spec §Assumptions, Spec §FR-034]
- [ ] CHK033 Does FR-034 require shadow STT discrepancy records to be retained as audit/review evidence even when transcript retention is summary-only (i.e., discrepancy records survive transcript pruning)? [Completeness, Spec §FR-034]
- [ ] CHK034 Does the spec define whether the retention floor applies to redacted or unredacted transcript variants (or both) so retention behavior under default-on redaction is unambiguous? [Ambiguity, Spec §FR-022, Spec §FR-033]
- [ ] CHK035 Does the spec address how the no-auto-delete posture interacts with the pointer-only retention mode (where artifacts are minimal by design)? [Gap, Spec §FR-033, Spec §Assumptions]

## Redaction and Secret Exclusion

- [ ] CHK036 Is default-on transcript redaction stated in FR-033 with no opt-out exception for any Slice 3 path? [Clarity, Spec §FR-033]
- [ ] CHK037 Does FR-033 require redaction to run "before any transcript artifact is written to disk" (so redaction cannot be retroactively skipped)? [Clarity, Spec §FR-033]
- [ ] CHK038 Is the no-secrets-in-artifacts guarantee enumerated for SignalWire credentials, real-time AI provider credentials, shadow STT provider credentials, and Dataverse credentials in FR-035? [Completeness, Spec §FR-035]
- [ ] CHK039 Is SC-018 the measurable form of FR-035 (0 secrets in logs, exported artifacts, run report, planned/actual write-back payloads)? [Measurability, Spec §SC-018]
- [ ] CHK040 Does FR-008 forbid logging of secrets associated with the callback signature-verification mechanism (separate from the general FR-035 / SC-018 guarantee)? [Consistency, Spec §FR-008, Spec §FR-035]
- [ ] CHK041 Does FR-034 require shadow STT transcript artifacts to honor the same retention policy as the live transcript (so a leaked shadow transcript cannot bypass redaction)? [Consistency, Spec §FR-033, Spec §FR-034]
- [ ] CHK042 Does the Edge Case "Default-on redaction applied to a Slice 3 transcript" align with FR-033 (redaction runs before any transcript artifact is written)? [Consistency, Spec §Edge Cases, Spec §FR-033]
- [ ] CHK043 Does the spec define what classes of content the default-on redaction MUST cover (PII, secrets, credentials, etc.) or is the redaction policy entirely deployment-configurable? [Ambiguity, Spec §FR-033, Spec §Assumptions]
- [ ] CHK044 Is the redaction requirement also enforced for the run report (FR-036) and not only transcripts? [Gap, Spec §FR-033, Spec §FR-035, Spec §FR-036]

## Callback Signature Verification

- [ ] CHK045 Does FR-008 require SignalWire callback authentication "using the provider's documented mechanism where supported (e.g., signature verification)"? [Completeness, Spec §FR-008]
- [ ] CHK046 Does FR-008 explicitly require rejection of callbacks that fail authentication (not merely logging the failure)? [Clarity, Spec §FR-008]
- [ ] CHK047 Does the spec define the behavior when SignalWire does not support a verification mechanism in a given deployment (the "where supported" caveat)? [Ambiguity, Spec §FR-008]
- [ ] CHK048 Does FR-008 explicitly forbid logging of the verification mechanism's secrets (consistent with FR-035 / SC-018)? [Consistency, Spec §FR-008, Spec §FR-035, Spec §SC-018]
- [ ] CHK049 Is the relationship between rejected-callback events and the callbacks audit log defined (does a rejected callback still create an audit row, and if so does it leak any payload)? [Gap, Spec §FR-007, Spec §FR-008]

## Telephony Authorization (Source Caller-ID)

- [ ] CHK050 Does FR-009 require the configured source caller-ID number to be "authorized for outbound dialing" as a hard pre-dial check (so spoofed or unauthorized origination cannot occur)? [Completeness, Spec §FR-009]
- [ ] CHK051 Is the "authorized for outbound dialing" semantics defined (provider-side authorization, local allowlist, or both)? [Ambiguity, Spec §FR-009]
- [ ] CHK052 Is the source-caller-ID authorization check consistent with User Story 3 #2 (the "missing or not authorized" failure path)? [Consistency, Spec §FR-009, Spec §User Story 3 #2]
- [ ] CHK053 Does the spec address the regulatory implication of source-caller-ID authorization (e.g., FCC / STIR/SHAKEN requirements, jurisdictional caller-ID rules)? [Gap, Spec §FR-009, Spec §Assumptions]

## Real-Dial Phone-Number Validation as a Regulatory Pre-Dial Block

- [ ] CHK054 Does FR-010 establish phone-number validation as a hard pre-dial block (not a warning), so a malformed destination cannot dial an unintended number? [Clarity, Spec §FR-010, Spec §Assumptions]
- [ ] CHK055 Does the spec explicitly state that the prior Slice 2 data-quality warning is promoted to a Slice 3 hard block (FR-010, Edge Cases "Real-dial phone-number validation failure", Assumptions "Hard E.164 validation")? [Consistency, Spec §FR-010, Spec §Edge Cases, Spec §Assumptions]
- [ ] CHK056 Is SC-009 the measurable form of FR-010 (100% blocked, 0 attempts consumed, 0 Phone Call activities)? [Measurability, Spec §SC-009]

## DNC / Opt-Out Honoring

- [ ] CHK057 Does FR-024 require the `do_not_call` disposition (or mid-call opt-out) to update Dataverse DNC / opt-out and queue-status fields AND create no callback or review Task? [Completeness, Spec §FR-024]
- [ ] CHK058 Is the DNC behavior consistent across FR-024, User Story 1 #4, User Story 5 #3, Edge Cases "Mid-call opt-out / DNC", and SC-006? [Consistency, Spec §FR-024, Spec §User Story 1 #4, Spec §User Story 5 #3, Spec §Edge Cases, Spec §SC-006]
- [ ] CHK059 Does FR-015 / User Story 5 #3 require the persona to stop the sales flow before any further sales utterance on opt-out (the "immediate stop" requirement)? [Completeness, Spec §FR-015, Spec §User Story 5 #3]
- [ ] CHK060 Does the spec require persona authority over the DNC trigger set (so the live model cannot suppress an opt-out signal), traceable to FR-014's persona authority over disposition rules? [Consistency, Spec §FR-014, Spec §FR-015, Spec §User Story 5 #3]
- [ ] CHK061 Does SC-006 quantify that a `do_not_call` outcome "prevents further automated attempts" — and is the mechanism by which this is enforced (DNC field write + eligibility check on next attempt) traceable to FR-019's eligibility-preserved behavior? [Measurability, Spec §FR-019, Spec §FR-024, Spec §SC-006]
- [ ] CHK062 Does the FR-009 eligibility-check (item (h)) include DNC as one of the six Slice 1 eligibility rules, so a DNC'd item is hard-blocked on any subsequent dial? [Consistency, Spec §FR-009, Spec §FR-019, Spec §FR-024]
- [ ] CHK063 Is the spec's enumeration of DNC trigger phrases / patterns either provided or unambiguously cross-referenced to the "Slice 1 DNC trigger set" (User Story 5 #3)? [Completeness, Spec §User Story 5 #3]

## Recording / Raw Audio Disclosure Gap

- [ ] CHK064 Is the decision to defer raw-audio capture to a later slice stated in Assumptions and in the 2026-05-25 Clarifications entry consistently? [Consistency, Spec §Assumptions, Spec §Clarifications]
- [ ] CHK065 Does the spec name the missing recording-disclosure design as deferred (with its own retention, consent, and redaction design) so a compliance reviewer can audit the deferral? [Clarity, Spec §Assumptions, Spec §Clarifications]
- [ ] CHK066 Does the spec address whether transcript-only retention (no raw audio) still requires a call-recording disclosure to the caller in any jurisdiction (i.e., is "transcript-only" equivalent to "no recording" for disclosure purposes)? [Gap, Spec §Assumptions, Spec §Clarifications]

## Jurisdictional / Consent Gaps

- [ ] CHK067 Does the spec name two-party-consent / all-party-consent jurisdictions and the corresponding requirements (or explicitly mark this as out of scope / deferred)? [Gap, Spec §FR-015, Spec §Assumptions]
- [ ] CHK068 Does the spec inherit or restate Slice 1's call-window / time-of-day eligibility rules so jurisdiction-specific calling-hour limits are preserved (FR-019 "six Slice 1 rules")? [Completeness, Spec §FR-019, Spec §FR-009]
- [ ] CHK069 Does the spec address regulatory frameworks beyond AI disclosure (e.g., TCPA-style prior express consent for autodialed calls, robocall registration, jurisdictional do-not-call registry checks) or mark them as deferred? [Gap, Spec §FR-015, Spec §Assumptions]
- [ ] CHK070 Does the spec define how the deployment communicates which jurisdiction's calling-hour and consent rules apply for a given queue item (per-item, per-campaign, or deployment-global)? [Gap, Spec §FR-009, Spec §FR-019, Spec §Assumptions]

## Auditability and Reviewer Surface

- [ ] CHK071 Does FR-036 require the run report to include enough information (session ID, real provider call ID, persona version, runtime/model identity, final disposition, shadow STT discrepancy summary, callbacks audit row counts, failing readiness check) for a compliance reviewer to reconstruct a session? [Completeness, Spec §FR-036]
- [ ] CHK072 Is the auditability scope ("traceable session ID, eligibility decision, real provider call ID, persona version, runtime/model identity, started/ended timestamps, final disposition, CRM correlation identifiers") in Constitution Alignment fully covered by FR-016 + FR-036? [Consistency, Spec §Constitution Alignment, Spec §FR-016, Spec §FR-036]
- [ ] CHK073 Does the spec require the compliance-relevant artifacts (run report, transcript or pointer, shadow STT artifacts, callbacks audit log) to be inspectable without a custom UI per FR-038 / SC-017? [Coverage, Spec §FR-038, Spec §SC-017]
- [ ] CHK074 Are all compliance-relevant requirements traceable to either a stated regulatory rationale (e.g., AI disclosure, DNC, no-PHI) or explicitly marked as deployment-config (e.g., retention, redaction policy details, jurisdiction)? [Traceability, Spec §FR-015, Spec §FR-024, Spec §FR-033, Spec §Assumptions]

## Scenario Classes

### Primary

- [ ] CHK075 Does the spec cover the primary compliant connected-call scenario (disclosure delivered → no opt-out → persona continues, FR-015 + User Story 5 #1)? [Coverage, Spec §FR-015, Spec §User Story 5 #1]
- [ ] CHK076 Does the spec cover the primary opt-in posture scenario (operator supplies real-call flag → readiness gate passes → call placed, User Story 1 #1 + SC-001)? [Coverage, Spec §User Story 1 #1, Spec §SC-001]

### Alternate

- [ ] CHK077 Does the spec cover the alternate rehearsal-mode posture (default safe mode → no dial, no Dataverse mutation, User Story 2 + SC-002 + SC-011)? [Coverage, Spec §User Story 2, Spec §SC-002, Spec §SC-011]
- [ ] CHK078 Does the spec cover the alternate transcript-retention modes (summary-only and pointer-only) so compliance-relevant artifacts are still produced (Edge Cases "Transcript retention is summary-only or pointer-only")? [Coverage, Spec §FR-033, Spec §Edge Cases]
- [ ] CHK079 Does the spec cover the alternate shadow-STT-disabled posture (no discrepancy lane → loop still works, FR-032 + SC-013 + User Story 6 #5)? [Coverage, Spec §FR-032, Spec §SC-013, Spec §User Story 6 #5]

### Exception / Error

- [ ] CHK080 Does the spec cover the mid-call opt-out exception (persona stops, `do_not_call`, DNC field write, no follow-up Task — Edge Cases "Mid-call opt-out / DNC", User Story 5 #3, SC-006)? [Coverage, Spec §Edge Cases, Spec §User Story 5 #3, Spec §SC-006]
- [ ] CHK081 Does the spec cover the mid-call PHI / out-of-allowed-claim exception (persona escalates with enumerated reason code, conversation ends safely, one review Task — Edge Cases "Mid-call PHI / out-of-allowed-claim attempt", User Story 5 #2)? [Coverage, Spec §Edge Cases, Spec §User Story 5 #2]
- [ ] CHK082 Does the spec cover the live-model-attempts-out-of-scope exception (persona overrides the live model with `needs_human_review`, User Story 5 #2 + FR-014)? [Coverage, Spec §FR-014, Spec §User Story 5 #2]
- [ ] CHK083 Does the spec cover the callback-authentication-failure exception (rejected, not processed, no secret logged — FR-008)? [Coverage, Spec §FR-008]
- [ ] CHK084 Does the spec cover the no-PHI exception path (caller volunteers PHI → persona refuses → no PHI in transcript artifact, FR-014 + FR-015 + Edge Cases)? [Coverage, Spec §FR-014, Spec §FR-015, Spec §Edge Cases]
- [ ] CHK085 Does the spec cover the readiness-gate exceptions that have a compliance dimension (unauthorized source caller-ID, malformed destination → potential wrong-number / regulatory violation — User Story 3 #2, #3 + FR-009 + FR-010)? [Coverage, Spec §User Story 3 #2, Spec §User Story 3 #3, Spec §FR-009, Spec §FR-010]

### Recovery

- [ ] CHK086 Does the spec cover compliance-safe recovery after a DNC outcome (the queue item's DNC field write + eligibility check prevents further dials, FR-019 + FR-024 + SC-006)? [Coverage, Spec §FR-019, Spec §FR-024, Spec §SC-006]
- [ ] CHK087 Does the spec cover compliance-safe recovery after a partial CRM write-back on a real call (resume only the missing writes, no duplicate DNC field write, FR-022 + User Story 7)? [Coverage, Spec §FR-022, Spec §User Story 7]
- [ ] CHK088 Does the spec cover compliance-safe recovery on orchestrator restart mid-call (live-call abandonment finalizes as `failed`, no false connected-call activity, no orphaned `in_progress` queue item, FR-026 + Edge Cases)? [Coverage, Spec §FR-026, Spec §Edge Cases]

### Non-Functional

- [ ] CHK089 Is the no-secrets-in-artifacts guarantee testable / verifiable (SC-018 → 0 secrets in any artifact across all run modes)? [Measurability, Spec §FR-035, Spec §SC-018]
- [ ] CHK090 Is the retention floor (≥ 90 days) measurable and auditable (e.g., file timestamps, retention metadata recorded)? [Measurability, Spec §FR-022, Spec §Assumptions]
- [ ] CHK091 Does the spec require the operator identity capture (FR-016) to be lossless across run modes (rehearsal AND real-call) so all run attempts are attributable, not only successful real calls? [Completeness, Spec §FR-016, Spec §FR-036]
- [ ] CHK092 Does the spec address how compliance-relevant configuration changes (e.g., changing the disclosure language, changing redaction policy, changing retention) are themselves audited / versioned? [Gap, Spec §FR-015, Spec §FR-033, Spec §FR-016]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

### Q11 PHI Tag-and-Redact (FR-015 / FR-033 amendment) — HIPAA-Adjacent Artifact Guarantee

- [ ] CHK093 Does FR-015 define the artifact-level PHI guarantee precisely enough that a compliance reviewer can confirm a caller-volunteered PHI utterance does NOT persist in any retained artifact unredacted (full transcript, session-result summary, shadow STT transcript, shadow STT discrepancy records — all four artifact types enumerated in FR-015 / FR-033)? [Completeness, Spec §FR-015, §FR-033] (closes CHK019)
- [ ] CHK094 Is the FR-015 PHI tag-and-redact requirement consistent with the Assumptions "Compliance scope" entry's non-clinical-scope assumption (i.e., the artifact-level redaction belt-and-suspenders is compatible with — and not in tension with — the explicit "non-clinical, non-HIPAA-class workflow" framing)? [Consistency, Spec §FR-015, §Assumptions — Compliance scope]
- [ ] CHK095 Does the spec address whether the FR-015 PHI tag-and-redact guarantee requires any update to the AI-on-behalf-of-Medx disclosure language (e.g., a "we do not collect health information" sentence) or whether the existing Slice 1 disclosure is sufficient given the persona's refusal-to-ask posture? [Gap, Spec §FR-015]
- [ ] CHK096 Is the `phi_collection_risk` escalation reason listed in the Slice 1 enumerated `human_review_reason` set and not introduced as a NEW reason for Slice 3 (FR-014 / FR-015 prohibit live-model expansion of the reason set)? [Consistency, Spec §FR-014, §FR-015, §CHK014 enumeration]
- [ ] CHK097 Does FR-015 define that the PHI-volunteered case MUST be observably distinct from a non-PHI call in the audit artifacts and run report (so a compliance reviewer can identify, audit, and follow up on every PHI-volunteered event)? [Measurability, Spec §FR-015]
- [ ] CHK098 Is the FR-015 tag-and-redact requirement timing-bound to "before any of those artifacts are written to disk" with no escape clause that could allow a non-redacted artifact to land on disk transiently? [Clarity, Spec §FR-015]
- [ ] CHK099 Does the spec define whether the persona's decision to continue the call after a caller-volunteered-PHI escalation requires any additional disclosure-language reminder (or any compliance-relevant addition to the script)? [Gap, Spec §FR-015]
- [ ] CHK100 Is the FR-015 tag-and-redact policy explicitly required to cover the run report (FR-036) when the run report quotes or summarizes a PHI-bearing utterance, consistent with CHK044's gap-flag on run-report redaction? [Consistency, Gap, Spec §FR-015, §FR-033, §FR-036]
- [ ] CHK101 Does the spec address whether the FR-015 PHI tag-and-redact policy is auditable from local artifacts alone (e.g., a redaction-applied marker on each affected artifact) so a compliance reviewer can confirm enforcement without reading source? [Measurability, Spec §FR-015, §FR-036]
- [ ] CHK102 Is the FR-015 PHI tag-and-redact requirement consistent with FR-034's "shadow STT discrepancy records retained as audit/review evidence even when transcript retention is summary-only" (i.e., the discrepancy records survive transcript pruning AND have PHI redacted before write)? [Consistency, Spec §FR-015, §FR-033, §FR-034]

### Q9 Rejected-By-Authentication Audit Log (FR-008 amendment) — Security Event Trail

- [ ] CHK103 Does FR-008 define the rejected-by-authentication audit log as a distinct log (separate from the duplicate / out-of-order callbacks audit log) so a security reviewer can isolate forgery attempts from delivery anomalies? [Clarity, Spec §FR-008] (closes CHK049)
- [ ] CHK104 Are the rejected-by-authentication audit log's required fields (`received_at`, source metadata) enumerated as a closed list so a compliance reviewer can audit the surface? [Completeness, Spec §FR-008]
- [ ] CHK105 Does FR-008 explicitly forbid the rejected-by-authentication audit log from containing the verification secret (consistent with FR-035 / SC-018 no-secrets-in-artifacts)? [Consistency, Spec §FR-008, §FR-035, §SC-018]
- [ ] CHK106 Does FR-008 explicitly forbid the rejected-by-authentication audit log from containing the callback body content (defense in depth against reflected-payload leakage), and is this requirement traceable to a stated security rationale? [Clarity, Spec §FR-008]
- [ ] CHK107 Does FR-036 require the run report to surface the rejected-by-authentication callbacks count for the session, and is this count distinct from the general callbacks-audit row count? [Completeness, Spec §FR-008, §FR-036]
- [ ] CHK108 Is the source metadata expectation in FR-008 ("provider-supplied source identifiers or IP-level metadata where available") consistent with what telephony providers actually expose, or is this an implicit deployment-configurable item? [Ambiguity, Spec §FR-008]
- [ ] CHK109 Does the spec address the compliance implication of an unknown-or-unsupported signature-verification mechanism (the FR-008 "where supported" caveat) on the rejected-by-authentication audit log (i.e., does the audit log still produce rows when verification is not in force)? [Gap, Spec §FR-008] (closes CHK047)

### Q13 Real-Call Flag on Resume (FR-001 / FR-022 amendment) — Operator Opt-In Trail

- [ ] CHK110 Does FR-022 explicitly require every resume re-invocation that performs a Dataverse mutation to supply the real-call / write-enabled flag (no "sticky" promotion from the original invocation)? [Completeness, Spec §FR-001, §FR-022]
- [ ] CHK111 Is the "absence of the flag on resume → run as rehearsal / readiness mode (no Dataverse mutation; surface what would have been written)" rule defined in FR-022 with no escape clause? [Clarity, Spec §FR-022]
- [ ] CHK112 Does the spec establish that EVERY Dataverse-mutating action has a recorded operator opt-in event (initial dial AND every resume), so the audit chain-of-custody for Dynamics mutations is complete? [Completeness, Spec §FR-001, §FR-016, §FR-022, §FR-036]
- [ ] CHK113 Is the real-call / write-enabled flag's behavior on resume traceable across FR-001 ("every Dataverse-mutating invocation"), FR-016 ("resume invocation must still satisfy the flag requirement"), FR-022 ("every resume re-invocation that performs a Dataverse mutation MUST supply the flag"), and the run report surfaces the flag state per FR-036? [Consistency, Spec §FR-001, §FR-016, §FR-022, §FR-036]
- [ ] CHK114 Does the spec address whether a rehearsal-mode resume's "surface what would have been written" output must itself be audited (e.g., is the would-have-written summary a compliance artifact subject to the no-secrets-in-artifacts guarantee and the retention floor)? [Gap, Spec §FR-022, §FR-035]
- [ ] CHK115 Is the FR-022 resume-without-flag rule (rehearsal-mode no-op for mutations) consistent with SC-011's "100% of runs that omit the flag run in rehearsal / readiness mode and place 0 SignalWire calls and create or update 0 Dynamics records" so the SC's quantification covers resume invocations? [Consistency, Spec §FR-022, §SC-011]

### Q12 Resume Operator Identity (FR-016 amendment) — Audit Chain-of-Custody

- [ ] CHK116 Does FR-016 preserve the original session's operator identity on the local session record and audit artifacts when a different operator resumes (so the original authorizer is not overwritten)? [Completeness, Spec §FR-016] (closes CHK091's lossless-across-modes flag for multi-operator resume)
- [ ] CHK117 Does FR-016 require the resuming operator's identity to be recorded separately on the run report (e.g., "resumed by X, original operator Y") so the audit chain-of-custody shows both identities? [Completeness, Spec §FR-016, §FR-036]
- [ ] CHK118 Is the resume-operator identity recording requirement local-only (not propagated into Dataverse) consistent with the original-operator local-only policy in FR-016? [Consistency, Spec §FR-016]
- [ ] CHK119 Does FR-036 explicitly require the run report to identify BOTH the original session's operator identity AND the resuming operator's identity on a resume invocation (so a compliance reviewer auditing the run report can reconstruct the full opt-in chain)? [Completeness, Spec §FR-016, §FR-036]
- [ ] CHK120 Does the spec address what happens when the operator identity capture (OS user or CLI-provided identifier per FR-016) is identical for the original and resuming invocations (i.e., is the run report still required to list "resumed by X, original operator X" or is a collapsed form permitted)? [Ambiguity, Spec §FR-016, §FR-036]
- [ ] CHK121 Is the multi-operator resume audit trail sufficient to attribute each Dataverse mutation to a specific operator opt-in event (i.e., can a compliance reviewer determine which operator authorized which Dataverse write within a resumed session)? [Measurability, Spec §FR-016, §FR-022, §FR-036]

### Q14 DNC-First Write Ordering (FR-024 amendment) — TCPA / State Opt-Out Compliance

- [ ] CHK122 Does FR-024 require the DNC / opt-out field write to be attempted FIRST in the write-back sequence — before the queue-status update, before the Phone Call activity, before any Task — on a `do_not_call` outcome? [Completeness, Spec §FR-024]
- [ ] CHK123 Is the DNC-first invariant traceable to a stated compliance rationale (i.e., even if a partial-write-back failure within the FR-022 retry budget loses everything BUT the DNC write, the contact is still protected from further automated outreach)? [Traceability, Spec §FR-024]
- [ ] CHK124 Does the spec address TCPA / state opt-out laws as the regulatory framework underpinning the DNC-first ordering requirement, or is the framework left implicit (and therefore at risk of being weakened by an implementation choice)? [Gap, Spec §FR-024, §Assumptions] (closes CHK069 partially for DNC-specific framework)
- [ ] CHK125 Is the DNC-first ordering compatible with FR-021's idempotency-key stamping (so a resume re-invocation does NOT produce a duplicate DNC write when the original DNC write already succeeded)? [Consistency, Spec §FR-021, §FR-024]
- [ ] CHK126 Does FR-024 require the DNC-first ordering on both end-of-call `do_not_call` AND mid-call opt-out (the FR-024 text covers both "a `do_not_call` disposition (or mid-call opt-out)" — is the ordering invariant identical in both cases)? [Consistency, Spec §FR-015, §FR-024]
- [ ] CHK127 Is the DNC-first ordering preserved across a resume invocation (i.e., if the original invocation failed before any write, does the resume also attempt DNC first; if the original succeeded only the DNC, does the resume skip the already-succeeded DNC write)? [Completeness, Spec §FR-022, §FR-024]
- [ ] CHK128 Does the DNC-first ordering's compliance benefit (contact protected from further outreach even on partial-write-back) hold under the FR-019 eligibility rule that uses the DNC field on the next attempt (i.e., is the DNC field write the actual block-future-dials mechanism)? [Consistency, Spec §FR-019, §FR-024, §SC-006]
- [ ] CHK129 Does the spec require the DNC write outcome to be operator-visible in the run report (FR-036) on every `do_not_call` session, distinct from the queue-status update outcome, so a compliance reviewer can verify DNC-write success independently? [Completeness, Spec §FR-024, §FR-036]
- [ ] CHK130 Is the DNC-first ordering consistent with FR-020's statement that the FR-024 DNC write is a field-level variant of the existing queue-status update operation and the four-operation count is preserved (i.e., the ordering requirement applies within / across the four-operation set without introducing a fifth operation)? [Consistency, Spec §FR-020, §FR-024]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Constitution Principle V + Round 2 Q11 — No-PHI-in-artifacts traceability through redaction layer

- [ ] CHK131 Is the no-PHI-in-artifacts guarantee (FR-035 + Round 2 Q10/Q11) traceable from the spec through the plan's redaction layer extension (Plan §Project Structure: `redaction/layer.py`) and on through the data-model §2.5 `RedactionPolicy` covering the four named artifact types (full transcript, session-result summary, shadow STT transcript, shadow STT discrepancy records)? [Traceability, Completeness, Spec §FR-015, §FR-033, §FR-035, Plan §Project Structure, Data-Model §2.5] (re-validates CHK094/CHK102 against the plan)
- [ ] CHK132 Does the data-model §2.5 PHI tag-and-redact pre-write trigger ("runs as a special-case pre-write step whenever a session's persona has emitted a `phi_collection_risk` escalation event") give the redaction layer a deterministic, observable signal so a compliance reviewer can verify every PHI-flagged session was redacted before any artifact write? [Measurability, Compliance, Data-Model §2.5, Spec §FR-015]
- [ ] CHK133 Is the redaction layer's exclusion of transcript-pointer metadata (Data-Model §2.5: "transcript pointer metadata, session IDs, provider call IDs, timestamps, run-report structural fields" remain unredacted) compatible with the no-PHI-in-artifacts compliance guarantee (i.e., is it stated that pointer metadata cannot carry PHI by construction)? [Consistency, Gap, Data-Model §2.5, Spec §FR-015, §FR-033]
- [ ] CHK134 Does the plan / data-model address the compliance posture when the PHI tag-and-redact pre-write step ITSELF fails (e.g., the redaction library throws) — does the plan specify a fail-closed posture (no artifact written) or fail-open (unredacted artifact written + alert)? [Gap, Ambiguity, Plan §Project Structure, Data-Model §2.5, Spec §FR-015, §FR-033]

### rejected_auth_callbacks audit log — TCPA / state-call-recording compliance posture

- [ ] CHK135 Does the contracts/rejected-auth-audit-log.md no-secret / no-body schema preserve any TCPA / state-call-recording compliance posture (i.e., is the schema's deliberate exclusion of callback body content sufficient to ensure a forged callback can never leak compliance-sensitive information such as audio URLs, call recordings, or transcripts into the audit log)? [Completeness, Compliance, Contract: rejected-auth-audit-log, Spec §FR-008, §FR-035] (re-validates CHK094/CHK095 from Round 1 / Round 2 against the explicit contract)
- [ ] CHK136 Is the rejected_auth_callbacks `source_metadata` field (Data-Model §1.4: "Provider-supplied source identifiers / IP-level metadata where available") defined narrowly enough that compliance-sensitive caller identifiers (caller phone number, caller email if SignalWire ever supplies one) cannot be silently captured into the audit log? [Gap, Ambiguity, Compliance, Data-Model §1.4, Contract: rejected-auth-audit-log]
- [ ] CHK137 Does the rejected-auth audit log's local-only retention (per research §10 file format + data-model §1.4 SQLite mirror) carry the same ≥ 90-day audit retention floor as other Slice 3 artifacts (Research §14 reuses Slice 2 retention), and is this compatible with any TCPA inquiry-response requirement? [Consistency, Gap, Research §10, §14, Data-Model §1.4]
- [ ] CHK138 Is the rejected_auth audit log's "may be null" `session_id` field (Data-Model §1.4: callback could not be associated with a known session) compatible with a compliance reviewer's need to attribute forgery attempts to a specific outreach campaign (i.e., does a null `session_id` mean the forgery attempt is untraceable to a campaign and is this operationally acceptable)? [Gap, Compliance, Data-Model §1.4, Contract: rejected-auth-audit-log]

### AI-disclosure attestation — deployment-configured real-time provider identity

- [ ] CHK139 Is the deployment-configured real-time AI provider's identity recording (FR-016 + contracts/pipecat-runtime.md + data-model §1.12 `RealtimeProviderSession`: `runtime_name`, `runtime_version`, `provider_name`, `model_name`, `model_version`) sufficient for an AI-disclosure audit such that an operator can attest, per session, "Provider X model Y version Z spoke to the caller on session S"? [Measurability, Compliance, Spec §FR-016, Data-Model §1.12, Contract: pipecat-runtime]
- [ ] CHK140 Does the run-report `runtime_identity` schema (Research §9, Contract: cli-slice3 minimum fields, Quickstart §4 example) preserve the FR-016 fields one-to-one so a downstream AI-disclosure audit consumer reads the same provider/model identity from a JSON file the operator can hand to a regulator? [Consistency, Traceability, Research §9, Contract: cli-slice3, Quickstart §4, Spec §FR-016]
- [ ] CHK141 Is the `RealtimeProviderSession` "MUST NOT contain credentials" invariant (Data-Model §1.12) preserved by the run-report schema so the AI-disclosure attestation artifact is safely shareable with a regulator (no API keys, no signing secrets leaked through the audit channel)? [Compliance, Consistency, Data-Model §1.12, Spec §FR-035, §FR-016]

### Operator-identity local-only invariant — operator-action-audit-trail compliance

- [ ] CHK142 Does the operator-identity local-only invariant (FR-016 + Round 2 Q12) satisfy operator-action-audit-trail requirements (i.e., can a compliance reviewer reconstruct which human operator authorized which Dataverse mutation from local artifacts alone, even though no operator identity propagates into Dynamics)? [Completeness, Compliance, Spec §FR-016, Data-Model §2.1] (re-validates CHK117/CHK121 from Round 2)
- [ ] CHK143 Does the plan / data-model address whether any compliance need requires the operator identity to appear in Dataverse (e.g., a Dynamics-side audit log of "who authorized this outbound call") or is the local-only posture (operator_identity_current / operator_identity_original on the SQLite `sessions` row) explicitly the canonical record? [Gap, Ambiguity, Compliance, Spec §FR-016, Data-Model §2.1, §2.3, Contract: crm-writeback-dnc-first]
- [ ] CHK144 Is the resume-operator local-only posture (Data-Model §2.1 `operator_identity_original` + `operator_identity_current` SQLite columns) auditable across a multi-operator resume chain without requiring Dynamics-side data, per FR-016 / Round 2 Q12? [Measurability, Compliance, Spec §FR-016, Data-Model §2.1]

### AI-on-behalf-of-Medx disclosure — single canonical text source per Constitution III

- [ ] CHK145 Is the AI-on-behalf-of-Medx disclosure (FR-015) traceable to a single canonical text source in the persona module per Constitution Principle III (Plan §Project Structure: `persona/alf_appointment_setter.py` — does the plan name the file where the disclosure text lives so the audit posture is "one persona module owns the disclosure")? [Traceability, Compliance, Spec §FR-015, Plan §Project Structure, Plan §Constitution Check III]
- [ ] CHK146 Does the plan / data-model define how persona version (recorded on the session per FR-016 + Data-Model §2.1) ties to the canonical disclosure text such that a compliance reviewer can read "persona_version = alf_appointment_setter@1.0.0" from a run report and reconstruct the exact disclosure text the caller heard? [Measurability, Compliance, Spec §FR-015, §FR-016, Data-Model §2.1, Quickstart §4]
- [ ] CHK147 Is the Pipecat runtime's "live model produces conversation turns and extraction events but MUST NOT mutate the deterministic disposition rules or the human-review reason set" boundary (Plan §Constitution Check III, Contract: pipecat-runtime) sufficient to guarantee the disclosure text cannot be paraphrased / altered by the live model in violation of FR-015's "canonical" disclosure requirement? [Completeness, Compliance, Plan §Constitution Check III, Contract: pipecat-runtime, Spec §FR-014, §FR-015]
- [ ] CHK148 Does the plan / data-model address whether a discrepancy event from the shadow STT lane (Data-Model §1.7) can be triggered when the live model's spoken disclosure diverges from the persona's canonical disclosure text (i.e., is "disclosure_text_drift" a configured high-value field or is it implicitly out-of-scope for the shadow lane)? [Gap, Ambiguity, Spec §FR-015, Data-Model §1.7, Contract: shadow-stt-lane]

### Cross-cutting compliance — Round 3 closes Round 2 follow-ups

- [ ] CHK149 Does the data-model §7 invariants list "no PHI in artifacts (caller-volunteered path)" with a stated enforcement mechanism (pre-write tag-and-redact runs whenever persona emits `phi_collection_risk`) — is the same enforcement traceable across all four artifact types named in Data-Model §2.5 (transcript, summary, shadow transcript, shadow discrepancy records)? [Consistency, Compliance, Data-Model §2.5, §7, Spec §FR-015, §FR-033]
- [ ] CHK150 Is the no-PHI guarantee enforced uniformly across the live conversation path AND a session resumed by a different operator (Round 2 Q12), so PHI redaction does not depend on the operator-identity continuity? [Consistency, Compliance, Spec §FR-015, §FR-016, Data-Model §2.1, §2.5]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate the requirement exists but is interpretable in multiple non-trivially-different ways.
- Items marked [Conflict] indicate two parts of the spec disagree on the same requirement.
- CHK093 – CHK130 are Round 2 amendments (2026-05-25) covering: Q11 PHI tag-and-redact artifact guarantee, Q9 rejected-by-authentication audit log, Q13 real-call flag on resume, Q12 multi-operator resume identity, Q14 DNC-first write ordering.
- CHK131 – CHK150 are Round 3 post-plan validation (2026-05-25) covering: no-PHI-in-artifacts traceability through `redaction/layer.py`, rejected_auth audit log TCPA / state-call-recording posture, AI-disclosure attestation via deployment-configured provider identity, operator-identity local-only operator-action-audit-trail sufficiency, AI-on-behalf-of-Medx disclosure single canonical text source.
- >=80% of items reference a spec section (FR-NNN, SC-NNN, Definitions, Edge Cases, User Story N, Assumptions, Clarifications, Constitution Alignment, or Key Entities) for traceability.
