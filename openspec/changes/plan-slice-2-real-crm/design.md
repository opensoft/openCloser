## Context

Slice 1 shipped a local SQLite/artifact-backed implementation of the complete openCloser loop: one queue item, eligibility, mock transport, scripted ALF persona, normalized result, local state, and mock CRM write-back. The Slice 1 contracts intentionally made the mock CRM adapter satisfy the same consumer-facing surface planned for Dataverse: `emit_phone_call_activity`, `emit_queue_status_update`, `emit_task`, and `build_writeback`.

Slice 2 must replace the local queue/write-back stand-in with Dynamics / Dataverse while keeping the call side mocked. This isolates CRM risk before SignalWire, Pipecat, and live audio introduce their own failure modes. The only currently open GitHub issue is also relevant to Slice 2 because the mock transport remains in use: invalid transport fixtures must be rejected before any session mutation or attempt-count increment.

## Goals / Non-Goals

**Goals:**

- Process one Dataverse-owned ALF queue item from `ready` through eligibility, mock call, scripted persona result, and CRM write-back.
- Verify live Dataverse table and field metadata before writing or proposing schema additions.
- Implement the Dataverse adapter behind the existing Slice 1 write-back contract so orchestrator and persona code stay vendor-neutral.
- Populate Dynamics Phone Call, Task, and queue-status fields with the same normalized result semantics proven in Slice 1.
- Add pre-mutation validation for mock transport fixtures so operator input errors do not consume attempts or create partial sessions.
- Introduce the Slice 2 transcript redaction boundary before transcript disk writes.

**Non-Goals:**

- No SignalWire, Pipecat live call path, real-time model, or real outbound traffic.
- No custom product UI, campaign builder, custom task queue, or CRM replacement.
- No batch processing, scheduler, multi-worker locking, Redis/Celery/Kubernetes, or generalized workflow engine.
- No opportunity creation or automated sales qualification beyond task/write-back fields.
- No multi-CRM abstraction; Dataverse is the only Slice 2 CRM target.

## Decisions

1. **Dataverse is the queue source and write-back target for Slice 2.**
   - Rationale: this satisfies the constitution's CRM control-plane rule and proves the operational workflow before real telephony.
   - Alternative rejected: keep local queue state and only mirror write-back to CRM. That would not prove CRM-owned queue status, attempt count, DNC, or task handling.

2. **Keep the mock call transport and scripted ALF persona unchanged except for fixture pre-validation.**
   - Rationale: Feature 2 should isolate CRM integration. Adding real calls or live LLM behavior would hide CRM mapping bugs behind unrelated transport/runtime failures.
   - Alternative rejected: jump directly to SignalWire. The MVP order explicitly makes real CRM the second slice and real call the third slice.

3. **Implement Dataverse as a concrete adapter over the Slice 1 write-back surface.**
   - Rationale: `PhoneCallActivityPayload`, `QueueStatusUpdatePayload`, and `TaskPayload` are the consumer-facing contract. Dataverse field names, lookups, owner IDs, and option-set values belong inside the adapter.
   - Alternative rejected: expose Dataverse entity payloads to the orchestrator. That would couple the core workflow to one CRM vendor and break the Slice 1 boundary work.

4. **Require live metadata discovery before schema or write behavior is finalized.**
   - Rationale: Dataverse field logical names, option-set values, standard Phone Call/Task required fields, and any custom Call Queue Item table must be verified before writes. Existing high-confidence CRM values must be preserved unless a specific overwrite policy is approved.
   - Alternative rejected: designing mappings only from memory or docs. That risks writing to wrong fields or creating duplicate schema.

5. **Use `assigned_to` as the Dataverse owner wiring point for callback/review tasks.**
   - Rationale: Slice 1 made `TaskPayload.assigned_to` optional specifically so Slice 2 could populate it from configuration. The adapter can map this to a Dataverse owner/team lookup without changing the orchestrator.
   - Alternative rejected: derive task owner ad hoc from each queue record. That adds CRM policy scope that is not needed for a one-campaign slice.

6. **Add a redaction boundary before transcript disk writes, default-on for Slice 2.**
   - Rationale: even scripted CRM demos can involve real business contacts, and the constitution requires minimizing sensitive data. A no-op-safe `RedactionLayer` keeps the artifact contract while giving the slice a clear privacy gate.
   - Alternative rejected: defer redaction until live telephony. That keeps an explicit Slice 1 carry-over unresolved and weakens the demo posture against real CRM data.

7. **Reject malformed mock transport fixtures before orchestrator state mutation.**
   - Rationale: GitHub issue #2 shows malformed fixtures can currently leave partial session state and a consumed attempt. Slice 2 still depends on fixtures, so `place_call` must validate fixture structure before the orchestrator moves the CRM queue item or increments attempts.
   - Alternative rejected: catch the exception after `event_stream`. That surfaces the error but does not protect state.

## Risks / Trade-offs

- **Dataverse schema mismatch** -> Mitigate with metadata discovery, documented field mapping, and read-only dry-run checks before writes.
- **CRM writes are hard to roll back** -> Mitigate with one test campaign/queue record, idempotency keys, explicit dry-run mode, and manual cleanup instructions for demo records.
- **Task/Phone Call required fields vary by environment** -> Mitigate by keeping adapter mapping environment-configurable and validating required fields during startup/readiness checks.
- **Redaction may hide useful demo text** -> Mitigate by storing a clear summary and transcript pointer while documenting redaction replacements; allow policy configuration without disabling by accident.
- **Local session state vs CRM business state can diverge** -> Mitigate by treating Dataverse as source of truth for queue lifecycle while keeping local state limited to session/audit/artifacts and correlation IDs.

## Migration Plan

1. Inspect Dataverse metadata for the candidate queue representation, standard Phone Call, Task, Account, Contact, Campaign, owner/team fields, and option sets.
2. Record the field mapping and any required missing CRM fields before code implementation.
3. Add Dataverse configuration using environment-provided secrets and non-secret TOML/YAML mapping.
4. Implement read-only queue loading and eligibility mapping.
5. Implement Dataverse write-back adapter and contract tests using recorded payload shapes.
6. Add fixture pre-validation and transcript redaction before any CRM write demo.
7. Run a dry-run against one CRM queue item, then a write-enabled demo against one test campaign record.

Rollback for implementation is operational: disable the Dataverse adapter configuration and return the demo queue item to its previous CRM status. Slice 1 local/mock behavior remains unchanged.

## Open Questions

- Which existing Dataverse table will represent the Slice 2 Call Queue Item: an existing custom table, a campaign/list record, or a new custom table?
- What are the exact logical names and option-set values for queue status, DNC/opt-out, attempt count, max attempts, last disposition, last session ID, and last error?
- Which user or team owns Slice 2 callback/review Tasks by default?
- Should Slice 2 hard-block non-E.164 phone numbers, or only record a data-quality warning until Slice 3 real telephony?
- Should `preferred_callback_window` remain free-form in CRM Task description, or should Slice 2 also populate a Dataverse due date when the phrase is parseable?
