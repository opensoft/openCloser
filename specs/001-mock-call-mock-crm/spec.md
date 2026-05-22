# Feature Specification: Slice 1 — Mock Call, Mock CRM

**Feature Branch**: `001-mock-call-mock-crm`

**Created**: 2026-05-19

**Status**: Draft

**Input**: User description: "Create feature 001: Slice 1 - Mock Call, Mock CRM. Build the first thin MVP slice for openCloser. This feature must prove the local end-to-end product loop without SignalWire or real Dynamics/Dataverse. Target slice: Slice 1 — mock call, mock CRM. No real telephony, no real CRM, no custom UI, no clinical workflow. Goal: given one local ALF prospect queue record, the system can evaluate eligibility, run a mock outbound call flow, execute the ALF appointment-setter persona against a scripted/mock conversation, produce a normalized session result, persist local state, and emit mock CRM write-back artifacts including a callback or review task payload when needed."

## Clarifications

### Session 2026-05-19

- Q: When does the system increment `attempt_count` on a queue record? → A: Every initiated call attempt increments exactly once, regardless of outcome (`connected`/`no_answer`/`voicemail`/`failed`/`completed`). Blocked-by-eligibility runs never increment.
- Q: What values does the queue record's callable-status field take, and which allow a call? → A: Fixed enum `ready` / `in_progress` / `completed` / `blocked` / `dnc`. Eligibility allows only `ready`.
- Q: What happens to local state and the mock CRM write-back when the persona observes a mid-call opt-out? → A: Set `dnc_flag=true` AND `callable_status='dnc'`; queue-status write-back reflects the DNC transition; final disposition is `do_not_call`; no follow-up task payload.
- Q: What is the default transcript storage shape for Slice 1? → A: `session-result.json` carries `summary` + a `transcript_pointer` (relative path); the full scripted transcript is written to a separate per-session file under the artifacts directory.
- Q: When a scripted conversation produces BOTH a captured/verified email and a callback request, which final disposition wins? → A: `interested_callback_requested`. The captured email is still recorded on the session result in its own field and MUST be included in the emitted callback task payload.
- Q: When persona disposition rules (FR-009) would emit a task payload for a disposition in FR-018's exclusion set (`not_interested` / `wrong_number` / `do_not_call` / `failed`), who wins? → A: FR-018 wins. The persona owns *which* disposition is selected, but task-payload emission for the four excluded dispositions is forbidden regardless of persona rules.
- Q: What disposition string is recorded for blocked-by-eligibility outcomes? → A: `blocked` is added as the 11th value of FR-013's enum; the failing rule names are recorded as a `blocked_reason` field on the session result.
- Q: For a blocked-by-eligibility run, is a session created? → A: Yes. The system MUST always create a session in `blocked` terminal state for every processed queue-item ID. No queue-item ID is ever processed without producing a session row.
- Q: When a duplicate event is also a conflicting late event, does writing the audit record violate FR-019's "duplicate events MUST be no-ops with respect to state"? → A: No. The audit log of conflicting events is a separate channel from the "state" referenced in FR-019; FR-019 and FR-020 both apply without conflict.
- Q: Does the Slice 1 pointer-default transcript storage (which writes the full scripted transcript to a file under the artifacts directory) violate FR-024's "minimize sensitive data"? → A: No, accepted for Slice 1: the persona is non-clinical and MUST NOT collect PHI, so the full scripted-fixture transcript carries no PHI by construction. A configurable redaction layer is deferred to Slice 2.

### Session 2026-05-19 (Round 2 — checklist closure)

- Q: How is "conceptual contract" operationally defined? → A: The Public Surface section of each `contracts/*.md` is the canonical language-neutral interface. It is reviewed against the future SDK's intended methods at Slice 2 plan time (verified by T075).
- Q: Should the persona's disclosure language be pinned verbatim for Slice 1? → A: Yes. The canonical first-utterance string is: `Hi, this is an AI assistant calling on behalf of Medx, the senior-living placement service. Is this a good time to chat for two minutes?` Paraphrases are forbidden in Slice 1; future slices may introduce variants behind the same persona boundary.
- Q: What allowed-claim categories may the persona discuss? → A: `services_offered` (senior-placement matchmaking), `geographic_coverage`, `scheduling`, `pricing_general` (free-to-prospect; partner facilities pay Medx; specific cost figures NOT allowed), `next_steps` (callback or email follow-up). Disallowed: specific cost figures, clinical recommendations, comparisons to specific competitors.
- Q: What PHI / disallowed topics MUST the persona refuse or escalate? → A: PHI data classes the persona MUST refuse to collect: resident names, room numbers, diagnoses, medications, treatment plans, family medical history, dietary restrictions framed as medical, fall-risk scores, cognitive-status indicators, end-of-life plans. Disallowed topic categories that MUST escalate (`non_clinical_topic_escalation`): clinical advice, legal advice, regulatory interpretations, insurance-coverage disputes, complaints about specific facilities.
- Q: What triggers the DNC pathway (`intent_classification='dnc_stated'`)? → A: Any of these phrase patterns: `"don't call"`, `"stop calling"`, `"take me off"`, `"remove me"`, `"do not contact"`, `"unsubscribe"`, `"opt out"`, `"opt-out"`. Or a Slice-1 rule-based heuristic classifying an explicit opt-out. Ambiguous statements ("I'm busy", "we'll get back to you", "not interested right now") MUST NOT trigger DNC — those are `not_interested` or `call_back_later`. Truly ambiguous DNC statements MUST escalate to `needs_human_review` with `ambiguous_dnc`.
- Q: Is collecting an email address considered safe for Slice 1? → A: Yes. Email is non-PHI business contact data. The persona MUST obtain explicit verbal consent + read-back before storing. Captured emails MUST NOT appear alongside clinical/health context in transcripts.
- Q: What is the Slice 2 transcript-redaction roadmap? → A: Slice 2 plan introduces a `RedactionLayer` module on the transcript pipeline pre-disk-write. Default policy: regex + named-entity strip on the PHI keyword set above, replaced with `[REDACTED]`. OFF in Slice 1 (no real conversation); ON by default in Slice 2; per-deployment configurable. Slice 2 backlog item; no Slice 1 deliverable.
- Q: How is the "decision-maker uncertain about engaging" case modeled? → A: `role_confidence` captures role certainty only; engagement uncertainty is `intent_classification`. The two fields are independent. This case = `role_confidence='confident_decision_maker'` + `intent_classification='uncertain'` → FR-036 rule #3 → `needs_human_review` with `uncertain_intent`.
- Q: What is the format of `refusal_topics`? → A: Enumerated set of category labels: `clinical_advice`, `legal_advice`, `regulatory_interpretation`, `insurance_dispute`, `competitor_comparison`, `pricing_specific`, `medical_history`. Free-form is forbidden in Slice 1.
- Q: What concrete trigger condition fires each FR-035 reason code? → A: `uncertain_role` ← `role_confidence='uncertain'`; `uncertain_intent` ← `intent_classification='uncertain'` AND `role_confidence!='uncertain'`; `ambiguous_dnc` ← contact uses DNC-adjacent phrasing the persona can't disambiguate; `captured_email_invalid_no_callback` ← FR-036 rule #7; `phi_collection_risk` ← contact volunteers (or persona detects) PHI from the enumerated PHI data classes; `legal_request` ← contact requests recording deletion / GDPR-style access / legal escalation; `non_clinical_topic_escalation` ← contact asks for clinical/legal/insurance advice the persona can't answer; `outside_allowed_claims` ← contact asks for info outside the allowed-claim categories; `script_truncated` ← fixture ended without producing a disposition (FR-036 rule #10).
- Q: Does the call window apply 7 days a week? → A: Yes for Slice 1 (matches sales-outreach default). Weekday filtering deferred to a future slice.
- Q: Are the call-window boundaries inclusive? → A: `[09:00, 20:00]` both ends inclusive at minute resolution. A call placed at exactly 20:00:00 local time is allowed; 20:01:00 is blocked.
- Q: What is the precise definition of "phone presence" for FR-004(a)? → A: Slice 1: non-null AND non-empty after trim (no whitespace-only strings). E.164 validation deferred to Slice 2 when real telephony arrives.
- Q: How is daylight-saving-time handled? → A: Slice 1 single-record processing makes mid-call DST irrelevant (a call lasts ~minutes). The eligibility evaluator uses the record's local time at decision time via the `zoneinfo` library which handles DST correctly. No special handling needed.
- Q: What payload sub-schema does each Mock Call Event type carry? → A: `connected` / `no_answer` / `completed` → `{}` (no payload). `voicemail` → `{"voicemail_length_seconds": int}` (optional; 0 allowed). `failed` → `{"failure_reason": str}` (one of `carrier_error`, `transport_error`, `invalid_number`, `unknown`). `callback_requested` → `{"window_hint": str | null}` (persona-extracted window if any). Slice 2 may add a `provider_raw` sub-key.
- Q: What format is `preferred_callback_window`? → A: Free-form string for Slice 1, preserved verbatim from the contact's words. Structured parsing (timestamp range) deferred to Slice 2 when scheduling integration arrives.
- Q: What is the `summary` field's format? → A: One-sentence outcome, ≤ 200 characters, persona-authored, plain English suitable for a sales-CRM activity feed. Structured fields (callback flag, email, window) remain separate; `summary` is the human-readable headline.
- Q: What does `last_decision_at` on the Queue Item represent? → A: Most recent of either the eligibility decision or the session finalization. Updated by the orchestrator at end-of-run.
- Q: Does the Task payload include an owner/assigned-to field? → A: Yes — `assigned_to` is an OPTIONAL field on FR-030. Slice 1 mock sets it to `null` (no real users). Slice 2 Dataverse populates from a configurable default-owner-per-task_kind mapping.
- Q: What format pins FR-033's "language-neutral interface"? → A: Markdown pseudo-code in `contracts/*.md` is the canonical Slice 1 format. Python ABCs in `src/opencloser/<module>/base.py` are the runtime enforcement. T075 (SC-008 review) verifies the markdown pseudo-code against real SDK shapes at Slice 2 plan time. No `.pyi` files needed in Slice 1.
- Q: Is Python-flavored pseudo-code in `contracts/*.md` "language-neutral enough"? → A: Yes. The pseudo-code's authority is the prose description of operations + inputs + outputs; the type-hint syntax is decorative and widely readable across languages. Each contract file carries a one-line header note stating this stance.

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

**Independent Test**: Load a queue record carrying a single disqualifying condition, run the processing command, and verify that (a) a session is created in a `blocked` terminal state with disposition `blocked` and no mock provider events, (b) the eligibility decision is persisted with every failing rule named in the `blocked_reason` field of the session, (c) no Phone Call-like activity is emitted by the mock CRM adapter, (d) the attempt count is unchanged, and (e) the operator can read the block reason from the exported artifacts. Repeat for each individual disqualifying condition.

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
2. **Given** a completed `needs_human_review` run, **When** the operator opens the session-result JSON, **Then** the human-review reason is present and the exported task payload is a review task payload (per FR-030).
3. **Given** any completed run, **When** the operator opens the mock CRM write-back JSON, **Then** they can identify a Phone Call-like activity payload, a queue-status update payload, and, when applicable, a Task-like callback or review payload.

---

### Edge Cases

- **Duplicate provider event after finalization**: a duplicate `connected`, `completed`, `failed`, `no_answer`, `voicemail`, or callback event arrives for an already-finalized session. The system MUST treat it as a no-op for state, attempt count, write-backs, and task payloads.
- **Late conflicting event**: a `failed` event arrives after a `completed` event has finalized the session, or vice versa. The system MUST NOT overwrite the finalized disposition; it MUST record the conflicting event for audit but MUST NOT mutate the result or emit a new write-back.
- **DNC stated mid-conversation**: the persona MUST stop immediately; the final disposition MUST be `do_not_call`; the queue record's `dnc_flag` MUST be set to true AND its `callable_status` MUST be set to `dnc` in local state; the mock CRM queue-status update payload MUST reflect the transition to `dnc`; no callback or review task payload MUST be emitted.
- **Wrong number stated**: the persona MUST stop the sales flow; the final disposition MUST be `wrong_number`; the mock CRM queue-status update payload MUST transition `new_status` to `blocked`; no callback or review task payload MUST be emitted.
- **Call window expires mid-call**: if the persona is mid-conversation when the local call window ends, the in-flight call is allowed to complete; no new mock call may start outside the window.
- **Missing or malformed timezone on the record**: the configured default timezone is used; this MUST be visible in the eligibility decision.
- **Email captured but invalid format**: the persona MUST store the captured value in the `captured_email_unverified` field (the `captured_email` field is reserved for verified values only), and the disposition MUST fall back to `interested_callback_requested` when a callback window was also captured, or `needs_human_review` otherwise. The disposition MUST NOT be `interested_email_captured`.
- **Mock transport emits an unknown event type**: the system MUST log it, MUST NOT mutate session state, and MUST NOT crash the workflow.
- **Persona is uncertain about role/intent**: disposition is `needs_human_review` and a review task payload (per FR-030) is produced.
- **Attempt count already at max when called**: blocked before any mock call (covered by Story 2) and not silently retried.
- **Daylight-saving-time transition**: Slice 1 single-record processing makes mid-call DST irrelevant (calls last ~minutes). The eligibility evaluator MUST use the record's local time at decision time via the `zoneinfo` library, which handles DST correctly. No special handling required.

## Requirements *(mandatory)*

### Functional Requirements

#### Queue ingestion and inputs

- **FR-001**: System MUST read local ALF prospect queue records from a local state store. Fixture loading from JSON or CSV files into that store is permitted as a developer convenience for Slice 1.
- **FR-002**: Each queue record MUST carry: a queue-item ID, a facility / account name, a phone number, a timezone (or an indication that the configured default timezone applies), an optional email, an attempt count, a DNC / opt-out flag, and a callable-status field whose value is one of the fixed enum `ready`, `in_progress`, `completed`, `blocked`, `dnc`.
- **FR-003**: The processing command MUST accept exactly one queue-item ID per invocation in Slice 1 and MUST process only that record.

#### Eligibility

- **FR-004**: System MUST evaluate eligibility for the target queue record using at least these rules, in this canonical order: (a) phone presence — Slice 1: `phone_number` is non-null AND non-empty after trim (E.164 validation deferred to Slice 2), (b) usable timezone — record-supplied or configured default, resolvable via `zoneinfo` (which handles DST), (c) current local time within the configured call window — `[start, end]` both ends inclusive at minute resolution, applies all 7 days in Slice 1, (d) DNC / opt-out flag not set, (e) attempt count below the configured maximum, and (f) callable-status equals `ready` (any other value — `in_progress`, `completed`, `blocked`, `dnc` — MUST block the call). The system MUST evaluate ALL six rules on every record (no short-circuit) and persist each rule's pass/fail result. When multiple rules fail, the persisted decision MUST list every failing rule by name, preserving rule order (a)–(f). The set of rule results MUST be persisted with the queue record's eligibility decision.
- **FR-005**: When eligibility allows the call, the system MUST proceed to the mock call transport. When eligibility blocks the call, the system MUST (a) create a session in `blocked` terminal state with final disposition `blocked`, (b) record the eligibility decision and copy the list of failing rule names into the session's `blocked_reason` field, (c) NOT initiate a mock call, (d) NOT produce a Phone Call-like activity payload, (e) NOT increment `attempt_count`, and (f) still emit a queue-status update payload reflecting the blocked outcome (per FR-029). Every processed queue-item ID MUST produce exactly one session row, whether eligible or blocked.

#### Mock call transport

- **FR-006**: System MUST provide a mock call transport that can emit, at minimum, `connected`, `no_answer`, `voicemail`, `failed`, `completed`, and duplicate-event variants of any of those (including a duplicate "callback requested" event). The transport MUST be fixture- or script-driven in Slice 1.
- **FR-007**: System MUST assign a `mock_provider_call_id` per initiated call attempt. The value MUST be globally unique across all sessions in local state (no two sessions may share the same `mock_provider_call_id`). The system MUST record it on the session so that real-transport implementations can later supply a real provider call ID without changing the consumer contract.
- **FR-008**: The mock call transport interface MUST be the only path through which call-level events enter the Interaction Core, and it MUST present the same conceptual contract that the future SignalWire transport will satisfy.

#### ALF appointment-setter persona

- **FR-009**: System MUST run the ALF appointment-setter persona against a scripted / fixture-driven conversation when the mock call reaches `connected`. The persona module MUST own its disclosure language, allowed claims, extraction schema, disposition rules, and escalation rules. The persona's allowed-claim categories for Slice 1 are: `services_offered` (senior-placement matchmaking), `geographic_coverage`, `scheduling`, `pricing_general` (free-to-prospect; partner facilities pay Medx; specific cost figures are NOT permitted), and `next_steps` (callback or email follow-up). Claims outside these categories — specific cost figures, clinical recommendations, comparisons to specific competitors — MUST trigger `needs_human_review` with reason `outside_allowed_claims` (per FR-035).
- **FR-010**: The persona MUST disclose, in its first utterance after the `connected` event, the canonical Slice 1 disclosure string: `Hi, this is an AI assistant calling on behalf of Medx, the senior-living placement service. Is this a good time to chat for two minutes?` Paraphrases are forbidden in Slice 1; the disclosure validator (per contracts/persona.md) enforces exact-match. The persona MUST remain non-clinical and MUST NOT collect resident or patient health information, where PHI data classes include at minimum: resident names, room numbers, diagnoses, medications, treatment plans, family medical history, dietary restrictions framed as medical, fall-risk scores, cognitive-status indicators, and end-of-life plans. The persona MUST honor DNC / opt-out statements by terminating the sales flow before any further sales utterance. DNC is triggered by any of the phrase patterns `"don't call"`, `"stop calling"`, `"take me off"`, `"remove me"`, `"do not contact"`, `"unsubscribe"`, `"opt out"`, `"opt-out"`, OR a Slice-1 rule-based heuristic classifying an explicit opt-out. Ambiguous statements (e.g., "I'm busy", "we'll get back to you", "not interested right now") MUST NOT trigger DNC — those are `not_interested` or `call_back_later`. The persona MUST mark uncertainty for human review with a stated reason drawn from FR-035's enumerated reason-code set.
- **FR-011**: The persona MUST be versioned, and the persona version that produced a given session result MUST be recorded on the session.

#### Normalized session result

- **FR-012**: System MUST produce a normalized session result for every processed queue record, including blocked records (with a "blocked" final disposition and a stated reason).
- **FR-013**: System MUST support, at minimum, these final dispositions: `interested_callback_requested`, `interested_email_captured`, `not_interested`, `call_back_later`, `wrong_number`, `no_answer`, `voicemail`, `do_not_call`, `needs_human_review`, `failed`, `blocked`. The `blocked` disposition is used exclusively for blocked-by-eligibility outcomes (per FR-005); the session's `blocked_reason` field MUST hold the ordered list of failing rule names from FR-004. When a scripted conversation produces BOTH a captured/verified email AND a callback request, the final disposition MUST be `interested_callback_requested`; the captured email MUST still be recorded on the session result in its `captured_email` field and MUST be included in the emitted callback task payload.
- **FR-014**: A normalized session result MUST include: session ID, queue-item ID, mock provider call ID (when a call was placed), persona version, final disposition, summary, `transcript_pointer`, `captured_email` (verified emails only — present only when the persona obtained explicit read-back/confirmation in the scripted conversation), `captured_email_unverified` (syntactically valid but unverified email values; mutually exclusive with `captured_email`), `callback_requested` flag, `preferred_callback_window` (when present), `human_review_reason` (when disposition is `needs_human_review`), `blocked_reason` (ordered list of failing rule names; present only when disposition is `blocked`), `started_at`, and `ended_at`. The `summary` field MUST be a one-sentence outcome, ≤ 200 characters, persona-authored, in plain English suitable for a sales-CRM activity feed. The `preferred_callback_window` field MUST be a free-form string preserved verbatim from the contact's words (e.g., `"Thursday 14:00"`, `"tomorrow afternoon"`); structured parsing is deferred to a future slice. All timestamps MUST be ISO 8601 in UTC with millisecond precision. The Slice 1 default is `summary` plus a `transcript_pointer` (relative path) in the exported `session-result.json`; the full scripted transcript MUST be written to a separate per-session file under the artifacts directory at the pointed-to path. Inline-transcript embedding is NOT the default.

#### Mock CRM write-back

- **FR-015**: System MUST provide a mock CRM write-back adapter that persists and exports, at minimum: a Phone Call-like activity payload (when a call was actually placed), a queue-status update payload (always when a record is processed), and a Task-like callback or review action payload (when the disposition warrants a follow-up).
- **FR-016**: The mock CRM write-back adapter MUST present the same conceptual contract that the future Dataverse adapter will satisfy. No Interaction Core code, eligibility code, persona code, or call-transport code may depend on mock-specific shapes.
- **FR-017**: System MUST NOT emit a Phone Call-like activity payload for a session that never reached the mock call transport (i.e., blocked-by-eligibility sessions).
- **FR-018**: System MUST NOT emit a callback or review task payload for `not_interested`, `wrong_number`, `do_not_call`, `failed`, or `blocked` dispositions. This exclusion is binding regardless of persona disposition rules: the persona (FR-009) owns *which* disposition is selected for a connected call, but task-payload emission for these five dispositions is forbidden absolutely. FR-018 takes precedence over FR-009 when the two would conflict. The `needs_human_review` and `interested_*` dispositions are unaffected by this exclusion and may produce task payloads per FR-031.

#### Idempotency and duplicate handling

- **FR-019**: Every mock provider event MUST carry a stable `event_id` (a transport-supplied identifier unique within the scope of one `mock_provider_call_id`). The system MUST compute an idempotency key as the tuple `(session_id, mock_provider_call_id, event_id, write_back_kind)` where `write_back_kind` is one of `session_state` / `normalized_result` / `attempt_count` / `phone_call_activity` / `queue_status_update` / `task_payload` / `exported_artifact`. Duplicate events MUST be no-ops with respect to every kind in that set. The conflicting-event audit log (FR-020) is a separate channel from this "state" surface and is NOT considered a no-op violation when written.
- **FR-020**: Once a session has been finalized with a disposition, conflicting later events (e.g., `failed` after `completed`) MUST NOT change the finalized disposition, MUST NOT mutate the normalized result, MUST NOT increment `attempt_count`, and MUST NOT emit any new write-back payload. The conflicting event MUST be recorded in a separate `conflicting_events` audit log keyed by `(session_id, event_id)` with fields: received timestamp, conflicting event payload, conflicting event type, and the finalized disposition that was preserved. The audit log is its own persistence channel and is exempt from FR-019's no-op constraint. When a single event is BOTH a duplicate (per FR-019's idempotency key) AND a conflicting late event, FR-019 wins — duplicates are silent no-ops and do NOT add a new audit row.
- **FR-021**: `attempt_count` MUST be incremented exactly once per unique `mock_provider_call_id`. The increment MUST occur at the moment the mock transport emits its first event for a new `mock_provider_call_id` and MUST NOT recur for any subsequent event (duplicate or distinct) bearing the same `mock_provider_call_id`. Every initiated mock call attempt produces exactly one increment regardless of final outcome (`connected`, `no_answer`, `voicemail`, `failed`, or `completed`). Blocked-by-eligibility runs (no `mock_provider_call_id` assigned, no mock call placed) MUST NOT increment `attempt_count`.

#### State, artifacts, and export

- **FR-022**: System MUST persist locally: queue items (or a working view thereof), sessions, mock call events, normalized results, mock CRM write-backs, generated task payloads, and idempotency keys.
- **FR-023**: System MUST export readable JSON artifacts on a successful or blocked run, at minimum: the session result JSON, the mock CRM write-back JSON, the task payload JSON (when one was generated), and the transcript or a transcript pointer. Artifact filenames MUST allow correlation by session ID.
- **FR-024**: Exported artifacts MUST NOT contain secrets and MUST minimize sensitive data, consistent with the project's transcript-retention guidance (pointer-only or summary-only retention MUST be supported).

#### Operator interface

- **FR-025**: System MUST provide a CLI / developer command that processes exactly one local queue record in Slice 1.
- **FR-026**: System MUST provide a dry-run / fixture-driven mode suitable for live demo, where the conversation is scripted and no external services (telephony, CRM, model providers operating on live data) are required.
- **FR-027**: Operator output (CLI output and exported artifacts) MUST surface, at minimum: the eligibility decision, the final disposition, the mock provider call ID (when present), the locations of the exported JSON artifacts, and `wall_time_ms` (end-to-end wall-clock duration in milliseconds from CLI invocation to the last artifact write). The `wall_time_ms` field is the canonical instrumentation for SC-001's 60-second budget.

#### Write-back payload shapes

- **FR-028**: The Phone Call-like activity payload MUST include, at minimum: `session_id`, `queue_item_id`, `mock_provider_call_id`, `persona_version`, `final_disposition`, `summary`, `started_at`, and `ended_at`. It MUST NOT be emitted for `blocked` sessions (per FR-017). Timestamps follow FR-014's ISO 8601 / UTC / millisecond rule.
- **FR-029**: The queue-status update payload MUST include, at minimum: `queue_item_id`, `session_id`, `previous_status`, `new_status`, `transition_reason`, and `transition_at`. It MUST be emitted exactly once per processed queue-item ID, including for `blocked` sessions. The `new_status` value MUST be drawn from the FR-002 enum and selected per FR-032's per-disposition mapping.
- **FR-030**: The Task payload MUST include, at minimum: `task_kind` (one of `callback` / `review`), `subject`, `reason_code` (from FR-035's enumeration for review tasks; null for callback tasks), `session_id`, `queue_item_id`, `persona_version`, `created_at`, `assigned_to` (OPTIONAL; null in Slice 1 mock; Slice 2 Dataverse populates from a configurable default-owner-per-`task_kind` mapping), and — when `task_kind=callback` — `preferred_callback_window` AND `captured_email` when the captured email is verified (per the Q5 clarification). It MUST NOT be emitted for dispositions excluded by FR-018.
- **FR-031**: The per-disposition write-back shape MUST follow this mapping (activity / queue-status update / task payload):

  | Final disposition | Phone Call activity | Queue-status update | Task payload |
  |---|---|---|---|
  | `interested_callback_requested` | yes | yes | callback |
  | `interested_email_captured` | yes | yes | callback |
  | `needs_human_review` | yes | yes | review |
  | `not_interested` | yes | yes | none |
  | `call_back_later` | yes | yes | callback |
  | `wrong_number` | yes | yes | none |
  | `no_answer` | yes | yes | none |
  | `voicemail` | yes | yes | none |
  | `do_not_call` | yes | yes | none |
  | `failed` | yes | yes | none |
  | `blocked` | no | yes | none |

- **FR-032**: The per-disposition `new_status` for the queue-status update payload MUST follow this mapping:

  | Final disposition | `new_status` |
  |---|---|
  | `interested_callback_requested` | `ready` (re-eligible for the callback attempt, subject to FR-021 attempt-count gate) |
  | `interested_email_captured` | `completed` |
  | `call_back_later` | `ready` |
  | `not_interested` | `completed` |
  | `wrong_number` | `blocked` |
  | `no_answer` | `ready` |
  | `voicemail` | `ready` |
  | `do_not_call` | `dnc` |
  | `needs_human_review` | `blocked` |
  | `failed` | `ready` |
  | `blocked` | unchanged from the record's pre-run value (the eligibility-block does not advance the record's lifecycle) |

#### Module boundaries

- **FR-033**: The five Slice 1 modules MUST each expose a named contract surface that the Interaction Core depends on. At minimum:
  - **Eligibility evaluator**: `evaluate(queue_item, config, clock) → EligibilityDecision` (the `clock` argument supplies the decision-time `now`; see `contracts/eligibility.md`).
  - **Mock call transport**: `place_call(queue_item) → mock_provider_call_id`, and an event-stream surface that yields Mock Call Events as defined in FR-006.
  - **Persona**: `run(session_context, conversation) → PersonaOutput` (per `contracts/persona.md`; `PersonaOutput` carries the persona-produced fields — extraction, disposition, summary — that the orchestrator assembles into the FR-014 `NormalizedResult`).
  - **Mock CRM write-back adapter**: `emit_phone_call_activity(payload)`, `emit_queue_status_update(payload)`, `emit_task(payload)` (where `payload` shapes follow FR-028/FR-029/FR-030).
  - **Interaction Core / Orchestrator**: owns session lifecycle, idempotency-key checks (FR-019), attempt-count increments (FR-021), and the call sequence into the four modules above. It MUST NOT contain persona language, eligibility-rule logic, transport-event interpretation, or vendor-shaped payload assembly.

  Each surface MUST be specified as a language-neutral interface (method names, input/output shapes); the Slice 1 implementation is free to choose protocol details (classes, async/sync, etc.) at plan time.

#### Persona module specifics

- **FR-034**: The persona's extraction schema MUST include, at minimum, the following fields per connected conversation: `captured_email` (verified per the Slice 1 verified-email assumption), `captured_email_unverified` (when captured but unverified), `callback_requested` (boolean), `preferred_callback_window` (when `callback_requested`), `role_confidence` (enum: `confident_decision_maker` / `confident_non_decision_maker` / `uncertain` — captures role certainty only; engagement uncertainty is conveyed by `intent_classification`), `intent_classification` (enum: `interested` / `not_interested` / `call_back_later` / `dnc_stated` / `wrong_number` / `uncertain`), and `refusal_topics` (list drawn from the enumerated set: `clinical_advice`, `legal_advice`, `regulatory_interpretation`, `insurance_dispute`, `competitor_comparison`, `pricing_specific`, `medical_history`; free-form is forbidden in Slice 1).
- **FR-035**: The persona MUST emit `needs_human_review` with a `human_review_reason` drawn from this enumerated set, with these trigger conditions:
  - `uncertain_role` — `role_confidence='uncertain'`
  - `uncertain_intent` — `intent_classification='uncertain'` AND `role_confidence!='uncertain'`
  - `ambiguous_dnc` — contact uses DNC-adjacent phrasing the persona can't disambiguate from "not interested right now"
  - `captured_email_invalid_no_callback` — FR-036 rule #7 (unverified email + no callback)
  - `phi_collection_risk` — contact volunteers (or persona detects) any PHI data class enumerated in FR-010
  - `legal_request` — contact requests recording deletion, GDPR-style data access, or escalation to legal
  - `non_clinical_topic_escalation` — contact asks for clinical / legal / regulatory / insurance advice the persona cannot answer
  - `outside_allowed_claims` — contact asks for info outside FR-009's allowed-claim categories
  - `script_truncated` — fixture ended without producing a disposition (FR-036 rule #10)

  Additional reason codes MAY be added in future slices ONLY by appending; existing codes MUST NOT be replaced or repurposed. Slice 1 MUST NOT introduce free-form reasons.
- **FR-036**: The persona's disposition rules MUST be deterministic and MUST follow this precedence on each connected conversation (highest priority first; first match wins):
  1. DNC stated → `do_not_call` (mid-call DNC handling per "DNC stated mid-conversation" edge case applies).
  2. Wrong number stated → `wrong_number`.
  3. Any escalation trigger from FR-035's enumerated reasons → `needs_human_review`.
  4. Verified email captured AND callback requested → `interested_callback_requested` (the verified email is recorded on the session result per FR-014 and carried in the callback task payload per FR-030, per the Q5 clarification).
  5. Callback requested (no email or unverified email) → `interested_callback_requested`.
  6. Verified email captured (no callback request) → `interested_email_captured`.
  7. Unverified email captured (no callback request) → `needs_human_review` with reason `captured_email_invalid_no_callback`.
  8. Contact asks to be called back later (vague, no specific window) → `call_back_later`.
  9. Contact explicitly declines → `not_interested`.
  10. Script ended without a clear signal → `needs_human_review` with reason `script_truncated`.

### Key Entities *(include if feature involves data)*

- **Queue Item**: A local representation of one ALF prospect to be contacted. Attributes include queue-item ID, facility / account name, phone number, timezone (with default fallback), optional email, attempt count, DNC / opt-out flag, callable-status (enum: `ready` / `in_progress` / `completed` / `blocked` / `dnc`), and `last_decision_at` — the most recent of either the eligibility decision or the session finalization, updated by the orchestrator at end-of-run.
- **Eligibility Decision**: A per-record record of which rules ran, which passed, which failed, and the overall allow / block outcome. Holds: rule-by-rule pass/fail (one entry per rule (a)–(f) from FR-004), the ordered list of failing rule names when blocked, the default-timezone-substituted indicator when applicable, decision timestamp, and references to the queue item and the session it produced. Every Eligibility Decision references exactly one session (always created — `blocked` or otherwise — per FR-005).
- **Session**: One end-to-end attempt to process a queue item. Holds session ID, queue-item ID, persona version (only set when persona ran), started / ended timestamps, current state (one of `created` / `eligibility_evaluated` / `in_flight` / `finalized` / `blocked`), final disposition (one of FR-013's eleven values), `blocked_reason` (ordered list of failing rule names; present only when disposition is `blocked`), and `mock_provider_call_id` (present only when a mock call was placed).
- **Mock Call Event**: One event emitted by the mock call transport for a session: type (`connected`, `no_answer`, `voicemail`, `failed`, `completed`, or `callback_requested`), event identity for idempotency, timestamp, and a per-type payload sub-schema:
  - `connected` / `no_answer` / `completed` → `{}` (no payload; the event is the signal)
  - `voicemail` → `{"voicemail_length_seconds": int}` (optional; 0 allowed)
  - `failed` → `{"failure_reason": "carrier_error" | "transport_error" | "invalid_number" | "unknown"}`
  - `callback_requested` → `{"window_hint": str | null}` (the persona-extracted callback window, if any)

  Slice 2 may add a `provider_raw` sub-key carrying the real provider's raw event blob.
- **Normalized Result**: The canonical, persona-produced outcome of a session. Holds the fields enumerated in FR-014.
- **Mock CRM Write-back**: The set of payloads the mock CRM adapter produced for a session: Phone Call-like activity (when applicable), queue-status update, and Task-like callback or review action (when applicable). Each payload references the session and the queue item.
- **Task Payload**: A callback or review action emitted through the mock CRM adapter. Holds the fields enumerated in FR-030: `task_kind` (`callback` / `review`), `subject`, `reason_code` (for review tasks), `session_id`, `queue_item_id`, `persona_version`, `created_at`, `preferred_callback_window` (callback tasks), and `captured_email` when a verified email was captured alongside a callback request (per the Q5 clarification).
- **Idempotency Key**: A composite identifier `(session_id, mock_provider_call_id, event_id, write_back_kind)` per FR-019, used to deduplicate state changes and exported artifacts across redelivered events. `write_back_kind` ∈ {`session_state`, `normalized_result`, `attempt_count`, `phone_call_activity`, `queue_status_update`, `task_payload`, `exported_artifact`}.
- **Conflicting Event Audit Record**: One row per late event that arrived after a session was finalized and that would have changed the disposition if not for FR-020. Holds: `session_id`, `event_id`, conflicting event type, received timestamp, full event payload, and the finalized disposition that was preserved. This is a separate persistence channel from session state (per FR-019/FR-020) and is exported as its own JSON artifact when any rows exist for a session.
- **Transcript / Transcript Pointer**: A scripted conversation fixture used in Slice 1, plus a `transcript_pointer` (relative path) stored on the session for later inspection. Slice 1 default writes the full transcript to a separate per-session file under the artifacts directory; summary-only retention (no transcript file) remains an allowed configuration.
- **Conversation Fixture**: A scripted JSON file representing a single conversation outcome. Carries: a `fixture_id`, an `expected_disposition` (used by tests only; persona MUST NOT read it), a `queue_item_ref`, an ordered list of `turns` (each `{role: "persona" | "contact", text}`), and an `expected_extraction` block (also test-only). One fixture per supported disposition. Shape pinned in `research.md` §Persona fixture format.
- **Transport Fixture**: A scripted JSON file representing one transport-path scenario. Carries: a `fixture_id` and an ordered list of `events` (each `{event_id, type, timestamp, payload}`). Duplicate-event scenarios repeat the same `event_id`; conflicting-late-event scenarios append events after a finalizing event. Shape pinned in `research.md` §Mock transport fixture format.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For one local eligible ALF queue record, the operator can run the Slice 1 command once and observe a final disposition, a session result JSON, and a mock CRM write-back JSON on disk within a single interactive run (target: under 60 seconds end-to-end on a developer laptop with a scripted conversation fixture).
- **SC-002**: 100% of records that fail any one of the configured eligibility rules are blocked before any mock call is initiated, the failing rule is named in the persisted decision, and no Phone Call-like activity is emitted for any blocked record.
- **SC-003**: Every supported disposition (`interested_callback_requested`, `interested_email_captured`, `not_interested`, `call_back_later`, `wrong_number`, `no_answer`, `voicemail`, `do_not_call`, `needs_human_review`, `failed`, `blocked`) can be reached via a scripted fixture (or, for `blocked`, a queue-record fixture that fails an eligibility rule), and each produces the per-disposition write-back shape defined in FR-031.
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
- **Transcript retention**: Slice 1 default is pointer-based: `session-result.json` carries `summary` + a `transcript_pointer` (relative path), and the full scripted transcript is written to a separate per-session file under the artifacts directory at the pointed-to path. Summary-only retention (no transcript file written) remains an allowed configuration, consistent with the constitution's retention guidance. Writing the full scripted transcript to disk is an accepted Slice 1 risk under FR-024's "minimize sensitive data" mandate: the persona is non-clinical and MUST NOT collect PHI (FR-010), so the scripted-fixture transcript carries no PHI by construction. A configurable redaction / hashing layer is deferred to Slice 2 when real conversation transcripts may appear.
- **Demo posture**: The dry-run / fixture-driven mode is the primary demo posture for Slice 1; no real outbound traffic of any kind is expected in this slice.
- **CRM as conceptual control plane**: In the absence of a real CRM in Slice 1, the mock CRM adapter and the local queue together stand in for the CRM control plane. They MUST NOT evolve into a parallel UI, campaign builder, or follow-up surface; their only job is to model the contract the real CRM will later honor.

## Deferred to Implementation Plan

The following questions are intentionally NOT pinned in this specification; they are execution-level decisions that belong in `/speckit.plan` rather than `/speckit.specify`. Each is listed with rationale so reviewers can confirm the deferral is intentional.

### Artifact and filesystem layout

- **Artifact filename pattern**: e.g., `{session_id}-session-result.json`, `{session_id}-writeback.json`, `{session_id}-task.json`, `{session_id}-transcript.txt`, `{session_id}-conflicting-events.json`. Specific pattern, separator, and case convention are plan-level.
- **Artifact directory location**: default path under the working directory, override mechanism (CLI flag or env var), per-session subdirectory vs. flat layout.
- **Per-session subdirectory grouping**: whether artifacts live in a `{session_id}/` subdirectory or share a flat directory with prefixed filenames.

### Encoding and serialization

- **JSON serialization style**: indented vs. minified, key sort order, line endings, UTF-8 BOM handling.
- **Timestamp serialization library**: FR-014 mandates ISO 8601 / UTC / millisecond precision; the specific formatter is plan-level.
- **Schema-versioning marker**: a `schema_version` key in each exported JSON artifact; the version-string format and bump policy.

### Configuration surface

- **Configuration file location and format**: TOML / YAML / JSON / env vars / CLI flags for call window, max attempts, default timezone, artifact directory.
- **Configuration validation**: how malformed configuration is reported to the operator.

### Fixture format

- **Scripted-conversation fixture file format**: turn-based JSON, state-machine descriptor, branching script DSL. Slice 1's persona module owns the schema; the plan picks the file representation.
- **Fixture-loading mechanism**: how a CLI invocation associates a queue-item ID with its conversation fixture.

### Module implementation

- **Module package boundaries in code**: language-level packages, internal vs. public APIs, dependency-injection style.
- **`persona_version` string format**: semver, ISO date, content hash, or opaque token.
- **State store schema**: SQLite tables / indexes / foreign keys (state store is assumed SQLite per the Assumptions section).
- **Determinism guarantees of the persona module**: how the scripted persona guarantees identical outputs across runs of the same fixture (no randomization, no clock dependency).

### Verification mechanics

- **CI gates for module isolation (SC-009)**: how each module's stand-alone-against-stubs property is enforced in CI.
- **Fixture catalog for SC-003**: the actual set of scripted fixtures, one per disposition; this is a deliverable list maintained alongside the implementation.
- **Performance instrumentation for SC-001**: how the 60-second budget is measured and reported.

Items not on this list — including all `[Gap]` markers in the `checklists/*.md` files that are not enumerated above — are either resolved in the requirements (FR-028 through FR-036), addressed by the Clarifications session, or are sub-questions of one of the items above.
