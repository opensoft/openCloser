# Feature Specification: Slice 2 — Mock Call, Real CRM

**Feature Branch**: `002-mock-call-real-crm`

**Created**: 2026-05-22

**Status**: Draft

**Input**: User description: "Create Feature 002: Slice 2 - Mock Call, Real CRM. Generate a Speckit feature spec for implementing Slice 2, where Dataverse is real but call transport and persona remain mocked/scripted. Preserve Slice 1 contracts unless the OpenSpec change explicitly says otherwise. Authoritative context: openspec/changes/plan-slice-2-real-crm/{proposal,design,tasks}.md, openspec/changes/plan-slice-2-real-crm/specs/mock-call-real-crm/spec.md, docs/prds/openCloser_MVP.md, docs/architecture/openCloser_Architecture.md, specs/001-mock-call-mock-crm/contracts/*.md."

## Constitution Alignment *(mandatory)*

- **CRM control plane**: Slice 2 makes the constitution's CRM-first principle real. Dynamics 365 / Dataverse becomes the operational source of truth: the queue item is read from a Dataverse-owned queue representation, and every outcome is written back as a Dataverse Phone Call activity, Dataverse queue-status / DNC / attempt fields, and a Dataverse Task. The local store is demoted to session, audit, artifact, and correlation-ID storage only; it no longer owns queue lifecycle. No parallel campaign UI, custom task queue, or replacement CRM is introduced — Dynamics remains the operator surface.
- **Thin slice**: Target slice is **Slice 2 — Mock Call, Real CRM** from the constitution's binding MVP order. The smallest independently demonstrable outcome is: one Dataverse-owned ALF queue item, from one ALF campaign, moves from `ready` to a final disposition with its outcome written back to Dynamics — using the unchanged mock call transport and scripted persona, so this slice isolates CRM-integration risk before real telephony.
- **Boundaries**: The five Slice 1 boundaries are preserved. The Dataverse CRM adapter is a new concrete implementation behind the existing write-back interface (the four operations: Phone Call activity emission, queue-status update emission, Task emission, write-back assembly) — Dataverse field names, lookups, option-set values, and owner/team IDs MUST be translated inside the adapter and MUST NOT leak into the orchestrator, eligibility evaluator, mock transport, or persona. A new Dataverse queue loader sits behind the existing queue-item contract consumed by the eligibility evaluator. A new redaction boundary sits between transcript text and artifact disk writes. The mock call transport and ALF appointment-setter persona are unchanged except for adding fixture pre-validation to call placement.
- **Safety and human handoff**: Persona safety behavior is unchanged from Slice 1 (AI-on-behalf-of-Medx disclosure, non-clinical scope, no PHI collection, immediate DNC stop, `needs_human_review` escalation with a reason code). Slice 2 adds two safety gates: (1) a default-on transcript `RedactionLayer` before any transcript disk write, because even scripted CRM demos can involve real business contacts; (2) callback and review Tasks written to Dynamics MUST be assigned to a configured owner/team so human follow-up has a real, accountable destination. DNC outcomes MUST update Dataverse DNC/opt-out fields and MUST NOT create a follow-up Task.
- **Auditability**: Every processed Dataverse queue item MUST produce a traceable session ID, the eligibility decision, the mock provider call ID when a call was placed, the persona version, started/ended timestamps, and a final disposition — plus the CRM correlation identifiers needed to detect and recover from duplicate or failed Dataverse writes. Duplicate mock provider events, repeated CLI invocations for the same session, and write-back retries after a transient Dataverse error MUST NOT create duplicate Phone Call activities, duplicate Tasks, duplicate queue-status transitions, or duplicate attempt-count increments. Live Dataverse table and field metadata MUST be verified before any write, and existing high-confidence CRM values outside the approved Slice 2 update fields MUST be preserved.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Process one Dataverse queue item end-to-end with real CRM write-back (Priority: P1)

A developer/operator runs the Slice 2 command, in write-enabled mode, against one ALF queue item that lives in Dynamics / Dataverse. The system claims that one CRM queue item, evaluates eligibility from the mapped CRM fields, runs the unchanged mock call transport and scripted ALF persona, produces the same normalized session result proven in Slice 1, and writes the outcome back to Dynamics as a Phone Call activity, queue-status / DNC / attempt-field updates, and (when the disposition warrants it) a callback or review Task assigned to a configured owner.

**Why this priority**: This is the entire point of Slice 2 and the constitution's CRM-first principle becoming operational. Until one Dynamics queue item can move `ready` → final disposition with real write-back, the team cannot judge whether the proven loop survives a real CRM. It is the first slice where Dynamics is the source of truth.

**Independent Test**: Configure a verified Dataverse mapping against one test campaign and one `ready` test queue item, run the Slice 2 CLI command in write-enabled mode with an interested-callback transport+conversation fixture, and confirm in Dynamics: the queue item's status/attempt/last-disposition/last-session fields updated, a Phone Call activity created, and a callback Task created and assigned to the configured owner — plus the local session-result artifact and transcript pointer.

**Acceptance Scenarios**:

1. **Given** a `ready` Dataverse queue item with the required Account/facility, phone, attempt count, DNC flag, timezone (or default), and max-attempts fields, and a scripted fixture ending in `interested_callback_requested`, **When** the operator runs the command in write-enabled mode, **Then** the Dataverse Phone Call activity is created, the queue-status / attempt / last-disposition / last-session fields are updated, and a callback Task is created in Dynamics assigned to the configured callback owner.
2. **Given** the same queue item and a fixture ending in `needs_human_review`, **When** the operator runs the command, **Then** the review Task created in Dynamics is assigned to the configured review owner and carries the human-review reason code.
3. **Given** the same queue item and a fixture ending in `do_not_call` (or a mid-call opt-out), **When** the operator runs the command, **Then** the adapter updates the Dataverse DNC/opt-out and queue-status fields and does NOT create any callback or review Task.
4. **Given** a Dataverse queue item that is NOT in the configured callable status, **When** the operator runs the command, **Then** the system records a blocked eligibility result, does NOT start the mock call transport, and writes only the configured blocked/status/error fields to Dataverse — no Phone Call activity and no Task.
5. **Given** any disposition reached in Slice 2, **When** the adapter writes back, **Then** the per-disposition emission decisions and the queue `new_status` value match the Slice 1 write-back contract exactly (no Slice-2-specific divergence).

---

### User Story 2 — Rehearse the run in dry-run mode with zero CRM writes (Priority: P1)

Before any write touches Dynamics, the operator runs the exact same queue item through the Slice 2 command in dry-run mode. The system validates the Dataverse field mapping, exercises eligibility, the mock call, and the persona, and produces the planned write-back artifacts (what it *would* write) — but performs zero create or update operations against Dataverse.

**Why this priority**: CRM writes are hard to roll back, and the constitution requires CRM data updates to be verified. Dry-run is the safety rehearsal that makes the write-enabled run (Story 1) trustworthy; the migration plan explicitly runs dry-run before write-enabled. It is independently valuable as the demo posture that needs no live write permissions.

**Independent Test**: Run the Slice 2 command in dry-run mode against one Dataverse queue item, confirm the planned write-back artifacts (planned Phone Call activity, planned queue-status update, planned Task) are written locally as inspectable artifacts, and confirm — by inspecting Dynamics — that no CRM record was created or modified.

**Acceptance Scenarios**:

1. **Given** a `ready` Dataverse queue item and a verified mapping, **When** the operator runs the command in dry-run mode, **Then** the system produces planned write-back artifacts locally and creates or updates zero Dataverse records.
2. **Given** a dry-run completes, **When** the operator inspects the planned write-back artifacts, **Then** they show the same payload content (Phone Call activity, queue-status update, Task when applicable) that a write-enabled run would have sent.
3. **Given** the configured mapping is incomplete, **When** the operator runs a dry-run, **Then** the dry-run still surfaces the mapping gap (it does not silently pass) so the gap is found before a write-enabled run.

---

### User Story 3 — Block write-enabled processing when Dataverse metadata cannot be verified (Priority: P2)

Before write-enabled processing, the system inspects and records the live Dataverse metadata it depends on (the queue item representation, Account, Contact, Campaign, Phone Call activity, Task, owner/team, status values, DNC/opt-out fields, attempt counters, last disposition, last session ID, last error). If any required table, field, lookup, or option-set value cannot be verified, Slice 2 setup fails and reports the missing mapping — without creating or updating any CRM record.

**Why this priority**: Dataverse field logical names and option-set values vary by environment; writing to the wrong field or inventing duplicate schema is a serious, hard-to-undo CRM error. This gate protects every later story. It is lower than P1 only because Stories 1 and 2 cannot be demonstrated at all until a verified mapping exists, so this is a precondition rather than the headline outcome.

**Independent Test**: Point the system at a Dataverse environment that is missing one required field or option-set value, run Slice 2 setup/readiness validation, and confirm it fails with an operator-visible report naming the missing mapping and that no CRM record was touched. Repeat with a complete mapping and confirm setup passes.

**Acceptance Scenarios**:

1. **Given** a required Dataverse table, field, lookup, or option-set value cannot be verified, **When** Slice 2 setup runs, **Then** it fails before write-enabled processing and reports the missing mapping, creating or updating no CRM records.
2. **Given** required Dataverse credentials or non-secret mapping configuration are missing, **When** startup/readiness validation runs, **Then** it fails with a clear message identifying what is missing.
3. **Given** a Dataverse record already holds a non-empty high-confidence value in a field outside the approved Slice 2 update set, **When** the system writes back, **Then** that value is left unchanged and no overwrite is recorded in the write-back payload.

---

### User Story 4 — Idempotent CRM write-back across duplicate events and retries (Priority: P2)

The operator exercises duplicate mock provider events, a repeated CLI invocation for the same session, and a write-back retry following a transient Dataverse error. In every case the system MUST NOT create duplicate Dynamics records.

**Why this priority**: Slice 1 proved idempotency against a local store; Slice 2 must prove it against a real CRM where a duplicate Phone Call activity or Task is operator-visible and embarrassing. Getting this right here is the foundation for safely adding real telephony (which introduces real duplicate provider callbacks) in Slice 3.

**Independent Test**: For each case — duplicate mock event ID, repeated CLI run for the same session, and a forced transient Dataverse write failure followed by a retry — run the path and confirm Dynamics holds exactly one Phone Call activity, at most one Task, one queue-status transition, and one attempt-count increment.

**Acceptance Scenarios**:

1. **Given** the mock transport emits the same event ID more than once for a CRM-backed session, **When** the run processes the duplicate, **Then** the second delivery is a no-op for both local session state and Dataverse write-back state.
2. **Given** a Dataverse write attempt fails after an idempotency key has been recorded or a CRM correlation identifier is known, **When** the write-back is retried, **Then** the retry reuses the existing correlation and creates no second Phone Call activity and no second Task.
3. **Given** a session already finalized and written back, **When** the operator re-invokes the CLI for the same session, **Then** no duplicate Phone Call activity, Task, queue-status transition, or attempt-count increment is produced in Dynamics.

---

### User Story 5 — Reject malformed mock transport fixtures before any state or attempt is consumed (Priority: P2)

The operator selects a transport fixture that is malformed — invalid JSON, no `events` array, or an event missing a required identity field. The mock transport MUST detect this during call placement, before the orchestrator mutates any session state, the Dataverse queue status, or the attempt count. The run fails with an operator-visible error and leaves no partial session and no consumed attempt.

**Why this priority**: This folds in the one open GitHub issue (#2): today a malformed fixture can leave partial session state and a consumed attempt. In Slice 2 a consumed attempt is a real Dynamics field change, so the failure mode is worse. Slice 2 still depends on fixtures, so the fix belongs here.

**Independent Test**: Run the Slice 2 command with (a) an invalid-JSON fixture, (b) a fixture with no `events` array, and (c) a fixture whose event is missing `type` / `event_id` / `timestamp`. In each case confirm the run fails with a clear error and that no session row was created, no attempt was consumed, and the Dataverse queue item is unchanged.

**Acceptance Scenarios**:

1. **Given** the configured transport fixture is invalid JSON, **When** the operator runs the command, **Then** the run fails with an operator-visible error and creates no session row, consumes no attempt, and makes no Dataverse queue update.
2. **Given** the fixture lacks an `events` array, **When** the operator runs the command, **Then** the same no-mutation failure behavior holds.
3. **Given** the fixture contains an event missing a required `type`, `event_id`, or `timestamp` field, **When** the operator runs the command, **Then** the same no-mutation failure behavior holds.

---

### User Story 6 — Redact transcript artifacts before they are written to disk (Priority: P3)

When the system writes a transcript artifact, the transcript text first passes through a configurable redaction layer. The default Slice 2 policy replaces configured sensitive patterns with `[REDACTED]`. A deployment may instead select summary-only retention, in which case no full transcript file is written at all.

**Why this priority**: The constitution requires minimizing sensitive data, and Slice 2 demos run against real business contacts in Dynamics. It is P3 because the normalized result, summary, and CRM write-back — the demonstrable loop — work without it; redaction hardens the artifact path rather than enabling the loop.

**Independent Test**: Run a scripted conversation whose transcript contains a value matching the configured redaction policy, confirm the written transcript artifact stores `[REDACTED]` in that value's place and the session-result artifact points to the redacted file. Re-run with summary-only retention configured and confirm no full transcript file is written while the session-result artifact still contains the summary and the retention mode.

**Acceptance Scenarios**:

1. **Given** transcript text contains a value matching the configured redaction policy, **When** the transcript artifact is written, **Then** the artifact stores `[REDACTED]` in place of that value and the session-result artifact points to the redacted transcript file.
2. **Given** the deployment configures summary-only transcript retention, **When** the run completes, **Then** no full transcript file is written and the session-result artifact still includes the normalized summary and the retention mode.
3. **Given** redaction is configured as a no-op policy, **When** the transcript artifact is written, **Then** the artifact contract (summary plus transcript pointer) is unchanged from Slice 1.

---

### Edge Cases

- **Transient Dataverse error mid-write-back**: e.g., the Phone Call activity is created but the Task create fails. A retry MUST reuse correlation identifiers and complete the missing writes without duplicating the ones that already succeeded.
- **Dataverse queue item changed by a human between claim and write-back**: the system writes only the approved Slice 2 update fields and preserves other high-confidence values; it does not blindly overwrite the whole record.
- **Required Phone Call / Task field varies by environment**: a required field that the mapping does not cover is caught by metadata verification (Story 3), not discovered at write time.
- **Non-E.164 / malformed phone number on the CRM record**: Slice 2 records a data-quality warning and continues (the mock transport does not dial); hard E.164 enforcement is deferred to Slice 3 real telephony.
- **`preferred_callback_window` captured as a free-form phrase**: the phrase is preserved in the Dataverse Task text; Slice 2 does not parse it into a structured Dataverse due date.
- **CRM queue item has no usable timezone**: the configured default timezone is applied and recorded in the eligibility decision, exactly as in Slice 1.
- **Dry-run requested but write credentials are absent**: dry-run still runs and validates mapping; absence of write credentials is not an error in dry-run mode.
- **Duplicate mock `callback_requested` event for a CRM-backed session**: the original callback Task is retained; no second Task is created in Dynamics.
- **Blocked-by-eligibility item**: only the approved blocked/status/error fields are written to Dataverse; no Phone Call activity, no Task, no attempt increment.
- **Local session/audit state diverges from CRM business state**: Dataverse is treated as the source of truth for queue lifecycle; local state is limited to session, audit, artifacts, and correlation IDs.

## Requirements *(mandatory)*

### Functional Requirements

#### Dataverse metadata verification and CRM value safety

- **FR-001**: The system MUST inspect and record the live Dataverse metadata required for Slice 2 before any write-enabled processing: the selected queue-item representation, Account, Contact (when present), Campaign (when present), Phone Call activity, Task, owner/team assignment, status values, DNC/opt-out fields, attempt counters, last disposition, last session ID, and last error.
- **FR-002**: When a required Dataverse table, field, lookup, or option-set value cannot be verified, Slice 2 setup MUST fail before write-enabled processing and report the missing mapping, without creating or updating any CRM record.
- **FR-003**: The system MUST leave non-empty high-confidence Dataverse values outside the approved Slice 2 update-field set unchanged, and MUST NOT record an overwrite of them in the write-back payload.
- **FR-004**: The recorded Dataverse field mapping (logical names, required fields, lookups, option-set values, approved update fields) MUST be captured as a documented Slice 2 mapping artifact.

#### Configuration and secrets

- **FR-005**: The system MUST load Dataverse connection secrets from environment variables (or a secret manager) and MUST NOT write secrets to logs or exported artifacts.
- **FR-006**: The system MUST read non-secret Dataverse mapping configuration (queue fields, status values, task owner mapping, run mode) from a configuration file.
- **FR-007**: The system MUST run a startup/readiness validation that fails with a clear, operator-visible message when required Dataverse mappings or credentials are missing.

#### Dataverse queue intake

- **FR-008**: The system MUST load one ALF queue item from the configured Dataverse queue source and map it into the existing queue-item contract consumed by the eligibility evaluator, without requiring a local CSV or local mock CRM queue row.
- **FR-009**: Claiming MUST be limited to one ALF campaign and one queue item per processing run in Slice 2.
- **FR-010**: The system MUST mark the Dataverse queue item as in-progress only after eligibility preconditions and run-mode rules are satisfied (a dry-run MUST NOT claim/mutate the CRM queue item).
- **FR-011**: When the selected Dataverse queue item is not in the configured callable status, the system MUST record a blocked eligibility result and MUST NOT start the mock call transport.

#### Calls remain mocked; Slice 1 contracts preserved

- **FR-012**: The system MUST use the existing fixture-driven mock call transport and the existing scripted ALF appointment-setter persona for Slice 2. No SignalWire call, Pipecat live audio path, real-time model, or real outbound traffic may be used.
- **FR-013**: The normalized session result MUST use the same deterministic persona extraction and disposition-precedence rules proven in Slice 1, and MUST support the same set of final dispositions.
- **FR-014**: The Slice 1 module contracts for the orchestrator, eligibility evaluator, mock transport, and persona MUST be preserved unchanged except for the fixture pre-validation added by FR-019; no Slice-2-specific behavior may be added to those modules.

#### Dataverse write-back adapter

- **FR-015**: The system MUST provide a Dataverse write-back adapter that implements the same four consumer-facing write-back operations as Slice 1 (Phone Call activity emission, queue-status update emission, Task emission, and write-back assembly).
- **FR-016**: Dataverse field names, required lookups, option-set values, and owner/team IDs MUST be translated inside the Dataverse adapter and MUST NOT leak into the orchestrator, eligibility evaluator, mock transport, or persona.
- **FR-017**: The per-disposition emission decisions (which of Phone Call activity / queue-status update / Task are produced) and the per-disposition queue `new_status` value MUST match the Slice 1 write-back contract exactly.
- **FR-018**: A blocked-by-eligibility queue item MUST result in only the approved Dataverse blocked/status/error field writes — no Phone Call activity and no Task.

#### Mock transport hardening (GitHub issue #2)

- **FR-019**: The mock call transport MUST validate the selected transport fixture during call placement, before the orchestrator mutates any session state, the Dataverse queue status, or the attempt count.
- **FR-020**: When the selected transport fixture is invalid JSON, lacks an `events` array, or contains an event missing a required `type`, `event_id`, or `timestamp` field, the run MUST fail with an operator-visible error and MUST NOT create a session row, consume an attempt, or update the Dataverse queue item.

#### Idempotency and error recovery

- **FR-021**: Duplicate mock provider events, repeated CLI invocations for the same session, and write-back retries MUST NOT create duplicate Dataverse Phone Call activities, duplicate Tasks, duplicate queue-status transitions, or duplicate attempt-count increments.
- **FR-022**: A duplicate mock event (same event ID) for a CRM-backed session MUST be a no-op for both local session state and Dataverse write-back state.
- **FR-023**: When a Dataverse write fails after an idempotency key has been recorded or a CRM correlation identifier is known, a retry MUST reuse the existing correlation and MUST NOT create a second Phone Call activity or Task.
- **FR-024**: The system MUST record the CRM correlation identifiers (or alternate keys) required to detect duplicate Phone Call and Task writes across retries and re-invocations.

#### Human follow-up task ownership

- **FR-025**: The system MUST populate Dataverse callback and review Task ownership from a configured default-owner-per-task-kind mapping, unless the selected CRM queue item supplies an approved owner override.
- **FR-026**: A review Task (final disposition `needs_human_review`) MUST be assigned to the configured review owner/team and MUST include the human-review reason code.
- **FR-027**: A `do_not_call` disposition (or mid-call opt-out) MUST update the Dataverse DNC/opt-out and queue-status fields and MUST NOT create a callback or review Task.

#### Transcript redaction

- **FR-028**: Transcript text MUST pass through a configurable redaction layer before any transcript artifact is written to disk. The default Slice 2 policy MUST replace configured sensitive patterns with `[REDACTED]`.
- **FR-029**: The redaction layer MUST preserve the normalized summary and the transcript-pointer artifact contract from Slice 1, including support for a no-op policy.
- **FR-030**: When the deployment configures summary-only transcript retention, the system MUST write no full transcript file, and the session-result artifact MUST still include the normalized summary and the retention mode.

#### Run modes, CLI, and demo evidence

- **FR-031**: The system MUST support a dry-run mode that validates the Dataverse mapping and produces the planned write-back artifacts while creating or updating zero Dataverse records, and a write-enabled mode that performs the actual Dataverse writes.
- **FR-032**: The system MUST provide a CLI / developer command that processes exactly one Dataverse queue item per invocation.
- **FR-033**: The system MUST produce a repeatable demo path that starts from one Dataverse queue item and ends with inspectable CRM records (the queue item, the Phone Call activity when applicable, the Task when applicable) plus local audit artifacts (the normalized session result and transcript pointer) — without requiring a custom openCloser UI.

#### Phone-number data quality

- **FR-034**: When a Dataverse queue item carries a non-E.164 or otherwise malformed phone number, the system MUST record a data-quality warning and continue processing; hard telephony-format (E.164) enforcement is deferred to Slice 3.

### Key Entities *(include if feature involves data)*

- **Dataverse Queue Item**: The CRM-owned representation of one ALF prospect to be contacted (an existing custom table, a campaign/list record, or a new custom table — determined by metadata discovery). Carries facility/Account, phone, timezone, attempt count, max attempts, DNC/opt-out, callable status, last disposition, last session ID, and last error.
- **CRM Field Mapping Artifact**: The documented, verified mapping from the Slice 1 conceptual fields to live Dataverse logical names, required fields, lookups, option-set values, and the approved Slice 2 update-field set.
- **Dataverse CRM Adapter**: The concrete write-back implementation behind the existing four write-back operations; the sole place Dataverse-specific field names, lookups, option sets, and owner/team IDs appear.
- **Dataverse Write-back Records**: The Phone Call activity, the queue-status / DNC / attempt / last-disposition / last-session / last-error field updates, and the callback or review Task — created or updated in Dynamics.
- **Task Owner Mapping**: Configuration that resolves callback and review Task ownership to a Dynamics owner or team per task kind, with an optional approved per-queue-item override.
- **Redaction Layer / Redaction Policy**: The configurable boundary that transforms transcript text before disk write (default: replace sensitive patterns with `[REDACTED]`; alternatives: no-op, or summary-only retention).
- **Run Mode**: Dry-run (validate mapping, produce planned write-back artifacts, zero CRM writes) versus write-enabled (perform Dataverse writes).
- **CRM Correlation Identifier**: The identifier(s) recorded locally that tie a session to its Dataverse Phone Call activity and Task so duplicate or retried writes can be detected.
- **Preserved Slice 1 Entities**: The queue-item contract, eligibility decision, session, mock call event, normalized result, write-back payloads, idempotency keys, and conversation/transport fixtures are reused unchanged; Slice 2 adds CRM-backed sources and a CRM-backed write-back target around them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One Dataverse-owned ALF queue item can move from `ready` to a final disposition with its outcome written back to Dynamics, with no manual intervention during the run.
- **SC-002**: The same queue item can be processed in dry-run mode, producing the planned write-back artifacts while creating or updating zero Dataverse records (verified by inspecting Dynamics).
- **SC-003**: An `interested_callback_requested` or `interested_email_captured` outcome creates exactly one callback Task in Dynamics, assigned to the configured callback owner; a `needs_human_review` outcome creates exactly one review Task assigned to the configured review owner with the human-review reason code.
- **SC-004**: A `do_not_call` outcome updates the Dataverse DNC/opt-out fields, prevents further automated attempts, and creates no follow-up Task.
- **SC-005**: 100% of duplicate mock provider events, repeated CLI invocations for the same session, and write-back retries after a transient CRM error leave Dynamics with exactly one Phone Call activity, at most one Task, one queue-status transition, and one attempt-count increment.
- **SC-006**: 100% of malformed transport fixtures (invalid JSON, missing `events` array, or an event missing a required identity field) fail before any session row, attempt increment, or Dataverse queue change.
- **SC-007**: When required Dataverse metadata cannot be verified, write-enabled processing is blocked 100% of the time, with an operator-visible report of the missing mapping and zero CRM records touched.
- **SC-008**: A blocked-by-eligibility queue item produces only the approved Dataverse blocked/status/error field writes — 0 Phone Call activities and 0 Tasks.
- **SC-009**: Transcript artifacts written during Slice 2 runs contain `[REDACTED]` in place of every value matching the configured redaction policy, and summary-only retention produces 0 full transcript files while still producing a session-result summary.
- **SC-010**: The orchestrator, eligibility evaluator, mock transport, and persona contain 0 Dataverse-specific field names or vendor payload shapes — all CRM-vendor detail is confined to the Dataverse adapter (verifiable by inspection / boundary test).
- **SC-011**: The Slice 1 write-back contract (per-disposition emission map and per-disposition `new_status`) is satisfied unchanged by the Dataverse adapter — verified by contract tests — confirming the Slice 1 forward-compatibility commitment held.
- **SC-012**: An operator can inspect the Slice 2 outcome — the updated CRM queue item, the Phone Call activity, the Task, the local session-result artifact, and the transcript pointer — without using a custom openCloser UI.

## Assumptions

- **Slice scope**: Slice 2 explicitly excludes SignalWire, Pipecat / live audio, real-time model providers, real outbound traffic, custom product UI, campaign builder, custom task queue, CRM replacement, batch processing, scheduler, multi-worker locking, Redis / Celery / Kubernetes, generalized workflow engines, opportunity creation, automated sales qualification beyond task/write-back fields, and any multi-CRM abstraction. Dataverse is the only Slice 2 CRM target. These are deferred per the constitution and the OpenSpec change.
- **Slice 1 contracts preserved**: Per the OpenSpec change (`Modified Capabilities: None`), Slice 2 adds a new CRM-backed capability and does not change Slice 1 mock-call/mock-CRM behavior. The orchestrator, eligibility, transport, and persona contracts are reused unchanged except for adding fixture pre-validation to mock-transport call placement.
- **Single campaign, single item**: Slice 2 processes one queue item from one ALF campaign per run. Concurrent claims, batch processing, and multi-campaign handling are out of scope.
- **Dataverse queue representation**: The exact table that represents the Slice 2 Call Queue Item (an existing custom table, a campaign/list record, or a new custom table) is determined during metadata discovery (FR-001) and recorded in the mapping artifact (FR-004); it is an implementation-discovery output, not a spec-level decision.
- **Dataverse field logical names and option-set values**: The exact logical names and option-set values for queue status, DNC/opt-out, attempt count, max attempts, last disposition, last session ID, and last error are discovered and verified during metadata discovery; the requirement is verification-before-write, not a pre-named field list.
- **Task ownership**: The specific Dynamics user or team that owns callback and review Tasks is deployment configuration (FR-025), not a spec decision. The spec requires owner assignment from configuration with an optional approved per-item override.
- **Non-E.164 phone numbers**: Slice 2 records a data-quality warning and continues, rather than hard-blocking, because the mock transport does not dial. Hard E.164 enforcement is mandatory before Slice 3 places a real call (per the MVP PRD).
- **`preferred_callback_window`**: Slice 2 preserves the captured callback-window phrase as free-form text in the Dataverse Task description and does not parse it into a structured Dataverse due date; due-date population is deferred until a scheduling integration exists.
- **Source of truth**: Dataverse is the source of truth for queue lifecycle (status, attempt count, DNC) in Slice 2. Local state is limited to session, audit, artifacts, and correlation identifiers.
- **Demo posture**: The dry-run mode is the safe rehearsal and the default demo posture; the write-enabled demo runs against one dedicated test campaign and one dedicated test queue record, with documented manual cleanup/rollback for the demo record.
- **GitHub issue #2**: The malformed-fixture pre-validation requirement (FR-019, FR-020) resolves GitHub issue #2; the issue is closed once that behavior is implemented and tested.
- **Redaction default**: The transcript redaction layer is default-on for Slice 2 with a `[REDACTED]` replacement policy; it is configurable (including a no-op policy and summary-only retention) but MUST NOT be silently disabled.
