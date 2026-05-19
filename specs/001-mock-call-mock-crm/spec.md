# Feature Specification: Slice 1 — Mock Call, Mock CRM

**Feature Branch**: `001-mock-call-mock-crm`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Create feature 001: Slice 1 - Mock Call, Mock CRM. Build the first thin MVP slice for openCloser. This feature must prove the local end-to-end product loop without SignalWire or real Dynamics/Dataverse. Target slice: Slice 1 — mock call, mock CRM. No real telephony, no real CRM, no custom UI, no clinical workflow. Goal: given one local ALF prospect queue record, the system can evaluate eligibility, run a mock outbound call flow, execute the ALF appointment-setter persona against a scripted/mock conversation, produce a normalized session result, persist local state, and emit mock CRM write-back artifacts including a callback or review task payload when needed."

## Constitution Alignment *(mandatory)*

- **CRM control plane**: CRM is the conceptual control plane even in Slice 1. The mock CRM adapter MUST be the only path through which the workflow records Phone Call-like activities, queue-status updates, and Task-like callback/review actions, and it MUST satisfy the same conceptual contract that the future Dataverse adapter will satisfy. The local queue store stands in for the CRM-owned queue for Slice 1 only; no parallel campaign workflow, UI, or follow-up surface is introduced.
- **Thin slice**: Target slice is **Slice 1 — Mock Call, Mock CRM** from the constitution's binding MVP order. The smallest independently demonstrable outcome is: one eligible local ALF prospect queue record moves end-to-end from "ready" through eligibility, a mock call, persona-driven mock conversation, normalized result, and mock CRM write-back including a callback/review task payload when warranted.
- **Boundaries**: Five separable responsibilities MUST remain distinct: (1) the Interaction Core / workflow orchestrator, (2) the eligibility evaluator, (3) the mock call transport, (4) the ALF appointment-setter persona module, and (5) the mock CRM write-back adapter. No business rule, persona language, or vendor-shape detail may leak across these boundaries. The persona owns disclosure language, allowed claims, extraction schema, disposition rules, and escalation rules. The mock call transport and the mock CRM adapter MUST present interfaces that the future SignalWire transport and the future Dataverse adapter can satisfy without core changes.
- **Safety and human handoff**: The persona MUST disclose, at the start of every connected conversation, that it is an AI assistant calling on behalf of Medx; MUST remain non-clinical and MUST NOT collect resident or patient health information; MUST honor opt-out / do-not-call statements immediately and persist the DNC signal; MUST respect a configured local call window and a maximum-attempts limit before placing a mock call; and MUST mark uncertain or unsafe outcomes for human review with a stated reason. Interested or uncertain outcomes MUST produce a callback or review task payload through the mock CRM write-back.
- **Auditability**: Every processed queue item MUST produce a traceable session ID, a queue-item ID, a mock provider call ID when a call was placed, a persona version, started/ended timestamps, a final disposition, a transcript or transcript pointer, and the inputs and outputs of the eligibility decision. The mock call transport MUST treat provider-style events idempotently keyed on the event identity so that duplicate connected, completed, failed, no-answer, voicemail, or callback events DO NOT create duplicate normalized results, duplicate mock CRM activities, duplicate task payloads, or duplicate attempt-count increments. Conflicting late events MUST NOT overwrite an already-finalized disposition.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Run the full mock loop on one eligible ALF queue record (Priority: P1)

A developer or sales operator has a local queue containing one eligible ALF prospect record. They invoke the Slice 1 command to process that record. The system evaluates eligibility, places a mock outbound call, runs the ALF appointment-setter persona against a scripted or fixture-driven conversation, produces a normalized session result, persists local state, and emits the corresponding mock CRM write-back artifacts (a Phone Call-like activity, a queue-status update, and, where appropriate, a Task-like callback or review action), and exports readable JSON artifacts for inspection.

**Why this priority**: This is the entire point of Slice 1. Without this end-to-end run on a single record, no later slice (real CRM, real telephony) can be planned with confidence. It is the first demonstrable product loop and the only story that proves the boundaries actually fit together.

**Independent Test**: Load a single eligible ALF queue record from a fixture, invoke the Slice 1 CLI/dev command in dry-run / fixture-driven mode, and observe (a) a final disposition that matches the scripted conversation outcome, (b) a session row plus event rows in local state, (c) a mock CRM Phone Call-like activity payload, (d) a queue-status update payload, (e) a task payload for interested / uncertain outcomes, and (f) inspectable JSON artifacts on disk for the session result, write-back, task, and transcript or transcript pointer.

**Acceptance Scenarios**:

1. **Given** a single eligible ALF queue record, a scripted conversation fixture that ends in an "interested, callback requested" outcome, and a clean local state store, **When** the operator runs the Slice 1 processing command for that record, **Then** the system records a session that ends with disposition `interested_callback_requested`, the mock CRM adapter persists and exports a Phone Call-like activity payload, a queue-status update payload, and a callback task payload referencing the captured preferred callback window, and the operator can open the exported session-result JSON and write-back JSON files.
2. **Given** the same eligible queue record and a scripted conversation fixture that ends in an "interested, email captured" outcome, **When** the operator runs the processing command, **Then** the session result includes the captured email, the disposition is `interested_email_captured`, and the mock CRM write-back includes a Task-like follow-up payload appropriate to the email-capture outcome.
3. **Given** the same eligible queue record and a scripted conversation fixture in which the persona becomes uncertain about the prospect's role or intent, **When** the operator runs the processing command, **Then** the session result records disposition `needs_human_review` with a stated human-review reason, and the mock CRM write-back includes a Task-like review action payload directed at a human operator.

---

### User Story 2 — Block an ineligible record before any mock call (Priority: P2)

The operator points the Slice 1 command at a queue record that fails one or more eligibility checks: missing phone number, no usable timezone, outside the configured local call window, DNC / opt-out flag set, max attempts already reached, or non-callable status. The system MUST record a clear block decision with the specific failing rule(s) and MUST NOT initiate a mock call, MUST NOT produce a Phone Call-like activity, MUST NOT increment attempt count, and MUST NOT emit a callback task payload.

**Why this priority**: Eligibility is the cheapest and most important safety gate in the loop. Without it, automation becomes harmful (DNC violations, calls outside hours, runaway attempts). It must be observable, auditable, and impossible to bypass.

**Independent Test**: Load a queue record carrying a single disqualifying condition, run the processing command, and verify that (a) no session is created, or a session is created in a "blocked" terminal state with no mock provider events, (b) the eligibility decision is persisted with the rule that failed, (c) no Phone Call-like activity is emitted by the mock CRM adapter, (d) the attempt count is unchanged, and (e) the operator can read the block reason from the exported artifacts. Repeat for each individual disqualifying condition.

**Acceptance Scenarios**:

1. **Given** a queue record with the DNC / opt-out flag set, **When** the operator runs the processing command, **Then** the system records a block decision citing the DNC rule, does not place a mock call, does not change the attempt count, and exits with a clear "blocked: DNC" outcome that is visible in local state and in an exported JSON artifact.
2. **Given** a queue record whose local time is outside the configured call window, **When** the operator runs the processing command, **Then** the system records a block decision citing the call-window rule and does not place a mock call.
3. **Given** a queue record whose attempt count already equals the configured maximum, **When** the operator runs the processing command, **Then** the system records a block decision citing the max-attempts rule and does not place a mock call.
4. **Given** a queue record with a missing phone number, **When** the operator runs the processing command, **Then** the system records a block decision citing the missing-phone rule and does not place a mock call.

---

### User Story 3 — Simulate every Slice 1 call path, including duplicates, without producing duplicate outcomes (Priority: P2)

The operator exercises each mock call path — connected, no-answer, voicemail, failed, completed, and duplicate provider events (including duplicate callback events) — against the same eligible queue record (or one per path). The system MUST distinguish each path in local state, MUST produce the right kind of mock CRM write-back for each path, and MUST treat duplicate mock provider events as idempotent.

**Why this priority**: Slice 1's audit and idempotency guarantees are the foundation for safely connecting real telephony and a real CRM later. Failing these guarantees here will multiply silently in Slices 2 and 3.

**Independent Test**: For each path (connected / no-answer / voicemail / failed / completed / duplicate event), run the processing command using a fixture-driven mock transport that emits the corresponding events. Verify that local state, the normalized session result, the mock CRM write-back payloads, and the attempt count match the expected shape for that path, and that re-delivering any provider event leaves all of those unchanged from the first delivery.

**Acceptance Scenarios**:

1. **Given** a fixture-driven mock transport that emits a `no_answer` event, **When** the operator runs the processing command, **Then** the session ends with disposition `no_answer`, the mock CRM write-back records the call attempt and a queue-status update appropriate to "no answer", does NOT emit a connected-call activity, and does NOT emit a callback task payload unless the no-answer policy explicitly requires one.
2. **Given** a fixture-driven mock transport that emits a `voicemail` event, **When** the operator runs the processing command, **Then** the session ends with disposition `voicemail` and the mock CRM write-back reflects voicemail rather than a connected conversation.
3. **Given** a fixture-driven mock transport that emits a `failed` event, **When** the operator runs the processing command, **Then** the session ends with disposition `failed`, the mock CRM write-back records the failed attempt, and the system does not emit a false connected-call activity or a callback task payload.
4. **Given** a successful first run that finalized a session for one queue record, **When** the mock transport re-delivers the same connected/completed event or the same callback event, **Then** the system DOES NOT create a second session, DOES NOT emit a second Phone Call-like activity, DOES NOT emit a second task payload, and DOES NOT increment the attempt count a second time.
5. **Given** a queue record that finalized as `interested_callback_requested`, **When** a duplicate "callback requested" provider event for the same session arrives, **Then** the system retains the original callback task payload and does NOT emit an additional one.

---

### User Story 4 — Inspect normalized results and follow-up task payloads (Priority: P3)

A Medx sales operator (or developer impersonating one) opens the JSON artifacts produced by the previous runs to read each normalized session result, transcript or transcript pointer, and the mock callback/review task payload. They MUST be able to understand the outcome of an interested or uncertain call without reading source code or running the system again.

**Why this priority**: Without inspectable artifacts, Slice 1 is unprovable to anyone outside the implementation. This story turns the loop into something demonstrable.

**Independent Test**: After running Stories 1 and 3, open the exported JSON files for at least one interested outcome and one needs-human-review outcome and confirm each contains the fields listed in FR-014.

**Acceptance Scenarios**:

1. **Given** a completed `interested_callback_requested` run, **When** the operator opens the session-result JSON, **Then** they see session ID, queue-item ID, mock provider call ID, final disposition, summary, transcript or transcript pointer, captured / verified email when present, callback-requested flag, preferred callback window, started timestamp, and ended timestamp.
2. **Given** a completed `needs_human_review` run, **When** the operator opens the session-result JSON, **Then** the human-review reason is present and the exported task payload describes a review-style follow-up.
3. **Given** any completed run, **When** the operator opens the mock CRM write-back JSON, **Then** they can identify a Phone Call-like activity payload, a queue-status update payload, and, when applicable, a Task-like callback or review payload.

---

### Edge Cases

- **Duplicate provider event after finalization**: a duplicate `connected`, `completed`, `failed`, `no_answer`, `voicemail`, or callback event arrives for an already-finalized session. The system MUST treat it as a no-op for state, attempt count, write-backs, and task payloads.
- **Late conflicting event**: a `failed` event arrives after a `completed` event has finalized the session, or vice versa. The system MUST NOT overwrite the finalized disposition; it MUST record the conflicting event for audit but MUST NOT mutate the result or emit a new write-back.
- **DNC stated mid-conversation**: the persona MUST stop immediately, the final disposition MUST be `do_not_call`, the queue record MUST be marked DNC in local state, and no callback task payload MUST be emitted.
- **Wrong number stated**: the persona MUST stop the sales flow, the final disposition MUST be `wrong_number`, and the mock CRM write-back MUST reflect "wrong number" without an interested follow-up task.
- **Call window expires mid-call**: if the persona is mid-conversation when the local call window ends, the in-flight call is allowed to complete; no new mock call may start outside the window.
- **Missing or malformed timezone on the record**: the configured default timezone is used; this MUST be visible in the eligibility decision.
- **Email captured but invalid format**: the persona MUST flag the captured value as unverified, and the disposition MUST fall back to `interested_callback_requested` or `needs_human_review` rather than `interested_email_captured`.
- **Mock transport emits an unknown event type**: the system MUST log it, MUST NOT mutate session state, and MUST NOT crash the workflow.
- **Persona is uncertain about role/intent**: disposition is `needs_human_review` and a review-style task payload is produced.
- **Attempt count already at max when called**: blocked before any mock call (covered by Story 2) and not silently retried.

## Requirements *(mandatory)*

### Functional Requirements

#### Queue ingestion and inputs

- **FR-001**: System MUST read local ALF prospect queue records from a local state store. Fixture loading from JSON or CSV files into that store is permitted as a developer convenience for Slice 1.
- **FR-002**: Each queue record MUST carry: a queue-item ID, a facility / account name, a phone number, a timezone (or an indication that the configured default timezone applies), an optional email, an attempt count, a DNC / opt-out flag, and a callable status field.
- **FR-003**: The processing command MUST accept exactly one queue-item ID per invocation in Slice 1 and MUST process only that record.

#### Eligibility

- **FR-004**: System MUST evaluate eligibility for the target queue record using at least these rules: (a) phone presence, (b) usable timezone (record-supplied or configured default), (c) current local time within the configured call window, (d) DNC / opt-out flag not set, (e) attempt count below the configured maximum, and (f) callable status. The set of rules and their pass/fail results MUST be persisted with the queue record's decision.
- **FR-005**: When eligibility allows the call, the system MUST proceed to the mock call transport. When eligibility blocks the call, the system MUST record a block decision naming the failing rule(s), MUST NOT initiate a mock call, MUST NOT produce a Phone Call-like activity, and MUST NOT increment attempt count.

#### Mock call transport

- **FR-006**: System MUST provide a mock call transport that can emit, at minimum, `connected`, `no_answer`, `voicemail`, `failed`, `completed`, and duplicate-event variants of any of those (including a duplicate "callback requested" event). The transport MUST be fixture- or script-driven in Slice 1.
- **FR-007**: System MUST assign a mock provider call ID per call attempt and MUST record it on the session so that real-transport implementations can later supply a real provider call ID without changing the consumer contract.
- **FR-008**: The mock call transport interface MUST be the only path through which call-level events enter the Interaction Core, and it MUST present the same conceptual contract that the future SignalWire transport will satisfy.

#### ALF appointment-setter persona

- **FR-009**: System MUST run the ALF appointment-setter persona against a scripted / fixture-driven conversation when the mock call reaches `connected`. The persona module MUST own its disclosure language, allowed claims, extraction schema, disposition rules, and escalation rules.
- **FR-010**: The persona MUST disclose at the start of every connected conversation that it is an AI assistant calling on behalf of Medx, MUST remain non-clinical, MUST NOT collect resident or patient health information, MUST honor DNC / opt-out statements immediately, and MUST mark uncertainty for human review with a stated reason.
- **FR-011**: The persona MUST be versioned, and the persona version that produced a given session result MUST be recorded on the session.

#### Normalized session result

- **FR-012**: System MUST produce a normalized session result for every processed queue record, including blocked records (with a "blocked" final disposition and a stated reason).
- **FR-013**: System MUST support, at minimum, these final dispositions: `interested_callback_requested`, `interested_email_captured`, `not_interested`, `call_back_later`, `wrong_number`, `no_answer`, `voicemail`, `do_not_call`, `needs_human_review`, `failed`. Blocked-by-eligibility outcomes MUST have a distinct, stated blocked reason.
- **FR-014**: A normalized session result MUST include: session ID, queue-item ID, mock provider call ID (when a call was placed), persona version, final disposition, summary, transcript or transcript pointer, captured / verified email (when present), callback-requested flag, preferred callback window (when present), human-review reason (when applicable), started timestamp, and ended timestamp.

#### Mock CRM write-back

- **FR-015**: System MUST provide a mock CRM write-back adapter that persists and exports, at minimum: a Phone Call-like activity payload (when a call was actually placed), a queue-status update payload (always when a record is processed), and a Task-like callback or review action payload (when the disposition warrants a follow-up).
- **FR-016**: The mock CRM write-back adapter MUST present the same conceptual contract that the future Dataverse adapter will satisfy. No Interaction Core code, eligibility code, persona code, or call-transport code may depend on mock-specific shapes.
- **FR-017**: System MUST NOT emit a Phone Call-like activity payload for a session that never reached the mock call transport (i.e., blocked-by-eligibility sessions).
- **FR-018**: System MUST NOT emit a callback or review task payload for `not_interested`, `wrong_number`, `do_not_call`, or `failed` dispositions unless the persona / disposition rules explicitly call for one (e.g., `needs_human_review`).

#### Idempotency and duplicate handling

- **FR-019**: Every mock provider event MUST carry an event identity that the system uses to detect duplicates. Duplicate events MUST be no-ops with respect to session state, normalized result, attempt count, Phone Call-like activities, queue-status updates, and task payloads.
- **FR-020**: Once a session has been finalized with a disposition, conflicting later events (e.g., `failed` after `completed`) MUST NOT change the finalized disposition. The conflicting event MUST be recorded for audit.
- **FR-021**: Attempt-count increments MUST be tied to a unique call attempt and MUST NOT increment again on duplicate events for the same attempt.

#### State, artifacts, and export

- **FR-022**: System MUST persist locally: queue items (or a working view thereof), sessions, mock call events, normalized results, mock CRM write-backs, generated task payloads, and idempotency keys.
- **FR-023**: System MUST export readable JSON artifacts on a successful or blocked run, at minimum: the session result JSON, the mock CRM write-back JSON, the task payload JSON (when one was generated), and the transcript or a transcript pointer. Artifact filenames MUST allow correlation by session ID.
- **FR-024**: Exported artifacts MUST NOT contain secrets and MUST minimize sensitive data, consistent with the project's transcript-retention guidance (pointer-only or summary-only retention MUST be supported).

#### Operator interface

- **FR-025**: System MUST provide a CLI / developer command that processes exactly one local queue record in Slice 1.
- **FR-026**: System MUST provide a dry-run / fixture-driven mode suitable for live demo, where the conversation is scripted and no external services (telephony, CRM, model providers operating on live data) are required.
- **FR-027**: Operator output (CLI output and exported artifacts) MUST surface, at minimum: the eligibility decision, the final disposition, the mock provider call ID (when present), and the locations of the exported JSON artifacts.

### Key Entities *(include if feature involves data)*

- **Queue Item**: A local representation of one ALF prospect to be contacted. Attributes include queue-item ID, facility / account name, phone number, timezone (with default fallback), optional email, attempt count, DNC / opt-out flag, callable status, and last-decision timestamp.
- **Eligibility Decision**: A per-record record of which rules ran, which passed, which failed, and the overall allow / block outcome. References the queue item and the eventual session (when one is started).
- **Session**: One end-to-end attempt to process a queue item. Holds session ID, queue-item ID, persona version, started / ended timestamps, current state, final disposition, and the mock provider call ID when a call was placed.
- **Mock Call Event**: One event emitted by the mock call transport for a session: type (e.g., `connected`, `no_answer`, `voicemail`, `failed`, `completed`, `callback_requested`), event identity for idempotency, timestamp, and optional payload (e.g., voicemail length, failure reason).
- **Normalized Result**: The canonical, persona-produced outcome of a session. Holds the fields enumerated in FR-014.
- **Mock CRM Write-back**: The set of payloads the mock CRM adapter produced for a session: Phone Call-like activity (when applicable), queue-status update, and Task-like callback or review action (when applicable). Each payload references the session and the queue item.
- **Task Payload**: A callback or human-review action emitted through the mock CRM adapter, with subject, due date / preferred callback window (when relevant), reason, and references to the session and queue item.
- **Idempotency Key**: A stable identifier (scoped to provider event identity, session, and write-back kind) used to deduplicate state changes and exported artifacts across redelivered events.
- **Transcript / Transcript Pointer**: A scripted conversation fixture used in Slice 1, plus a pointer (or summary) stored on the session for later inspection. Pointer-only / summary-only storage MUST be supported.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For one local eligible ALF queue record, the operator can run the Slice 1 command once and observe a final disposition, a session result JSON, and a mock CRM write-back JSON on disk within a single interactive run (target: under 60 seconds end-to-end on a developer laptop with a scripted conversation fixture).
- **SC-002**: 100% of records that fail any one of the configured eligibility rules are blocked before any mock call is initiated, the failing rule is named in the persisted decision, and no Phone Call-like activity is emitted for any blocked record.
- **SC-003**: Every supported disposition (`interested_callback_requested`, `interested_email_captured`, `not_interested`, `call_back_later`, `wrong_number`, `no_answer`, `voicemail`, `do_not_call`, `needs_human_review`, `failed`) can be reached via a scripted fixture, and each produces the expected mock CRM write-back shape (activity, queue-status update, and task payload when applicable).
- **SC-004**: For an `interested_callback_requested` outcome, the system produces a callback task payload that includes the preferred callback window captured during the conversation.
- **SC-005**: 100% of duplicate mock provider events redelivered for the same session leave state, normalized result, attempt count, Phone Call-like activities, queue-status updates, and task payloads unchanged.
- **SC-006**: 0 false connected-call activities are emitted for sessions that ended in `no_answer`, `voicemail`, or `failed`.
- **SC-007**: An operator (or stakeholder) who did not implement the feature can read the exported session-result JSON, the mock CRM write-back JSON, and any task payload JSON for an interested or uncertain outcome and explain the outcome without consulting source code.
- **SC-008**: The mock CRM adapter's payload shapes and method surface are reused unchanged by the planned Slice 2 work, demonstrating that the conceptual contract held when swapping the mock CRM adapter for the real Dataverse adapter (forward-looking criterion verified at Slice 2 plan time).
- **SC-009**: Each of the five named module boundaries (Interaction Core, eligibility, mock call transport, persona, mock CRM write-back) can be exercised in isolation against fixtures without instantiating the others.

## Assumptions

- **Slice scope**: Slice 1 explicitly excludes SignalWire, Pipecat (other than as a stub boundary if needed), Dynamics / Dataverse, React / Next.js / admin UI, campaign builder, opportunity creation, clinical personas, multi-worker scaling, and Redis / Celery / Kubernetes. These are deferred to later slices per the constitution.
- **Single-record processing**: Slice 1 processes one queue record per command invocation. Batch processing, claim-and-lock semantics for concurrent workers, and scheduler / retry orchestration are out of scope.
- **Local state store**: Per the constitution's "SQLite or local artifacts for Slice 1" guidance, the local state store is assumed to be SQLite. Schema specifics are deferred to the implementation plan.
- **Fixture-driven conversations**: The ALF appointment-setter persona runs against scripted or fixture-driven conversation transcripts in Slice 1; no live model-provider audio or real-time AI provider integration is required by this feature. A future slice will swap in the real persona runtime behind the same persona boundary.
- **Call window default**: A configured local call window applies (assumed default: 9:00 AM – 8:00 PM in the record's local timezone unless overridden). The exact default is a configuration concern, not a spec concern; configurability is the requirement.
- **Max-attempts default**: A configured maximum-attempts limit applies (assumed default: 5 attempts unless overridden). Configurability is the requirement.
- **Default timezone fallback**: When a queue record lacks a usable timezone, a configured default timezone applies and is recorded in the eligibility decision.
- **DNC signal source**: The DNC / opt-out flag is read from the queue record itself and may also be set by the persona during a conversation (e.g., on an explicit opt-out). External DNC list sources are out of scope for Slice 1.
- **Email "verified"**: For Slice 1, a captured email is considered "verified" when it is syntactically valid AND the persona obtained an explicit read-back / confirmation in the scripted conversation. Anything else is "captured but unverified" and downgrades the disposition.
- **Idempotency-key scope**: Idempotency keys are scoped per session and per write-back kind (Phone Call-like activity, queue-status update, task payload) using the mock provider event identity. Cross-session idempotency is out of scope.
- **Transcript retention**: Pointer-only or summary-only transcript storage is acceptable for Slice 1, consistent with the constitution's retention guidance.
- **Demo posture**: The dry-run / fixture-driven mode is the primary demo posture for Slice 1; no real outbound traffic of any kind is expected in this slice.
- **CRM as conceptual control plane**: In the absence of a real CRM in Slice 1, the mock CRM adapter and the local queue together stand in for the CRM control plane. They MUST NOT evolve into a parallel UI, campaign builder, or follow-up surface; their only job is to model the contract the real CRM will later honor.
