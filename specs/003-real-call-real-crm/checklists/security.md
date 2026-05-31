# Security & Privacy Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the security & privacy dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Callback Authentication (SignalWire Webhooks)

- [ ] CHK001 Does the spec require SignalWire callback authentication on every callback delivery (status and media)? [Completeness, Spec §FR-008]
- [ ] CHK002 Is the "where supported" hedge in FR-008 explicit about what conditions cause authentication to be skipped — or is it ambiguous whether authentication is mandatory? [Ambiguity, Spec §FR-008]
- [ ] CHK003 Does the spec require that callbacks failing authentication MUST be rejected (no state mutation, no normalized-event emission, no CRM write)? [Completeness, Spec §FR-008]
- [ ] CHK004 Does the spec define what "rejected" means for an unauthenticated callback (HTTP response code, audit log entry, no orchestrator hand-off)? [Gap, Spec §FR-008]
- [ ] CHK005 Is there a requirement that the rejected-callback event itself is recorded in the callbacks audit log (so attempted forgeries are visible to the operator)? [Gap, Spec §FR-007, §FR-008]
- [ ] CHK006 Does the spec require that the signature-verification mechanism's secrets (e.g., signing keys) are NEVER logged, including in rejected-callback log entries? [Completeness, Spec §FR-008, §FR-035]
- [ ] CHK007 Is the callback authentication requirement applied to BOTH status callbacks and media callbacks (not only status)? [Completeness, Spec §FR-007, §FR-008]
- [ ] CHK008 Does the spec define behavior when the authentication mechanism is not supported by SignalWire (does the run still proceed, does it fail readiness)? [Ambiguity, Spec §FR-008]
- [ ] CHK009 Is the callback authentication treated as a deployment configuration requirement (i.e., must be configured before deploy) per the readiness checks? [Gap, Spec §FR-009, §Definitions: Telephony readiness check]
- [ ] CHK010 Does the spec require that an authentication failure does not leak provider-internal context that could aid an attacker (e.g., reflected callback contents in error messages)? [Gap, Spec §FR-008, §FR-035]

## Secret-Exclusion Coverage (Per Credential Class)

- [ ] CHK011 Does the spec name SignalWire credentials in the no-secrets-in-artifacts guarantee? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK012 Does the spec name real-time AI provider credentials in the no-secrets-in-artifacts guarantee? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK013 Does the spec name shadow STT provider credentials in the no-secrets-in-artifacts guarantee? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK014 Does the spec name Dataverse credentials in the no-secrets-in-artifacts guarantee? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK015 Is the "or any other secret" catch-all stated so future-added credentials are covered by default? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK016 Is the no-secrets guarantee stated for every artifact class produced by Slice 3: logs, run report, session-result artifact, transcript artifact, callbacks audit log, conflicting-events audit log, shadow STT artifact, shadow STT discrepancy record, planned write-back payloads, actual write-back payloads, telephony readiness report, write-back progress ledger? [Completeness, Spec §FR-033, §FR-034, §FR-035, §FR-036, §FR-038, §SC-018, §Key Entities]
- [ ] CHK017 Is the no-secrets guarantee quantified (0 secrets) and verifiable per SC-018? [Measurability, Spec §SC-018]
- [ ] CHK018 Does the spec require that the SignalWire callback signature-verification secret is excluded from artifacts (covered by FR-035 as "any other secret")? [Completeness, Spec §FR-008, §FR-035]
- [ ] CHK019 Does the spec require that secrets are excluded even from error / exception traces (not only from happy-path artifacts)? [Gap, Spec §FR-035]
- [ ] CHK020 Is the secret-exclusion guarantee preserved across the resume path (resumed runs do not regress to producing secret-laden artifacts)? [Consistency, Spec §FR-022, §FR-035]

## Redaction-Before-Disk (Transcripts)

- [ ] CHK021 Does the spec require default-on transcript redaction before any transcript artifact is written to disk? [Completeness, Spec §FR-033, §Edge Cases: Default-on redaction applied to a Slice 3 transcript]
- [ ] CHK022 Is the default-on redaction applied to BOTH the live conversation path transcript and the shadow STT transcript? [Completeness, Spec §FR-033, §FR-034]
- [ ] CHK023 Is the redaction-before-disk requirement stated everywhere a transcript artifact is written (every retention mode that produces a transcript file)? [Completeness, Spec §FR-033, §FR-034, §Edge Cases: Transcript retention is summary-only or pointer-only, §Edge Cases: Default-on redaction applied to a Slice 3 transcript]
- [ ] CHK024 Does the spec define the default redaction token / behavior (e.g., `[REDACTED]`) or reference the Slice 2 default explicitly? [Completeness, Spec §FR-033]
- [ ] CHK025 Does the spec define behavior when redaction is disabled by deployment configuration (is that even allowed, and is the operator warned)? [Gap, Spec §FR-033]
- [ ] CHK026 Does the spec require redaction of the transcript pointer itself (when pointer-only retention is used) so the pointer cannot leak sensitive content via its path / metadata? [Gap, Spec §FR-033]
- [ ] CHK027 Is the redaction policy applied to summary text within the session-result artifact, not only to the full transcript file? [Gap, Spec §FR-033, §Edge Cases: Transcript retention is summary-only or pointer-only]
- [ ] CHK028 Is the redaction-before-disk semantic stated as a hard ordering (redaction MUST complete before any write), not a best-effort "should"? [Completeness, Spec §FR-033, §Edge Cases: Default-on redaction applied to a Slice 3 transcript]
- [ ] CHK029 Does the spec require that shadow STT discrepancy records (which compare live vs. shadow values for high-value fields) themselves honor the redaction policy when the values being compared contain sensitive content? [Gap, Spec §FR-030, §FR-034]

## PHI Exclusion

- [ ] CHK030 Does the spec require the persona MUST NOT collect resident/patient PHI on every connected call? [Completeness, Spec §Constitution Alignment: Safety and human handoff, §FR-014, §FR-015]
- [ ] CHK031 Is the PHI exclusion preserved verbatim from Slice 1 persona policy (no weakening)? [Consistency, Spec §Constitution Alignment: Safety and human handoff, §Assumptions: Persona policy preserved]
- [ ] CHK032 Does the spec require the persona to escalate with `needs_human_review` using the `phi_collection_risk` reason when PHI collection is attempted by the live model or the contact? [Completeness, Spec §FR-015, §Edge Cases: Mid-call PHI / out-of-allowed-claim attempt]
- [ ] CHK033 Does the spec state that the live model MUST NOT relax the PHI prohibition (i.e., the persona policy is authoritative over the model)? [Completeness, Spec §FR-014, §FR-015]
- [ ] CHK034 Is the non-clinical scope explicitly required for Slice 3 (no clinical / patient-care workflows)? [Completeness, Spec §Constitution Alignment: Safety and human handoff, §FR-015, §Assumptions: Compliance scope]
- [ ] CHK035 Does the spec state that Slice 3 is explicitly NOT a HIPAA-class patient-care or clinical workflow? [Completeness, Spec §Assumptions: Compliance scope]
- [ ] CHK036 Is the PHI exclusion stated as both a persona-level requirement AND an artifact-level guarantee (i.e., PHI doesn't appear in transcripts / artifacts even if a caller volunteers it)? [Gap, Spec §FR-015, §FR-033]
- [ ] CHK037 Does the spec require that the shadow STT lane also honors the PHI exclusion (so the shadow transcript does not become a back-channel for PHI)? [Gap, Spec §FR-028, §FR-030, §FR-034]
- [ ] CHK038 Is the persona's escalation behavior on PHI attempt operator-visible via the run report (so PHI escalations can be audited)? [Completeness, Spec §FR-015, §FR-036]

## Operator-Identity Scoping

- [ ] CHK039 Does the spec define operator identity as captured on the local session and run report only (not propagated into Dynamics)? [Completeness, Spec §FR-016, §Clarifications Session 2026-05-25]
- [ ] CHK040 Is the operator-identity scope boundary stated explicitly (local-only, no Dataverse field added for operator identity)? [Completeness, Spec §FR-016]
- [ ] CHK041 Does the spec define the minimum content of the operator identity (OS user or CLI-provided identifier)? [Completeness, Spec §FR-016]
- [ ] CHK042 Is the operator identity required on EVERY Slice 3 session (not only real-call sessions)? [Completeness, Spec §FR-016]
- [ ] CHK043 Does the spec require that operator identity recording excludes secrets (e.g., operator session tokens, API keys)? [Completeness, Spec §FR-016, §FR-035]
- [ ] CHK044 Is the operator identity recorded in the run report explicitly (per FR-036)? [Consistency, Spec §FR-016, §FR-036]
- [ ] CHK045 Does the spec define the resume-session behavior for operator identity (does the resume use the original session's operator, or record the resuming operator)? [Gap, Spec §FR-016, §FR-022]
- [ ] CHK046 Is the operator-identity scoping consistent with the "no new Dataverse field" guarantee preserving the Slice 2 mapping surface unchanged? [Consistency, Spec §FR-016, §FR-020]

## Authorization Gates (Real-Call Flag, Source-Number Authorization)

- [ ] CHK047 Does the spec require the real-call / write-enabled flag as an explicit authorization gate before any SignalWire dial or Dataverse mutation? [Completeness, Spec §FR-001, §FR-025]
- [ ] CHK048 Is the real-call flag's authorization role consistent with the rehearsal-mode default (the flag's absence ALWAYS triggers rehearsal, not just sometimes)? [Consistency, Spec §FR-001, §FR-002, §SC-011]
- [ ] CHK049 Does the spec require source-caller-ID authorization for outbound dialing as a separate authorization gate (FR-009)? [Completeness, Spec §FR-009, §Definitions: Telephony readiness check]
- [ ] CHK050 Is the unauthorized source-number case explicitly handled as a telephony readiness failure that blocks before dial? [Completeness, Spec §FR-009, §User Story 3 scenario 2]
- [ ] CHK051 Does the spec require that the suspended-credentials / unauthorized source-number mid-run case is detected on the next pre-dial check (defense in depth)? [Completeness, Spec §Edge Cases: SignalWire credentials or source number unauthorized / suspended mid-run]
- [ ] CHK052 Is the real-call flag treated as an authorization gate that cannot be bypassed by retry, resume, or callback delivery (no implicit promotion)? [Gap, Spec §FR-001, §FR-022]
- [ ] CHK053 Does the spec require that callback owner and review-task owner mappings are resolved (an authorization-adjacent assignment gate) before a real dial? [Completeness, Spec §FR-009, §Definitions: Telephony readiness check, §User Story 3 §Independent Test (g)]
- [ ] CHK054 Is the queue-claim semantics (Slice 2) preserved as an authorization-adjacent gate against concurrent invocations? [Consistency, Spec §FR-003, §Clarifications Session 2026-05-25, §Edge Cases: Concurrent CLI invocation on the same Dataverse queue item]

## Rejected-Callback Audit Behavior

- [ ] CHK055 Does the spec define the audit-log behavior for callbacks rejected by authentication? [Gap, Spec §FR-008]
- [ ] CHK056 Does the spec require that rejected callbacks do NOT log the verification secret (positive) or the full callback payload (defense-in-depth, depending on policy)? [Gap, Spec §FR-008, §FR-035]
- [ ] CHK057 Is the rejected-callback case distinct from the duplicate-callback case in the audit log (so attempted forgeries don't look like duplicate deliveries)? [Gap, Spec §FR-007, §FR-008]
- [ ] CHK058 Does the spec require the run report to summarize the count of rejected-by-authentication callbacks (so operators see attempted forgeries)? [Gap, Spec §FR-036]
- [ ] CHK059 Is the rejected-callback behavior consistent across the Slice 2 conflicting-events audit channel (rejected callbacks may be a separate channel or share it)? [Ambiguity, Spec §FR-008, §FR-027, §Key Entities: Conflicting Event Audit Record]

## Scenario Class: Primary (Authenticated Real-Call Run)

- [ ] CHK060 Is the primary security scenario (authenticated SignalWire callbacks, redacted transcripts on disk, operator identity captured locally, no secrets in artifacts) covered by spec text? [Completeness, Spec §FR-008, §FR-016, §FR-033, §FR-035]
- [ ] CHK061 Is the primary scenario's security posture quantified (0 secrets per SC-018, 0 PHI-collection events expected)? [Measurability, Spec §SC-018, §FR-015]

## Scenario Class: Alternate (Rehearsal-Mode, Shadow Disabled)

- [ ] CHK062 Does the spec define security posture for rehearsal mode (no dial, no mutation — and therefore no callback authentication risk, but secrets still must not appear in the readiness report)? [Completeness, Spec §FR-002, §FR-035]
- [ ] CHK063 Does the spec define security posture when shadow STT is disabled (no shadow STT credentials needed, no shadow transcript on disk)? [Completeness, Spec §FR-032, §FR-035]
- [ ] CHK064 Does the spec define security posture for summary-only or pointer-only retention (smaller artifact surface — does redaction policy still apply where applicable)? [Completeness, Spec §FR-033, §Edge Cases: Transcript retention is summary-only or pointer-only]

## Scenario Class: Exception / Error (Failed Signature, Suspended Credentials Mid-Run, Provider 4xx)

- [ ] CHK065 Is the failed-signature exception scenario covered (callback rejected, no state mutation, no secret logged)? [Completeness, Spec §FR-008]
- [ ] CHK066 Is the suspended-credentials-mid-run exception scenario covered with the spec stating in-flight calls are allowed to complete and the next pre-dial check fails? [Completeness, Spec §Edge Cases: SignalWire credentials or source number unauthorized / suspended mid-run]
- [ ] CHK067 Is the provider-rejected dial (4xx) exception covered as an authorization-adjacent failure (provider rejects an invalid/blocked/unauthorized number, no attempt consumed)? [Completeness, Spec §FR-012, §Edge Cases: Provider 4xx on dial request]
- [ ] CHK068 Is the live model attempting an out-of-allowed-claim or PHI question covered as a safety/authorization exception (persona escalates with the enumerated reason)? [Completeness, Spec §FR-014, §FR-015, §Edge Cases: Mid-call PHI / out-of-allowed-claim attempt]
- [ ] CHK069 Is the mid-call opt-out / DNC scenario covered as a persona safety gate that supersedes the live model's behavior? [Completeness, Spec §FR-015, §Edge Cases: Mid-call opt-out / DNC, §User Story 5 scenario 3]
- [ ] CHK070 Is the malformed / blank destination phone number case covered as a pre-dial security/safety block (no dial, no attempt consumed)? [Completeness, Spec §FR-010, §Edge Cases: Real-dial phone-number validation failure]

## Scenario Class: Recovery (Security-Sensitive Resume / Conflict)

- [ ] CHK071 Does the spec require that resumed runs preserve the no-secrets guarantee on all artifacts produced during resume? [Consistency, Spec §FR-022, §FR-035]
- [ ] CHK072 Does the spec require that conflicting-late callbacks (after disposition finalized) do not retroactively introduce secrets or unredacted content into any artifact? [Consistency, Spec §FR-027, §FR-033, §FR-035]
- [ ] CHK073 Does the spec require that the operator identity captured on the original session is preserved through the resume so the audit trail of who initiated the original real call is not lost? [Gap, Spec §FR-016, §FR-022]
- [ ] CHK074 Is the queue-conflict-detection (human-edited queue item between claim and write-back) preserved as a security-relevant guard (avoiding silent overwrites of human edits)? [Completeness, Spec §Edge Cases: CRM queue item changed by a human between claim and write-back]

## Scenario Class: Non-Functional (Privacy, Auditability, Absence-of-Attack-Surface)

- [ ] CHK075 Does the spec note the absence of any visual openCloser UI in Slice 3 (no UI attack surface for Slice 3)? [Completeness, Spec §FR-038, §Assumptions: Operator surface]
- [ ] CHK076 Is the auditability posture (operator can explain outcome without source code) preserved with the security guarantees intact (no secrets, redacted transcripts)? [Consistency, Spec §SC-017, §FR-035, §FR-033]
- [ ] CHK077 Is the no-secrets-in-artifacts guarantee quantified for verification (0 occurrences per SC-018) and stated as a release gate? [Measurability, Spec §SC-018]
- [ ] CHK078 Is the persona-policy-authoritative requirement quantified for the live model (100% of dispositions selected by deterministic precedence per SC-014)? [Measurability, Spec §SC-014, §FR-014]
- [ ] CHK079 Is the boundary requirement (0 SignalWire / Pipecat / real-time AI / shadow STT specifics leak into orchestrator / persona / Dataverse adapter) quantified per SC-015 (so a security review can verify the boundary)? [Measurability, Spec §SC-015]
- [ ] CHK080 Does the spec require that telephony readiness failures surface the FAILING check name (so operators get actionable info) but do not surface secrets in the failure message? [Completeness, Spec §FR-011, §FR-035]
- [ ] CHK081 Is the shadow STT lane required to honor the same retention AND security guarantees as the live transcript (no separate, weaker security model for shadow)? [Consistency, Spec §FR-034, §FR-035]
- [ ] CHK082 Does the spec require that the DNC / opt-out persistence to Dataverse is treated as a privacy-sensitive write that completes even when other write-back operations are deferred (so opt-out is honored ASAP)? [Gap, Spec §FR-024, §Constitution Alignment: Safety and human handoff]
- [ ] CHK083 Is the no-clinical-workflow requirement stated as a hard out-of-scope guard (clinical personas require a separate PRD and safety model)? [Completeness, Spec §Assumptions: Compliance scope]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments (FR-001/008/013/015/016/020/022/024/026/029/033/036 + Mid-call PHI edge case + Performance Deferred-to-Plan subsection + new Clarifications block) and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

### Rejected-by-authentication audit log (Q9 — FR-008)

- [ ] CHK084 Does the amended FR-008 require rejected-by-authentication callbacks to be recorded in a DISTINCT audit log, separate from the duplicate / out-of-order callbacks audit log (closes Round 1 CHK057, CHK055)? [Completeness, Spec §FR-008, §Clarifications Session 2026-05-25 (Round 2) Q4]
- [ ] CHK085 Is the rejected-by-authentication audit log's minimum content set (`received_at`, `source metadata`) defined specifically enough that a reviewer can verify a log entry conforms to it? [Measurability, Spec §FR-008]
- [ ] CHK086 Does FR-008 state as a hard exclusion that the rejected-by-authentication audit log MUST NOT include the verification secret AND MUST NOT include the callback body content (defense in depth against reflected-payload leakage, closes Round 1 CHK056)? [Completeness, Spec §FR-008]
- [ ] CHK087 Is "source metadata" defined or exemplified (e.g., provider-supplied source identifiers / IP-level metadata where available) so a reviewer can tell what is allowed in the log vs. what is excluded? [Clarity, Spec §FR-008, Ambiguity]
- [ ] CHK088 Is the run-report rejected-by-authentication count requirement stated in BOTH FR-008 and FR-036 with consistent wording (closes Round 1 CHK058)? [Consistency, Spec §FR-008, §FR-036]
- [ ] CHK089 Is the rejected-by-authentication audit log requirement distinguished from the conflicting-events audit channel (which it is NOT — rejected-by-auth is its own channel, conflicting-late-after-finalization is its own channel, duplicate-or-out-of-order is the callbacks audit log) so the three channels remain non-overlapping (closes Round 1 CHK059)? [Consistency, Spec §FR-007, §FR-008, §FR-027, §Key Entities: Callbacks Audit Log]
- [ ] CHK090 Does the spec name the HTTP rejection requirement ("provider-appropriate HTTP response code") AND the audit log requirement together so a reader cannot infer that one satisfies the other? [Completeness, Spec §FR-008]
- [ ] CHK091 Is the "no callback body content" exclusion stated as a hard MUST NOT rather than a SHOULD NOT so a deployment cannot opt in to body retention for rejected callbacks (defense-in-depth invariant)? [Completeness, Spec §FR-008]
- [ ] CHK092 Does the spec confirm that the rejected-by-authentication audit log is itself covered by the no-secrets-in-artifacts guarantee (FR-035) so the rejection-record artifact cannot regress the secret-exclusion posture? [Consistency, Spec §FR-008, §FR-035, §SC-018]
- [ ] CHK093 Is the rejected-by-authentication count specified to appear in the run report on EVERY run (not only runs that recorded a rejection) so a zero-count is itself auditable evidence? [Completeness, Spec §FR-036, Gap]

### Default-on redaction scope expansion (Q10 — FR-033)

- [ ] CHK094 Does the amended FR-033 name all FOUR artifact classes covered by default-on redaction (full transcript file, session-result `summary`, shadow STT transcript, shadow STT discrepancy records) — closing Round 1 CHK027 and CHK029? [Completeness, Spec §FR-033, §Clarifications Session 2026-05-25 (Round 2) Q5]
- [ ] CHK095 Is the transcript pointer (and its metadata) explicitly EXCLUDED from the default-on redaction policy with a stated rationale (machine-readable for resume / inspection) so a reader cannot conclude pointers should also be redacted? [Clarity, Spec §FR-033]
- [ ] CHK096 Is the pointer-exclusion narrowly scoped to the pointer itself and its metadata (not the artifact the pointer refers to) so a redaction-bypass attack cannot exploit the exclusion by stuffing content into pointer fields? [Completeness, Spec §FR-033, Gap]
- [ ] CHK097 Is the default-on redaction policy on the session-result `summary` stated consistently between FR-033 and the Slice 3 retention modes (specifically the summary-only retention mode, where the summary is the primary persisted artifact)? [Consistency, Spec §FR-033, §Edge Cases: Transcript retention is summary-only or pointer-only]
- [ ] CHK098 Is the default-on redaction scope on the shadow STT discrepancy records stated as covering BOTH the live and shadow values held in the record (so a discrepancy record cannot become a side channel for unredacted content)? [Completeness, Spec §FR-033, §Key Entities: Shadow STT Discrepancy Record, Gap]
- [ ] CHK099 Is the redaction-before-disk ordering preserved verbatim for each of the four covered artifact classes (i.e., redaction completes before each artifact is written, not best-effort) so the ordering invariant from Round 1 CHK028 holds across all four? [Consistency, Spec §FR-033]

### PHI tag-and-redact pre-write invariant (Q11 — FR-015)

- [ ] CHK100 Does the amended FR-015 require that when a caller VOLUNTEERS PHI mid-call, the default-on redaction policy MUST tag-and-redact the PHI-bearing utterance in all four artifacts (full transcript, session-result summary, shadow STT transcript, shadow STT discrepancy records) BEFORE any of them are written to disk (closes Round 1 CHK023, CHK036)? [Completeness, Spec §FR-015, §FR-033, §Clarifications Session 2026-05-25 (Round 2) Q6]
- [ ] CHK101 Is the redact-BEFORE-write ordering stated as hard sequencing (no PHI-bearing utterance reaches disk in any of the four artifact classes) rather than a best-effort cleanup pass after write? [Completeness, Spec §FR-015]
- [ ] CHK102 Is the requirement to "tag" the PHI utterance (as distinct from redacting it) defined sufficiently to be testable — i.e., a reviewer can identify that an utterance was tagged as PHI in the artifact even though its content is redacted? [Measurability, Spec §FR-015, Gap]
- [ ] CHK103 Does the spec require that the PHI-volunteered case is OBSERVABLY DISTINCT in the audit artifacts and the run report from a non-PHI call (per FR-015 final sentence) so an auditor can detect-and-count PHI-volunteered sessions? [Measurability, Spec §FR-015, §FR-036]
- [ ] CHK104 Is the PHI-volunteered requirement consistent between FR-015 (escalation + redaction) and the Edge Cases entry "Mid-call PHI / out-of-allowed-claim attempt" so a reader cannot conclude one is authoritative and the other indicative? [Consistency, Spec §FR-015, §Edge Cases: Mid-call PHI / out-of-allowed-claim attempt]
- [ ] CHK105 Is the redaction requirement preserved when retention is summary-only (the redaction still applies to the persisted summary) and pointer-only (the artifact the pointer references is still subject to redaction before write)? [Consistency, Spec §FR-015, §FR-033, §Edge Cases: Transcript retention is summary-only or pointer-only]
- [ ] CHK106 Does the spec confirm that the PHI tag-and-redact invariant is preserved on the resume path (a resume that produces or rewrites any of the four artifact classes still applies the redaction-before-write ordering)? [Consistency, Spec §FR-015, §FR-022, §FR-033, Gap]

### Resume operator identity + real-call flag on resume (Q12, Q13 — FR-016, FR-001, FR-022)

- [ ] CHK107 Does the amended FR-016 require that the ORIGINAL session's operator identity is preserved on the local session record and audit artifacts on resume (the original authorizer is not overwritten) — closing Round 1 CHK073, CHK045? [Completeness, Spec §FR-016, §Clarifications Session 2026-05-25 (Round 2) Q7]
- [ ] CHK108 Does FR-016 require that the RESUMING operator's identity is recorded SEPARATELY on the run report (e.g., "resumed by X, original operator Y") so both authorizers are visible without losing the original? [Completeness, Spec §FR-016, §FR-036]
- [ ] CHK109 Is the resume-operator format ("resumed by X, original operator Y") stated in FR-016 AND in FR-036 with consistent wording so a reader cannot infer one is the format and the other is illustrative? [Consistency, Spec §FR-016, §FR-036]
- [ ] CHK110 Does the amended FR-016 / FR-022 / FR-001 jointly state that EVERY Dataverse-mutating invocation — including resume — MUST supply the real-call / write-enabled flag (closing Round 1 CHK052)? [Completeness, Spec §FR-001, §FR-016, §FR-022, §Clarifications Session 2026-05-25 (Round 2) Q8]
- [ ] CHK111 Is the no-"sticky"/no-session-inherited-flag-promotion rule stated explicitly so a reader cannot conclude that the original invocation's flag promotes through the resume path? [Completeness, Spec §FR-001, §FR-022]
- [ ] CHK112 Does FR-022 define the behavior when a resume invocation OMITS the real-call / write-enabled flag (runs in rehearsal / readiness mode — no Dataverse mutation; the run report surfaces what would have been written)? [Completeness, Spec §FR-022]
- [ ] CHK113 Is the rehearsal-on-resume behavior consistent with the rehearsal-mode default behavior in FR-002 (no SignalWire dial, no Dataverse mutation, planned write-back artifacts produced) so the two paths produce equivalent guarantees? [Consistency, Spec §FR-002, §FR-022]
- [ ] CHK114 Is the no-implicit-flag-promotion rule stated to apply to retry, resume, AND callback delivery (not only resume) so a reader cannot infer an exception exists for in-run retries or provider callback handling? [Completeness, Spec §FR-001, §FR-021, §FR-022, Gap]
- [ ] CHK115 Does the run report's resume-operator format requirement cover the case where the resume invocation runs in rehearsal mode (so the "what would have been written" surface still identifies both operators)? [Consistency, Spec §FR-022, §FR-036, Gap]
- [ ] CHK116 Is the original-operator-preservation rule cross-referenced from the local audit artifacts (session record + audit) so a reviewer cannot conclude the original operator is preserved on the run report alone? [Completeness, Spec §FR-016, §FR-036]

### DNC write-first ordering invariant (Q14 — FR-024)

- [ ] CHK117 Does the amended FR-024 require the DNC / opt-out field write to be attempted FIRST in the write-back sequence — before the queue-status update, before the Phone Call activity emission, and before any Task emission — closing Round 1 CHK082? [Completeness, Spec §FR-024, §Clarifications Session 2026-05-25 (Round 2) Q9]
- [ ] CHK118 Is the rationale for write-first ordering ("a partial-write-back failure within the FR-022 retry budget that loses everything BUT the DNC write still leaves the contact protected from further automated outreach") stated in FR-024 so a future plan cannot reorder the writes for performance? [Completeness, Spec §FR-024]
- [ ] CHK119 Does the spec require that idempotency-key stamping (FR-021) prevents duplicate DNC writes on resume so the write-first invariant is safely re-runnable? [Consistency, Spec §FR-021, §FR-022, §FR-024]
- [ ] CHK120 Is the write-first ordering required for BOTH the `do_not_call` final disposition AND the mid-call opt-out trigger (per FR-024 wording "or mid-call opt-out") so the privacy-protective ordering applies even when the opt-out happens mid-conversation? [Completeness, Spec §FR-024, §Edge Cases: Mid-call opt-out / DNC]
- [ ] CHK121 Is the write-first ordering compatible with the four-operations write-back count preservation (Q8) — i.e., DNC is still a field-level variant of the queue-status update emission operation, not a fifth operation (closes Round 1 CHK046)? [Consistency, Spec §FR-020, §FR-024, §Clarifications Session 2026-05-25 (Round 2) Q3]
- [ ] CHK122 Does FR-024 specify the behavior when the DNC write itself fails (does the retry budget still apply, does the subsequent ordering still hold)? [Clarity, Spec §FR-022, §FR-024, Gap]
- [ ] CHK123 Is the DNC write-first ordering preserved on resume (i.e., a resume that finds DNC unwritten still attempts DNC first before any other missing write)? [Consistency, Spec §FR-022, §FR-024]
- [ ] CHK124 Does the spec confirm that the DNC write-first ordering preserves the "no callback or review Task" requirement on `do_not_call` so a reader cannot infer that a Task could be created if the DNC write fails permanently? [Consistency, Spec §FR-024, §SC-006]

### Cross-cutting Round 2 consistency

- [ ] CHK125 Are the four write-back operations (Q8) preserved verbatim in FR-020 after the Round 2 amendments — i.e., the DNC field write, blocked-status field write, and dial-blocked field write are explicitly field-level variants of the existing queue-status update emission operation, not new operations (closes Round 1 CHK046)? [Consistency, Spec §FR-020, §FR-012, §FR-023, §FR-024, §Clarifications Session 2026-05-25 (Round 2) Q3]
- [ ] CHK126 Is the "rejected-by-authentication audit log" concept introduced as a new artifact class in the security-relevant artifact inventory so Round 1 CHK016's "every artifact class" list is updated for Round 2 coverage? [Completeness, Spec §FR-008, §FR-035, §SC-018, Gap]
- [ ] CHK127 Does the run report's resume-operator format requirement coexist with the existing operator-identity-local-only rule (FR-016, Round 1 CHK039–CHK046) so a reader cannot conclude that resume promotes operator identity into Dataverse? [Consistency, Spec §FR-016, §FR-036]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### HMAC-SHA256 signature mechanism (Research §2 ↔ FR-008)

- [ ] CHK128 Is the choice of HMAC-SHA256 as the SignalWire callback signature algorithm stated as confirmed-against-SignalWire-documentation versus an [Assumption] the plan adopted pending vendor confirmation (re-validates Round 1 spec-level coverage of FR-008 against the plan-side decision)? [Clarity, Research §2, Contract: rejected-auth-audit-log, Spec §FR-008, Ambiguity]
- [ ] CHK129 Is the HMAC-SHA256 selection internally consistent across research.md §2 ("SignalWire's documented HMAC-SHA256 signature mechanism"), signalwire-transport.md ("every inbound callback MUST be HMAC-SHA256-verified"), and rejected-auth-audit-log.md ("fail HMAC-SHA256 signature verification") so no other algorithm name appears in any plan-side artifact? [Consistency, Research §2, Contract: signalwire-transport, Contract: rejected-auth-audit-log]
- [ ] CHK130 Does the plan specify the SignalWire signing-secret env-var name (`SIGNALWIRE_SIGNING_SECRET`) consistently in research.md §2, research.md §11, and quickstart.md §1.2 with no alternative naming proposed? [Consistency, Research §2, Research §11, Quickstart §1.2]
- [ ] CHK131 Is the signature-verification module location (`transport/signalwire/signature.py`) defined as the single point where verification happens "before any orchestrator hand-off", so the verification choke point is unambiguous and auditable? [Completeness, Plan §Project Structure, Research §2]

### SQLite CHECK (http_status = 401) ↔ FR-008 reject-with-HTTP-code

- [ ] CHK132 Does the SQLite `CHECK (http_status = 401)` constraint on the `rejected_auth_callbacks` table (Data-Model §3, Contract: rejected-auth-audit-log) enforce FR-008's "reject callbacks that fail authentication with the provider-appropriate HTTP response code" requirement at the schema level so a non-401 row cannot be inserted by any future code path? [Completeness, Data-Model §3, Contract: rejected-auth-audit-log, Spec §FR-008]
- [ ] CHK133 Is the `http_status = 401` schema constraint reconciled with FR-008's softer "provider-appropriate HTTP response code" wording — i.e., is the spec's allowance for any provider-appropriate code narrowed by the plan to exactly 401, and is that narrowing justified by the SignalWire-specific decision in Research §2? [Consistency, Data-Model §3, Spec §FR-008, Research §2, Ambiguity]
- [ ] CHK134 Does the contract test `test_http_status_is_401` (Contract: rejected-auth-audit-log) explicitly exercise the CHECK constraint (insertion attempt with non-401 fails) so the schema-level enforcement is measurable, not just declared? [Measurability, Contract: rejected-auth-audit-log]
- [ ] CHK135 Is the run report's `rejected_auth_callbacks_count` (Research §9) defined as a pure-count derivation from rows where `http_status = 401` — i.e., the count cannot inadvertently include non-rejection rows because the CHECK constraint precludes them? [Consistency, Research §9, Data-Model §3, Contract: rejected-auth-audit-log]

### Per-session JSONL coverage + `artifacts/_unassociated/` fallback

- [ ] CHK136 Does the plan define `artifacts/<session_id>/rejected_auth_callbacks.jsonl` (Data-Model §4, Research §10, Contract: rejected-auth-audit-log) AND the `artifacts/_unassociated/rejected_auth_callbacks.jsonl` fallback as jointly covering every callback-not-matchable-to-session case so no rejected callback is ever silently dropped? [Completeness, Data-Model §4, Contract: rejected-auth-audit-log, Research §10]
- [ ] CHK137 Is the rule for when a callback is "unassociatable" (i.e., `session_id IS NULL`) defined precisely enough to be testable — e.g., signature fails AND no session-id parameter can be recovered from the callback URL path or headers (Contract: rejected-auth-audit-log #7)? [Measurability, Contract: rejected-auth-audit-log, Gap]
- [ ] CHK138 Does the contract test `test_unassociated_callback_session_id_null` (Contract: rejected-auth-audit-log) verify that the `_unassociated/` directory is created on demand and that the JSONL file there has the same schema as the per-session file? [Completeness, Contract: rejected-auth-audit-log]
- [ ] CHK139 Is the run report's `rejected_auth_callbacks_count` defined for unassociatable rows — i.e., does an unassociatable rejection appear in any session's run report, or is it only countable in aggregate across the `_unassociated/` directory (potential surfacing gap)? [Clarity, Research §9, Contract: rejected-auth-audit-log, Gap]
- [ ] CHK140 Is the `_unassociated/` directory's retention policy stated consistent with the FR-034 / Slice 2 §11 ≥90-day local-artifact retention floor (re-used per Research §14) so unassociatable forgery attempts are not retained for a shorter window than associated ones? [Consistency, Research §14, Spec §FR-034, Gap]

### Schema-bounded row shape (`received_at, source_metadata, http_status`)

- [ ] CHK141 Is the rejected-auth row schema strictly bounded to `(received_at, source_metadata, http_status)` plus a nullable `session_id` (Data-Model §1.4, Contract: rejected-auth-audit-log) so the column set excludes any path through which the body or a secret could be persisted (re-validates Round 2 CHK126 against the plan)? [Completeness, Data-Model §1.4, Contract: rejected-auth-audit-log, Spec §FR-008]
- [ ] CHK142 Is the `source_metadata` field constrained (Contract: rejected-auth-audit-log Required Behavior #3, Data-Model §1.4) to provider-supplied source identifiers / IP-level metadata only, so it cannot be used as a back-channel for raw header / cookie content that may carry authentication material? [Completeness, Contract: rejected-auth-audit-log, Data-Model §1.4, Gap]
- [ ] CHK143 Does the `source_metadata` schema in the plan specify an upper bound on field count or value size so a hostile sender cannot stuff secrets into provider-supplied source metadata that then lands in the audit log (defense-in-depth parallel to no-body)? [Measurability, Contract: rejected-auth-audit-log, Data-Model §1.4, Gap]
- [ ] CHK144 Is the JSONL on-disk shape (Contract: rejected-auth-audit-log "File format") byte-for-byte aligned with the SQLite column set (Data-Model §3) — i.e., the JSONL has no field absent from SQLite and SQLite has no column absent from JSONL (other than auto-increment id) so the dual-store cannot diverge silently? [Consistency, Data-Model §3, Contract: rejected-auth-audit-log]

### Defense-in-depth: no body content (Contract: rejected-auth-audit-log #4)

- [ ] CHK145 Is the "even if the body would not contain a secret, storing it risks reflected-payload leakage" rationale (Contract: rejected-auth-audit-log Required Behavior #4) reflected in the SQLite table schema (Data-Model §3) — i.e., the table has zero columns capable of holding the callback body, not just a documented prohibition? [Completeness, Data-Model §3, Contract: rejected-auth-audit-log]
- [ ] CHK146 Does the contract test `test_schema_excludes_secret_and_body` (Contract: rejected-auth-audit-log) test for BOTH the verification secret AND a body-content fixture, so the prohibition is enforced for both classes (parallels SC-018)? [Measurability, Contract: rejected-auth-audit-log, Spec §SC-018]
- [ ] CHK147 Is the no-body rule cross-referenced from the orchestrator-level callback handler description (Data-Model §6 "on each callback: verify signature → fail: log to RejectedAuthCallbackLog... no orch hand-off") so the body never even enters orchestrator memory after a signature failure? [Consistency, Data-Model §6, Contract: rejected-auth-audit-log, Gap]
- [ ] CHK148 Does the plan specify that the in-process callback receiver (Research §1, FastAPI ASGI) drops the request body buffer immediately on signature failure so a memory dump would not retain the body — or is that property implicit and untestable? [Measurability, Research §1, Contract: rejected-auth-audit-log, Gap]

### `count_for_session` O(1) ↔ run_report surfacing

- [ ] CHK149 Does the SQLite mirror's `idx_rejected_auth_session` index (Data-Model §3, Contract: rejected-auth-audit-log "SQLite mirror") enable the O(1) / O(log N) `count_for_session` query that the run-report builder requires per FR-036, so the surfacing requirement is not silently O(file-line-count)? [Measurability, Data-Model §3, Contract: rejected-auth-audit-log, Research §9]
- [ ] CHK150 Does the contract test `test_count_for_session_matches_jsonl` (Contract: rejected-auth-audit-log) cross-check the SQLite-derived count against the JSONL line count so the dual-store integrity is testable on every contract run? [Measurability, Contract: rejected-auth-audit-log]
- [ ] CHK151 Is the run-report field name `rejected_auth_callbacks_count` (Research §9) used consistently in Data-Model §1.10 ("rejected_auth_callbacks_count": int) and Contract: rejected-auth-audit-log Required Behavior #5 so no alternative field name appears in any plan-side artifact? [Consistency, Research §9, Data-Model §1.10, Contract: rejected-auth-audit-log]

### Credential handling: env-vars-only (Research §1, §3, §4, §11) ↔ FR-035

- [ ] CHK152 Are SignalWire credentials (`SIGNALWIRE_PROJECT_ID`, `SIGNALWIRE_API_TOKEN`, `SIGNALWIRE_SIGNING_SECRET`), real-time AI provider credentials (`SLICE3_REALTIME_API_KEY`), and shadow STT credentials (`SLICE3_SHADOW_STT_API_KEY`) defined as env-var-only in Research §11 and quickstart.md §1.2 with no TOML / config-file path proposed (preserves FR-035)? [Consistency, Research §11, Quickstart §1.2, Spec §FR-035]
- [ ] CHK153 Does Research §11 explicitly prohibit secrets in `config/slice3.toml` ("Alternatives rejected: secrets in TOML (forbidden)") so a future deployment cannot rationalize moving a credential into the non-secret config? [Completeness, Research §11, Spec §FR-035]
- [ ] CHK154 Is the env-vars-only rule preserved for the `httpx` callback-verification side channel (Research §1) — i.e., the signing secret is loaded from env at module init, never read from disk or passed via argv? [Completeness, Research §1, Research §2, Spec §FR-035, Gap]
- [ ] CHK155 Does the `RealtimeProviderSession` schema (Data-Model §1.12) explicitly exclude credential strings ("MUST NOT contain credentials") and is that exclusion testable via the contract test `test_runtime_identity_recorded_no_credentials` (Contract: pipecat-runtime)? [Measurability, Data-Model §1.12, Contract: pipecat-runtime, Spec §FR-035]

### Operator identity local-only invariant (Plan §Constraints, FR-016, Round 2 Q12)

- [ ] CHK156 Is the operator-identity local-only invariant (Plan §Constraints "Operator identity captured locally only; not propagated to Dataverse") preserved by the Pipecat runtime contract — i.e., the `RealtimeProviderSession` identity property (Contract: pipecat-runtime) records `{runtime_name, runtime_version, provider_name, model_name, model_version}` but NO operator identifier (re-validates Round 2 CHK107–CHK108 against the plan)? [Consistency, Plan §Constraints, Contract: pipecat-runtime, Data-Model §1.12]
- [ ] CHK157 Does the `Session.operator_identity_current` / `Session.operator_identity_original` SQLite column set (Data-Model §3) confirm the local-only invariant — i.e., these columns exist in `opencloser.db` but NO equivalent field exists in the Slice 2 Dataverse mapping artifact reuse statement (Plan §Technical Context "CRM target")? [Consistency, Data-Model §3, Plan §Technical Context]
- [ ] CHK158 Is the `PhoneCallActivityPayload` extension (Data-Model §2.3) explicit that "No new Dataverse field is added by Slice 3 for operator identity" so a reader cannot misread the renamed `provider_call_id` addition as also adding an operator field? [Completeness, Data-Model §2.3, Spec §FR-016]

### Redaction pre-write across 4 artifact types (Data-Model §2.5 + FR-033 + Q11)

- [ ] CHK159 Does the redaction layer's pre-write pass (Data-Model §2.5, Plan §Project Structure `redaction/layer.py`) cover all four artifact classes — full transcript + session-result summary + shadow STT transcript + shadow STT discrepancy records — consistently across plan.md, contracts/pipecat-runtime.md #4, contracts/shadow-stt-lane.md #7, and quickstart.md §1.3 redaction policy? [Consistency, Data-Model §2.5, Contract: pipecat-runtime, Contract: shadow-stt-lane, Quickstart §1.3]
- [ ] CHK160 Is the redaction-BEFORE-write ordering stated identically across the four artifact types so a reader cannot infer one is best-effort while another is hard sequencing (re-validates Round 2 CHK101 against contracts)? [Consistency, Data-Model §2.5, Contract: pipecat-runtime, Contract: shadow-stt-lane]
- [ ] CHK161 Does the PHI tag-and-redact pre-write step (Data-Model §2.5, Contract: pipecat-runtime #4) run as a "special-case pre-write step on the four artifact types above whenever a session's persona has emitted a `phi_collection_risk` escalation event" — and is the trigger condition (emission of `phi_collection_risk`) defined consistently in the persona module location (Plan §Project Structure `persona/extraction.py` "PHI-volunteered handling per Round 2 Q11")? [Consistency, Data-Model §2.5, Contract: pipecat-runtime, Plan §Project Structure]
- [ ] CHK162 Is the transcript-pointer-exclusion rule (Data-Model §2.5 "Excluded ... transcript pointer metadata") preserved by the redaction layer's pre-write pass across all four artifact types — i.e., shadow transcript pointers and discrepancy-record pointers are also exempt, parallel to live transcript pointers? [Consistency, Data-Model §2.5, Spec §FR-033]
- [ ] CHK163 Does the plan confirm that the redaction layer's coverage of shadow STT discrepancy records (Data-Model §2.5, §1.7) applies to BOTH the `live_value` AND the `shadow_value` columns so the discrepancy record cannot be a side channel (re-validates Round 2 CHK098 against the plan)? [Completeness, Data-Model §1.7, Data-Model §2.5, Contract: shadow-stt-lane]
- [ ] CHK164 Is the redaction coverage stated to apply on the resume path — i.e., a resume invocation that rewrites or appends to any of the four artifact types still applies the same redaction-before-write ordering (re-validates Round 2 CHK106 against the plan-side resume flow Data-Model §6)? [Consistency, Data-Model §6, Spec §FR-022, Spec §FR-033, Gap]

### Cross-cutting plan-side consistency

- [ ] CHK165 Is the FastAPI ASGI callback receiver (Research §1) confined to real-call / write-enabled mode ("rehearsal mode does not bind a port") so the rejected-auth attack surface is closed in rehearsal — re-validates Round 1 rehearsal-mode no-mutation invariant against the plan? [Completeness, Research §1, Spec §FR-002]
- [ ] CHK166 Does the plan define the SignalWire callback URL templates (`status_callback_url_template`, `media_callback_url_template`) in Quickstart §1.3 with `{session_id}` interpolation so signature-mismatched callbacks against URLs that don't match the templated shape can be classified as unassociatable without exposing other session IDs? [Clarity, Quickstart §1.3, Research §1, Gap]
- [ ] CHK167 Is the SC-018 no-secrets / no-sensitive-content release-gate measurement (referenced by `test_no_secrets_in_artifact_files` in Contract: rejected-auth-audit-log) defined in terms that cover the new `rejected_auth_callbacks.jsonl` and `_unassociated/rejected_auth_callbacks.jsonl` paths so a future artifact-class addition cannot bypass the gate? [Consistency, Contract: rejected-auth-audit-log, Spec §SC-018, Gap]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate language that may need tightening before plan / implementation.
- ≥80% of items reference a spec section or a quality marker for traceability.
