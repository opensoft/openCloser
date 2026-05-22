# openCloser MVP

Status: Draft

Parent PRD: [openCloser PRD](./openCloser_PRD.md)

Related PRD: [ALF Outbound Appointment Setter PRD](./ALF_Outbound_Appointment_Setter_PRD.md)

Last updated: 2026-05-22

## MVP Definition

The smallest useful MVP is a single-campaign ALF outbound caller that takes one queued facility record, runs one bounded AI persona, writes one structured CRM outcome back, and then graduates to a real phone call once the CRM loop is proven.

The MVP exists to prove the product loop:

```text
Queue record -> eligibility gate -> outbound call -> AI conversation -> structured result -> CRM write-back -> human follow-up
```

The MVP should not try to prove every future platform direction. It should prove whether a CRM-owned prospect can reliably move through the call loop and create a useful disposition and follow-up task. The build order intentionally proves real CRM write-back before real telephony because the CRM path is expected to be easier and more immediately useful to validate.

## Primary Outcome

Given one assisted living facility prospect in the queue, openCloser can:

1. Decide whether the record is eligible to call.
2. Run a mock outbound call first, then a real SignalWire call in the final MVP slice.
3. Run the ALF appointment-setter persona.
4. Capture a disposition, short summary, transcript or transcript pointer, email when provided, and callback intent.
5. Write the result back to Dynamics or a local write-back adapter.
6. Create a human callback or review task when needed.

## MVP User Story

As a Medx sales operator, I want an AI assistant to call one assisted living facility prospect from our queue, determine whether they are interested, capture the best email if appropriate, and create a callback task for a human when the facility wants follow-up.

## In Scope

### Queue Input

The MVP supports one queue source at a time, with the source changing by slice.

Slice 1:

- Local CSV, JSON, or SQLite queue.
- Mock CRM/write-back adapter.
- One campaign.
- One record claimed at a time.

Slices 2 and 3:

- Dynamics 365 / Dataverse custom Call Queue Item table.
- Verified Dataverse field mapping before any write-enabled run.
- One campaign.
- One worker process.

Required queue fields:

- Queue item ID.
- Account or facility name.
- Phone number.
- Time zone or default time zone.
- Optional email.
- Attempt count.
- DNC or opt-out flag.
- Status.

### Eligibility Gate

The MVP includes only the minimum call-before-dial checks:

- Phone number is present.
- Time zone is present or can fall back to a configured default.
- Current time is inside the configured local call window.
- DNC or opt-out is not set.
- Attempt count is below the configured maximum.
- Queue item status is callable.

The gate records allow or block with a reason. It does not need a full compliance rules engine yet.

Slice 2 maps these checks from CRM fields and keeps real dialing disabled.
Hard telephony-format validation such as E.164 becomes mandatory before Slice 3
places a SignalWire call.

### Outbound Call

The MVP stages telephony after the CRM loop is working.

Slices 1 and 2 use a mock call transport that simulates connected, no-answer, failed, completed, and duplicate callback events. Slice 3 places one outbound call through SignalWire.

Slice 2 must reject malformed mock transport fixtures before session state,
attempt counts, or CRM queue status change.

Required Slice 3 behavior:

- Start an outbound call.
- Store the provider call ID.
- Receive basic call status callbacks.
- Detect connected, no-answer, failed, and completed outcomes.
- Prevent duplicate callback handling from creating duplicate outcomes.

### AI Conversation

The MVP runs one persona: ALF appointment setter.

Required behavior:

- Disclose that it is an AI assistant calling on behalf of Medx.
- Ask whether the facility is interested in learning more.
- Verify or capture email when appropriate.
- Ask whether tomorrow morning local time works for a callback when interest is detected.
- End politely when not interested.
- Stop after a clear do-not-call request.
- Mark uncertain or out-of-scope calls for human review.

The MVP conversation is non-clinical. It must not collect resident or patient health information.

### Structured Result

Every attempted session produces a normalized result.

Required fields:

- Session ID.
- Queue item ID.
- Provider call ID when available.
- Final disposition.
- Summary.
- Transcript or transcript pointer when available.
- Captured or verified email.
- Callback requested: yes/no.
- Preferred callback window when available.
- Human-review reason when applicable.
- Started and ended timestamps.

For Slices 1 and 2, the provider call ID is the mock provider call ID. Slice 3
renames the same concept to the real provider call ID when SignalWire is used.

### Dispositions

The MVP should support this reduced disposition set:

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

`gatekeeper_reached` can be folded into `call_back_later` or `needs_human_review` until reporting needs prove it should be separate.

### Write-Back

The MVP supports one write-back target at a time.

Slice 1:

- Local JSON write-back artifact or SQLite write-back table through a mock CRM adapter.

Slices 2 and 3:

- Dataverse metadata verification before field or option-set assumptions are
  used in code.
- Dynamics Phone Call activity for connected calls.
- Dynamics Task for interested or review-needed outcomes.
- Queue item status update.
- Idempotency protection against duplicate activities, duplicate Tasks, and
  duplicate attempt-count increments.

The MVP does not create Opportunities.

### Human Follow-Up

The MVP creates a callback or review task when the AI finds interest or uncertainty.

Required task fields:

- Facility/account name.
- Phone number.
- Email if captured.
- Disposition.
- Summary.
- Preferred callback window.
- Transcript pointer when available.
- Reason a human should follow up.
- Owner or team assignment from configuration for Slice 2 and Slice 3.

## UI Rails

The MVP should not include a custom product UI. The product surface should be the smallest interface that proves the call loop.

### Development UI

Use CLI commands and local artifacts.

Required development surfaces:

- Command to process one local queue record.
- Command or flag for dry-run mode.
- Local JSON or SQLite output for session results.
- Local logs with correlation IDs.
- Transcript or transcript pointer in the local result.

The development UI does not need a web dashboard.

### Pilot UI

Use Dynamics as the operator UI.

Required Dynamics surfaces:

- Call Queue Items view.
- Account timeline with Phone Call activity.
- Task queue for callbacks and human review.
- Basic CRM columns for disposition, attempt count, last call time, last summary, and last error.

The pilot should make the workflow usable from CRM without requiring operators to learn a separate campaign tool.

### Explicitly Not MVP UI

Do not build these for MVP:

- React dashboard.
- Next.js app.
- Admin SPA.
- Campaign builder.
- Transcript review console.
- Analytics dashboard.
- Custom task queue.
- Custom CRM replacement.

Custom UI should wait until real pilot usage shows which inspection, override, and reporting workflows are actually needed.

## Tech Stack Rails

The MVP stack should stay boring and narrow.

Recommended stack:

- Language: Python 3.11 or newer.
- API: FastAPI.
- Worker: simple async worker loop.
- Config: YAML or TOML config plus environment secrets, loaded through typed settings.
- Local state: SQLite for Slice 1.
- Pilot state: Dynamics as the business system of record for Slices 2 and 3; add PostgreSQL only if app-side session or write-back durability requires it.
- CRM adapter: Dynamics 365 / Dataverse Web API.
- HTTP client: `httpx`.
- Telephony: mock transport for Slices 1 and 2; SignalWire outbound calls and status callbacks for Slice 3.
- Voice runtime: Pipecat for Slice 3.
- First AI model path: OpenAI Realtime through the Pipecat pipeline.
- Tests: pytest with mocked CRM adapter, Dataverse contract/integration tests, mocked SignalWire callbacks, and persona transcript fixtures.
- Packaging and local development: `uv`.
- Local services: Docker Compose only when needed.

Avoid these until the MVP loop is proven:

- Celery or a distributed job system.
- Redis as a required dependency.
- Kubernetes.
- Multiple CRM adapters.
- Multiple telephony providers.
- A frontend framework.
- A generalized workflow engine.

### Minimal Implementation Shape

```text
apps/
  api/
    main.py
  worker/
    main.py

packages/
  core/
    queue.py
    eligibility.py
    sessions.py
    results.py
    writeback.py
  crm/
    local_adapter.py
    dataverse_adapter.py
  transports/
    mock_call_adapter.py
    signalwire_adapter.py
  runtimes/
    pipecat_runtime.py
  personas/
    alf_outreach.yaml
```

This structure is intentionally smaller than the long-term architecture. It should preserve clear boundaries without creating unused abstractions.

## Out of Scope

- App voice.
- App video.
- AI nurse persona.
- AI doctor persona.
- Avatar rendering.
- Multiple CRMs.
- Multiple telephony providers.
- Full campaign-management UI.
- Dev console.
- React dashboard.
- Next.js app.
- Admin SPA.
- Transcript review console.
- Analytics dashboard.
- Opportunity creation.
- Real appointment scheduling integration.
- Advanced retry orchestration.
- Full transcript review console and production redaction workflow. Slice 2 still
  includes a minimal configurable redaction layer before transcript disk writes.
- Clinical safety engine.
- Inbound callback handling.
- Multi-worker scaling.

## MVP Build Sequence

### Slice 1: Mock Call, Mock CRM

Goal: prove the domain loop without external systems.

Input:

- One local queue record.
- Mock CRM/write-back target.
- Mock call transport.

Behavior:

- Run eligibility checks.
- Run the ALF persona against a simulated conversation or scripted transcript.
- Produce a normalized session result.
- Produce a local write-back payload.
- Produce a callback or review task payload for interested or uncertain outcomes.

Done when:

- A local queue record can move from `ready` to a final disposition.
- The output payload contains the fields needed for CRM write-back.
- The result can create a callback task payload for interested outcomes.
- Blocked, failed, no-answer, and duplicate mock callback paths are represented without duplicate outcomes.

### Slice 2: Mock Call, Real CRM

Goal: prove the operational CRM workflow before adding real telephony.

Input:

- One Dynamics Call Queue Item from one ALF campaign.
- Mock call transport.
- Verified Dataverse field mapping and task owner mapping.

Behavior:

- Inspect Dataverse metadata before write-enabled processing.
- Claim a Dynamics queue item.
- Run eligibility checks.
- Run the ALF persona against a simulated conversation or scripted transcript.
- Write Phone Call activity, Task, and queue status back to Dynamics.
- Redact transcript artifacts before disk write according to the Slice 2 policy.

Done when:

- A Dynamics queue item can move from `ready` to final disposition without manual intervention.
- The same run can be exercised in dry-run mode with planned write-back artifacts
  and no CRM writes.
- Interested outcomes create callback Tasks in Dynamics.
- Callback and review Tasks are assigned to the configured Dynamics owner or
  team.
- DNC outcomes prevent additional automated attempts.
- Duplicate mock provider callbacks do not create duplicate CRM records.
- Malformed mock transport fixtures fail before CRM state or attempt count
  changes.
- The CRM write-back path can be demonstrated without a live phone call.

### Slice 3: Real Call, Real CRM

Goal: prove the full MVP loop with real telephony and real CRM write-back.

Input:

- One Dynamics Call Queue Item from one ALF campaign.

Behavior:

- Claim a queue item.
- Run eligibility checks.
- Place a real SignalWire outbound call.
- Stream audio through Pipecat and the configured AI provider.
- Run the ALF persona.
- Write Phone Call activity, Task, and queue status back to Dynamics.

Done when:

- A Dynamics queue item can move from `ready` to final disposition without manual intervention.
- Interested outcomes create callback Tasks.
- DNC outcomes prevent additional automated attempts.
- Duplicate provider callbacks do not create duplicate CRM records.
- Connected, no-answer, failed, and voicemail paths produce sane outcomes.
- The AI result includes disposition, summary, and extracted email or callback intent when available.

## Acceptance Criteria

- The system can process one queued ALF prospect end to end.
- Calls are blocked when minimum eligibility checks fail.
- Slice 1 can process a mock call against a mock CRM/write-back target.
- Slice 2 can process a mock call against real Dynamics write-back.
- Slice 3 can place a real outbound call through SignalWire and write the result to Dynamics.
- The ALF persona stays within non-clinical appointment-setting scope.
- The final result includes a normalized disposition and summary.
- Interested outcomes create a human callback task.
- No-answer and failed outcomes update the queue item without creating a false connected-call record.
- Duplicate provider callbacks do not duplicate tasks or activities.
- The MVP can run locally without Dynamics for development.
- The pilot path can write the essential records to Dynamics.

## Key Product Risk

The main MVP risk is not whether openCloser can become a broad communication platform. The risk is whether an AI-driven call flow can reliably produce a useful, auditable disposition and follow-up task from CRM data.

The MVP should optimize for proving that loop with the least surface area possible. That means proving CRM write-back with mock calls before taking on the added uncertainty of real telephony and audio.

## Decisions

- The first persona is ALF appointment setter.
- The first real telephony provider is SignalWire.
- The first voice runtime path is Pipecat plus a configured real-time AI provider.
- The first CRM pilot target is Dynamics 365 / Dataverse.
- The first local development path can use file or SQLite adapters.
- The MVP proves real CRM write-back before real telephony.
- Slice 1 is mock call plus mock CRM.
- Slice 2 is mock call plus real CRM.
- Slice 3 is real call plus real CRM.
- The MVP has no custom product UI.
- Development uses CLI commands and local artifacts.
- The pilot operator UI is Dynamics.
- Python, FastAPI, Pipecat, SignalWire, and the Dataverse Web API are the default implementation stack.
- Opportunities are excluded from MVP.
- Clinical workflows are excluded from MVP.
- App voice and video are excluded from MVP.

## Open Questions

- What exact AI disclosure language should Medx approve?
- What should "tomorrow morning" mean for callback Tasks?
- Who owns callback Tasks in Dynamics by default?
- Should voicemail leave a message or hang up?
- Which Dataverse table or existing CRM construct should represent Slice 2 Call Queue Items?
- Should Slice 2 populate a CRM Task due date when a callback window is parseable, or preserve the phrase only in task text until scheduling integration exists?
