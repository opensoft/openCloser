## 1. CRM Discovery And Mapping

- [ ] 1.1 Inspect live Dataverse metadata for Account, Contact, Campaign, Phone Call, Task, owner/team, and the selected queue item representation.
- [ ] 1.2 Document logical names, required fields, lookups, option-set values, and approved update fields in a Slice 2 CRM mapping artifact.
- [ ] 1.3 Decide whether the Slice 2 queue source is an existing custom table, a campaign/list representation, or a new custom table proposal.
- [ ] 1.4 Define the one-campaign demo record setup and rollback instructions.

## 2. Configuration And Secrets

- [ ] 2.1 Add non-secret Dataverse mapping configuration for queue fields, status values, task owner mapping, and dry-run/write-enabled mode.
- [ ] 2.2 Add environment-variable based Dataverse credential loading without writing secrets to logs or artifacts.
- [ ] 2.3 Add startup/readiness validation that fails when required Dataverse mappings or credentials are missing.

## 3. Dataverse Queue Intake

- [ ] 3.1 Implement a Dataverse queue loader that maps one CRM queue item into the existing `QueueItem` contract.
- [ ] 3.2 Implement a one-item claim path that marks the CRM queue item in progress only after eligibility preconditions and dry-run rules are satisfied.
- [ ] 3.3 Add unit tests for CRM-to-queue mapping, missing fields, non-ready status, DNC, attempt count, and default timezone fallback.

## 4. Mock Transport Hardening

- [ ] 4.1 Move transport fixture parsing and structural validation into `FixtureDrivenTransport.place_call()` before orchestrator state mutation.
- [ ] 4.2 Add tests proving malformed fixture JSON, missing `events`, and missing event identity fields create no session row, no attempt increment, and no CRM update.
- [ ] 4.3 Close GitHub issue #2 after the validation behavior is implemented and tested.

## 5. Dataverse Write-Back Adapter

- [ ] 5.1 Implement a Dataverse adapter behind `emit_phone_call_activity`, `emit_queue_status_update`, `emit_task`, and `build_writeback`.
- [ ] 5.2 Map `PhoneCallActivityPayload` to the verified Dataverse Phone Call required fields and correlation identifiers.
- [ ] 5.3 Map `QueueStatusUpdatePayload` to the verified queue status, DNC, attempt, last disposition, last session, and last error fields.
- [ ] 5.4 Map `TaskPayload` to Dataverse Task fields, including callback/review owner assignment and captured email when present.
- [ ] 5.5 Add adapter-level tests that Dataverse field names stay inside the adapter and do not leak into core, eligibility, transport, or persona modules.

## 6. Idempotency And Error Recovery

- [ ] 6.1 Add CRM correlation identifiers or alternate keys needed to detect duplicate Phone Call and Task writes.
- [ ] 6.2 Add retry tests for transient Dataverse write failures without duplicate activity/task creation.
- [ ] 6.3 Add duplicate mock event tests against the Dataverse adapter path.
- [ ] 6.4 Ensure blocked eligibility creates only the approved CRM queue/status update and no Phone Call or Task.

## 7. Transcript Redaction And Artifacts

- [ ] 7.1 Add a configurable `RedactionLayer` before transcript disk writes with Slice 2 default-on policy.
- [ ] 7.2 Add tests for sensitive-pattern replacement with `[REDACTED]`.
- [ ] 7.3 Add summary-only retention tests proving no full transcript file is written when configured.
- [ ] 7.4 Keep `session-result.json` summary and transcript pointer behavior compatible with Slice 1 artifacts.

## 8. Slice 2 Demo And Documentation

- [ ] 8.1 Update MVP and architecture docs with the narrowed Slice 2 scope, carry-forward decisions, and remaining deferrals to Slice 3.
- [ ] 8.2 Generate the Feature 002 Speckit spec from the accepted Slice 2 scope and run clarify, plan, checklist, tasks, and analyze in the feature worktree.
- [ ] 8.3 Add a quickstart for dry-run and write-enabled processing of one Dataverse queue item.
- [ ] 8.4 Run a dry-run CRM demo and record the planned write-back artifacts.
- [ ] 8.5 Run a write-enabled CRM demo against one test queue item and verify the CRM queue item, Phone Call, Task, local session result, and transcript retention behavior.
