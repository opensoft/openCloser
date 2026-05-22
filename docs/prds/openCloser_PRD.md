# openCloser PRD

Status: Draft

Owner: openCloser maintainers

Last updated: 2026-05-19

## Summary

openCloser is an open-source AI communication platform for healthcare-oriented outreach, scheduling, and virtual care conversations. The product starts with CRM-driven outbound calling for assisted living facility outreach, then expands into patient scheduling, nurse intake, follow-up, and AI-assisted virtual care over phone, app voice, and app video.

The first release should prove that a small clinic or sales team can run compliant, auditable AI-assisted phone outreach directly from its CRM without buying a full contact-center stack or building one-off call automation.

## Problem

Healthcare organizations have many low-complexity communication workflows that are expensive to staff and difficult to scale:

- Prospect outreach and first-touch qualification.
- Appointment setting and callback scheduling.
- Patient intake and follow-up calls.
- Reminder, adherence, and care coordination calls.
- Early triage that must escalate safely to humans.

Most teams already store the relevant business context in a CRM or patient system, but the calling workflow is often manual, inconsistent, and hard to audit. Existing contact-center platforms can be expensive or too rigid, while generic AI voice demos usually lack CRM state, compliance controls, retries, handoff, and write-back.

## Product Vision

openCloser should provide reusable interaction infrastructure that can be paired with specialized AI personas. The same core should be able to run a sales appointment setter, a patient scheduling assistant, a nurse intake agent, or a doctor visit agent, while keeping persona behavior, safety rules, and CRM mappings configurable.

## Target Users

- Clinic operators who need low-cost outreach automation.
- Sales and growth teams running healthcare prospecting campaigns.
- Care coordinators handling routine patient calls.
- Developers building healthcare-specific voice AI workflows.
- Small healthcare organizations that need self-hostable tooling.

## First Customer Scenario

Medx needs to call assisted living facilities from Dynamics 365 Sales Hub. The AI should ask whether the facility is interested in Medx services, verify or capture email, and schedule a callback for the following morning local time when appropriate. The call outcome must be written back to CRM as structured data and timeline activity.

## Goals

- Run outbound calls from CRM-owned lists or queue records.
- Enforce call windows, attempt limits, do-not-call status, opt-outs, and consent rules before dialing.
- Use an AI persona to hold a bounded phone conversation.
- Capture transcript, summary, disposition, extracted fields, and next actions.
- Write durable outcomes back to CRM.
- Create human follow-up tasks when the AI identifies interest, risk, uncertainty, or escalation.
- Make personas swappable without changing the interaction core.
- Keep the first version deployable by a small team.
- Establish architecture that can later support app voice, app video, and clinical personas.

## Non-Goals

- Building a general-purpose CRM in the first version.
- Building a full campaign management UI in the first version.
- Replacing licensed clinicians for diagnosis or treatment decisions.
- Creating opportunities for every positive signal without qualification rules.
- Supporting every telephony provider or CRM at launch.
- Supporting fully autonomous clinical workflows at launch.

## Product Principles

- CRM is the source of truth for business workflow.
- The platform reads from and writes back to CRM rather than becoming a parallel system of record.
- Interaction infrastructure is separated from persona behavior.
- Every automated interaction is auditable.
- Compliance and safety gates run before the AI can act.
- Clinical personas require stricter identity, consent, escalation, and documentation controls than sales personas.
- Human handoff is a core product path, not an exception path.
- Open-source deployments should be understandable, configurable, and inexpensive.

## MVP

The MVP is an outbound appointment-setting caller for Medx assisted living facility prospecting. The canonical MVP scope is defined in [openCloser MVP](./openCloser_MVP.md).

The smallest useful MVP is a single-campaign ALF outbound caller that takes one queued facility record, runs one bounded AI persona, writes one structured CRM outcome back, and then graduates to a real phone call after the CRM loop is proven.

The thin MVP is built in three slices:

1. Mock call, mock CRM.
2. Mock call, real CRM.
3. Real call, real CRM.

### MVP Workflow

1. A local queue or Dynamics 365 queue provides one ALF prospect record, depending on the slice.
2. The worker evaluates minimum eligibility: phone number, local call window, DNC or opt-out, attempt limit, and callable status.
3. The worker starts a mock call for Slices 1 and 2, or an outbound SignalWire call for Slice 3.
4. The call path provides simulated transcript/events in Slices 1 and 2, or SignalWire streams call audio to the openCloser API in Slice 3.
5. Pipecat runs the ALF outreach persona using the configured real-time model provider.
6. The persona asks whether the facility is interested.
7. The persona verifies or captures an email address when appropriate.
8. The persona proposes a callback for tomorrow morning in the facility local time zone when interest is detected.
9. The platform produces a normalized session result.
10. The platform writes the essential outcome locally in Slice 1 or to Dynamics in Slices 2 and 3.
11. The platform creates a follow-up Task for interested or review-needed outcomes in the pilot path.
12. The platform updates queue status, attempt count, and final disposition.

### MVP Dispositions

- `interested_callback_requested`
- `interested_email_captured`
- `not_interested`
- `call_back_later`
- `wrong_number`
- `no_answer`
- `voicemail`
- `do_not_call`
- `needs_human_review`
- `failed`

### MVP Success Criteria

- One queued ALF prospect can move from `ready` to a final disposition without manual intervention.
- Calls only start when compliance and scheduling gates pass.
- Slice 1 can prove the loop with a mock call and mock CRM/write-back adapter.
- Slice 2 can prove real Dynamics write-back with a mock call.
- Slice 3 can place a real outbound call through SignalWire and write the result to Dynamics.
- The ALF persona produces a normalized disposition, summary, and extracted fields.
- Interested prospects receive a human callback task with local-time scheduling context in the CRM pilot path.
- Failed provider callbacks and duplicate webhooks do not create duplicate write-back records.

## Functional Requirements

### Queue Intake

Priority: P0

The system must read due call queue items from a configured queue source. Slice 1 can use a local file or SQLite queue with a mock CRM adapter. Slices 2 and 3 should use Dynamics 365 / Dataverse. A due item must include campaign, target account or facility name, optional contact, phone number, local time zone or configured default, attempt count, and current status.

Acceptance criteria:

- Queue polling can be filtered by campaign.
- Queue polling only selects eligible statuses.
- A selected queue item is locked or leased before dialing.
- Stale locks can be recovered.
- Queue items are idempotently updated after every attempt.

### Compliance Gate

Priority: P0

Before starting a call, the system must evaluate the target against configured communication rules.

Acceptance criteria:

- Calls are blocked outside configured local call windows.
- Calls are blocked for DNC or opt-out records.
- Calls are blocked after max attempts.
- Calls are blocked when the queue item or account is no longer active.
- Each allow or block decision is recorded with rule results.

### Outbound Dialing

Priority: P0

The system must support a mock call transport for Slices 1 and 2 and initiate outbound PSTN calls through SignalWire for Slice 3.

Acceptance criteria:

- Provider request and response IDs are stored.
- Provider status callbacks update the session and queue item.
- No-answer, busy, failed, and voicemail outcomes map to normalized dispositions.
- Retries are controlled by campaign policy, not by provider callbacks alone.

### Real-Time Conversation

Priority: P0

The system must connect call audio to a real-time AI conversation runtime.

Acceptance criteria:

- Call audio is streamed to Pipecat.
- The configured persona receives session context and CRM fields.
- The persona can emit structured events such as extracted email, interest level, callback request, and escalation request.
- The system can terminate the session cleanly when the caller hangs up, the provider fails, or the persona reaches completion.

### Persona Configuration

Priority: P0

Personas must be configured separately from core workflow code.

Acceptance criteria:

- A persona defines goal, opening, disclosures, allowed claims, questions, extraction schema, dispositions, and escalation rules.
- A campaign references one persona version.
- Persona changes can be versioned.
- Completed sessions record which persona version was used.

### Write-Back

Priority: P0

The system must write call outcomes to a configured write-back target. Slice 1 can write a local artifact through a mock CRM adapter. Slices 2 and 3 should write essential outcomes back to Dynamics 365 / Dataverse.

Acceptance criteria:

- A local structured result is produced for every attempted session in development.
- A Phone Call activity is created for every connected call in the CRM pilot path.
- Failed or blocked attempts are represented in queue history.
- The transcript or transcript pointer is stored according to deployment policy.
- Summary, disposition, extracted email, and next actions are written in structured fields.
- Follow-up Tasks are created for interested prospects and human-review outcomes in the CRM pilot path.
- Account and Contact fields are updated only when the persona has captured or verified durable facts.

### Human Follow-Up

Priority: P0

The system must create actionable handoff records for humans.

Acceptance criteria:

- Callback tasks include target account, contact if available, phone number, email if captured, reason for callback, preferred local time window, summary, and transcript link or pointer.
- `needs_human_review` tasks explain why review is required.
- Escalation rules can be configured by persona.

### Observability

Priority: P1

The system must provide enough logs and metrics to debug calls and monitor campaign health.

Acceptance criteria:

- Each queue item, session, provider call, and CRM write-back has a correlation ID.
- Logs avoid storing secrets and follow PHI policy.
- Metrics include attempted calls, connected calls, dispositions, provider errors, write-back failures, and average call duration.
- Failed write-backs can be retried idempotently.

### Admin and Developer Configuration

Priority: P1

The first version can be configured with files and environment variables. A full campaign UI is not required.

Acceptance criteria:

- A deployment can configure CRM connection, provider credentials, call windows, attempt limits, persona, and write-back mappings.
- A local developer can run a dry-run queue worker without placing calls.
- Example config is included without secrets.

### App Voice and Video Transport

Priority: P2

The architecture must leave room for app-based voice and video visits.

Acceptance criteria:

- Phone transport concerns are isolated from session and persona logic.
- A future WebRTC or LiveKit transport can reuse session state, persona configuration, transcript handling, and write-back.
- Avatar rendering is treated as a video client concern, not as core business workflow.

## Clinical Persona Requirements

Clinical personas are not part of the first release, but the product must establish a safety model that can support them later.

Clinical personas must define:

- Medical scope.
- Permitted actions: education, intake, scheduling, triage, documentation support, or clinician-assist.
- Identity verification requirements.
- Consent language.
- Clinical protocol references.
- Red-flag symptoms.
- Required emergency instructions.
- Human escalation criteria.
- Documentation standard.
- Whether outputs require clinician review before becoming part of the medical record.

Clinical personas must not be released without a separate clinical PRD, safety review, and compliance implementation plan.

## Data Requirements

### Core Entities

- Campaign.
- Queue item.
- Interaction session.
- Participant.
- Persona version.
- Provider call.
- Transcript segment.
- Extracted field.
- Disposition.
- Follow-up action.
- Compliance decision.
- Audit event.
- CRM write-back job.

### Retention

Retention should be deployment-configurable because clinical, sales, and regional requirements may differ.

The MVP should support:

- Storing transcript inline in CRM when allowed.
- Storing transcript externally and writing a pointer to CRM.
- Disabling full transcript persistence while keeping summary and structured outcome.

## Nonfunctional Requirements

- Reliability: duplicate provider callbacks and retries must be idempotent.
- Security: credentials must be stored outside source control.
- Privacy: logs must minimize sensitive data.
- Auditability: state transitions and automated decisions must be traceable.
- Maintainability: provider, CRM, runtime, and persona integrations must use explicit interfaces.
- Extensibility: new personas should not require changes to the queue worker.
- Cost control: MVP should run on small cloud instances for low call volume.
- Latency: real-time calls should avoid delays that make conversation feel unnatural.

## Milestones

### M0: Documentation and Skeleton

- Project PRD and architecture.
- Example repository structure.
- Core domain model.
- Example persona schema.
- Example Dynamics queue schema.

### M1: Mock Call, Mock CRM

- Queue worker dry run.
- Mock CRM adapter.
- Mock telephony transport.
- Persona execution in a simulated session.
- Write-back job simulation.

### M2: Mock Call, Real CRM

- Dynamics queue read and claim in a sandbox environment.
- Dynamics Phone Call, Task, and queue status write-back.
- Mock call status callbacks.
- ALF outreach persona using simulated transcript or mock conversation events.
- Idempotent write-back verification with duplicate mock callbacks.

### M3: Real Call, Real CRM

- Real Dynamics campaign queue.
- SignalWire outbound dialing.
- SignalWire status callback handling.
- Pipecat audio pipeline.
- ALF outreach persona.
- Limited call volume.
- Human review of transcripts and tasks.
- Campaign reporting.
- Operational runbook.

### M4: Extensible Platform

- Persona versioning.
- Additional CRM or transport adapters.
- Developer examples.
- Compliance documentation.
- Optional dev console.

## Open Questions

- Should the Dynamics call queue be a custom Dataverse table or derived from existing Campaign/Marketing List records?
- Which exact AI disclosure language should be used for each call type?
- What DNC, consent, and recording rules apply to each deployment region?
- Should all calls be recorded, transcript-only, summary-only, or configurable per campaign?
- What qualification threshold creates an Opportunity?
- What exact callback window should "tomorrow morning" mean for Medx?
- Which provider should be the long-term app voice/video transport?
- What clinical workflows are allowed before a licensed clinician enters the loop?
