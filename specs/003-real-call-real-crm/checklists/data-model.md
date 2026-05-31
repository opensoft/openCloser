# Data Model / Entity Definitions Requirements Quality Checklist: Slice 3 — Real Call, Real CRM

**Purpose**: Validate requirement quality for the entity-definitions dimension before planning / implementation
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)
**Depth**: Release gate (maximum coverage, all five scenario classes)

## Entity Enumeration

- [ ] CHK001 Are all Slice 3 entities named in Key Entities enumerated in one canonical place (SignalWire Telephony Transport, Pipecat Realtime Audio Runtime, Configured Real-time AI Provider, Real Provider Call ID, Telephony Readiness Report, Callbacks Audit Log, Shadow STT Lane / Shadow Transcript, Shadow STT Discrepancy Record, Live-Call Abandonment Outcome, Run Report)? [Completeness, Spec §Key Entities]
- [ ] CHK002 Are all preserved Slice 1 / Slice 2 entities enumerated in one canonical place (Queue Item, Eligibility Decision, Session, Normalized Result, Phone Call activity payload, Queue-status update payload, Task payload, Idempotency Key, Conflicting Event Audit Record, Conversation Fixture, Transport Fixture, Dataverse Queue Item, CRM Field Mapping Artifact, Dataverse CRM Adapter, Task Owner Mapping, Redaction Layer / Redaction Policy, CRM Correlation Identifier, Write-Back Progress Ledger)? [Completeness, Spec §Key Entities > Preserved Slice 1 / Slice 2 Entities]
- [ ] CHK003 Are entities that appear only in Definitions (e.g., Telephony readiness check, SignalWire status callback, SignalWire media callback, Normalized call event, Live conversation path, Shadow STT discrepancy, High-value field, Real-dial phone-number validation, Attempt consumed (Slice 3), Live-call abandonment) cross-listed in Key Entities or explicitly marked as concept-only definitions so reviewers know whether each carries a persisted shape? [Clarity, Spec §Definitions, Spec §Key Entities]
- [ ] CHK004 Is the boundary between persisted entities (stored locally, written to Dynamics, or in audit artifacts) and ephemeral concepts (e.g., normalized events traversing the bus) defined for each entity? [Clarity, Spec §Key Entities]
- [ ] CHK005 Is every Slice 3 entity scoped as either (a) deployment-configured, (b) per-run, (c) per-session, or (d) per-callback, so reviewers know each entity's lifecycle? [Completeness, Spec §Key Entities]
- [ ] CHK006 Are entity name collisions with Slice 1 / Slice 2 (e.g., "Real Provider Call ID" vs. the old "mock provider call ID" field name) reconciled with explicit rename language? [Consistency, Spec §FR-006, Spec §FR-018]
- [ ] CHK007 Does the spec confirm the Slice 1 / Slice 2 Mock Call Event entity is renamed to `CallEvent` at the transport boundary and that the renamed entity carries the same shape (no semantic change)? [Consistency, Spec §FR-018, Spec §Key Entities > Preserved Slice 1 / Slice 2 Entities]
- [ ] CHK008 Is the relationship between the SignalWire Telephony Transport entity (the adapter) and the Real Provider Call ID entity (the assigned identifier) defined so reviewers know which owns assignment? [Clarity, Spec §Key Entities > SignalWire Telephony Transport, Spec §Key Entities > Real Provider Call ID]
- [ ] CHK009 Is the relationship between the Pipecat Realtime Audio Runtime entity and the Configured Real-time AI Provider entity defined (runtime bridges to provider; provider identity recorded on session)? [Clarity, Spec §Key Entities > Pipecat Realtime Audio Runtime, Spec §Key Entities > Configured Real-time AI Provider]
- [ ] CHK010 Is the relationship between the Shadow STT Lane / Shadow Transcript entity and the Shadow STT Discrepancy Record entity defined (lane emits discrepancy records keyed to a session)? [Clarity, Spec §Key Entities > Shadow STT Lane, Spec §Key Entities > Shadow STT Discrepancy Record]
- [ ] CHK011 Is the relationship between the Callbacks Audit Log entity and the Conflicting Event Audit Record entity defined (the conflicting-late callback is logged into a conflicting-events audit log keyed `(session_id, provider_event_id)` — same key, different artifact)? [Consistency, Spec §FR-007, Spec §FR-027, Spec §Key Entities > Callbacks Audit Log]
- [ ] CHK012 Is the relationship between the Live-Call Abandonment Outcome entity and the Session entity defined (abandonment is a finalization path that mutates the session's disposition + reason)? [Clarity, Spec §FR-026, Spec §Key Entities > Live-Call Abandonment Outcome]
- [ ] CHK013 Is the Run Report entity scoped as per-invocation (one report per CLI invocation, including rehearsal / readiness mode)? [Clarity, Spec §FR-002, Spec §FR-036]

## Attribute Completeness

### Queue Item / Dataverse Queue Item / Eligibility Decision

- [ ] CHK014 Does the spec preserve the Slice 1 / Slice 2 Queue Item attribute set unchanged for Slice 3 (no Slice 3 attribute additions, deletions, or repurposings)? [Completeness, Spec §FR-019, Spec §Assumptions > Slice 1 / Slice 2 contracts preserved]
- [ ] CHK015 Does the spec name the Eligibility Decision attributes carried into Slice 3 (the six Slice 1 eligibility rule results, the `blocked` disposition, the `blocked_reason` field) so reviewers can confirm none were silently dropped? [Completeness, Spec §FR-019, Spec §FR-017]
- [ ] CHK016 Does the spec confirm the Dataverse Queue Item DNC / opt-out fields are the same Slice 1 / Slice 2 fields updated by Slice 3 (no new DNC field added)? [Consistency, Spec §FR-024, Spec §User Story 1 acceptance scenario 4]

### Session

- [ ] CHK017 Are the Session attributes for Slice 3 enumerated, at minimum: session ID, queue-item ID, eligibility decision, real provider call ID (when assigned), persona version, runtime/model identity, started_at, ended_at, final disposition, invoking operator identity? [Completeness, Spec §Constitution Alignment > Auditability, Spec §FR-016, Spec §FR-036]
- [ ] CHK018 Is the invoking operator identity defined as a Session attribute that is LOCAL-ONLY (recorded on session and run report; never propagated into Dataverse)? [Consistency, Spec §FR-016, Spec §Clarifications > 2026-05-25]
- [ ] CHK019 Does the spec confirm that the Session entity is the carrier of the Slice 3 rename `mock_provider_call_id` → `provider_call_id` (and backwards-compatible for pre-Slice-3 sessions)? [Consistency, Spec §FR-006, Spec §FR-018]

### Normalized Result

- [ ] CHK020 Is the normalized session result's full field list enumerated for Slice 3 (session ID, queue-item ID, real provider call ID, persona version, final disposition, summary, transcript or transcript pointer, captured email when verified or `captured_email_unverified` otherwise, `callback_requested`, `preferred_callback_window`, `human_review_reason` when applicable, `blocked_reason` when applicable, `started_at`, `ended_at`)? [Completeness, Spec §FR-017]
- [ ] CHK021 Is the normalized result shape stated as IDENTICAL to Slice 1 / Slice 2 (no Slice 3 additions or removals) so reviewers can verify the rename is the only Slice 3 change? [Consistency, Spec §FR-017, Spec §SC-016, Spec §User Story 5 acceptance scenario 6]
- [ ] CHK022 Is the captured email field's two-value behavior (verified email value OR sentinel `captured_email_unverified`) stated unambiguously so reviewers can confirm the field is non-nullable in the contract sense? [Clarity, Spec §FR-017, Spec §User Story 5 acceptance scenario 6]
- [ ] CHK023 Does the spec confirm `blocked_reason` is populated only for `blocked` disposition outcomes (and `human_review_reason` only for `needs_human_review` outcomes), preserving Slice 1 / Slice 2 conditional-field semantics? [Consistency, Spec §FR-017, Spec §FR-019]

### Phone Call Activity Payload

- [ ] CHK024 Does the spec confirm the Phone Call activity payload is reused from Slice 2 unchanged except for the two Slice 3 additions (real provider call ID in place of mock provider call ID, plus connected-call timestamps SignalWire supplies)? [Consistency, Spec §FR-020, Spec §User Story 1 acceptance scenario 6]
- [ ] CHK025 Are the connected-call timestamps from SignalWire callbacks (e.g., answered-at, completed-at) named explicitly enough that reviewers can verify the adapter knows which timestamps to record? [Clarity, Spec §FR-020, Spec §User Story 1 acceptance scenario 6]
- [ ] CHK026 Is it explicit that the real provider call ID replaces the mock provider call ID in the same payload slot (not a new additional field)? [Clarity, Spec §FR-020, Spec §FR-006]
- [ ] CHK027 Is the persona-authored summary field preserved on the Phone Call activity payload for Slice 3 (consistent with Slice 1 / Slice 2)? [Consistency, Spec §FR-020, Spec §User Story 1]
- [ ] CHK028 Does the spec confirm that no new Phone Call activity field is added for operator identity (FR-016 local-only)? [Consistency, Spec §FR-016, Spec §FR-020]

### Queue-Status Update Payload

- [ ] CHK029 Does the spec confirm the Queue-status update payload is reused from Slice 2 unchanged for Slice 3? [Consistency, Spec §FR-020]
- [ ] CHK030 Are the queue-status / attempt / last-disposition / last-session field updates named explicitly for the User Story 1 happy path? [Completeness, Spec §User Story 1, Spec §User Story 1 acceptance scenario 1]

### Task Payload

- [ ] CHK031 Does the spec confirm the Task payload is reused from Slice 2 unchanged for Slice 3 (carrying captured callback window, captured email, or human-review reason as applicable)? [Consistency, Spec §FR-020, Spec §User Story 1 acceptance scenarios 1-3]
- [ ] CHK032 Does the spec confirm the Task Owner Mapping entity (callback owner / review owner) is reused from Slice 2 unchanged? [Consistency, Spec §FR-020, Spec §Key Entities > Preserved Slice 1 / Slice 2 Entities]

### Idempotency Key

- [ ] CHK033 Is the Idempotency Key entity defined consistently with Slice 2 (a stable session-derived key stamped onto a metadata-verified Dataverse field of every Phone Call activity and Task, with a pre-query before each create)? [Consistency, Spec §FR-021]
- [ ] CHK034 Does the spec confirm the Slice 3 dial does not change the Idempotency Key derivation (still session-derived; the real provider call ID is recorded separately on the payload)? [Clarity, Spec §FR-021, Spec §FR-006]

### Callbacks Audit Log

- [ ] CHK035 Are the Callbacks Audit Log attributes enumerated: `(session_id, provider_event_id)` key, receipt timestamp, callback type, normalized event produced, conflicting-late audit row when applicable? [Completeness, Spec §Key Entities > Callbacks Audit Log, Spec §FR-007]
- [ ] CHK036 Is the rule "every callback received, INCLUDING duplicates, is recorded" stated as a schema-level invariant of the Callbacks Audit Log (not only a behavioral note)? [Completeness, Spec §FR-007, Spec §FR-021]

### Conflicting Event Audit Record

- [ ] CHK037 Are the Conflicting Event Audit Record attributes enumerated and consistent with the Slice 1 conflicting-events audit channel (key `(session_id, provider_event_id)`, the finalized disposition unchanged, the late callback contents)? [Completeness, Spec §FR-027, Spec §Edge Cases > delivered after disposition finalized]
- [ ] CHK038 Is the relationship between Callbacks Audit Log (every callback) and Conflicting Event Audit Record (the subset that arrived after finalization) defined so reviewers can confirm they are two distinct artifacts with the same key shape? [Clarity, Spec §FR-007, Spec §FR-027]

### Shadow STT Lane / Shadow Transcript

- [ ] CHK039 Are the Shadow STT Lane attributes enumerated (shadow transcript or pointer under the same session and retention policy, per-high-value-field comparison record, discrepancy events)? [Completeness, Spec §Key Entities > Shadow STT Lane, Spec §FR-028, Spec §FR-030]
- [ ] CHK040 Does the spec name the configured high-value fields the shadow lane compares (opt-out / DNC, wrong number, captured email, callback intent / preferred callback window, person reached name and role, interest level, final disposition)? [Completeness, Spec §Definitions > High-value field, Spec §FR-030]
- [ ] CHK041 Does the spec define the shadow transcript retention behavior (same retention policy as the live transcript: full + redacted, summary-only, or pointer-only)? [Completeness, Spec §FR-034]

### Shadow STT Discrepancy Record

- [ ] CHK042 Are the Shadow STT Discrepancy Record attributes enumerated (session ID, field(s) that disagreed, live value(s), shadow value(s), classification benign vs. uncertain, resulting review-task reason code when escalation applied)? [Completeness, Spec §Key Entities > Shadow STT Discrepancy Record]
- [ ] CHK043 Does the spec confirm the Shadow STT Discrepancy Record is retained as audit/review evidence even when transcript retention is summary-only (retention floor for discrepancy records is independent of the transcript-mode toggle)? [Consistency, Spec §FR-034]
- [ ] CHK044 Does the spec define the discrepancy classification value set (at minimum benign vs. uncertain) so the record schema is implementable? [Completeness, Spec §FR-031, Spec §Edge Cases > Shadow STT mismatch on a high-value field]

### Live-Call Abandonment Outcome

- [ ] CHK045 Are the Live-Call Abandonment Outcome attributes defined (disposition `failed`, reason `live_call_abandonment`, configured-timeout origin, queue item leaves `in_progress`)? [Completeness, Spec §FR-026, Spec §Key Entities > Live-Call Abandonment Outcome]
- [ ] CHK046 Is it explicit that a Live-Call Abandonment Outcome MUST NOT yield a false connected-call Phone Call activity when the call never reached the connected state? [Completeness, Spec §FR-026, Spec §Edge Cases > Live-call abandonment]
- [ ] CHK047 Is the live-call abandonment timeout defined as deployment-configurable (default value left as deployment configuration, not pinned in spec)? [Clarity, Spec §FR-026, Spec §Assumptions > Live-call abandonment timeout]

### Run Report

- [ ] CHK048 Are the Run Report attributes enumerated at minimum (run mode, session ID, invoking operator identity, real provider call ID when assigned, persona version, runtime/model identity, final disposition, per-write-back-operation status [planned / completed / resume-needed / blocked], shadow STT enabled/disabled flag, discrepancy summary when enabled, callbacks audit / conflicting-callbacks audit row counts, failing readiness check or block reason when applicable)? [Completeness, Spec §FR-036]
- [ ] CHK049 Does the spec confirm the run report includes telephony readiness summary (per-check result) as an attribute, not only a free-text section? [Completeness, Spec §FR-009, Spec §FR-011, Spec §Key Entities > Run Report]
- [ ] CHK050 Is the run report's operator-identity field explicitly local-only (consistent with FR-016) — i.e., the run report carries it but the Dataverse adapter never sees it? [Consistency, Spec §FR-016, Spec §FR-036]

### Telephony Readiness Report

- [ ] CHK051 Are the Telephony Readiness Report attributes enumerated (per-check result for SignalWire credentials, source number, destination phone format, callback URLs, persona/runtime configuration, Dataverse mapping, callback owner mapping, eligibility)? [Completeness, Spec §FR-009, Spec §Key Entities > Telephony Readiness Report]
- [ ] CHK052 Is the failing-check-name field defined as a required attribute on any readiness failure (so an operator can act on it)? [Completeness, Spec §FR-011, Spec §User Story 3 independent test]
- [ ] CHK053 Does the spec confirm that the Telephony Readiness Report is produced by BOTH rehearsal / readiness mode AND real-call / write-enabled mode (not only by rehearsal)? [Consistency, Spec §FR-002, Spec §Key Entities > Telephony Readiness Report]

### SignalWire Telephony Transport / Pipecat Realtime Audio Runtime / Configured Real-time AI Provider

- [ ] CHK054 Are the SignalWire Telephony Transport entity's attributes enumerated (credentials use, dial-plan construction, source caller-ID number, status/media callback registration and authentication, normalization rules, real provider call ID assignment)? [Completeness, Spec §Key Entities > SignalWire Telephony Transport]
- [ ] CHK055 Are the Pipecat Realtime Audio Runtime entity's attributes enumerated (audio bridging, persona turn-driving, transcript-segment emission, extraction-event emission, persona output return)? [Completeness, Spec §Key Entities > Pipecat Realtime Audio Runtime]
- [ ] CHK056 Are the Configured Real-time AI Provider entity's audit attributes enumerated (provider name and model version, recorded on session) with explicit "credentials MUST NOT appear in logs or artifacts" constraint? [Completeness, Spec §Key Entities > Configured Real-time AI Provider, Spec §FR-035]

### Real Provider Call ID

- [ ] CHK057 Are the Real Provider Call ID attributes defined (SignalWire-assigned call SID or carrier-equivalent, recorded on session, used for SignalWire callback correlation)? [Completeness, Spec §Key Entities > Real Provider Call ID, Spec §FR-006]
- [ ] CHK058 Does the spec confirm backwards-compatible correlation for pre-Slice-3 sessions that carry the old "mock provider call ID" identifier shape? [Completeness, Spec §Assumptions > Backwards-compatible call ID correlation, Spec §FR-006]

### CRM Field Mapping Artifact / Dataverse CRM Adapter / Task Owner Mapping / Redaction Layer / CRM Correlation Identifier / Write-Back Progress Ledger

- [ ] CHK059 Does the spec confirm the CRM Field Mapping Artifact entity is reused from Slice 2 unchanged for Slice 3? [Consistency, Spec §FR-020, Spec §Key Entities > Preserved Slice 1 / Slice 2 Entities]
- [ ] CHK060 Does the spec confirm the Dataverse CRM Adapter entity is reused from Slice 2 unchanged for Slice 3 (no Slice 3 weakening or deletion)? [Consistency, Spec §FR-020]
- [ ] CHK061 Does the spec confirm the Task Owner Mapping entity (callback owner / review owner / team) is reused from Slice 2 unchanged? [Consistency, Spec §FR-020]
- [ ] CHK062 Does the spec confirm the Redaction Layer / Redaction Policy entity is reused from Slice 2 unchanged (default-on `[REDACTED]` policy or its configured replacement; runs before any transcript artifact is written)? [Consistency, Spec §FR-033]
- [ ] CHK063 Does the spec confirm the CRM Correlation Identifier entity is reused from Slice 2 unchanged for Slice 3 (used to detect duplicate / failed Dataverse writes)? [Consistency, Spec §Constitution Alignment > Auditability, Spec §FR-022]
- [ ] CHK064 Does the spec confirm the Write-Back Progress Ledger entity is reused from Slice 2 unchanged for Slice 3 (drives resume-only-missing-writes behavior)? [Consistency, Spec §FR-022, Spec §User Story 4 acceptance scenario 7]
- [ ] CHK065 Is the local-audit retention floor (>= 90 days, or longer when configured) defined as a property of the audit-artifact entities (CRM Correlation, Write-Back Progress Ledger, Callbacks Audit Log, Shadow STT artifacts)? [Completeness, Spec §FR-022, Spec §Assumptions > Local artifact retention]

## Identity & Uniqueness Rules

- [ ] CHK066 Is the session ID defined as the primary identity for a Session entity and as the foreign key on all per-session artifacts (Run Report, Callbacks Audit Log, Shadow Transcript, Shadow STT Discrepancy Record, Conflicting Event Audit Record)? [Completeness, Spec §Constitution Alignment > Auditability]
- [ ] CHK067 Is the `(session_id, provider_event_id)` composite key defined as the unique key for Callbacks Audit Log entries (used for duplicate detection)? [Completeness, Spec §FR-007, Spec §FR-021]
- [ ] CHK068 Is the `(session_id, provider_event_id)` composite key defined as the unique key for Conflicting Event Audit Record entries (consistent with the Callbacks Audit Log key shape)? [Consistency, Spec §FR-027]
- [ ] CHK069 Is the Idempotency Key's uniqueness scope defined (per Phone Call activity and per Task, stable across re-invocations of the same session) so duplicate detection at the Dataverse level is unambiguous? [Completeness, Spec §FR-021]
- [ ] CHK070 Is the Real Provider Call ID's uniqueness scope defined (one per dialed call attempt) and recorded on the session? [Completeness, Spec §FR-006, Spec §FR-025]
- [ ] CHK071 Does the spec confirm one Dataverse queue item is processed per invocation (FR-003), so the Session-to-Queue-Item relationship is many-sessions-per-queue-item but exactly-one-queue-item-per-session? [Clarity, Spec §FR-003]
- [ ] CHK072 Is the run-report identity defined as one-report-per-invocation (vs. one per session — the two coincide here because of FR-003)? [Clarity, Spec §FR-003, Spec §FR-036]
- [ ] CHK073 Does the spec specify that the queue-claim semantics (Slice 2 reuse) make a queue item observable as not-`ready` by a concurrent invocation, preventing two sessions from claiming the same queue item at the same time? [Completeness, Spec §FR-003, Spec §Clarifications > 2026-05-25]

## State Transitions

### Queue Item Lifecycle

- [ ] CHK074 Are the Queue Item state transitions defined for Slice 3 (`ready` → `in_progress` on claim → final disposition state on finalization → status reset on resume only for missing writes)? [Completeness, Spec §User Story 1, Spec §FR-022]
- [ ] CHK075 Is the rule "queue item MUST NOT remain in `in_progress` indefinitely" stated as a state-transition obligation tied to the live-call abandonment timeout? [Completeness, Spec §FR-026, Spec §Edge Cases > Live-call abandonment]
- [ ] CHK076 Is the rule "blocked-by-eligibility queue item produces only the approved blocked / status / error field writes; no attempt increment" stated as a state-transition obligation? [Completeness, Spec §FR-023]

### Session Lifecycle

- [ ] CHK077 Are the Session lifecycle states defined (created → eligibility-evaluated → readiness-checked → dialed (real provider call ID assigned) → connected → finalized (with disposition))? [Completeness, Spec §Constitution Alignment > Auditability]
- [ ] CHK078 Is the rule "once finalized, the disposition MUST NOT change on a late / duplicate callback" stated as a state-transition obligation? [Completeness, Spec §FR-027]
- [ ] CHK079 Is the rule "live-runtime degradation pre-connection finalizes as `failed` with runtime-failure reason; post-connection finalizes as `needs_human_review` with `script_truncated`" stated as a state-transition obligation with both branches enumerated? [Completeness, Spec §FR-013, Spec §Edge Cases > Live model failure or runtime crash mid-call]
- [ ] CHK080 Is the rule "trigger (c) silence-after-connection timeout is not applicable before connection" stated explicitly so reviewers can confirm the state machine has no orphan branch? [Clarity, Spec §FR-013, Spec §Edge Cases > Live model failure or runtime crash mid-call]

### Attempt-Count Transitions

- [ ] CHK081 Are the conditions under which attempt count is incremented enumerated completely (eligibility allows + flag supplied + real-dial phone-number validation passes + telephony readiness passes + Dataverse metadata verification passes + SignalWire dial successful with real provider call ID assigned)? [Completeness, Spec §FR-025]
- [ ] CHK082 Are the conditions under which attempt count is NOT incremented enumerated completely (rehearsal/readiness, flag absent, telephony readiness failure, real-dial phone-number validation failure, Dataverse unreachable at start, provider-rejected dial, malformed dial-plan / persona-runtime config, duplicate SignalWire callbacks)? [Completeness, Spec §FR-025]
- [ ] CHK083 Is the rule "attempt count incremented exactly once per session" stated as a state-transition invariant (preventing duplicate increments on retries or recovery)? [Completeness, Spec §FR-025, Spec §SC-008]

### Disposition Transitions

- [ ] CHK084 Are the per-disposition `new_status` values for the Dataverse queue item stated as preserved-from-Slice-1/2 and unchanged for Slice 3 (so reviewers can confirm no Slice 3 disposition-to-status drift)? [Consistency, Spec §FR-020]
- [ ] CHK085 Does the spec confirm the disposition precedence (Slice 1 FR-036 deterministic rules) is the ONLY mechanism that selects the final disposition (not the live model)? [Completeness, Spec §FR-014, Spec §SC-014]

### DNC / Opt-Out Transitions

- [ ] CHK086 Is the DNC / opt-out state transition defined (clear opt-out → disposition `do_not_call` → Dataverse DNC / opt-out and queue-status fields updated → no callback or review Task created)? [Completeness, Spec §FR-024, Spec §User Story 1 acceptance scenario 4]
- [ ] CHK087 Does the spec confirm the mid-call opt-out triggers the same DNC state transition as a pre-dial DNC eligibility block at the disposition level (consistent terminal outcome)? [Consistency, Spec §FR-024, Spec §Edge Cases > Mid-call opt-out / DNC]

### Shadow STT Discrepancy Escalation Transition

- [ ] CHK088 Is the discrepancy-policy state transition defined (live-vs-shadow disagreement on high-value field → classification benign / uncertain → uncertain escalates session to `needs_human_review` with `shadow_stt_discrepancy` review-task reason)? [Completeness, Spec §FR-031, Spec §User Story 6 acceptance scenario 4]
- [ ] CHK089 Does the spec confirm the shadow lane CANNOT independently mutate the session's disposition (the orchestrator's discrepancy escalation hook applies the persona's deterministic disposition rules)? [Consistency, Spec §FR-030, Spec §SC-013]

## Renames & Additive Entries

- [ ] CHK090 Is the rename `mock_provider_call_id` → `provider_call_id` listed in exactly one canonical sanctioned-renames list so reviewers can verify no other rename was smuggled in? [Clarity, Spec §FR-018, Spec §Assumptions > Slice 1 / Slice 2 contracts preserved]
- [ ] CHK091 Is the rename `MockCallEvent` → `CallEvent` listed in the same canonical sanctioned-renames list? [Clarity, Spec §FR-018]
- [ ] CHK092 Is the rename `fixture_id` → `dial_plan` listed in the same canonical sanctioned-renames list and scoped to the SignalWire transport boundary? [Clarity, Spec §FR-018]
- [ ] CHK093 Is the additive entry `shadow_stt_discrepancy` declared as the ONLY Slice 3 addition to the `human_review_reason` enumeration, with existing reason codes preserved? [Completeness, Spec §FR-031]
- [ ] CHK094 Does the spec confirm the disposition enumeration is unchanged (no Slice-3-specific disposition added)? [Consistency, Spec §FR-017]
- [ ] CHK095 Does the spec confirm no new Dataverse field is added for operator identity (the Slice 2 Dataverse mapping surface is unchanged on the operator-identity dimension)? [Consistency, Spec §FR-016]
- [ ] CHK096 Are renames described consistently in FR-006, FR-018, Key Entities, and Assumptions (every section uses the new name; the old name is only referenced inside explicit "renamed from" language)? [Consistency, Spec §FR-006, Spec §FR-018, Spec §Key Entities, Spec §Assumptions]
- [ ] CHK097 Does the spec explicitly state that NO Slice 1 / Slice 2 contract attribute is weakened or deleted (so reviewers know all additive / rename changes are net-additive at the schema level)? [Completeness, Spec §FR-020, Spec §Assumptions > Slice 1 / Slice 2 contracts preserved]

## Normalized Session Result Shape

- [ ] CHK098 Is the normalized session result shape's field ORDER / structure either pinned or explicitly deferred (the field list in FR-017 is enumerated, but ordering for serialization is not — flag this if downstream contract tests depend on it)? [Ambiguity, Spec §FR-017]
- [ ] CHK099 Is each normalized session result field's source defined (session, persona, transport, runtime, or eligibility) so reviewers can confirm each field has an owner? [Completeness, Spec §FR-017]
- [ ] CHK100 Is the transcript-or-transcript-pointer field's two-mode behavior (full transcript inline vs. pointer-only) defined consistently with the retention-mode toggle (FR-033)? [Consistency, Spec §FR-017, Spec §FR-033]
- [ ] CHK101 Is the persona version field's source defined (the persona module, recorded on the session per FR-016)? [Completeness, Spec §FR-016, Spec §FR-017]
- [ ] CHK102 Is the runtime/model identity field's source defined (the Pipecat runtime adapter and the Configured Real-time AI Provider entity, recorded on the session per FR-016)? [Completeness, Spec §FR-016, Spec §FR-017]

## Per-Disposition `new_status` Map

- [ ] CHK103 Is the per-disposition `new_status` map stated as preserved-from-Slice-1/2 unchanged for Slice 3, with a citation reviewers can follow back to the Slice 2 mapping? [Consistency, Spec §FR-020, Spec §User Story 1 acceptance scenario 6, Spec §SC-016]
- [ ] CHK104 Does the spec confirm that the per-disposition emission decisions (Phone Call activity yes/no, queue-status update yes/no, Task yes/no) are preserved-from-Slice-1/2 unchanged for Slice 3? [Consistency, Spec §FR-020, Spec §User Story 1 acceptance scenario 6]
- [ ] CHK105 Is the `blocked` disposition's `new_status` value defined consistently with the FR-023 "approved blocked / status / error field writes" rule (no contradiction between disposition-state and queue-status field)? [Consistency, Spec §FR-019, Spec §FR-023]
- [ ] CHK106 Does the spec confirm provider-rejected dial cases (FR-012) "advance the Dataverse queue per the existing per-disposition mapping for blocked / failed cases" — and is the exact disposition (blocked vs. failed) pinned or explicitly deferred? [Ambiguity, Spec §FR-012]

## Audit-Record Schemas

- [ ] CHK107 Is the Callbacks Audit Log schema specified enough to implement (key `(session_id, provider_event_id)`, receipt timestamp, callback type, normalized event produced, optional conflicting-late audit row)? [Completeness, Spec §Key Entities > Callbacks Audit Log]
- [ ] CHK108 Is the Conflicting Event Audit Record schema specified enough to implement (key `(session_id, provider_event_id)`, finalized disposition reference, late callback contents)? [Completeness, Spec §FR-027]
- [ ] CHK109 Is the Shadow STT Discrepancy Record schema specified enough to implement (session ID, field(s) that disagreed, live values, shadow values, classification, optional review-task reason code)? [Completeness, Spec §Key Entities > Shadow STT Discrepancy Record]
- [ ] CHK110 Are audit-record file formats either pinned or explicitly deferred to plan (the spec defers run-report file format, shadow STT artifact filename pattern, callbacks-audit-log file format — confirm this is intentional)? [Assumption, Spec §Deferred to Implementation Plan > Run-report and artifact layout]
- [ ] CHK111 Does the spec confirm audit records contain no secrets (FR-035 applies to audit artifacts as well as the run report)? [Consistency, Spec §FR-035, Spec §SC-018]
- [ ] CHK112 Is the relationship between Write-Back Progress Ledger entries and Phone Call activity / Task / queue-status / attempt-count writes defined so reviewers know what the ledger persists to support resume? [Completeness, Spec §FR-022]

## Scenario Class — Primary

- [ ] CHK113 Does the spec define entity state at the end of a happy-path User Story 1 run for every entity touched (Queue Item updated, Session finalized, Phone Call activity payload created, Queue-status update payload applied, Task payload created when warranted, Idempotency Key stamped, Callbacks Audit Log populated, Run Report produced, transcript artifact written per retention policy)? [Completeness, Spec §User Story 1, Spec §FR-020]
- [ ] CHK114 Does the spec define entity state at the end of an `interested_email_captured` outcome (captured email field populated on normalized result; one callback / follow-up Task created with the captured email)? [Completeness, Spec §FR-017, Spec §User Story 1 acceptance scenario 2]
- [ ] CHK115 Does the spec define entity state at the end of an `interested_callback_requested` outcome (`callback_requested` true, `preferred_callback_window` populated; one callback Task created)? [Completeness, Spec §FR-017, Spec §User Story 1 acceptance scenario 1]

## Scenario Class — Alternate

- [ ] CHK116 Does the spec define entity state after a rehearsal / readiness run (Telephony Readiness Report produced, planned write-back artifacts produced locally, ZERO Dataverse records created or updated, ZERO SignalWire calls placed, real provider call ID marked as not-yet-assigned)? [Completeness, Spec §FR-002, Spec §User Story 2]
- [ ] CHK117 Does the spec define entity state when shadow STT is disabled (no Shadow Transcript, no Shadow STT Discrepancy Record; Run Report records shadow STT was disabled)? [Completeness, Spec §FR-032, Spec §User Story 6 acceptance scenario 5]
- [ ] CHK118 Does the spec define entity state when transcript retention is summary-only or pointer-only (no full transcript file written; session-result still includes summary, retention mode, persona version, runtime/model identity; shadow transcript follows same policy; discrepancy records retained regardless)? [Completeness, Spec §FR-033, Spec §FR-034, Spec §Edge Cases > Transcript retention is summary-only or pointer-only]

## Scenario Class — Exception / Error

- [ ] CHK119 Does the spec define entity state when telephony readiness fails (Telephony Readiness Report names the failing check; no SignalWire call placed; no attempt consumed; no Phone Call activity; Dataverse queue unchanged beyond approved blocked-status write)? [Completeness, Spec §FR-011]
- [ ] CHK120 Does the spec define entity state when real-dial phone-number validation fails (Telephony Readiness Report names the phone-format failure; no SignalWire call; no attempt; no Phone Call activity)? [Completeness, Spec §FR-010, Spec §Edge Cases > Real-dial phone-number validation failure]
- [ ] CHK121 Does the spec define entity state when provider-rejected dial occurs (no real provider call ID assigned; no attempt; no Phone Call activity; Run Report records the provider-rejected-dial failure; queue-status advanced per blocked / failed mapping)? [Completeness, Spec §FR-012]
- [ ] CHK122 Does the spec define entity state when callback authentication fails (callback rejected at transport; no normalized event; no state mutation; no audit entry that includes secrets)? [Completeness, Spec §FR-008, Spec §FR-035]
- [ ] CHK123 Does the spec define entity state when the shadow STT lane fails or times out (Live call entities unaffected; Run Report records the shadow-lane failure; no Shadow STT Discrepancy Records for the missing-shadow case)? [Completeness, Spec §FR-029, Spec §User Story 6 acceptance scenario 6]
- [ ] CHK124 Does the spec define entity state when a Dataverse metadata mismatch is detected mid-run (live verification fails; run exits before dial; reusing Slice 2 lightweight live verification behavior)? [Completeness, Spec §Edge Cases > Dataverse metadata drift]
- [ ] CHK125 Does the spec define entity state when a CRM queue item changes between claim and write-back (high-confidence values preserved; write-back stops before final status update; conflict reported for review — Slice 2 behavior reused)? [Completeness, Spec §Edge Cases > CRM queue item changed by a human between claim and write-back]

## Scenario Class — Recovery (Including Rollback Where State Mutates)

- [ ] CHK126 Does the spec define entity state when a duplicate SignalWire status callback arrives (Session state unchanged; normalized result unchanged; attempt count unchanged; Dataverse write-back unchanged; Callbacks Audit Log gains one row)? [Completeness, Spec §FR-021, Spec §User Story 4 acceptance scenario 1]
- [ ] CHK127 Does the spec define entity state when out-of-order status callbacks arrive (normalized event stream still produces a single coherent disposition; Run Report records the out-of-order delivery)? [Completeness, Spec §FR-005, Spec §User Story 4 acceptance scenario 2]
- [ ] CHK128 Does the spec define entity state when a conflicting-late callback arrives after finalization (finalized disposition preserved; normalized result preserved; attempt count preserved; no new write-back; Conflicting Event Audit Record created)? [Completeness, Spec §FR-027, Spec §Edge Cases > delivered after disposition finalized]
- [ ] CHK129 Does the spec define entity state on a transient Dataverse write failure followed by in-run retry (one Phone Call activity in Dynamics; one Task at most; one queue-status transition; one attempt-count increment; Write-Back Progress Ledger updated)? [Completeness, Spec §FR-022, Spec §User Story 7 acceptance scenario 1]
- [ ] CHK130 Does the spec define entity state on retry-budget exhaustion followed by CLI re-invocation (Write-Back Progress Ledger drives resume of only the missing writes; no duplicates of any already-written CRM record)? [Completeness, Spec §FR-022, Spec §User Story 4 acceptance scenario 7]
- [ ] CHK131 Does the spec define entity state on orchestrator restart between SignalWire `completed` callback and Dataverse write-back (Real Provider Call ID preserved; resume only the missing writes)? [Completeness, Spec §User Story 7 acceptance scenario 4]
- [ ] CHK132 Does the spec define entity state on live-call abandonment (Live-Call Abandonment Outcome produced; queue item leaves `in_progress`; Slice 2 resume path applies to any partial write-back)? [Completeness, Spec §FR-026]
- [ ] CHK133 Does the spec define entity state when re-invoking the CLI for an already-finalized + already-written-back session (no duplicate Phone Call activity, Task, queue-status transition, or attempt-count increment)? [Completeness, Spec §User Story 4 acceptance scenario 9]
- [ ] CHK134 Does the spec define entity state when the resume path runs but transcript retention disables the transcript artifact (resume runs the missing CRM writes from local audit artifacts; absence of transcript file is not an error)? [Completeness, Spec §Edge Cases > Resume after a real call when retention policy disables the transcript artifact]

## Scenario Class — Non-Functional

- [ ] CHK135 Is the local-audit retention floor (>= 90 days for correlation rows and progress rows) measurable at the entity level (e.g., a created-at timestamp on each audit row enables retention enforcement)? [Measurability, Spec §FR-022, Spec §Assumptions > Local artifact retention]
- [ ] CHK136 Is the no-secrets-in-artifacts guarantee a schema-level invariant (no entity attribute holds SignalWire / real-time AI provider / shadow STT / Dataverse credentials)? [Completeness, Spec §FR-035, Spec §SC-018]
- [ ] CHK137 Is the redaction policy (default-on, runs before any transcript artifact is written) defined as an entity-level invariant on the Transcript and Shadow Transcript artifacts? [Completeness, Spec §FR-033, Spec §Edge Cases > Default-on redaction applied to a Slice 3 transcript]
- [ ] CHK138 Is "auto-deletion of audit artifacts is forbidden; pruning is a manual operator action" stated as a property of the audit-artifact entities? [Completeness, Spec §Assumptions > Local artifact retention]
- [ ] CHK139 Are deployment-configurable values (live-call abandonment timeout default, silence-after-connection timeout default, shadow STT enable / disable, discrepancy policy, transcript retention mode) each tied to an entity or configuration surface so reviewers can confirm each is parameterized? [Completeness, Spec §FR-013, Spec §FR-026, Spec §FR-032, Spec §FR-033, Spec §Assumptions]
- [ ] CHK140 Is the Configured Real-time AI Provider entity's recorded-for-audit attribute set (provider name + model version) sufficient to satisfy the FR-016 reproducibility goal, or is additional model-config attribute coverage needed? [Completeness, Spec §FR-016, Spec §Key Entities > Configured Real-time AI Provider]

## Round 2 — Post-Amendment Validation (2026-05-25)

The items below validate the Round 2 spec amendments and the new concepts they introduce. Items reference Round 1 CHK IDs where they explicitly close or re-test a previously-flagged [Gap].

- [ ] CHK141 Is the rejected-by-authentication audit log added to Key Entities (or explicitly stated as a sub-record of the existing Callbacks Audit Log) so an inspector knows whether it is a distinct entity or a partition of an existing one? [Completeness, Spec §FR-008, Spec §Key Entities > Callbacks Audit Log]
- [ ] CHK142 Is the rejected-by-authentication audit log's schema (at minimum `(received_at, source metadata)`) defined precisely enough that an implementer knows which fields are required vs. optional and which fields are forbidden (verification secret, callback body)? [Completeness, Spec §FR-008]
- [ ] CHK143 Is the distinction between the rejected-by-authentication audit log and the (existing) duplicate / out-of-order callbacks audit log defined at the data-model level (separate file, separate table, separate index, or separate record-type discriminator)? [Clarity, Spec §FR-008, Spec §Key Entities > Callbacks Audit Log]
- [ ] CHK144 Is the rejected-by-authentication audit row schema explicit that the verification secret MUST NOT appear AND the callback body MUST NOT appear, so a reviewer can confirm the schema is forgery-evidence-only? [Completeness, Spec §FR-008]
- [ ] CHK145 Is the `shadow_lane_truncated` event modeled as a row in the Shadow STT Lane / Shadow Transcript entity or as a distinct entity, so the data model unambiguously locates the record? [Clarity, Spec §FR-029, Spec §Key Entities > Shadow STT Lane / Shadow Transcript]
- [ ] CHK146 Is the `shadow_lane_truncated` event schema specified enough that an inspector can distinguish it from a regular Shadow STT Discrepancy Record (e.g., a type/event discriminator field, a "post-finalization" flag, or a distinct record-type)? [Completeness, Spec §FR-029, Spec §Key Entities > Shadow STT Discrepancy Record]
- [ ] CHK147 Is the `shadow_lane_truncated` event's audit-only nature reflected in the data model (no Dataverse correlation field, no `new_status` mapping, no Task reason code)? [Consistency, Spec §FR-029, Spec §FR-030]
- [ ] CHK148 Is the resume-operator identity recording on the Run Report defined as a fixed shape (e.g., two distinct fields `original_operator` + `resuming_operator` vs. an ordered array of `operator_identities`) so multi-resume scenarios are unambiguous? [Clarity, Spec §FR-016, Spec §FR-036]
- [ ] CHK149 Does the data model define how the resume-operator identity field on the Run Report scales across multiple resume invocations of the same session (one resume vs. N resumes — is it append-only, last-wins, or single-pair-only)? [Completeness, Spec §FR-016, Spec §FR-036]
- [ ] CHK150 Is the local-session-record's operator identity field defined as immutable on resume (the original operator is preserved on the session record per FR-016), so a reviewer can confirm no overwrite-on-resume semantics? [Completeness, Spec §FR-016]
- [ ] CHK151 Is the PHI redaction marker (the FR-015 "tag-and-redact" obligation) visible in the data model on each covered artifact (full transcript file, session-result `summary`, shadow STT transcript, shadow STT discrepancy records) so an inspector can tell a span was redacted because of PHI vs. because of the standard `[REDACTED]` rule? [Completeness, Spec §FR-015, Spec §FR-033]
- [ ] CHK152 Is the transcript pointer entity (and its metadata) explicitly excluded from the PHI tag-and-redact obligation at the data-model level, preserving the FR-033 "pointer remains machine-readable for resume / inspection" rule? [Consistency, Spec §FR-033, Spec §FR-015]
- [ ] CHK153 Does the data model differentiate the standard default-on `[REDACTED]` policy marker from the new PHI-volunteered marker (so an audit reader can answer "was this transcript span redacted because of PHI, or because of the default policy?") — or is a single marker the intended design? [Clarity, Spec §FR-015, Spec §FR-033]
- [ ] CHK154 Are the per-disposition `new_status` mapping values (FR-020) consistent with the DNC-write-first ordering (FR-024) at the data-model level — i.e., the `do_not_call` `new_status` value is unchanged and the ordering refers only to the field-write sequence within the queue-status-update operation? [Consistency, Spec §FR-020, Spec §FR-024]
- [ ] CHK155 Is the four-operation count (FR-020) reconcilable at the data model with the DNC opt-out field write being a field-level variant of the queue-status update (no new entity, no new payload, no new write-back operation)? [Consistency, Spec §FR-020, Spec §FR-024] (Resolves CHK047 [Conflict] from requirements.md.)
- [ ] CHK156 Are the additive `shadow_stt_discrepancy` reason code (Slice 1 enumeration extension) and the new `shadow_lane_truncated` audit event reconcilable with the existing Slice 1 / Slice 2 enumerations (no duplicate code, no shadowed name, no semantic collision)? [Consistency, Spec §FR-029, Spec §FR-031, Spec §Key Entities > Preserved Slice 1 / Slice 2 Entities]
- [ ] CHK157 Is the rejected-by-authentication count surfaced on the Run Report defined as a derived count over the rejected-by-authentication audit log (not a separately-incremented Run-Report counter that could drift from the audit log)? [Consistency, Spec §FR-008, Spec §FR-036]
- [ ] CHK158 Is the Run Report's `telephony_readiness_summary` field defined enough that an inspector knows it lists one entry per FR-009 readiness check with its result (vs. a free-text blob)? [Completeness, Spec §FR-036, Spec §FR-009] (Resolves CHK012 [Conflict] from observability — FR-036 / Key Entities Run Report field-list mismatch.)
- [ ] CHK159 Does the Run Report data model list the rejected-by-authentication count alongside the other audit-row counts (callbacks audit / conflicting-callbacks audit) so the Run Report's audit-counts section is internally complete? [Completeness, Spec §FR-036, Spec §FR-008]
- [ ] CHK160 Is the post-finalization grace window's audit trail (e.g., grace-window started / grace-window elapsed / shadow event arrived during grace) reflected in the data model so the resume / inspection path can reconstruct why a `shadow_lane_truncated` event was recorded? [Completeness, Spec §FR-029]
- [ ] CHK161 Are the local-only operator identity fields (original + resuming) confirmed absent from the Dataverse Queue Item, Phone Call activity payload, Queue-status update payload, and Task payload schemas at the data-model level (per FR-016 local-only rule)? [Consistency, Spec §FR-016, Spec §FR-036]
- [ ] CHK162 Does the data model define the resume-on-`answered`-but-no-terminal-event finalization (FR-026) as updating the existing Live-Call Abandonment Outcome entity (not as a new entity), preserving the entity inventory? [Consistency, Spec §FR-026, Spec §Key Entities > Live-Call Abandonment Outcome]

## Round 3 — Post-Plan Validation (2026-05-25)

The items below validate the Phase-1 plan-side artifacts (plan.md, research.md, data-model.md, contracts/, quickstart.md) generated after Rounds 1-2 closed. Items cite [Spec §...], [Plan §...], [Research §<N>], [Data-Model §...], [Contract: <name>], [Quickstart §<N>] as traceability markers, plus [Gap] / [Ambiguity] / [Conflict] when surfacing new issues. Round 1/2 CHK IDs are cross-referenced where Round 3 explicitly re-validates a prior item against the new plan-side content.

- [ ] CHK163 Does the `data-model.md §1.1 SignalWireDial` field table fully specify each field's type, nullability rules, and source (config vs. queue item vs. SignalWire response), so an implementer can build the SQLite table from the entity alone? [Completeness, Data-Model §1.1]
- [ ] CHK164 Is the §1.1 `SignalWireDial` uniqueness rule `(session_id, provider_call_id)` consistent with the §3 SQLite schema (where `sessions.provider_call_id` is the relevant column) and with the FR-006 "one real provider call ID per dialed call attempt" statement? [Consistency, Data-Model §1.1, Data-Model §3, Spec §FR-006]
- [ ] CHK165 Does the §1.2 `CallEvent.event_type` enum (`connected | no_answer | voicemail | failed | completed | callback_requested`) match the FR-005 normalized event set exactly, with `provider_intermediate_state` clearly marked as informational-only? [Consistency, Data-Model §1.2, Spec §FR-005]
- [ ] CHK166 Are the §1.2 `CallEvent` boolean flags (`out_of_order`, `late_after_finalization`) specified precisely enough that an implementer knows the rules for setting each (received_at comparison vs. session-finalization check)? [Clarity, Data-Model §1.2, Spec §FR-027]
- [ ] CHK167 Does the §1.3 `CallbacksAuditLog.raw_callback_body` field's "stored only if retention policy allows; subject to redaction" caveat align with FR-033's enumerated artifact list (transcript + summary + shadow transcript + shadow discrepancy records) — is the raw callback body an additional artifact that needs redaction-policy treatment, and is that addressed? [Gap, Data-Model §1.3, Spec §FR-033]
- [ ] CHK168 Is the §1.4 `RejectedAuthCallbackLog` schema enumeration `(received_at, session_id, source_metadata, http_status)` consistent with the §3 SQLite `CHECK (http_status = 401)` constraint AND with the contracts/rejected-auth-audit-log.md schema, with no field drift across the three locations? [Consistency, Data-Model §1.4, Data-Model §3, Contract: rejected-auth-audit-log.md]
- [ ] CHK169 Are the §1.4 explicit exclusions ("MUST NOT contain: the verification secret, the callback body, the failed signature value") complete enough that an implementer cannot accidentally include a field that carries any of these via, e.g., a `request_metadata` JSON column that would otherwise be a natural addition? [Completeness, Data-Model §1.4, Spec §FR-008, Spec §Clarifications Round 2 Q9]
- [ ] CHK170 Does the §1.6 `ShadowSTTLane` `provider_name` field's nullability (`str | null`) correctly model the disabled-shadow case (where `enabled=False` AND `provider_name=null`), with the §3 schema and §1.6 entity table consistent? [Consistency, Data-Model §1.6, Spec §FR-032]
- [ ] CHK171 Does §1.7 `ShadowSTTDiscrepancyRecord.field` enum match the seven (or eight, counting `final_disposition`) high-value fields enumerated in FR-030 and in `shadow-stt-lane.md` "high_value_fields" enumeration exactly? [Consistency, Data-Model §1.7, Spec §FR-030, Contract: shadow-stt-lane.md]
- [ ] CHK172 Is the §1.7 `live_value` / `shadow_value` "Redacted per FR-033 + FR-015 (PHI tag-and-redact if applicable)" annotation specified clearly enough that an implementer knows BOTH the default-on `[REDACTED]` policy AND the PHI tag-and-redact pass apply BEFORE the value is persisted? [Clarity, Data-Model §1.7, Spec §FR-015, Spec §FR-033]
- [ ] CHK173 Does the §1.8 `ShadowLaneTruncatedEvent` invariant ("MUST NOT mutate the finalized disposition, MUST NOT emit a new CRM write-back payload, MUST NOT generate a `shadow_stt_discrepancy` review Task") align with the §7 invariant "Shadow lane truncation never mutates disposition" and with FR-029? [Consistency, Data-Model §1.8, Data-Model §7, Spec §FR-029]
- [ ] CHK174 Does the §1.8 `ShadowLaneTruncatedEvent.would_have_classified_as` enum (`benign | uncertain | null`) match the §1.7 `classification` enum (no third value introduced for truncated events) so the discrepancy taxonomy stays consistent? [Consistency, Data-Model §1.7, Data-Model §1.8]
- [ ] CHK175 Are the nine `TelephonyReadinessReport.check_name` enum values in §1.9 a complete enumeration of every check named in FR-009 (SignalWire credentials, source caller-id, destination phone E.164, status callback URL, media callback URL, campaign-persona-runtime mapping, Dataverse metadata, task owner mapping, eligibility) — with one entry per FR-009 check? [Completeness, Data-Model §1.9, Spec §FR-009]
- [ ] CHK176 Does the §1.10 `RunReport` field enumeration (`operator_identity`, `telephony_readiness_summary`, `rejected_auth_callbacks_count`, `shadow_stt.lane_truncated`, `per_writeback_operation_status` reflecting DNC-first) cover every Round 2 amendment to FR-036, with no Round 2 Q field left unrepresented? [Completeness, Data-Model §1.10, Spec §FR-036, Spec §Clarifications Round 2]
- [ ] CHK177 Is the §1.11 `WriteBackOperation` variant table consistent with the spec FR-020 four-operation count — i.e., NORMAL/DNC/BLOCKED/DIAL_BLOCKED are explicitly labeled as variants of `queue_status_update`, not as four separate operations? [Consistency, Data-Model §1.11, Spec §FR-020, Spec §Clarifications Round 2 Q8] (Re-validates CHK155 from Round 2.)
- [ ] CHK178 Does the §1.11 `queue_status_update.blocked` variant's "Fields updated: status, blocked_reason, attempt_count (no increment)" specification align with FR-023 (blocked-by-eligibility, no attempt increment) AND with FR-025 (attempt-count semantics, blocked eligibility MUST NOT increment)? [Consistency, Data-Model §1.11, Spec §FR-023, Spec §FR-025]
- [ ] CHK179 Does the §1.11 `queue_status_update.dial_blocked` variant's "Fields updated: status, blocked_reason" align with FR-012's provider-rejected-dial outcome where NO attempt is consumed and NO Phone Call activity is created? [Consistency, Data-Model §1.11, Spec §FR-012, Spec §FR-025]
- [ ] CHK180 Does the §1.12 `RealtimeProviderSession.runtime_name = "pipecat"` constant align with the spec FR-013 ("Pipecat real-time audio runtime adapter") and the constitution Slice 3 voice-runtime decision (Pipecat-only)? [Consistency, Data-Model §1.12, Spec §FR-013, Plan §Technical Context]
- [ ] CHK181 Is the §1.12 "MUST NOT contain credentials" note enforceable at the schema level (no field that could carry a credential), preserving FR-035's no-secrets-in-artifacts guarantee? [Completeness, Data-Model §1.12, Spec §FR-035]
- [ ] CHK182 Does the §2.1 `Session.operator_identity_original` nullability (`str | null` with `null` on first invocation) correctly model the first-invocation case AND the resume-by-different-operator case, with the §6 state-transition diagram showing both paths? [Consistency, Data-Model §2.1, Data-Model §6, Spec §Clarifications Round 2 Q12]
- [ ] CHK183 Is the §2.1 `Session.cm_writeback_started_at` field name a typo for `crm_writeback_started_at`, or is it intentionally abbreviated — does the data model define this consistently? [Ambiguity, Data-Model §2.1]
- [ ] CHK184 Does the §3 SQLite `CHECK (run_mode IN ('rehearsal', 'real_call'))` constraint match the §2.1 `Session.run_mode` enum exactly, with no value drift between the entity table and the DDL? [Consistency, Data-Model §2.1, Data-Model §3]
- [ ] CHK185 Does the §3 SQLite `CHECK (classification IN ('benign', 'uncertain'))` constraint on `shadow_stt_discrepancies.classification` match the §1.7 `ShadowSTTDiscrepancyRecord.classification` enum exactly? [Consistency, Data-Model §1.7, Data-Model §3]
- [ ] CHK186 Does the §3 SQLite `CHECK (would_have_classified_as IN ('benign', 'uncertain'))` constraint on `shadow_lane_truncated_events.would_have_classified_as` match the §1.8 enum (`benign | uncertain | null`) — does the CHECK constraint allow NULL (SQLite CHECK semantics) for the in-time / not-discrepancy case? [Consistency, Data-Model §1.8, Data-Model §3]
- [ ] CHK187 Are the §4 artifacts directory layout entries (each file with its conditional-creation rule like "only when ≥1 rejected callback received") consistent with the per-contract file-format decisions in `research.md §10`? [Consistency, Data-Model §4, Research §10]
- [ ] CHK188 Does the §6 state-transition diagram's rehearsal-mode path cover every readiness-failure exit (any single FR-009 check failing) with the correct "no dial, no mutation" outcome, matching FR-002 / FR-011? [Completeness, Data-Model §6, Spec §FR-002, Spec §FR-011]
- [ ] CHK189 Does the §6 real-call-mode state-transition diagram's `callback_loop` cover all four callback dispositions (signature fail → RejectedAuthCallbackLog; duplicate → CallbacksAuditLog no-op; late-after-finalization → ConflictingEventAuditLog; fresh → normalize → orchestrator), with no fifth case missing? [Completeness, Data-Model §6, Spec §FR-007, Spec §FR-008, Spec §FR-021, Spec §FR-027]
- [ ] CHK190 Does the §6 `crm_writeback` block's "if disposition == do_not_call: DNC field write FIRST (Q14)" line align with the §1.11 `WriteBackOperation` table's "FIRST in the write-back sequence on `do_not_call`" rule AND with `crm-writeback-dnc-first.md`'s `assemble_writeback` Protocol? [Consistency, Data-Model §6, Data-Model §1.11, Contract: crm-writeback-dnc-first.md, Spec §FR-024]
- [ ] CHK191 Does the §6 resume-invocation diagram's "if session previously received `answered` but no terminal event: finalize as failed/live_call_abandonment immediately (Q6)" match FR-026's resume contract AND the `cli-slice3.md` exit-code-6 condition? [Consistency, Data-Model §6, Spec §FR-026, Spec §Clarifications Round 2 Q6, Contract: cli-slice3.md]
- [ ] CHK192 Does the §7 invariant list ("No duplicate writes", "No secrets in artifacts", "No PHI in artifacts (caller-volunteered path)", "No operator identity in Dataverse", "DNC-first on `do_not_call`", "Four write-back operations preserved", "Non-blocking shadow STT at finalization", "Shadow lane truncation never mutates disposition", "Real-call flag required on every Dataverse mutation") cover every Slice 3 cross-cutting invariant the spec / Round 1 / Round 2 surfaced — or is an invariant missing? [Completeness, Data-Model §7, Spec §SC-008, Spec §SC-013, Spec §SC-014, Spec §SC-015, Spec §SC-016, Spec §SC-018]
- [ ] CHK193 Does the §7 "No PHI in artifacts (caller-volunteered path)" invariant explicitly enumerate the same four artifact types (transcript, summary, shadow transcript, shadow discrepancy records) that FR-015 / FR-033 enumerate — no fifth or missing artifact? [Consistency, Data-Model §7, Spec §FR-015, Spec §FR-033]
- [ ] CHK194 Does the §7 "Real-call flag required on every Dataverse mutation" invariant — enforced via `Session.run_mode = 'real_call'` — match the `crm-writeback-dnc-first.md` "The adapter MUST refuse to perform any write when `Session.run_mode != 'real_call'`" rule AND with FR-001 / FR-022 / Round 2 Q13? [Consistency, Data-Model §7, Contract: crm-writeback-dnc-first.md, Spec §FR-001, Spec §FR-022]
- [ ] CHK195 Does the §5 "reused unchanged" entity list correctly omit every entity that Slice 3 actually extends (`Session`, `NormalizedResult`, `PhoneCallActivityPayload`, `RedactionPolicy`) — confirming no extended entity is mis-listed as unchanged? [Consistency, Data-Model §5, Data-Model §2.1, Data-Model §2.2, Data-Model §2.3, Data-Model §2.5]
- [ ] CHK196 Are the §2.4 `IdempotencyKey` "reused unchanged" claim AND the §2.5 `RedactionPolicy` Round 2-extended claim mutually consistent — i.e., extending the redaction policy does NOT require a new idempotency-key shape because both apply at orthogonal write boundaries? [Consistency, Data-Model §2.4, Data-Model §2.5, Spec §FR-021, Spec §FR-033]
- [ ] CHK197 Is the §1.3 `CallbacksAuditLog`'s lack of a uniqueness constraint ("duplicates are recorded") consistent with the §1.2 `CallEvent`'s `(session_id, provider_event_id)` dedup key — i.e., the audit log records every receipt (including duplicates) but the normalized `CallEvent` is deduplicated for orchestrator consumption? [Consistency, Data-Model §1.2, Data-Model §1.3, Spec §FR-007, Spec §FR-021]
- [ ] CHK198 Does the data-model define the JSONL line format for each of the six JSONL file types (callbacks_audit, rejected_auth_callbacks, conflicting_callbacks_audit, shadow_discrepancies, plus implicit per-record schemas) consistently enough that an inspector can grep / jq across them with predictable field names? [Completeness, Data-Model §1.3, Data-Model §1.4, Data-Model §1.5, Data-Model §1.7, Data-Model §4]
- [ ] CHK199 Re-validating CHK148-CHK150 from Round 2: does `Session.operator_identity_original` (immutable on resume, preserved from first invocation) AND `Session.operator_identity_current` (overwritten on every invocation) correctly resolve the "multi-resume scenarios" ambiguity by using a single-pair model rather than an append-only array? [Clarity, Data-Model §2.1, Spec §FR-016, Spec §Clarifications Round 2 Q12]
- [ ] CHK200 Does the §3 `ALTER TABLE sessions ADD COLUMN provider_call_id TEXT` migration preserve backwards-compatibility for pre-Slice-3 reads (where `mock_provider_call_id` was the column name) — is there a documented read-path that handles both? [Gap, Data-Model §3, Spec §FR-006, Spec §FR-018]

## Notes

- Items marked [Gap] indicate the spec should be amended or a Deferred-to-Plan note should be added.
- Items marked [Ambiguity] / [Conflict] / [Assumption] indicate clarifying language is needed.
- >=80% of items reference a spec section or a quality marker for traceability.
