# Deployment Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the deployment, rollout, rollback, and safety-posture dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Default-Safe-Mode Posture

- [ ] CHK001 Is the default behavior when the real-call / write-enabled flag is omitted explicitly defined as rehearsal / readiness mode (no SignalWire dial, no Dataverse mutation)? [Completeness, Spec §FR-001, §FR-002, §SC-011]
- [ ] CHK002 Is the rehearsal / readiness mode named as the literal default of the CLI (not merely "available" or "supported") in every place a run mode is mentioned? [Consistency, Spec §FR-002, §FR-037, §Assumptions: Default safe mode]
- [ ] CHK003 Does the spec require that absence of the real-call flag blocks BOTH SignalWire dialing AND Dataverse mutation as a single combined gate (not two independent gates with potential drift)? [Consistency, Spec §FR-001, §Definitions: Real-call / write-enabled mode]
- [ ] CHK004 Is the rehearsal-mode-is-default requirement stated as a measurable outcome (i.e., a percentage of runs that omit the flag and stay safe), not only as a behavioral expectation? [Measurability, Spec §SC-011]
- [ ] CHK005 Is the default-safe posture stated in every place where a real-call risk exists — at minimum the run-mode requirements section, telephony readiness, attempt-count semantics, and the operator interface section? [Completeness, Spec §FR-001, §FR-009, §FR-025, §FR-037]
- [ ] CHK006 Is the "equivalent deliberate action" hedge in the real-call flag definition (FR-001) bounded — i.e., does the spec define what counts as an equivalent deliberate action or mark it as deferred to plan? [Ambiguity, Spec §FR-001]
- [ ] CHK007 Does the spec define expected operator-visible output when the rehearsal-default kicks in (so the operator knows the safe default applied)? [Completeness, Spec §FR-002, §FR-036, §SC-011]
- [ ] CHK008 Is the relationship between rehearsal mode and the Slice 2 dry-run default explicitly stated (extension, not replacement)? [Consistency, Spec §FR-001, §FR-002]
- [ ] CHK009 Does the spec explicitly forbid any silent / implicit promotion of a rehearsal run into a real-call run (e.g., on retry, on resume, on callback delivery)? [Gap, Spec §FR-001]
- [ ] CHK010 Is the rehearsal-mode default reaffirmed for the resume-on-re-invocation case (so that a resume of a session originally placed in real-call mode does NOT bypass the flag requirement for a fresh dial)? [Gap, Spec §FR-022]

## Secret Management

- [ ] CHK011 Does the spec enumerate every credential class that must be excluded from logs and artifacts (SignalWire, real-time AI provider, shadow STT provider, Dataverse, any other secret)? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK012 Is the no-secrets-in-artifacts guarantee stated at every place an artifact is produced — at minimum: run report, transcript artifact, callbacks audit log, shadow STT artifact, planned write-back payloads, conflicting-events audit log, session-result artifact? [Completeness, Spec §FR-035, §FR-036, §FR-038, §SC-018]
- [ ] CHK013 Is the secret-exclusion guarantee quantified (0 secrets in artifacts) and made independently verifiable per SC-018? [Measurability, Spec §SC-018]
- [ ] CHK014 Does the spec specify where SignalWire credentials, source caller-ID number, callback URL configuration, and real-time AI provider credentials are configured (deployment configuration surface) or explicitly defer it to plan? [Completeness, Spec §Definitions: Telephony readiness check, §Deferred to Implementation Plan: Telephony adapter details]
- [ ] CHK015 Does the spec state that SignalWire callback authentication secrets (signature-verification keys) MUST NOT be logged, including in the rejected-callback case? [Completeness, Spec §FR-008, §FR-035]
- [ ] CHK016 Is the shadow STT provider credentials class explicitly included in the secret-exclusion guarantee (not merely the live model / SignalWire / Dataverse credentials)? [Completeness, Spec §FR-035, §SC-018]
- [ ] CHK017 Does the spec require that operator identity recording (FR-016) MUST NOT include secrets (e.g., session tokens, API keys), only the OS user or a CLI-provided identifier? [Completeness, Spec §FR-016]
- [ ] CHK018 Does the spec state how secrets are presented at run time without being persisted (e.g., env vars, secret store) or defer the secret-loading surface to plan? [Gap, Spec §Deferred to Implementation Plan: Telephony adapter details]

## Resume & Rollback Contracts

- [ ] CHK019 Is the resume behavior for Slice 3 explicitly defined as reusing Slice 2's resume-on-re-invocation semantics unchanged? [Consistency, Spec §FR-022, User Story 7]
- [ ] CHK020 Does the spec state that a resumed run creates 0 duplicate Phone Call activities, 0 duplicate Tasks, 0 duplicate queue-status transitions, and 0 duplicate attempt-count increments? [Measurability, Spec §FR-022, §SC-008]
- [ ] CHK021 Is the resume contract preserved across the new Slice 3 failure modes (live-call abandonment, orchestrator restart mid-call, persistent SignalWire callback delivery failure)? [Completeness, Spec §FR-026, User Story 7 scenario 4]
- [ ] CHK022 Does the spec require that resume after a real-call session reuses the recorded real provider call ID for correlation (so the resume cannot create a new Phone Call activity by losing the correlation key)? [Completeness, Spec §FR-022, User Story 7 scenario 4]
- [ ] CHK023 Is the resume path explicitly defined for the case where the Phone Call activity write succeeded but the Task creation failed (partial write-back)? [Completeness, Spec §User Story 7 §Independent Test (d), §FR-022]
- [ ] CHK024 Does the spec address whether resume requires the original real-call / write-enabled flag (i.e., is resume itself a write-enabled action requiring the flag)? [Ambiguity, Spec §FR-001, §FR-022]
- [ ] CHK025 Is the "rollback" posture for an already-written-back real call defined — or is it explicitly stated that there is no automated rollback and the queue item progression is forward-only? [Gap, Spec §FR-020, §FR-022]
- [ ] CHK026 Does the spec require that a resume run preserves the operator identity captured on the original session, OR records a separate operator identity for the resume invocation? [Gap, Spec §FR-016]
- [ ] CHK027 Is the conflict-detection rollback behavior (queue item changed by a human between claim and write-back) preserved verbatim from Slice 2? [Consistency, Spec §Edge Cases: CRM queue item changed by a human between claim and write-back]
- [ ] CHK028 Does the spec define how the write-back progress ledger is used to decide which writes are still missing on resume? [Completeness, Spec §Key Entities: Write-Back Progress Ledger, §FR-022]
- [ ] CHK029 Is the resume contract consistent with the no-duplicate guarantees in SC-008 across all enumerated retry / resume cases (transient Dataverse error, callback retry, orchestrator restart, finalized session re-invocation)? [Consistency, Spec §SC-008, §User Story 4, §User Story 7]

## Retention Floor & No-Auto-Delete

- [ ] CHK030 Is the local artifact retention floor explicitly stated (≥ 90 days, or longer when configured) for Slice 3? [Completeness, Spec §Assumptions: Local artifact retention, §FR-022]
- [ ] CHK031 Does the spec explicitly state that the application MUST NOT auto-delete audit artifacts, with pruning being a manual operator action? [Completeness, Spec §Assumptions: Local artifact retention]
- [ ] CHK032 Is the retention floor applied to ALL of: session-result artifact, transcript / transcript pointer, callbacks audit log, conflicting-events audit log, shadow STT artifact, shadow STT discrepancy record, run report, write-back progress ledger? [Completeness, Spec §FR-033, §FR-034, §FR-036, §Assumptions: Local artifact retention]
- [ ] CHK033 Does the spec require that shadow STT discrepancy records are retained even when transcript retention is summary-only? [Completeness, Spec §FR-034]
- [ ] CHK034 Is the relationship between transcript retention mode (full / summary-only / pointer-only) and the no-auto-delete floor explicit (i.e., even pointer-only retention has a floor on the pointer record itself)? [Ambiguity, Spec §FR-033, §FR-034, §Assumptions: Local artifact retention]
- [ ] CHK035 Does the spec define what happens to local artifacts when the deployment-configured retention is shorter than the 90-day floor (the floor wins vs. the configuration wins)? [Ambiguity, Spec §Assumptions: Local artifact retention]
- [ ] CHK036 Is the retention floor stated as a measurable outcome (e.g., percentage of artifacts retained ≥ floor, 0 auto-deletes)? [Measurability, Gap, Spec §Assumptions: Local artifact retention]
- [ ] CHK037 Does the spec require that the retention mode (full / summary-only / pointer-only) is recorded on every session-result artifact for forensic clarity? [Completeness, Spec §FR-033]
- [ ] CHK038 Is default-on transcript redaction (FR-033) preserved as the default across all retention modes that produce a transcript file? [Consistency, Spec §FR-033, §Edge Cases: Default-on redaction applied to a Slice 3 transcript]
- [ ] CHK039 Is the redaction-runs-before-disk requirement stated unambiguously (no transcript artifact reaches disk unredacted when default-on redaction is active)? [Completeness, Spec §FR-033, §Edge Cases: Default-on redaction applied to a Slice 3 transcript]

## Bench Ownership & Exclusion Boundary

- [ ] CHK040 Does the spec explicitly state that Feature 003 is fully owned by `py-bench`? [Completeness, Spec §Bench Owner, §Assumptions: Bench ownership and contract handoff]
- [ ] CHK041 Is Flutter admin-app work, generated Dart client, install-checklist UI, dashboard UI, and tenant-onboarding screen work explicitly excluded from Slice 3? [Completeness, Spec §Constitution Alignment: Thin slice, §Assumptions: Slice scope, §Assumptions: Bench ownership]
- [ ] CHK042 Does the spec state that Feature 003 MUST NOT contain any Flutter implementation tasks? [Completeness, Spec §Assumptions: Bench ownership and contract handoff]
- [ ] CHK043 Is the deferral of Flutter work to Features 004+ in `flutterBench` explicit and identifiable in deployment / rollout planning? [Completeness, Spec §Constitution Alignment: Thin slice, §Assumptions: Bench ownership]
- [ ] CHK044 Does the spec rule out any other UI deliverables (custom openCloser UI, campaign UI, transcript review console, analytics dashboard, replacement CRM task queue) from Slice 3 deployment scope? [Completeness, Spec §Constitution Alignment: CRM control plane, §Assumptions: Slice scope, §FR-038]
- [ ] CHK045 Is the operator surface for Slice 3 deployment unambiguously CLI / API output + local artifacts + Dynamics records (no custom UI)? [Completeness, Spec §Assumptions: Operator surface, §FR-038]
- [ ] CHK046 Does the spec rule out Celery, Redis-as-a-required-dependency, Kubernetes, broad scheduler / batch processing, multi-worker coordination, and distributed job queues as Slice 3 deployment dependencies? [Completeness, Spec §Assumptions: Slice scope]

## Pre-Deploy Verification

- [ ] CHK047 Does the spec require a verified Dataverse mapping (two-phase verification: one-time discovery + lightweight live verification before each write-enabled run) as a pre-deploy / pre-run gate? [Completeness, Spec §FR-020, §FR-009]
- [ ] CHK048 Is the lightweight live Dataverse verification explicitly required before EACH write-enabled run (not only once at deploy time)? [Completeness, Spec §FR-020, §Edge Cases: Dataverse metadata drift detected between rehearsal and real-call run]
- [ ] CHK049 Does the spec require a rehearsal run as a pre-real-call verification step before the operator's first real dial in any deployment? [Gap, Spec §User Story 2]
- [ ] CHK050 Is a pre-pilot demo-evidence checklist named or explicitly deferred to plan? [Gap, Spec §Deferred to Implementation Plan: Test posture for real calls]
- [ ] CHK051 Does the spec define the run-report fields that constitute pre-deploy evidence (run mode, session ID, real provider call ID, persona version, runtime/model identity, per-write-back-operation status, telephony readiness summary, callbacks audit row counts, shadow STT enabled/disabled flag)? [Completeness, Spec §FR-036]
- [ ] CHK052 Is the telephony readiness check explicitly required before EVERY real-call dial (not only at deployment time)? [Completeness, Spec §FR-009, §FR-011]
- [ ] CHK053 Does the spec require that the callback URL reachability check is part of pre-deploy verification when reachability is verifiable in the deployment? [Completeness, Spec §FR-009, §Edge Cases: Status / media callback URL unreachable from SignalWire side]
- [ ] CHK054 Does the spec require pre-deploy verification of source caller-ID authorization for outbound dialing (so an unauthorized number is caught before the first dial)? [Completeness, Spec §FR-009, §Definitions: Telephony readiness check]
- [ ] CHK055 Is the pre-deploy verification surface inspectable without a custom UI (i.e., readiness report + CLI output)? [Consistency, Spec §FR-038, §Key Entities: Telephony Readiness Report]
- [ ] CHK056 Does the spec define how the deployment verifies that the additive `shadow_stt_discrepancy` human-review reason is registered in the Dynamics review-task reason enumeration before going live with shadow STT enabled? [Gap, Spec §FR-031]

## Slice 3 → Slice 4+ Forward-Compatibility Commitment

- [ ] CHK057 Does the spec explicitly state that no Slice 1 or Slice 2 contract is weakened or deleted by Slice 3? [Completeness, Spec §Assumptions: Slice 1 / Slice 2 contracts preserved, §FR-020]
- [ ] CHK058 Are the only sanctioned Slice 1 → Slice 3 boundary amendments enumerated (the three name-only renames + the additive `shadow_stt_discrepancy` reason)? [Completeness, Spec §Assumptions: Slice 1 / Slice 2 contracts preserved, §FR-018]
- [ ] CHK059 Is the Slice 2 retention floor (≥ 90 days) preserved unchanged for Slice 3? [Consistency, Spec §FR-022, §Assumptions: Local artifact retention]
- [ ] CHK060 Is the backwards-compatible call-id correlation for pre-Slice-3 sessions preserved (so pre-Slice-3 audit inspection still works after Slice 3 deploys)? [Completeness, Spec §FR-006, §Assumptions: Backwards-compatible call ID correlation]
- [ ] CHK061 Does the spec define a verification mechanism (contract tests / boundary inspection) for SC-016 forward-compatibility preservation? [Measurability, Spec §SC-016]

## Scenario Class: Primary (Default-Safe Deploy)

- [ ] CHK062 Is the primary deployment scenario (operator deploys, runs in rehearsal mode by default, confirms readiness, then opts into a real-call run) covered by spec text? [Completeness, Spec §User Story 2, §FR-002, §SC-011]
- [ ] CHK063 Is the primary post-deploy demo path (one queue item from `ready` to final disposition with Dynamics write-back) measurable per SC-001? [Measurability, Spec §SC-001]

## Scenario Class: Alternate (Rehearsal-Only Deploy)

- [ ] CHK064 Does the spec support a deployment configuration where shadow STT is disabled and the Slice 3 loop still completes? [Completeness, Spec §FR-032, §User Story 6 scenario 5]
- [ ] CHK065 Does the spec support a deployment configuration where transcript retention is summary-only or pointer-only, with the demonstrable loop preserved? [Completeness, Spec §FR-033, §Edge Cases: Transcript retention is summary-only or pointer-only]

## Scenario Class: Exception / Error (Pre-Dial Block)

- [ ] CHK066 Is every telephony readiness failure category (SignalWire credentials, source number, destination phone format, callback URLs, persona/runtime mapping, Dataverse mapping, callback owner mapping, eligibility) covered as a pre-deploy / pre-dial exception scenario? [Completeness, Spec §FR-009, §User Story 3 §Independent Test (a)-(h)]
- [ ] CHK067 Is the provider-rejected dial case (SignalWire returns 4xx) covered as an exception scenario that consumes no attempt and creates no Phone Call activity? [Completeness, Spec §FR-012, §Edge Cases: Provider 4xx on dial request]
- [ ] CHK068 Is the SignalWire credentials suspended mid-run case covered (next pre-dial check fails, in-flight calls allowed to complete)? [Completeness, Spec §Edge Cases: SignalWire credentials or source number unauthorized / suspended mid-run]

## Scenario Class: Recovery (Partial-Rollback / Resume Semantics)

- [ ] CHK069 Is the orchestrator-restart-between-dial-and-write-back recovery scenario explicitly covered with no-duplicate guarantees? [Completeness, Spec §User Story 7 scenario 4, §FR-022, §SC-008]
- [ ] CHK070 Is the partial write-back case (Phone Call activity succeeded, Task failed) explicitly covered with no-duplicate guarantees on resume? [Completeness, Spec §User Story 7 §Independent Test (d), §FR-022]
- [ ] CHK071 Is the live-call abandonment recovery path (queue item leaves `in_progress` within timeout, no false connected-call activity) covered with measurable outcome (100% per SC-012)? [Measurability, Spec §FR-026, §SC-012]
- [ ] CHK072 Is the conflicting-late callback recovery (callback arrives after disposition finalized) defined to NOT mutate the finalized disposition? [Completeness, Spec §FR-027, §Edge Cases: SignalWire status callback delivered after disposition finalized]
- [ ] CHK073 Does the spec define the operator action required when an in-run retry budget is exhausted (re-invocation reuses the same session — what triggers the operator awareness)? [Completeness, Spec §FR-022, §User Story 4 scenario 7, §FR-036]
- [ ] CHK074 Is the resume path verified for the case where the local audit artifacts are intact but Dynamics is missing one specific write (e.g., the queue-status update)? [Completeness, Spec §FR-022, §User Story 7 scenario 2]

## Scenario Class: Non-Functional (Deployment Safety / Auditability)

- [ ] CHK075 Are the no-duplicate guarantees stated as quantified outcomes (100% / 0) so they are verifiable post-deploy? [Measurability, Spec §SC-008, §SC-012]
- [ ] CHK076 Is auditability of the run report a measurable outcome (operator can explain outcome without reading source code per SC-017)? [Measurability, Spec §SC-017]
- [ ] CHK077 Is the no-secrets-in-artifacts non-functional requirement quantified (0 occurrences per SC-018)? [Measurability, Spec §SC-018]
- [ ] CHK078 Is the deployment-configurability of the live-call abandonment timeout explicitly required (without pinning the default value)? [Completeness, Spec §FR-026, §Assumptions: Live-call abandonment timeout]
- [ ] CHK079 Is the deployment-configurability of the silence-after-connection / no-extraction-event timeout explicitly required (without pinning the default value)? [Completeness, Spec §FR-013]
- [ ] CHK080 Is the deployment-configurability of the shadow STT enable/disable toggle and discrepancy policy explicitly required? [Completeness, Spec §FR-032, §Assumptions: Shadow STT toggle and discrepancy policy]
- [ ] CHK081 Does the spec require that the deployment can disable shadow STT entirely without weakening the demonstrable Slice 3 loop? [Completeness, Spec §FR-032, §User Story 6 scenario 5]
- [ ] CHK082 Is the no-multi-worker-coordination requirement preserved for deployment topology (Slice 3 deploys for single-CLI-invocation per queue item only)? [Completeness, Spec §FR-003, §Assumptions: Slice scope, §Constitution Alignment: Thin slice]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap] or [Ambiguity].

### Real-call flag on every Dataverse-mutating invocation incl. resume (Q13 / FR-001 / FR-022)

- [ ] CHK083 Does FR-022 now explicitly require that EVERY resume re-invocation performing a Dataverse mutation MUST supply the real-call / write-enabled flag, closing the Round 1 CHK024 [Ambiguity]? [Completeness, Spec §FR-022, Spec §FR-001, closes CHK024]
- [ ] CHK084 Is the prohibition on "sticky" or session-inherited promotion of the original invocation's real-call flag explicitly stated for the resume case, closing the Round 1 CHK009 [Gap]? [Completeness, Spec §FR-022, Spec §FR-001, closes CHK009]
- [ ] CHK085 Is the resume-without-flag behavior (resume runs in rehearsal / readiness mode, no Dataverse mutation, surfaces what would have been written) defined precisely enough that a deployment-safety reviewer can confirm an accidental flag-forgotten resume cannot cause data loss? [Measurability, Spec §FR-022, Spec §FR-001]
- [ ] CHK086 Does the spec define how a resume-in-rehearsal-mode run is observably distinct from a resume-in-real-call-mode run on the run report (so the operator can tell from the artifact alone which mode applied)? [Completeness, Spec §FR-022, Spec §FR-036]
- [ ] CHK087 Is the operator-ergonomics risk of a forgotten flag on resume addressed in the spec (e.g., explicit operator-visible message that the resume is running in rehearsal mode because the flag was omitted)? [Gap, Spec §FR-022, Spec §FR-036]
- [ ] CHK088 Is the requirement that the flag-required-on-every-mutation rule applies uniformly to: initial real-call run, resume after retry-budget exhaustion, resume after orchestrator restart mid-call, AND resume after live-call abandonment, stated consistently? [Consistency, Spec §FR-022, Spec §FR-001, Spec §FR-026]
- [ ] CHK089 Is the "every Dataverse-mutating invocation" scope unambiguous — i.e., does it cover resume of a session that previously succeeded all writes but is being re-invoked, or only resumes with pending writes? [Ambiguity, Spec §FR-022, Spec §FR-001]
- [ ] CHK090 Does FR-022's rehearsal-on-resume-without-flag rule preserve the Slice 2 no-duplicate guarantees (SC-008) — i.e., the rehearsal resume is a no-op for CRM state and therefore inherently duplicate-safe? [Consistency, Spec §FR-022, Spec §SC-008]

### Grace-window default and rollback implications (Q7 / FR-029)

- [ ] CHK091 Does the spec require the grace window to be deployment-configurable AND require that the deployment MUST set a non-zero default (so the system does not silently degrade to Option A "no grace window")? [Gap, Spec §FR-029]
- [ ] CHK092 Is the grace window's failure-mode behavior — what happens if the grace window is misconfigured to an excessively long value during an incident — addressed (e.g., does the orchestrator surface a stuck-shadow-lane warning that allows the operator to roll back or intervene)? [Gap, Spec §FR-029]
- [ ] CHK093 Is the rollback / operator-intervention path for a write-back held by the grace window defined (i.e., can the operator force the write-back to proceed without the shadow result during an incident)? [Gap, Spec §FR-029]
- [ ] CHK094 Is the grace window's relationship to the live-call abandonment timeout (FR-026) defined — i.e., the grace window applies AFTER session finalization and is independent of the abandonment timeout? [Clarity, Spec §FR-029, Spec §FR-026]
- [ ] CHK095 Does the spec require that the grace-window default value (or its configurability) is captured in the deferred-to-plan section's "Performance and latency targets" subsection, consistent with the Round 2 addition of that subsection? [Consistency, Spec §FR-029, Spec §Deferred to Implementation Plan Performance and latency targets]
- [ ] CHK096 Is the grace window's no-mutation guarantee (a late shadow-lane output that arrives after the grace window MUST NOT mutate the finalized disposition or emit a new CRM write-back) preserved in the spec wording? [Consistency, Spec §FR-029, Spec §FR-027]
- [ ] CHK097 Does the spec define a rollout posture for the grace window (e.g., a deployment can start with a small grace window and tune up, OR the deployment is required to have measured the shadow-lane budget before enabling shadow STT)? [Gap, Spec §FR-029, Spec §FR-032]

### DNC-first deployment safety (Q14 / FR-024)

- [ ] CHK098 Does FR-024 now explicitly require the DNC / opt-out field write to be attempted FIRST in the write-back sequence (before queue-status update, Phone Call activity, any Task)? [Completeness, Spec §FR-024]
- [ ] CHK099 Is the rationale for DNC-first ordering (partial-write-back failure within retry budget that loses everything BUT the DNC write still leaves the contact protected) stated in the spec as the safety property being enforced? [Clarity, Spec §FR-024]
- [ ] CHK100 Is the deployment safety posture defined for the case where Dataverse rejects the DNC write itself for a real-call `do_not_call` outcome (e.g., schema rejection, permissions, transient error after retry budget) — is the operator alerted that the contact may not be protected? [Gap, Spec §FR-024]
- [ ] CHK101 Does the spec require that the run report surfaces the DNC-first write status as a distinct per-operation status (per FR-036 per-write-back-operation status) so a deployment incident reviewer can confirm DNC protection succeeded? [Coverage, Spec §FR-024, Spec §FR-036]
- [ ] CHK102 Is the four-write-back-operation count preserved verbatim by treating the DNC field write as a field-level variant of the queue-status update operation (Q8) consistent with the new DNC-first ordering rule (Q14)? [Consistency, Spec §FR-020, Spec §FR-024]
- [ ] CHK103 Is the idempotency-key stamping guarantee (FR-021) explicitly preserved for the DNC-first write under resume — i.e., a resume re-invocation MUST NOT create a duplicate DNC write? [Consistency, Spec §FR-024, Spec §FR-021, Spec §FR-022]
- [ ] CHK104 Does the spec define whether the DNC-first ordering rule applies to mid-call opt-out (where the persona terminates the call mid-conversation) the same way it applies to a `do_not_call` disposition reached at normal call end? [Coverage, Spec §FR-024, Spec §FR-015]
- [ ] CHK105 Is the deployment-safety implication of a DNC write that succeeds while a later write (queue-status update or Phone Call activity) fails within the retry budget defined — i.e., is the session reported as a partial failure on the run report even though DNC protection succeeded? [Completeness, Spec §FR-024, Spec §FR-022, Spec §FR-036]

### PHI redaction deployment posture (Q11 / FR-015 / FR-033)

- [ ] CHK106 Is the tag-and-redact policy (PHI-bearing utterance tagged and redacted across full transcript, session-result summary, shadow STT transcript, and shadow STT discrepancy records) defined as a load-bearing compliance requirement that is REQUIRED on every Slice 3 deployment, or is it deployment-configurable? [Ambiguity, Spec §FR-015, Spec §FR-033]
- [ ] CHK107 If the tag-and-redact policy is deployment-configurable, does the spec define the conditions under which a deployment MAY disable it (e.g., never, only in non-production environments, only when transcript retention is pointer-only)? [Gap, Spec §FR-015, Spec §FR-033]
- [ ] CHK108 Is the PHI redaction requirement coupled to the default-on transcript redaction policy (FR-033) such that disabling default-on redaction would ALSO disable PHI redaction, or are they independent toggles? [Ambiguity, Spec §FR-015, Spec §FR-033]
- [ ] CHK109 Does the spec require that the deployment is unable to write PHI-bearing artifacts to disk without the tag-and-redact pass running (i.e., the redaction pass is a deployment-enforced precondition for write, not an optional post-process)? [Clarity, Spec §FR-015, Spec §FR-033]
- [ ] CHK110 Is the transcript-pointer exclusion (pointers MUST remain machine-readable for resume / inspection) consistent with the PHI tag-and-redact policy — i.e., a pointer record cannot itself contain PHI? [Consistency, Spec §FR-033, Spec §FR-015]
- [ ] CHK111 Does the spec require the deployment to log (in the run report or an audit artifact) that the PHI tag-and-redact pass ran when a `phi_collection_risk` escalation occurred, so a compliance reviewer can verify the redaction policy fired? [Gap, Spec §FR-015, Spec §FR-036]
- [ ] CHK112 Is the PHI redaction policy's no-secrets guarantee preserved (the redaction pass itself MUST NOT inadvertently log the PHI it is redacting to a debug stream)? [Coverage, Spec §FR-015, Spec §FR-035]
- [ ] CHK113 Does the spec define the deployment rollback posture for a deployment that discovers its tag-and-redact pass has been silently disabled or broken (e.g., is the deployment required to fail safely and refuse to write artifacts)? [Gap, Spec §FR-015, Spec §FR-033]

### Performance and latency targets subsection (Round 2 deferred-to-plan addition)

- [ ] CHK114 Does the spec's Deferred to Implementation Plan section now include a "Performance and latency targets" subsection explicitly stating that numeric latency / throughput / wall-clock targets are deferred to plan? [Completeness, Spec §Deferred to Implementation Plan Performance and latency targets]
- [ ] CHK115 Is the deferred performance subsection sufficient to keep the deployment posture flexible per environment without re-amending the spec (i.e., the configurability is the requirement; the numbers belong in plan or deployment configuration)? [Clarity, Spec §Deferred to Implementation Plan Performance and latency targets]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

### Cold-to-rehearsal sufficiency of Quickstart §1 one-time setup

- [ ] CHK116 Do the one-time setup steps in Quickstart §1 (install / build, configure secrets, configure non-secret deployment options, verify Slice 2 prerequisites) enumerate every deployment artifact and dependency needed to go from a cold checkout to a successful rehearsal run with no manual undocumented step? [Coverage, Quickstart §1, Quickstart §2]
- [ ] CHK117 Is the `uv sync` step in Quickstart §1.1 sufficient to install every Slice 3 runtime dependency listed in Plan §Technical Context (`signalwire` SDK, `pipecat-ai`, the chosen real-time AI provider's client, the chosen shadow STT provider's client)? [Coverage, Quickstart §1.1, Plan §Technical Context, Gap]
- [ ] CHK118 Does Quickstart §1 instruct an operator to create or place `config/shadow_stt_discrepancy_policy.json` on disk before the first rehearsal run (Research §4 names the file; Quickstart §1.3 references it but does not document its provenance)? [Gap, Quickstart §1.3, Research §4]
- [ ] CHK119 Does the cold-to-rehearsal path require any database migration / schema initialization for the SQLite extensions in Data-Model §3 (new tables: `rejected_auth_callbacks`, `shadow_stt_discrepancies`, `shadow_lane_truncated_events`; ALTER on `sessions`) that the quickstart should document? [Gap, Quickstart §1, Data-Model §3]

### FastAPI ASGI callback receiver ingress / firewall / TLS posture (Research §1)

- [ ] CHK120 Does the deployment documentation address the ingress / firewall / TLS posture required by the FastAPI ASGI callback receiver in Research §1 (the receiver only binds in real-call mode but MUST be reachable from SignalWire on the configured callback URLs)? [Gap, Research §1, Quickstart §1]
- [ ] CHK121 Is the operator-side responsibility for exposing the callback receiver to the public internet (e.g., reverse proxy, ngrok tunnel for dev, TLS termination, public DNS for the URL template host) defined for a real-call deployment? [Gap, Research §1, Quickstart §1.3]
- [ ] CHK122 Is the deployment posture defined when the callback receiver port is firewalled — does the readiness check `status_callback_url_configured` / `media_callback_url_configured` detect un-reachability, and does the quickstart name the failure mode? [Coverage, Contract: cli-slice3.md, Quickstart §8, Research §1]
- [ ] CHK123 Is the TLS / HTTPS requirement on the SignalWire callback URLs enforced or strongly recommended by the deployment guidance (Quickstart §1.3 example uses `https://`, but no explicit "HTTPS required" statement)? [Ambiguity, Quickstart §1.3, Research §1]

### Slice 2 environment reuse (Research §14 ↔ Quickstart §1)

- [ ] CHK124 Does Quickstart §1 enumerate every Slice 2 environment prerequisite that Slice 3 reuses (Research §14: SQLite state store, `httpx` Dataverse client, OAuth2 client-credentials, `config/dataverse_mapping.json` discovery + verification, idempotency-key stamping, bounded retry, resume coordinator, retention floor ≥ 90 days)? [Coverage, Research §14, Quickstart §1]
- [ ] CHK125 Is the operator instructed in Quickstart §1.4 to run `opencloser dataverse-verify` against a Slice 2 mapping artifact that ALREADY exists from prior Slice 2 deployment — or does the quickstart need to document how to bootstrap that artifact on a brand-new Slice 3-first deployment? [Gap, Quickstart §1.4, Research §14]
- [ ] CHK126 Is the Dataverse env-var reuse from Slice 2 (`DATAVERSE_TENANT_ID`, `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`, `DATAVERSE_ENV_URL`) compatible with a Slice 3-only deployment (no required Slice 2 CLI execution before Slice 3 first-use)? [Consistency, Research §14, Quickstart §1.2]

### Bench-ownership boundary preservation (Feature 003 owned by py-bench)

- [ ] CHK127 Does Slice 3 plan / research / data-model / contracts / quickstart preserve the bench-ownership boundary (Feature 003 owned by `py-bench`; Flutter admin/install work confined to Features 004+ per Spec §Constitution Alignment "Thin slice")? [Consistency, Plan §Project Structure, Spec §Constitution Alignment]
- [ ] CHK128 Does any plan-side artifact (plan.md, research.md, data-model.md, contracts/, quickstart.md) introduce a Flutter dependency, a `flutterBench` artifact, or a UI surface that would violate the Feature 003 py-bench-only scope? [Conflict, Plan §Project Structure, Spec §Constitution Alignment]

### Resume-on-re-invocation flow state-store migration from Slice 2 → Slice 3 (Data-Model §3 ↔ Quickstart §5)

- [ ] CHK129 Is the SQLite schema migration from a Slice 2 state store to a Slice 3 state store (new tables + ALTER on `sessions` per Data-Model §3) documented for the deployment so a Slice 2 → Slice 3 upgrade does not require manual SQL? [Gap, Data-Model §3, Quickstart §1]
- [ ] CHK130 Is the additive-only nature of the Slice 3 SQLite changes (new tables, ALTER ADD COLUMN only — no drops, no renames) verified against the Data-Model §3 schema so the migration is safely forward-only? [Consistency, Data-Model §3]
- [ ] CHK131 Does the resume flow in Quickstart §5 work against a session row written by Slice 2 (no `provider_call_id`, no `runtime_identity_json`, no `operator_identity_*`, etc.) — and is the backwards-compat behavior of the ALTERed columns (nullable per Data-Model §3) sufficient for that case? [Coverage, Quickstart §5, Data-Model §2.1, Data-Model §3]

### Slice 3 → Slice 2 rollback / downgrade posture (Data-Model §3)

- [ ] CHK132 Is the rollback posture (downgrade from Slice 3 back to Slice 2) defined given the additive SQLite columns in Data-Model §3 — Slice 2 code reading a Slice-3-written `sessions` row MUST ignore the new columns without error? [Gap, Data-Model §3]
- [ ] CHK133 Is the rollback behavior defined for the new Slice 3 tables (`rejected_auth_callbacks`, `shadow_stt_discrepancies`, `shadow_lane_truncated_events`) — does a Slice 2 rollback leave them in place (dormant) or drop them, and is data loss prevented? [Gap, Data-Model §3]
- [ ] CHK134 Is the rollback posture for the artifact directory layout (Data-Model §4) defined — Slice 2 code MUST not crash when it finds Slice 3-only files (`shadow_*.{txt,jsonl,json}`, `rejected_auth_callbacks.jsonl`) in `artifacts/<session_id>/`? [Gap, Data-Model §4]

### Real-call flag per-invocation gate deployment safety (Round 2 Q13)

- [ ] CHK135 Is the per-invocation `--real-call` gate (Round 2 Q13) deployment-safe under the "operator forgets the flag" scenario — the deployment guarantees no SignalWire dial and no Dataverse mutation occurs, BUT does the operator-visible artifact set make it obvious to the operator that nothing happened (so they do not assume success)? [Coverage, Contract: cli-slice3.md, Spec §FR-001, Quickstart §3]
- [ ] CHK136 When `--real-call` is omitted, does the run report's `run_mode = "rehearsal"` field appear prominently enough (e.g., near the top of `run_report.json`, surfaced in CLI stdout) that an operator running a "real call" by intent immediately sees they ran a rehearsal? [Gap, Quickstart §4, Contract: cli-slice3.md]
- [ ] CHK137 Is the resume-flag-absent behavior (resume runs as rehearsal mode per Round 2 Q13) operator-visible enough on the deployment surface that a partial-write-back recovery attempt without `--real-call` is not mistaken for a successful resume? [Coverage, Quickstart §5, Contract: cli-slice3.md, Contract: crm-writeback-dnc-first.md]
- [ ] CHK138 Is the deployment posture defined when an operator habitually adds `--real-call` to every invocation (e.g., via a shell alias) — does the per-invocation gate still function as intended, or does the convenience erode the safety guarantee? [Ambiguity, Contract: cli-slice3.md, Spec §FR-001, Gap]

### Plan-side artifact deployment-completeness

- [ ] CHK139 Does the deployment surface (Quickstart §1) document the existence and location of `docs/slice3/demo-evidence-checklist.md` (Research §13) so a pre-pilot operator can collect the required demo evidence without re-discovering the file? [Gap, Research §13, Quickstart §1, Quickstart §7]
- [ ] CHK140 Is the deployment instructed to confirm `pytest` passes (Quickstart §1.1) against the Slice 1 / Slice 2 / Slice 3 test suites — and is that confirmation sufficient evidence that the Slice 3 deployment is functional before the first real-call run? [Coverage, Quickstart §1.1, Research §12]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] indicate language that may need tightening before plan / implementation.
- ≥80% of items reference a spec section or a quality marker for traceability.
