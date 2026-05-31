# Telephony Readiness Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the pre-dial telephony readiness gate before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Readiness-Check Enumeration

- [ ] CHK001 Are all eight readiness checks (SignalWire credentials, source caller-ID, destination phone, callback URLs, campaign-to-persona/runtime mapping, verified Dataverse mapping, callback/review Task owner mapping, eligibility) enumerated in FR-009 in a single authoritative list? [Completeness, Spec §FR-009]
- [ ] CHK002 Is the readiness-check list in the "Telephony readiness check" definition identical (same set, same wording) to the list in FR-009? [Consistency, Spec §Definitions, Spec §FR-009]
- [ ] CHK003 Is the readiness-check list in User Story 3 Independent Test identical to the list in FR-009 (categories (a)–(h))? [Consistency, Spec §User Story 3, Spec §FR-009]
- [ ] CHK004 Are the eight readiness checks individually testable as distinct failure categories (no two collapsed into one)? [Measurability, Spec §FR-009, Spec §User Story 3]
- [ ] CHK005 Does the spec identify a source of truth for the "campaign-to-persona/runtime mapping" check (configuration file, CLI argument, Dataverse field, or other)? [Gap, Spec §FR-009]
- [ ] CHK006 Does the spec define what "SignalWire credentials present and validatable" means in terms of validatability (e.g., format-only vs. live API probe vs. either)? [Ambiguity, Spec §FR-009]
- [ ] CHK007 Does the spec define what "configured source caller-ID number authorized for outbound dialing" means in terms of authorization (provider-side authorization check vs. local allowlist vs. either)? [Ambiguity, Spec §FR-009]
- [ ] CHK008 Does the spec specify when callback-URL reachability MUST be verified versus when "configured" alone is sufficient (the "reachable when reachability is verifiable in the deployment" caveat)? [Ambiguity, Spec §FR-009]
- [ ] CHK009 Does the spec define what "callback and review Task owner/team mapping resolved" means (presence-only vs. live Dynamics owner lookup vs. either)? [Ambiguity, Spec §FR-009]
- [ ] CHK010 Are the "six Slice 1 eligibility rules" referenced in FR-009 enumerated or unambiguously cross-referenced so a reader can identify all six? [Completeness, Spec §FR-009, Spec §FR-019]
- [ ] CHK011 Is the readiness check defined as occurring before every real-call / write-enabled dial (not once per process / not once per session-start) so the suspension-mid-run edge case in the Edge Cases section is well-defined? [Consistency, Spec §FR-009, Spec §Edge Cases]
- [ ] CHK012 Does the spec state whether the eight readiness checks have a defined ordering, or whether they may run in parallel and report all failures together? [Gap, Spec §FR-009, Spec §FR-011]
- [ ] CHK013 Are the checks distinguishable from the rehearsal/readiness-mode verification list in FR-002 (which mentions Dataverse mapping, SignalWire telephony readiness, destination phone format, persona/runtime configuration, eligibility, planned dial plan, write-back payloads) for completeness parity? [Consistency, Spec §FR-002, Spec §FR-009]
- [ ] CHK014 Does the spec name the "verified Dataverse mapping" check as the Slice 2 live verification gate (not the one-time discovery), so the check is unambiguous? [Consistency, Spec §FR-009, Spec §FR-020]

## Per-Check Failure Semantics

- [ ] CHK015 Does FR-011 enumerate the four required no-side-effects guarantees on any readiness failure (no dial, no attempt, no Phone Call activity, no advance beyond approved blocked-status write or unchanged for non-eligibility failures)? [Completeness, Spec §FR-011]
- [ ] CHK016 Is the same four-guarantee set repeated identically in the "Telephony readiness failure" definition? [Consistency, Spec §Definitions, Spec §FR-011]
- [ ] CHK017 Is the same four-guarantee set repeated identically in User Story 3's narrative and Independent Test? [Consistency, Spec §User Story 3, Spec §FR-011]
- [ ] CHK018 Does the spec distinguish "advance to approved blocked-status write" (eligibility-block case) from "leave queue unchanged" (non-eligibility readiness failures) so the right Dataverse side-effect can be selected per failure category? [Clarity, Spec §FR-011, Spec §User Story 3 #5, Spec §FR-023]
- [ ] CHK019 Is the eligibility-block path's allowed-side-effects set (blocked / status / error field writes only — no Phone Call activity, no Task, no attempt increment) consistent with FR-023? [Consistency, Spec §User Story 3 #5, Spec §FR-023]
- [ ] CHK020 Does FR-009 / FR-011 specify whether a readiness failure produces the `blocked` disposition (and which `blocked_reason`) or a different finalization, for each of the eight categories? [Gap, Spec §FR-009, Spec §FR-011, Spec §FR-017]
- [ ] CHK021 Does the spec require that the readiness failure exit happens "before the dial" with no ambiguity about partial-dial intermediate states (e.g., SignalWire request in-flight at exit time)? [Clarity, Spec §FR-011, Spec §FR-012]
- [ ] CHK022 Are each of the eight readiness-failure categories represented by an acceptance scenario in User Story 3 (CHK enumeration → scenario coverage)? [Coverage, Spec §User Story 3, Spec §FR-009]
- [ ] CHK023 Does the spec define whether multiple simultaneous readiness failures produce a single combined report or fail-fast on the first failing check? [Gap, Spec §FR-009, Spec §FR-011]
- [ ] CHK024 Is the operator-visibility requirement for the failing check name uniform across FR-011, the "Telephony readiness failure" definition, and User Story 3 Independent Test? [Consistency, Spec §FR-011, Spec §Definitions, Spec §User Story 3]

## Uniform "No Dial / No Attempt / No Activity / No Advance" Guarantees

- [ ] CHK025 Is the no-attempt-consumed guarantee on readiness failure stated in FR-011, FR-025, the "Attempt consumed (Slice 3)" definition, and the "Telephony readiness failure" definition with the same meaning? [Consistency, Spec §FR-011, Spec §FR-025, Spec §Definitions]
- [ ] CHK026 Does FR-025 enumerate every condition that MUST NOT increment the attempt count (rehearsal mode, flag absence, readiness failure, phone validation failure, Dataverse-unreachable-at-start, provider-rejected dial, malformed dial-plan / persona-runtime configuration, duplicate callbacks)? [Completeness, Spec §FR-025]
- [ ] CHK027 Is the FR-025 not-incremented list consistent with the "Attempt consumed (Slice 3)" definition's not-incremented list (same items, no drift)? [Consistency, Spec §FR-025, Spec §Definitions]
- [ ] CHK028 Is the no-Phone-Call-activity guarantee on readiness failure stated identically in FR-011, the "Telephony readiness failure" definition, the "Real-dial phone-number validation" definition, and User Story 3? [Consistency, Spec §FR-011, Spec §Definitions, Spec §User Story 3]
- [ ] CHK029 Is the no-dial guarantee phrased so it covers both "no SignalWire HTTP request to place a call" and "no provider call ID assigned" (so the attempt-counter / activity guarantees follow)? [Clarity, Spec §FR-011, Spec §FR-006, Spec §FR-025]
- [ ] CHK030 Does SC-010 quantify the readiness-failure guarantees with 100% / 0% so they are measurable? [Measurability, Spec §SC-010]
- [ ] CHK031 Does SC-010's failure category list match FR-009's check list (so the success criterion does not under-cover the readiness gate)? [Consistency, Spec §SC-010, Spec §FR-009]
- [ ] CHK032 Are the no-advance / no-write guarantees consistent between FR-011 and the rehearsal-mode "creates or updates zero Dataverse records" guarantee in FR-002 / SC-002 for the readiness-failure path? [Consistency, Spec §FR-002, Spec §FR-011, Spec §SC-002]
- [ ] CHK033 Does the spec require that the readiness gate runs even in rehearsal/readiness mode (so an operator catches the failure before promoting to real-call), and is that requirement explicit? [Completeness, Spec §FR-002, Spec §FR-009]

## Readiness-Report Field Requirements

- [ ] CHK034 Does the Telephony Readiness Report key entity enumerate every required field (per-check result for all eight checks)? [Completeness, Spec §Key Entities — Telephony Readiness Report]
- [ ] CHK035 Does the readiness report MUST name the failing check on every failure category (FR-011, "Telephony readiness failure" definition, and User Story 3)? [Consistency, Spec §FR-011, Spec §Definitions, Spec §User Story 3]
- [ ] CHK036 Does FR-036 (run report) require that the failing readiness check / block reason appears on the operator-readable run report? [Completeness, Spec §FR-036]
- [ ] CHK037 Is the telephony readiness summary required on the Slice 3 Run Report key entity in addition to the standalone Telephony Readiness Report? [Consistency, Spec §Key Entities — Run Report, Spec §Key Entities — Telephony Readiness Report]
- [ ] CHK038 Does the spec define whether the readiness report is produced on every run (real-call AND rehearsal) or only when failures occur? [Ambiguity, Spec §FR-002, Spec §FR-011, Spec §Key Entities — Telephony Readiness Report]
- [ ] CHK039 Does the spec require that the report identifies the failing check by a stable machine-parseable identifier (so downstream tooling can branch on category) rather than only a human-readable string? [Gap, Spec §FR-011, Spec §FR-036]
- [ ] CHK040 Does FR-036 require the readiness summary to include the per-check status for passes as well as failures (full audit) or only failures? [Ambiguity, Spec §FR-036, Spec §Key Entities — Telephony Readiness Report]
- [ ] CHK041 Does the readiness report exclude secrets per FR-035 (e.g., a "SignalWire credentials present" check MUST NOT print the credential value)? [Consistency, Spec §FR-011, Spec §FR-035]

## E.164 / Provider-Acceptable Validation

- [ ] CHK042 Is real-dial phone-number validation defined identically as a hard pre-dial block in FR-010, the "Real-dial phone-number validation" definition, the Edge Cases ("Real-dial phone-number validation failure" entry), and User Story 3 #3? [Consistency, Spec §FR-010, Spec §Definitions, Spec §Edge Cases, Spec §User Story 3 #3]
- [ ] CHK043 Does FR-010 explicitly state that this validation supersedes / promotes the Slice 2 non-E.164 data-quality warning (no ambiguity that the prior behavior is retained)? [Clarity, Spec §FR-010, Spec §Assumptions — "Hard E.164 validation"]
- [ ] CHK044 Are "E.164" and "provider-acceptable equivalent" defined or scoped (e.g., does provider-acceptable widen the rule, narrow it, or just permit SignalWire-equivalent normalization)? [Ambiguity, Spec §FR-010, Spec §Definitions]
- [ ] CHK045 Does the spec enumerate the three failure shapes (missing, blank, malformed) explicitly so the validator's coverage is unambiguous? [Completeness, Spec §FR-010, Spec §Definitions, Spec §Edge Cases]
- [ ] CHK046 Is the validation requirement enforced in rehearsal mode (User Story 2 #4: phone-format failure surfaced in readiness report) consistent with the real-call hard-block requirement (FR-010, User Story 3 #3)? [Consistency, Spec §User Story 2 #4, Spec §User Story 3 #3, Spec §FR-010]
- [ ] CHK047 Does SC-009 quantify the phone-validation guarantee as 100% blocked with 0 attempts consumed and 0 Phone Call activities created? [Measurability, Spec §SC-009]
- [ ] CHK048 Does the spec require that the readiness report names "phone-format failure" specifically (so the operator can distinguish it from a generic readiness failure)? [Clarity, Spec §FR-010, Spec §User Story 3 #3, Spec §Edge Cases]
- [ ] CHK049 Does the spec address whether the destination phone number is read from the Dataverse queue item only, or whether operator override is supported (which would change the validation surface)? [Gap, Spec §FR-009, Spec §FR-010]
- [ ] CHK050 Is the phone-validation failure category clearly listed as one of FR-009's eight readiness checks (item (c)) so it inherits the uniform failure semantics? [Consistency, Spec §FR-009, Spec §FR-010, Spec §FR-011]

## Provider-Rejected Dial

- [ ] CHK051 Does FR-012 define a distinct provider-rejected-dial failure category (not folded into general readiness failure)? [Clarity, Spec §FR-012]
- [ ] CHK052 Does FR-012 enumerate the same no-side-effects guarantees (no attempt consumed, no Phone Call activity created) as the readiness-failure path? [Consistency, Spec §FR-011, Spec §FR-012]
- [ ] CHK053 Does FR-012 specify that the provider-rejected-dial outcome MUST advance the Dataverse queue per the per-disposition mapping for blocked / failed cases (not "no advance" like non-eligibility readiness failures)? [Clarity, Spec §FR-012]
- [ ] CHK054 Is the provider-rejected-dial outcome's distinction from telephony readiness failure (post-pre-dial check but pre-call-placement) stated unambiguously? [Clarity, Spec §FR-011, Spec §FR-012]
- [ ] CHK055 Is the provider-rejected-dial behavior in FR-012 consistent with the Edge Case entry "Provider 4xx on dial request"? [Consistency, Spec §FR-012, Spec §Edge Cases]
- [ ] CHK056 Does FR-025 explicitly include "provider-rejected dial requests" in the not-incremented list (so attempt-count semantics align with FR-012)? [Consistency, Spec §FR-012, Spec §FR-025]
- [ ] CHK057 Does the spec require that provider-rejected-dial outcomes are recorded in the run report as a distinct failure type (per FR-012's "recorded in the run report as a provider-rejected-dial failure")? [Completeness, Spec §FR-012, Spec §FR-036]
- [ ] CHK058 Does the spec define what "4xx" / "invalid / blocked / unauthorized" provider responses qualify for FR-012 vs. responses that should be treated as transient (and thus retryable)? [Ambiguity, Spec §FR-012, Spec §Edge Cases]
- [ ] CHK059 Does the spec require that the Dataverse advance for provider-rejected-dial cases routes through the same idempotency / write-back contracts as eligibility-block writes (so no duplicate blocked-status transitions can occur)? [Consistency, Spec §FR-012, Spec §FR-021, Spec §FR-023]
- [ ] CHK060 Is the per-disposition mapping for "blocked / failed cases" referenced in FR-012 traceable to an authoritative table (Slice 1 / Slice 2 mapping) the reader can consult? [Traceability, Spec §FR-012, Spec §FR-020]

## Real-Call / Write-Enabled Flag Gate

- [ ] CHK061 Is the real-call / write-enabled flag explicitly defined as a precondition the readiness gate runs after (so flag-absence → rehearsal mode by default, not a readiness "failure")? [Clarity, Spec §FR-001, Spec §FR-002, Spec §User Story 3 #6]
- [ ] CHK062 Does User Story 3 #6 ("invoked without the flag → rehearsal / readiness mode by default; no SignalWire call placed") align with FR-001 / FR-002 / SC-011? [Consistency, Spec §User Story 3 #6, Spec §FR-001, Spec §FR-002, Spec §SC-011]
- [ ] CHK063 Does FR-025 explicitly list "real-call / write-enabled flag absence" as a not-incremented condition? [Consistency, Spec §FR-001, Spec §FR-025]
- [ ] CHK064 Is the relationship between rehearsal-mode failures (User Story 2 #3, #4) and real-call readiness failures (User Story 3) explicit (same checks, same failing-check naming, different mutation posture)? [Consistency, Spec §User Story 2, Spec §User Story 3, Spec §FR-002, Spec §FR-009]

## Live-Suspension and Mid-Run Edge Cases

- [ ] CHK065 Does the Edge Case "SignalWire credentials or source number unauthorized / suspended mid-run" explicitly state that in-flight calls MUST complete (the readiness check MUST NOT terminate a connected call) so the semantics of mid-run readiness are unambiguous? [Clarity, Spec §Edge Cases]
- [ ] CHK066 Does the spec require that the suspension event is recorded on the next pre-dial check rather than acted on immediately, so the "next pre-dial check" timing is unambiguous? [Clarity, Spec §Edge Cases, Spec §FR-009]
- [ ] CHK067 Does the spec address whether the readiness check is exercised on a re-invocation / resume path, or only on a fresh dial (so resume after partial write-back does not re-trigger readiness exit)? [Gap, Spec §FR-009, Spec §FR-022, Spec §User Story 4 #6, #7]
- [ ] CHK068 Is the "status / media callback URL unreachable from SignalWire side" edge case explicitly tied to FR-009 item (d) and FR-011's exit-before-dial behavior? [Consistency, Spec §Edge Cases, Spec §FR-009, Spec §FR-011]

## Scenario Classes

### Primary

- [ ] CHK069 Does the spec cover the primary "all eight readiness checks pass → proceed to dial" scenario (User Story 1 acceptance scenario 1 + SC-001)? [Coverage, Spec §User Story 1 #1, Spec §SC-001]

### Alternate

- [ ] CHK070 Does the spec cover the alternate rehearsal-mode path where readiness passes and produces planned write-back artifacts without dialing (User Story 2 #1, #2)? [Coverage, Spec §User Story 2 #1, Spec §User Story 2 #2]
- [ ] CHK071 Does the spec cover the alternate flag-omitted path where rehearsal mode runs by default and the readiness gate produces a report but no dial (User Story 3 #6 + SC-011)? [Coverage, Spec §User Story 3 #6, Spec §SC-011]

### Exception / Error (each readiness-failure category)

- [ ] CHK072 Does the spec cover the SignalWire credentials missing exception with named failing check and no dial (User Story 3 #2 + FR-009(a))? [Coverage, Spec §User Story 3 #2, Spec §FR-009]
- [ ] CHK073 Does the spec cover the source caller-ID missing/unauthorized exception (User Story 3 #2 + FR-009(b))? [Coverage, Spec §User Story 3 #2, Spec §FR-009]
- [ ] CHK074 Does the spec cover the destination phone missing/blank/non-E.164/provider-rejected-format exception (User Story 3 #3 + FR-009(c) + FR-010)? [Coverage, Spec §User Story 3 #3, Spec §FR-009, Spec §FR-010]
- [ ] CHK075 Does the spec cover the status/media callback URL missing/unreachable exception (User Story 3 #4 + FR-009(d))? [Coverage, Spec §User Story 3 #4, Spec §FR-009]
- [ ] CHK076 Does the spec cover the campaign-to-persona/runtime mapping missing exception (User Story 3 Independent Test (e) + FR-009(e))? [Coverage, Spec §User Story 3, Spec §FR-009]
- [ ] CHK077 Does the spec cover the Dataverse metadata mapping unverified exception (User Story 3 #1 + FR-009(f) + FR-020 live verification)? [Coverage, Spec §User Story 3 #1, Spec §FR-009, Spec §FR-020]
- [ ] CHK078 Does the spec cover the callback / review Task owner mapping missing/invalid exception (User Story 3 Independent Test (g) + FR-009(g))? [Coverage, Spec §User Story 3, Spec §FR-009]
- [ ] CHK079 Does the spec cover the local call-window / DNC / attempt eligibility blocked exception with the `blocked` disposition + `blocked_reason` write (User Story 3 #5 + FR-009(h) + FR-019 + FR-023)? [Coverage, Spec §User Story 3 #5, Spec §FR-009, Spec §FR-019, Spec §FR-023]
- [ ] CHK080 Does the spec cover the provider-rejected dial (4xx) exception as distinct from readiness failure (FR-012 + Edge Cases)? [Coverage, Spec §FR-012, Spec §Edge Cases]

### Recovery

- [ ] CHK081 Does the spec address recovery after a readiness failure (e.g., operator fixes the named failing check and re-runs — is the re-run a fresh readiness pass or does some state persist)? [Gap, Spec §FR-009, Spec §FR-011]
- [ ] CHK082 Does the spec address recovery after a provider-rejected dial (does the queue item remain in a state where re-dialing is possible after the operator corrects the cause, or is it permanently blocked / failed)? [Gap, Spec §FR-012, Spec §FR-023]

### Non-Functional

- [ ] CHK083 Does the spec quantify or scope the time budget for the readiness check (so it does not become a hidden source of run-time latency before every dial)? [Gap, Spec §FR-009, Spec §FR-036]
- [ ] CHK084 Does FR-035 / FR-036 ensure that the readiness report's contents do not leak secrets even when a credentials-check fails (e.g., "credentials missing" message MUST NOT include partial credential material)? [Consistency, Spec §FR-011, Spec §FR-035]
- [ ] CHK085 Does the spec ensure that the readiness check is deterministic across rehearsal and real-call runs (so a passing rehearsal predicts a passing real-call pre-dial check, modulo time-variant inputs like Dataverse metadata drift covered in Edge Cases)? [Consistency, Spec §FR-002, Spec §FR-009, Spec §Edge Cases]
- [ ] CHK086 Does the spec specify operator-visible logging of every readiness check result (not only failures) to support post-incident audit? [Gap, Spec §FR-009, Spec §FR-036, Spec §Key Entities — Telephony Readiness Report]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

### FR-036 telephony_readiness_summary — Run-Report Field Shape

- [ ] CHK087 Is the FR-036 `telephony_readiness_summary` run-report field defined as listing "each readiness check from FR-009 with its result" so the summary's shape is unambiguous? [Completeness, Spec §FR-036] (closes CHK037 — confirms the readiness summary is required on the Run Report key entity)
- [ ] CHK088 Is the format of "each readiness check from FR-009 with its result" defined precisely enough to be machine-parseable (e.g., a structured array of `{check_id, status, message}` records), or is the format left as [Ambiguous]? [Ambiguity, Spec §FR-036, §FR-009] (closes CHK039 partially)
- [ ] CHK089 Does FR-036's `telephony_readiness_summary` include the per-check status for PASSES as well as failures (so the run report is a full audit of all eight checks, not only the failing one)? [Completeness, Spec §FR-036, §FR-009] (closes CHK040)
- [ ] CHK090 Is the FR-036 `telephony_readiness_summary` consistent with the standalone Telephony Readiness Report key entity (i.e., the run-report summary and the standalone artifact contain reconcilable data — same eight checks, same status values, same naming)? [Consistency, Spec §FR-036, §Key Entities — Telephony Readiness Report, §Key Entities — Run Report] (closes CHK037 with the cross-artifact reconciliation lens)
- [ ] CHK091 Is the eligibility check (FR-009 item (h)) in the readiness summary the same shape as checks (a)-(g) — i.e., does the eligibility check produce a single pass/fail status, or does it produce a multi-rule sub-summary (six Slice 1 eligibility rules)? [Ambiguity, Spec §FR-009, §FR-036]
- [ ] CHK092 Are deterministic pass/fail criteria stated for the eligibility check (h) in the readiness summary the same way as the seven non-eligibility checks have deterministic criteria? [Measurability, Spec §FR-009, §FR-019, §FR-036]
- [ ] CHK093 Does the FR-036 readiness summary exclude secrets (consistent with FR-035 / SC-018) even when a credentials-check fails (e.g., the readiness-summary entry for check (a) MUST NOT include partial credential material)? [Consistency, Spec §FR-035, §FR-036] (closes CHK084 for the run-report variant)
- [ ] CHK094 Is the FR-036 `telephony_readiness_summary` required on EVERY Slice 3 invocation (real-call AND rehearsal) so an operator inspecting the run report always sees the full readiness picture? [Consistency, Spec §FR-036, §FR-002] (closes CHK038)

### Q13 Real-Call Flag on Resume — Readiness Check Behavior

- [ ] CHK095 Does the spec define whether a resume invocation re-runs the FR-009 telephony readiness check, or whether the readiness check is bypassed because the original call already happened (and the resume only completes missing CRM writes)? [Gap, Spec §FR-009, §FR-022, §FR-026] (closes CHK067)
- [ ] CHK096 If a resume re-runs the readiness check, does the spec define which subset of the eight FR-009 checks apply (e.g., Dataverse mapping check (f) and callback owner mapping (g) still matter for write-back; SignalWire credentials (a) / source caller-ID (b) / destination phone (c) / callback URLs (d) may not apply because no further dial occurs)? [Completeness, Gap, Spec §FR-009, §FR-022]
- [ ] CHK097 Is the resume-path readiness behavior consistent across (i) a session that connected but write-back failed (no re-dial needed), (ii) a session that received `answered` but no terminal event (resume immediately finalizes as `failed` / `live_call_abandonment` per Q6), and (iii) a session that never dialed (resume should never apply because no attempt was consumed)? [Consistency, Spec §FR-022, §FR-026]
- [ ] CHK098 Does the spec require the resume invocation's readiness behavior to be operator-visible in the run report (i.e., does the run report show which readiness checks were re-run, skipped, or bypassed on a resume)? [Completeness, Gap, Spec §FR-022, §FR-036]
- [ ] CHK099 Is the resume-invocation real-call / write-enabled flag check (per FR-001 / FR-022 / Q13) ordered relative to the FR-009 readiness check on a resume (i.e., does the flag check happen first, so a rehearsal-mode resume never invokes any readiness check that would attempt a live probe)? [Consistency, Gap, Spec §FR-001, §FR-009, §FR-022]
- [ ] CHK100 Does the spec address whether a Dataverse-unreachable failure detected on a resume invocation is reported as a telephony readiness failure (FR-009 item (f)) or as a separate resume-failure category? [Ambiguity, Spec §FR-009, §FR-022, §FR-025]

### Q9 Auth-Rejected Callback — Readiness Check Coverage

- [ ] CHK101 Does the spec define whether the FR-009 item (d) "status / media callback URL reachable" readiness check is related to or independent of "callback authentication mechanism configured" (FR-008) — i.e., is callback-URL reachability a separate concept from callback-signature-verification configurability? [Ambiguity, Gap, Spec §FR-008, §FR-009]
- [ ] CHK102 Should "callback authentication configured" be added as a NINTH readiness check in FR-009 (so the pre-dial gate verifies that the signature-verification mechanism is wired before allowing a dial that will generate authenticatable callbacks)? [Gap, Spec §FR-008, §FR-009]
- [ ] CHK103 If callback authentication is NOT a separate readiness check, does the spec state that callback authentication failures are detected only at callback time (FR-008) rather than at pre-dial, and is this operator-acceptable for the security posture? [Clarity, Gap, Spec §FR-008, §FR-009]
- [ ] CHK104 Does the FR-036 `telephony_readiness_summary` include a callback-authentication-readiness entry when callback authentication is a configuration the operator can verify pre-dial (e.g., the verification secret is present in deployment configuration)? [Completeness, Gap, Spec §FR-008, §FR-009, §FR-036]
- [ ] CHK105 Is the relationship between FR-009 item (d) (callback URL reachability) and the FR-008 rejected-by-authentication audit log defined (i.e., a callback URL that is reachable but does NOT authenticate produces a rejected-by-auth row — is this the only place that distinction is drawn)? [Consistency, Spec §FR-008, §FR-009]
- [ ] CHK106 Does the spec require the FR-036 readiness summary to be consistent with the FR-008 rejected-by-authentication count on the same run report (e.g., if callback-URL readiness passes pre-dial but every callback authenticates as rejected post-dial, are both numbers visible to the operator)? [Consistency, Spec §FR-008, §FR-036]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Data-model §1.9 nine-check enumeration vs. FR-009 readiness categories

- [ ] CHK107 Does the data-model §1.9 `TelephonyReadinessReport.check_name` enum's nine values (`signalwire_credentials`, `source_caller_id_authorized`, `destination_phone_e164`, `status_callback_url_configured`, `media_callback_url_configured`, `campaign_persona_runtime_mapping`, `dataverse_metadata_verified`, `task_owner_mapping_resolved`, `eligibility`) cover every FR-009 readiness category one-to-one (FR-009 enumerates eight categories (a)-(h); the data-model splits the FR-009 (d) "status / media callback URL" into two enum values, yielding nine — is this split intentional and traceable)? [Completeness, Consistency, Spec §FR-009, Data-Model §1.9] (re-validates CHK101 against the data-model split)
- [ ] CHK108 Is the data-model §1.9 split of FR-009 (d) into `status_callback_url_configured` AND `media_callback_url_configured` consistent with the contracts/cli-slice3.md "Required readiness checks before any dial" list (which also splits the URLs) and the quickstart §8 remedy table (which also lists both URLs as separate rows)? [Consistency, Spec §FR-009, Data-Model §1.9, Contract: cli-slice3, Quickstart §8]
- [ ] CHK109 Is the data-model §1.9 enum's omission of any "signalwire_signature_secret_present" / "callback_authentication_configured" entry consistent with research §11's `SIGNALWIRE_SIGNING_SECRET` env-var-only posture and CHK102's open question of whether a NINTH (now TENTH) readiness check should exist? [Gap, Ambiguity, Spec §FR-008, §FR-009, Research §11, Data-Model §1.9] (re-validates CHK102/CHK104 against the plan)
- [ ] CHK110 Does the data-model §1.9 nine-check enum traceably cover the `campaign_persona_runtime_mapping` check named in the plan's `slice3/readiness.py` (Project Structure), and is the mapping check's reuse of the Slice 2 mapping artifact (research §14) documented as the source of truth (i.e., the readiness check verifies the Slice 2 artifact has a persona/runtime entry for the campaign)? [Traceability, Consistency, Plan §Project Structure, Research §14, Data-Model §1.9]

### Quickstart §8 remedy table vs. FR-009 nine-check coverage

- [ ] CHK111 Does the quickstart §8 "Common readiness failures and remedies" table contain exactly one row for each of the nine data-model §1.9 enum values (i.e., does the operator-facing remedy table have full coverage of the readiness enum so any pass/fail row in `telephony_readiness.json` has a remedy entry)? [Completeness, Consistency, Quickstart §8, Data-Model §1.9]
- [ ] CHK112 Is the quickstart §8 row for `eligibility` ("This is the expected blocked-status outcome; no remediation needed") consistent with the FR-019 / FR-023 blocked-status write behavior, and is it distinguishable in the run report from a configuration / wiring readiness failure that DOES require remediation? [Consistency, Clarity, Spec §FR-019, §FR-023, Quickstart §8] (re-validates CHK091)
- [ ] CHK113 Does the quickstart §8 remedy table list a remedy for a hypothetical TENTH check (callback-authentication readiness — CHK102/CHK109), or does its absence confirm the plan's decision to detect auth failures only at callback time per FR-008? [Gap, Ambiguity, Spec §FR-008, §FR-009, Quickstart §8, Research §2]

### Contracts/cli-slice3.md exit code 4 mapping to FR-009 checks

- [ ] CHK114 Is the contracts/cli-slice3.md exit code 4 ("Telephony readiness failure") mapped to a specific failure detail in `telephony_readiness.json` (i.e., does the contract guarantee that any of the nine data-model §1.9 checks failing produces exit code 4, with the failing check identifiable from the readiness report)? [Measurability, Consistency, Contract: cli-slice3, Data-Model §1.9, Spec §FR-011]
- [ ] CHK115 Does the contracts/cli-slice3.md test `test_telephony_readiness_failure_exits_with_code_4` assertion "Each FR-009 readiness check individually failing exits with code 4" align with the nine-value data-model §1.9 enum (i.e., are all nine values exercisable or only the eight FR-009 categories)? [Consistency, Contract: cli-slice3, Data-Model §1.9, Spec §FR-009]

### SignalWire signing-secret readiness vs. runtime detection

- [ ] CHK116 Does the plan / research define whether the `SIGNALWIRE_SIGNING_SECRET` env var (research §11) is verified PRESENT as part of the readiness gate (so a missing secret blocks before dial), or whether the secret is only consulted when the first callback arrives (so a missing secret produces a runtime `RejectedAuthCallbackLog` entry on every callback)? [Ambiguity, Gap, Research §2, §11, Data-Model §1.9, Contract: signalwire-transport]
- [ ] CHK117 Is the operator security posture between "secret missing at readiness time → exit code 4 before dial" and "secret missing at callback time → every callback authenticates as rejected, run continues" defined and consistent with the FR-008 Round 2 Q9 forgery-detection requirement? [Consistency, Clarity, Spec §FR-008, Research §2, §11] (extends CHK103)
- [ ] CHK118 Does the contracts/signalwire-transport.md "Signature verification" required-behaviors section reconcile the readiness-time vs. callback-time signing-secret check (the contract names "every inbound callback MUST be HMAC-SHA256-verified" but does not pin whether the SECRET itself is validated as configured at readiness time)? [Gap, Consistency, Contract: signalwire-transport, Research §2]

### Campaign-to-persona/runtime mapping reuse from Slice 2

- [ ] CHK119 Is the plan's `slice3/readiness.py` campaign-to-persona/runtime mapping check tied unambiguously to the Slice 2 `config/dataverse_mapping.json` artifact reuse named in research §14, so a single artifact is the source of truth for both the Dataverse mapping verification (FR-009 (f)) AND the persona/runtime mapping (FR-009 (e))? [Traceability, Consistency, Plan §Project Structure, Research §14, Data-Model §1.9]
- [ ] CHK120 Does the plan / research define what happens when the Slice 2 mapping artifact verifies for Dataverse field shape but is missing the Slice-3-specific persona/runtime entry (i.e., are these two readiness checks decoupled enough that one can pass while the other fails)? [Completeness, Gap, Plan §Project Structure, Research §14, Spec §FR-009]

### Round 2 telephony_readiness_summary cross-validation against new data-model

- [ ] CHK121 Does the data-model §1.10 `RunReport.telephony_readiness_summary` field shape ("array of TelephonyReadinessReport entries") align with the contracts/cli-slice3.md run-report minimum-fields list and the research §9 JSON schema such that all three artifacts describe the same array-of-objects shape with the same keys (`check`, `result`, `detail`)? [Consistency, Data-Model §1.10, Contract: cli-slice3, Research §9]
- [ ] CHK122 Is the rehearsal-mode requirement that `telephony_readiness_summary` appear on EVERY invocation (re-validating CHK094) preserved in the data-model §6 state-transitions section (which shows the readiness report being written in BOTH rehearsal and real-call branches)? [Consistency, Spec §FR-002, §FR-036, Data-Model §6] (re-validates CHK094)

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate the requirement exists but is interpretable in multiple non-trivially-different ways.
- Items marked [Conflict] indicate two parts of the spec disagree on the same requirement.
- CHK087 – CHK106 are Round 2 amendments (2026-05-25) covering: FR-036 telephony_readiness_summary shape, Q13 resume-path readiness behavior, Q9 callback-authentication readiness coverage.
- CHK107 – CHK122 are Round 3 post-plan validation (2026-05-25) covering: data-model §1.9 nine-check enum vs. FR-009 categories, quickstart §8 remedy-table coverage, contracts/cli-slice3.md exit code 4 mapping, SignalWire signing-secret readiness vs. runtime detection, campaign-to-persona/runtime mapping reuse from Slice 2.
- >=80% of items reference a spec section (FR-NNN, SC-NNN, Definitions, Edge Cases, User Story N, or Key Entities) for traceability.
