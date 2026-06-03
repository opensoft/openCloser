## Why

Slice 1 proved the local loop, but openCloser is constitutionally CRM-first and the next MVP risk is whether the same queue, eligibility, persona, result, and write-back loop works with Dynamics / Dataverse as the operational control plane. This change scopes Slice 2 so the team can integrate real CRM before taking on real telephony.

## What Changes

- Add a Dataverse-backed queue source for one ALF campaign and one queue item at a time.
- Add a Dataverse CRM adapter that satisfies the Slice 1 write-back contract for Phone Call activity creation, queue-status updates, and Task creation.
- Keep the Slice 1 mock call transport and scripted ALF persona so Feature 2 isolates CRM integration risk.
- Carry forward Slice 1 contract-review items that matter for Slice 2: `assigned_to` owner mapping for tasks, transcript redaction before disk write, and Dataverse field-shape verification.
- Fold GitHub issue #2 into Slice 2 planning by validating mock transport fixtures before any session state or attempt count changes.
- Preserve the MVP rails: no SignalWire, no Pipecat live call path, no custom UI, no batch worker, no opportunity creation, no multi-CRM abstraction.

## Capabilities

### New Capabilities

- `mock-call-real-crm`: Process one CRM-owned ALF queue item through the existing mock call and scripted persona path, then write the normalized outcome back to Dynamics / Dataverse.

### Modified Capabilities

- None. The shipped Slice 1 contracts remain the baseline; Slice 2 adds a new CRM-backed capability rather than changing the Slice 1 mock-call/mock-CRM behavior.

## Impact

- Affected specs and docs: new OpenSpec capability for Slice 2, MVP PRD Slice 2 details, architecture CRM integration notes, and Slice 1 forward-compat notes where they contain stale Slice 2 wording.
- Affected code areas when implemented: `src/opencloser/crm/`, queue-loading/claim code, configuration/secrets, artifact writing, mock transport validation, and integration tests.
- External systems: Dynamics 365 / Dataverse Web API and existing CRM metadata for Account, Contact, Campaign, Phone Call, Task, and the selected Call Queue Item representation.
- Required verification: live CRM schema inspection before field creation or writes, dry-run/read-only CRM checks, contract tests against Dataverse payload mapping, and a demo against one CRM queue item.
