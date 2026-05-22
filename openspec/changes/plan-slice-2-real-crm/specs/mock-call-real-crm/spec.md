## ADDED Requirements

### Requirement: Dataverse schema is verified before writes
The system MUST inspect and record the live Dataverse metadata needed for Slice 2 before creating fields, changing picklists, or writing queue/activity/task data. The mapping MUST cover the selected queue item representation, Account, Contact when present, Campaign when present, Phone Call activity, Task, owner/team assignment, status values, DNC/opt-out fields, attempt counters, last disposition, last session ID, and last error.

#### Scenario: Metadata discovery blocks unsafe assumptions
- **WHEN** a required table, field, lookup, or option-set value cannot be verified in Dataverse
- **THEN** the Slice 2 setup fails before write-enabled processing and reports the missing mapping without creating or updating CRM records

#### Scenario: Existing CRM values are preserved
- **WHEN** a Dataverse record already has a non-empty high-confidence value outside the approved Slice 2 update fields
- **THEN** the system MUST leave that value unchanged and record no overwrite in the write-back payload

### Requirement: One CRM queue item can be loaded and claimed
The system SHALL load one eligible candidate from the configured Dataverse queue source and map it into the existing queue-item contract used by the eligibility evaluator. Claiming MUST be limited to one campaign and one queue item at a time for Slice 2.

#### Scenario: Ready CRM queue item is claimed
- **WHEN** a Dataverse queue item is in the configured `ready` state and has the required Account/facility, phone, attempt, DNC, timezone/default-timezone, and max-attempt fields
- **THEN** the system claims exactly that queue item for one processing run and exposes the mapped queue item to eligibility without requiring a local CSV or local mock CRM queue row

#### Scenario: Non-ready CRM queue item is not called
- **WHEN** the selected Dataverse queue item is not in the configured callable status
- **THEN** the system records a blocked eligibility result and MUST NOT start the mock call transport

### Requirement: Slice 2 keeps calls mocked while CRM is real
The system SHALL use the existing fixture-driven mock call transport and scripted ALF appointment-setter persona for Slice 2. No SignalWire call, Pipecat live audio path, real-time model, or real outbound traffic may be used by this capability.

#### Scenario: CRM demo uses mock transport
- **WHEN** an operator processes a Dataverse queue item in Slice 2
- **THEN** the call outcome comes from a configured mock transport fixture and not from a live telephony provider

#### Scenario: Persona output remains deterministic
- **WHEN** the configured scripted conversation fixture reaches a supported disposition
- **THEN** the normalized result uses the same deterministic persona extraction and disposition precedence rules proven in Slice 1

### Requirement: Dataverse adapter satisfies existing write-back contract
The Dataverse adapter MUST implement the same consumer-facing write-back operations as Slice 1: `emit_phone_call_activity`, `emit_queue_status_update`, `emit_task`, and `build_writeback`. Dataverse field names, required lookups, option-set values, and owner/team IDs MUST be translated inside the adapter and MUST NOT leak into the orchestrator, eligibility evaluator, mock transport, or persona.

#### Scenario: Connected interested result writes CRM records
- **WHEN** a CRM queue item completes with `interested_callback_requested`
- **THEN** the adapter creates or updates the configured Dataverse Phone Call activity, queue-status fields, and callback Task using the existing normalized payload fields

#### Scenario: DNC result updates queue without follow-up task
- **WHEN** the persona records a `do_not_call` disposition or mid-call opt-out
- **THEN** the adapter updates the Dataverse DNC/opt-out and queue status mapping and MUST NOT create a callback or review Task

#### Scenario: Blocked eligibility writes only queue status
- **WHEN** eligibility blocks the queue item before call initiation
- **THEN** the adapter writes the configured blocked/status/error fields to Dataverse and MUST NOT create a Phone Call activity or Task

### Requirement: CRM write-back is idempotent
The system MUST prevent duplicate mock provider events, repeated CLI invocations for the same session, and write-back retries from creating duplicate Dataverse Phone Call activities, duplicate Tasks, duplicate queue-status transitions, or duplicate attempt-count increments.

#### Scenario: Duplicate mock event is replayed
- **WHEN** the mock transport emits the same event ID more than once for a CRM-backed session
- **THEN** the second delivery is a no-op for local session state and Dataverse write-back state

#### Scenario: Write-back retry follows a transient CRM error
- **WHEN** a Dataverse write attempt fails after an idempotency key has been recorded or a CRM correlation identifier is known
- **THEN** a retry MUST reuse the existing correlation and MUST NOT create a second Phone Call activity or Task

### Requirement: Invalid mock fixtures fail before state mutation
The mock transport MUST validate the selected transport fixture during call placement before the orchestrator mutates session state, CRM queue status, or attempt count.

#### Scenario: Malformed transport fixture is selected
- **WHEN** the configured transport fixture is invalid JSON, lacks an `events` array, or contains an event missing required `type`, `event_id`, or `timestamp` fields
- **THEN** the run fails with an operator-visible error and MUST NOT create a session row, consume an attempt, or update the Dataverse queue item

### Requirement: Slice 2 redacts transcript artifacts before disk write
The system SHALL pass transcript text through a configurable `RedactionLayer` before writing transcript artifacts to disk. The default Slice 2 policy MUST replace configured sensitive patterns with `[REDACTED]` while preserving the normalized summary and transcript pointer contract.

#### Scenario: Transcript contains configured sensitive pattern
- **WHEN** the transcript text contains a value matching the configured redaction policy
- **THEN** the transcript artifact stores `[REDACTED]` in place of that value and the session-result artifact points to the redacted transcript file

#### Scenario: Summary-only retention is configured
- **WHEN** the deployment config selects summary-only transcript retention
- **THEN** the system writes no full transcript file and the session-result artifact still includes the normalized summary and retention mode

### Requirement: Human follow-up tasks are assigned through configuration
The system MUST populate Dataverse callback and review Task ownership from a configured default-owner-per-task-kind mapping unless the selected CRM queue item supplies an approved owner override.

#### Scenario: Callback task uses configured owner
- **WHEN** the final disposition requires a callback Task and no queue-item owner override is configured
- **THEN** the emitted Dataverse Task is assigned to the configured callback owner or team

#### Scenario: Review task uses review owner
- **WHEN** the final disposition is `needs_human_review`
- **THEN** the emitted Dataverse Task is assigned to the configured review owner or team and includes the human-review reason code

### Requirement: Slice 2 produces demo evidence from CRM
The system SHALL produce a repeatable demo path that starts from one Dataverse queue item and ends with inspectable CRM records plus local audit artifacts. The demo MUST show the CRM queue item, the Phone Call activity when applicable, the Task when applicable, the normalized session result, and the transcript retention/redaction behavior.

#### Scenario: Write-enabled CRM demo completes
- **WHEN** a test Dataverse queue item is processed with an interested callback fixture in write-enabled mode
- **THEN** the operator can inspect the updated CRM queue item, related Phone Call activity, callback Task, local session-result artifact, and transcript pointer without using a custom openCloser UI

#### Scenario: Dry-run CRM demo performs no writes
- **WHEN** the same queue item is processed in dry-run mode
- **THEN** the system validates mapping and produces planned write-back artifacts without creating or updating Dataverse records
