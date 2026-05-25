# CRM Integration Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for Dataverse metadata verification, schema safety,
queue intake, the write-back adapter, and boundary isolation — for completeness, clarity,
consistency, measurability, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-24 against `plan.md`, `research.md`, `data-model.md`, `contracts/` (post-`45a2356` audit pass; see `reverification.md`)
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: CRM integration domain · **Audience**: PR reviewer / spec author

## Metadata Verification & Schema Safety

- [x] CHK001 Does the spec define which Dataverse error classes are transient (retryable) vs. permanent for verification and write paths? [Gap, Spec §FR-023] — Resolved by Definitions.
- [x] CHK002 Is the one-time discovery step's required metadata inventory enumerated completely (queue representation, Account, Contact, Campaign, Phone Call activity, Task, owner/team, status values, DNC/opt-out, attempt counters, last disposition, last session ID, last error, idempotency-key field)? [Completeness, Spec §FR-001] — Resolved: FR-001 enumerates the full inventory incl. the idempotency-key field.
- [x] CHK003 Is "lightweight live verification" specified with the exact tables/fields/lookups/option-sets it must re-check on every write-enabled run? [Clarity, Spec §FR-001] — Resolved by Definitions + FR-001.
- [x] CHK004 Is the pass/fail criterion for per-run verification defined objectively? [Measurability, Spec §FR-001] — Resolved: Definitions §Lightweight live verification + FR-002; contracts/metadata-discovery-verification.md (`MetadataVerificationReport`).
- [x] CHK005 Are requirements defined for metadata drift detected between the one-time discovery step and a later write-enabled run? [Gap, Coverage, Spec §FR-001] — Resolved: FR-002 ("when metadata drift is detected ... MUST fail").
- [x] CHK006 Are requirements defined for a previously-verified field being removed or renamed in Dataverse between runs? [Gap] — Resolved: FR-002 (a removed/renamed field is "cannot be verified" / drift).
- [x] CHK007 Are requirements defined for partial metadata availability (some required tables verifiable, others not)? [Coverage, Spec §FR-002] — Resolved: FR-002 ("when only part of the required metadata can be read").
- [x] CHK008 Are requirements defined for option-set value mismatches (value present but label/integer differs from the mapping)? [Coverage, Gap, Spec §FR-002] — Resolved: FR-002 + Definitions §Permanent error (option-set mismatch).
- [x] CHK009 Does the spec require metadata verification to be non-mutating (read-only) so it is safe in dry-run? [Completeness, Spec §FR-001] — Resolved: Definitions §Lightweight live verification ("read-only, non-mutating"); contracts/metadata-discovery-verification.md.
- [x] CHK010 Is the failure behavior for unverifiable metadata required to create or update zero CRM records? [Completeness, Spec §FR-002] — Resolved: FR-002 ("without creating or updating any CRM record").
- [x] CHK011 Is verification of the idempotency-key field explicitly required so its absence blocks write-enabled mode? [Completeness, Spec §FR-024] — Resolved: FR-024 + FR-002 + SC-015.

## CRM Value Safety

- [x] CHK012 Is "high-confidence value" defined with objective criteria so the FR-003 preservation rule is testable? [Ambiguity, Spec §FR-003] — Resolved by Definitions.
- [x] CHK013 Does the spec require non-approved fields to be both left unchanged AND absent from the write-back payload? [Completeness, Spec §FR-003] — Resolved: FR-003 ("MUST be absent from the write-back payload").
- [x] CHK014 Is it specified whether the adapter may read existing CRM values to enforce preservation, and how that read is bounded? [Clarity, Spec §FR-003] — Resolved: FR-003 (adapter MAY read, limited to mapped + preserved fields).
- [x] CHK015 Are requirements defined for a queue item modified by a human between claim and write-back, including a status change (not only a field overwrite)? [Gap, Spec §Edge Cases] — Resolved: §Edge Cases (status change away from session-owned state → write-back stops, conflict for human review).

## Mapping Artifact

- [x] CHK016 Are the "approved Slice 2 update fields" required to be enumerated explicitly (not described abstractly) in the mapping artifact? [Completeness, Spec §FR-004] — Resolved: FR-004 + data-model §2 (`approved_update_field` flag per field).
- [x] CHK017 Is the format and persistence location of the documented mapping artifact specified? [Clarity, Spec §FR-004] — Resolved: research §4 + data-model §2 (`config/dataverse_mapping.json`).
- [x] CHK018 Does the spec define who or what "approves" the mapping artifact before write-enabled runs? [Ambiguity, Spec §FR-004] — Resolved: research §4 + contracts/metadata-discovery-verification.md (PR review sets `_meta.approved = true`).
- [x] CHK019 Is the mapping artifact required to record logical names, required fields, lookups, option-set values, and the idempotency-key field consistently with FR-001? [Consistency, Spec §FR-004] — Resolved: FR-004 + data-model §2.

## Queue Intake

- [x] CHK020 Is the Dataverse queue-item representation required to map into the existing queue-item contract without a local CSV or mock CRM row? [Completeness, Spec §FR-008] — Resolved: FR-008; contracts/dataverse-queue-loader.md.
- [x] CHK021 Are requirements defined for selecting which item is processed when multiple ALF items share the callable status? [Gap, Spec §FR-009] — Resolved by FR-008 and Edge Cases.
- [x] CHK022 Are requirements defined for the empty-queue case (zero items in the callable status)? [Gap, Coverage] — Resolved by FR-009 and Edge Cases.
- [x] CHK023 Are requirements defined for a configured ALF campaign that cannot be found in Dataverse? [Gap, Coverage] — Resolved: §Edge Cases distinguishes configured-campaign-not-found from empty queue, and FR-002 treats an unverifiable configured campaign as a permanent configuration/readiness failure before session, claim, attempt, or write.
- [x] CHK024 Is the rule that a dry-run must not claim or mutate the CRM queue item stated unambiguously? [Clarity, Spec §FR-010] — Resolved: FR-010.
- [x] CHK025 Is the ordering between eligibility preconditions, run-mode rules, and in-progress marking fully specified? [Clarity, Spec §FR-010] — Resolved: FR-010 (in-progress only after metadata/readiness, selection, eligibility allow, run-mode checks, fixture pre-validation).
- [x] CHK026 Is the behavior for a queue item not in the configured callable status defined (blocked result, no transport start)? [Completeness, Spec §FR-011] — Resolved: FR-011.
- [x] CHK027 Does the spec specify the exact point at which the attempt count is incremented (at claim/in-progress vs. at write-back)? [Gap, Spec §FR-008] — Resolved by the `Attempt consumed` definition and FR-021.

## Write-back Adapter & Per-Disposition Contract

- [x] CHK028 Are the four write-back operations (Phone Call activity emission, queue-status update, Task emission, write-back assembly) each defined with their inputs and outputs? [Completeness, Spec §FR-015] — Resolved: contracts/dataverse-adapter.md + specs/001/contracts/crm-writeback.md (payload shapes).
- [x] CHK029 Is the per-disposition emission decision map (which artifacts each disposition produces) specified in full? [Completeness, Spec §FR-017] — Resolved: FR-017 + specs/001/contracts/crm-writeback.md emission table.
- [x] CHK030 Is the per-disposition queue `new_status` value defined for every supported disposition? [Completeness, Spec §FR-017] — Resolved: FR-017 + crm-writeback.md `new_status` table (covers all 11 FR-013 dispositions).
- [x] CHK031 Is "the Slice 1 write-back contract" pinned to a specific, locatable Slice 1 artifact or version? [Traceability, Spec §FR-014] — Resolved: plan + contracts/dataverse-adapter.md pin it to `specs/001-mock-call-mock-crm/contracts/crm-writeback.md`.
- [x] CHK032 Is the blocked-by-eligibility write set ("approved blocked/status/error fields") enumerated explicitly? [Completeness, Spec §FR-018] — Resolved: FR-018 + data-model §2 (mapping artifact `approved_update_field` set incl. status/last-error).
- [x] CHK033 Are requirements defined for an adapter write that partially succeeds within a single operation? [Coverage, Spec §Edge Cases] — Resolved: each `emit_*` is an atomic unit (contracts/dataverse-adapter.md); cross-operation partial failure is handled by §Edge Cases + FR-023 resume.
- [x] CHK034 Does the spec define adapter behavior when an owner/team ID in configuration no longer exists in Dataverse? [Gap, Coverage] — Resolved: owner/team is verified metadata (Definitions §Lightweight live verification) and a 404 is a Permanent error (FR-002).
- [x] CHK035 Can "the adapter satisfies the Slice 1 write-back contract" be objectively verified by a defined contract test? [Measurability, Spec §SC-011] — Resolved: SC-011 + plan §Verification evidence (contract tests).

## Boundary Isolation

- [x] CHK036 Are requirements clear that Dataverse field names, lookups, option-sets, and owner/team IDs must not appear in the orchestrator, eligibility evaluator, transport, or persona? [Clarity, Spec §FR-016] — Resolved: FR-016.
- [x] CHK037 Can "0 Dataverse-specific field names or vendor payload shapes outside the adapter" be objectively verified by inspection or a boundary test? [Measurability, Spec §SC-010] — Resolved: SC-010 + plan §Verification (boundary test).
- [x] CHK038 Is the "write-back assembly" contract specified independently of the Dataverse vendor payload format? [Clarity, Spec §FR-015] — Resolved: contracts/dataverse-adapter.md (`build_writeback` assembles the conceptual `WriteBack` aggregate).

## Adapter Unit-Test Surface (T048 — added 2026-05-24)

- [x] CHK039 Does the adapter unit-test surface (T048) cover the four behaviors that the contract test (T017) and integration test (T023) don't surface granularly — approved owner-override decision branches, idempotency-key field selection from the mapping artifact, dry-run capture (no POST/PATCH issued), and `preserve_if_present` filtering? [Coverage, T048] — Resolved: T048 enumerates all four; §Definitions §Approved owner override + FR-003 + FR-024 + FR-031 + data-model §2 supply the spec basis.

## Notes

- Requirements-quality audit only. `[Gap]` = missing requirement; `[Ambiguity]` = undefined term; `[Conflict]` = internal contradiction.
- **Re-verification result: 39/39 resolved.** The plan's metadata model, mapping-artifact schema, adapter contract, configured-campaign-not-found rule, and T048 adapter unit-test surface close every item.
