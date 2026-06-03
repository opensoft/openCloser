# Feature 003 Speckit Specify Prompt

Run from the root checkout while on `main`. OpenSpec/Speckit shell commands
should run from `py-bench`; the root checkout there is
`/workspace/projects/openCloser`.

```text
GIT_BRANCH_NAME=003-real-call-real-crm SPECIFY_FEATURE_DIRECTORY=specs/003-real-call-real-crm /speckit.specify Create Feature 003: Slice 3 - Real Call, Real CRM.

Generate the Speckit feature specification for openCloser Feature 003, the third and final MVP slice: Real Call, Real CRM.

Authoritative context:
- `.specify/memory/constitution.md`
- `specs/README.md`
- `docs/prds/openCloser_MVP.md`
- `docs/prds/openCloser_PRD.md`
- `docs/architecture/openCloser_Architecture.md`
- `docs/prds/ALF_Outbound_Appointment_Setter_PRD.md`
- `specs/001-mock-call-mock-crm/spec.md`
- `specs/001-mock-call-mock-crm/contracts/*.md`
- `specs/001-mock-call-mock-crm/SC008_REVIEW.md`
- `specs/002-mock-call-real-crm/spec.md`
- `specs/002-mock-call-real-crm/plan.md`
- `specs/002-mock-call-real-crm/contracts/*.md`

Feature 003 target slice:
- Bench owner: `py-bench`.
- Target MVP slice: Slice 3 - Real Call, Real CRM.
- Goal: prove the full MVP loop with one Dynamics / Dataverse queue item, one real SignalWire outbound call, a live Pipecat real-time audio conversation path, the ALF appointment-setter persona, structured outcome capture, and Dynamics write-back.
- The smallest independently demonstrable outcome is: one eligible Dataverse-owned ALF queue item moves from `ready` to a final disposition after a real outbound call, and Dynamics receives the correct Phone Call activity, queue status / attempt / disposition updates, and callback or review Task when warranted.
- This feature must be fully owned by `py-bench`. Do not add Flutter admin app,
  mobile/web UI, generated Dart client, dashboard, install-checklist UI, or
  tenant-onboarding screen tasks to Feature 003. Those start at Feature 004+ in
  `flutterBench`.

What Feature 003 must preserve from Features 001 and 002:
- Preserve Dynamics / Dataverse as the CRM source of truth and operator surface. Do not introduce a parallel campaign UI, custom task queue, or CRM replacement.
- Reuse the Slice 2 Dataverse queue source and write-back behavior: metadata verification before write-enabled runs, approved mapping artifacts, owner/team mapping for callback and review Tasks, high-confidence CRM value preservation, dry-run/readiness checks, explicit write-enabled mode, local audit artifacts, idempotency-key stamping, bounded retry, and resume behavior for partial write-back.
- Preserve the Slice 1 conceptual contracts wherever possible: queue item, eligibility decision, normalized session result, disposition enum, Phone Call activity, queue-status update, Task payload, idempotency expectations, and artifact/report surfaces.
- Preserve the ALF persona policy: AI disclosure on behalf of Medx, non-clinical scope, no resident/patient PHI collection, opt-out/DNC stop, allowed-claim limits, extraction schema, human-review reason codes, and deterministic disposition rules. The live model may help produce conversation turns and extraction events, but final disposition and safety behavior must remain auditable.

New Feature 003 scope:
- Add real SignalWire outbound dialing for one selected eligible Dataverse queue item.
- Add SignalWire status and media callback handling needed for the MVP real-call path.
- Rename the provider-call concept from mock provider call ID to real provider call ID for Slice 3 while keeping backwards-compatible correlation where needed.
- Translate SignalWire provider states and callbacks into the normalized openCloser event/disposition model: connected, no-answer, voicemail, failed, completed, and any required ringing/answered/intermediate states.
- Enforce hard telephony readiness before any real dial: SignalWire credentials, source number, destination number, call/webhook configuration, campaign/persona mapping, verified Dataverse mapping, callback owner mapping, and local call-window/DNC/attempt eligibility must all pass.
- Enforce E.164 or provider-acceptable phone-number validation before placing a SignalWire call. A missing or malformed real-dial phone number must block before dialing and must not consume an attempt.
- Add the live Pipecat runtime path using the configured real-time audio model provider as the primary conversation path.
- Stream or bridge call audio through Pipecat and the configured real-time AI provider so the ALF appointment-setter persona can converse live, emit extraction events, and produce a final structured result.
- Add non-blocking shadow STT support for Slice 3 when enabled. Shadow STT listens to the same caller audio, stores a transcript or pointer under the same session and retention policy, compares high-value fields against the realtime model transcript/log, records discrepancies, and routes uncertain outcomes to human review. Shadow STT must not block live conversation turns and must not independently write CRM records or override final disposition in the MVP.
- Keep transcript and artifact retention deployment-configurable, including summary-only or pointer-only policies. Redaction must remain default-on before transcript artifacts are written. Logs and artifacts must not contain secrets.
- Produce an operator-readable run report and local audit artifacts sufficient to explain provider status, live conversation result, CRM write-back, shadow STT discrepancy status when enabled, and any failure or blocked reason without a custom openCloser UI.

Required run and safety posture:
- The default or safest invocation must not place a real call accidentally. A live dial must require an explicit real-call/write-enabled flag or equivalent deliberate action.
- Provide a rehearsal/readiness path that verifies Dataverse mapping, SignalWire readiness, callback URL configuration, credentials presence, phone formatting, and persona/runtime configuration without dialing or mutating CRM beyond approved dry-run behavior.
- Real-call mode processes exactly one Dataverse queue item per invocation for the MVP. Batch calling, schedulers, campaign automation loops, multi-worker processing, and distributed job queues are out of scope.
- A blocked eligibility or readiness result must create no provider call, consume no attempt, and create no false Phone Call activity.
- If a provider call starts but Dataverse write-back partially fails, the same Slice 2 retry/resume and duplicate-prevention guarantees must apply.

User stories the generated spec should cover:
- Process one eligible Dataverse queue item through a real SignalWire call and write the final result to Dynamics.
- Rehearse a real-call run with zero dial and zero CRM writes beyond approved dry-run/readiness artifacts.
- Block unsafe or unready real dialing before the provider call starts.
- Handle SignalWire callbacks, duplicate callbacks, provider failures, no-answer, voicemail, hangup, and completed calls idempotently.
- Run the live Pipecat / real-time model conversation path while preserving ALF persona safety and structured-result requirements.
- Record shadow STT discrepancies without blocking the live call and route uncertain high-value discrepancies to human review.
- Recover from transient provider or CRM failures without duplicate Phone Call activities, duplicate Tasks, duplicate queue transitions, or duplicate attempt increments.

Out of scope for Feature 003:
- Flutter admin app work, generated Dart clients, mobile/web packaging,
  tenant-onboarding UI, install-checklist UI, dashboard UI, and campaign status
  UI. These are separate `flutterBench` features after 003.
- Multiple telephony providers.
- App voice/video, avatars, LiveKit, or browser calling.
- Clinical, patient-facing, nurse, doctor, or medical workflows.
- Opportunity creation.
- Custom product UI, campaign UI, analytics dashboard, transcript review console, or replacement CRM task queue.
- Dograh as a required runtime or campaign system.
- Celery, Redis as a required dependency, Kubernetes, broad scheduler/batch processing, multi-worker coordination, or generalized workflow engine.
- Automatic sales qualification beyond the approved ALF appointment-setter disposition, summary, captured email, callback intent, DNC, and review-task fields.

Expected measurable outcomes:
- One eligible Dataverse ALF queue item can be dialed through SignalWire and moved to a final disposition with Dynamics write-back and local audit evidence.
- An interested outcome creates exactly one Dynamics callback Task assigned to the configured owner/team.
- A `needs_human_review` outcome creates exactly one Dynamics review Task with a reason code.
- A DNC/opt-out outcome updates the Dataverse DNC/opt-out fields and prevents further automated attempts, with no follow-up Task.
- No-answer, voicemail, failed, and hangup paths produce sane normalized outcomes and do not create false connected-call results.
- 100% of duplicate SignalWire callbacks and repeated recovery attempts leave Dynamics with no duplicate Phone Call activities, Tasks, queue transitions, or attempt increments.
- 100% of malformed or non-provider-acceptable destination numbers are blocked before a SignalWire call is placed.
- Shadow STT discrepancies, when enabled, are recorded as audit/review evidence and never block the live call path or directly mutate CRM in the MVP.
- The feature can be demonstrated without a custom openCloser UI: operator evidence comes from CLI/API output, local audit artifacts, and Dynamics records.

Specification instructions:
- Write the spec as a requirements document, not an implementation plan. Keep code layout, dependency choices beyond the already-governing stack, endpoint shapes, and package names for `/speckit.plan`.
- Include a clear Constitution Alignment section covering CRM control plane, thin slice, adapter/runtime/persona boundaries, audit/idempotency, safety/privacy/human handoff, and architecture constraints.
- Include the required Bench Owner field with `py-bench`, and state that any
  Flutter/admin-app work is a later feature that consumes versioned contracts.
- Include explicit assumptions and edge cases for provider callback ordering, duplicate callbacks, abandoned calls, mid-call opt-out, phone-number validation, provider/webhook readiness, partial CRM write-back, shadow STT mismatch, and transcript retention.
- Do not weaken or delete any Slice 1 or Slice 2 contract unless the spec explicitly calls out a justified, minimal amendment for the real-call boundary.
```
