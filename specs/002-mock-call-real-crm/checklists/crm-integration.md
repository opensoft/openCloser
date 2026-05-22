# CRM Integration Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for Dataverse metadata verification, schema safety,
queue intake, the write-back adapter, and boundary isolation — for completeness, clarity,
consistency, measurability, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: CRM integration domain · **Audience**: PR reviewer / spec author

## Metadata Verification & Schema Safety

- [x] CHK001 Does the spec define which Dataverse error classes are transient (retryable) vs. permanent for verification and write paths? [Gap, Spec §FR-023] — Resolved by Definitions.
- [ ] CHK002 Is the one-time discovery step's required metadata inventory enumerated completely (queue representation, Account, Contact, Campaign, Phone Call activity, Task, owner/team, status values, DNC/opt-out, attempt counters, last disposition, last session ID, last error, idempotency-key field)? [Completeness, Spec §FR-001]
- [x] CHK003 Is "lightweight live verification" specified with the exact tables/fields/lookups/option-sets it must re-check on every write-enabled run? [Clarity, Spec §FR-001] — Resolved by Definitions + FR-001.
- [ ] CHK004 Is the pass/fail criterion for per-run verification defined objectively? [Measurability, Spec §FR-001]
- [ ] CHK005 Are requirements defined for metadata drift detected between the one-time discovery step and a later write-enabled run? [Gap, Coverage, Spec §FR-001]
- [ ] CHK006 Are requirements defined for a previously-verified field being removed or renamed in Dataverse between runs? [Gap]
- [ ] CHK007 Are requirements defined for partial metadata availability (some required tables verifiable, others not)? [Coverage, Spec §FR-002]
- [ ] CHK008 Are requirements defined for option-set value mismatches (value present but label/integer differs from the mapping)? [Coverage, Gap, Spec §FR-002]
- [ ] CHK009 Does the spec require metadata verification to be non-mutating (read-only) so it is safe in dry-run? [Completeness, Spec §FR-001]
- [ ] CHK010 Is the failure behavior for unverifiable metadata required to create or update zero CRM records? [Completeness, Spec §FR-002]
- [ ] CHK011 Is verification of the idempotency-key field explicitly required so its absence blocks write-enabled mode? [Completeness, Spec §FR-024]

## CRM Value Safety

- [x] CHK012 Is "high-confidence value" defined with objective criteria so the FR-003 preservation rule is testable? [Ambiguity, Spec §FR-003] — Resolved by Definitions.
- [ ] CHK013 Does the spec require non-approved fields to be both left unchanged AND absent from the write-back payload? [Completeness, Spec §FR-003]
- [ ] CHK014 Is it specified whether the adapter may read existing CRM values to enforce preservation, and how that read is bounded? [Clarity, Spec §FR-003]
- [ ] CHK015 Are requirements defined for a queue item modified by a human between claim and write-back, including a status change (not only a field overwrite)? [Gap, Spec §Edge Cases]

## Mapping Artifact

- [ ] CHK016 Are the "approved Slice 2 update fields" required to be enumerated explicitly (not described abstractly) in the mapping artifact? [Completeness, Spec §FR-004]
- [ ] CHK017 Is the format and persistence location of the documented mapping artifact specified? [Clarity, Spec §FR-004]
- [ ] CHK018 Does the spec define who or what "approves" the mapping artifact before write-enabled runs? [Ambiguity, Spec §FR-004]
- [ ] CHK019 Is the mapping artifact required to record logical names, required fields, lookups, option-set values, and the idempotency-key field consistently with FR-001? [Consistency, Spec §FR-004]

## Queue Intake

- [ ] CHK020 Is the Dataverse queue-item representation required to map into the existing queue-item contract without a local CSV or mock CRM row? [Completeness, Spec §FR-008]
- [x] CHK021 Are requirements defined for selecting which item is processed when multiple ALF items share the callable status? [Gap, Spec §FR-009] — Resolved by FR-008 and Edge Cases.
- [x] CHK022 Are requirements defined for the empty-queue case (zero items in the callable status)? [Gap, Coverage] — Resolved by FR-009 and Edge Cases.
- [ ] CHK023 Are requirements defined for a configured ALF campaign that cannot be found in Dataverse? [Gap, Coverage]
- [ ] CHK024 Is the rule that a dry-run must not claim or mutate the CRM queue item stated unambiguously? [Clarity, Spec §FR-010]
- [ ] CHK025 Is the ordering between eligibility preconditions, run-mode rules, and in-progress marking fully specified? [Clarity, Spec §FR-010]
- [ ] CHK026 Is the behavior for a queue item not in the configured callable status defined (blocked result, no transport start)? [Completeness, Spec §FR-011]
- [x] CHK027 Does the spec specify the exact point at which the attempt count is incremented (at claim/in-progress vs. at write-back)? [Gap, Spec §FR-008] — Resolved by the `Attempt consumed` definition and FR-021.

## Write-back Adapter & Per-Disposition Contract

- [ ] CHK028 Are the four write-back operations (Phone Call activity emission, queue-status update, Task emission, write-back assembly) each defined with their inputs and outputs? [Completeness, Spec §FR-015]
- [ ] CHK029 Is the per-disposition emission decision map (which artifacts each disposition produces) specified in full? [Completeness, Spec §FR-017]
- [ ] CHK030 Is the per-disposition queue `new_status` value defined for every supported disposition? [Completeness, Spec §FR-017]
- [ ] CHK031 Is "the Slice 1 write-back contract" pinned to a specific, locatable Slice 1 artifact or version? [Traceability, Spec §FR-014]
- [ ] CHK032 Is the blocked-by-eligibility write set ("approved blocked/status/error fields") enumerated explicitly? [Completeness, Spec §FR-018]
- [ ] CHK033 Are requirements defined for an adapter write that partially succeeds within a single operation? [Coverage, Spec §Edge Cases]
- [ ] CHK034 Does the spec define adapter behavior when an owner/team ID in configuration no longer exists in Dataverse? [Gap, Coverage]
- [ ] CHK035 Can "the adapter satisfies the Slice 1 write-back contract" be objectively verified by a defined contract test? [Measurability, Spec §SC-011]

## Boundary Isolation

- [ ] CHK036 Are requirements clear that Dataverse field names, lookups, option-sets, and owner/team IDs must not appear in the orchestrator, eligibility evaluator, transport, or persona? [Clarity, Spec §FR-016]
- [ ] CHK037 Can "0 Dataverse-specific field names or vendor payload shapes outside the adapter" be objectively verified by inspection or a boundary test? [Measurability, Spec §SC-010]
- [ ] CHK038 Is the "write-back assembly" contract specified independently of the Dataverse vendor payload format? [Clarity, Spec §FR-015]

## Notes

- Requirements-quality audit only. `[Gap]` = missing requirement; `[Ambiguity]` = undefined term; `[Conflict]` = internal contradiction.
- Resolved in this pass: CHK001 (transient/permanent errors), CHK003 ("lightweight" scoped), CHK012 ("high-confidence" defined), CHK021/CHK022 (item selection and empty queue), CHK027 (attempt-increment timing).
