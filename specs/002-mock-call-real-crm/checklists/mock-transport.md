# Mock Transport & Slice 1 Contract Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for fixture pre-validation (GitHub issue #2), mock
transport scope, Slice 1 contract preservation, and persona/disposition determinism — for
completeness, clarity, consistency, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Mock transport & contract domain · **Audience**: PR reviewer / spec author

## Fixture Pre-Validation (GitHub Issue #2)

- [ ] CHK001 Is the complete set of required mock-event identity fields enumerated (is `type`/`event_id`/`timestamp` exhaustive)? [Completeness, Spec §FR-020]
- [ ] CHK002 Is fixture validation required to run during call placement, before any session-state, queue-status, or attempt-count mutation? [Clarity, Spec §FR-019]
- [ ] CHK003 Are the three malformed-fixture classes (invalid JSON; no `events` array; an event missing a required field) each backed by explicit requirements? [Completeness, Spec §FR-020]
- [ ] CHK004 Does the spec require a malformed fixture to create no session row, consume no attempt, and make no Dataverse queue update? [Completeness, Spec §FR-020]
- [ ] CHK005 Are requirements defined for a fixture file that is missing entirely (not just malformed)? [Gap, Coverage, Spec §FR-020]
- [ ] CHK006 Does the spec define validation behavior for a fixture that is valid JSON but semantically inconsistent (e.g., events out of timestamp order)? [Coverage, Gap, Spec §FR-019]
- [ ] CHK007 Is it specified whether fixture pre-validation applies in both dry-run and write-enabled modes? [Coverage, Spec §FR-019]
- [ ] CHK008 Is the GitHub issue #2 closure condition stated as a testable requirement? [Traceability, Spec §Assumptions]
- [ ] CHK009 Is the relationship between a transport fixture and a conversation fixture defined (one artifact or two)? [Ambiguity, Spec §US1]
- [ ] CHK010 Are requirements defined for a fixture referencing a disposition not in the supported set? [Coverage, Gap, Spec §FR-013]
- [ ] CHK011 Can "100% of malformed fixtures fail before any state, attempt, or queue change" be objectively verified? [Measurability, Spec §SC-006]

## Mock Transport Scope

- [ ] CHK012 Does the spec require the existing fixture-driven mock transport and scripted persona, excluding SignalWire, Pipecat/live audio, real-time models, and real outbound traffic? [Completeness, Spec §FR-012]
- [ ] CHK013 Is it explicit that the mock transport does not dial, so hard phone-format enforcement is deferred? [Clarity, Spec §FR-034]
- [ ] CHK014 Is the mock provider call ID required to be recorded when a call is placed? [Completeness, Spec §Constitution Alignment]
- [ ] CHK015 Are requirements defined for the mock transport failing to initialize after eligibility passes? [Gap, Coverage]

## Slice 1 Contract Preservation

- [ ] CHK016 Are the preserved Slice 1 module contracts (orchestrator, eligibility evaluator, transport, persona) each individually identified? [Completeness, Spec §FR-014]
- [ ] CHK017 Is "no Slice-2-specific behavior added to those modules" stated as an objectively reviewable constraint? [Measurability, Spec §FR-014]
- [ ] CHK018 Is the FR-019 fixture pre-validation the sole stated exception to contract preservation? [Consistency, Spec §FR-014]
- [ ] CHK019 Is "the Slice 1 write-back contract" pinned to a locatable Slice 1 artifact or version? [Traceability, Spec §FR-014]
- [ ] CHK020 Is the queue-item contract consumed by the eligibility evaluator required to be reused unchanged? [Completeness, Spec §FR-008]

## Persona & Disposition Determinism

- [ ] CHK021 Is the deterministic persona extraction rule referenced precisely enough to validate it is "unchanged"? [Clarity, Spec §FR-013]
- [ ] CHK022 Is the disposition-precedence rule specified or referenced unambiguously? [Clarity, Spec §FR-013]
- [ ] CHK023 Is the complete set of supported final dispositions enumerated in one authoritative place? [Completeness, Spec §FR-013]
- [ ] CHK024 Is the persona-version identifier's format and source specified so it can be recorded reliably? [Clarity, Gap, Spec §Constitution Alignment]
- [ ] CHK025 Are requirements defined for the persona/transport behavior under a mid-call opt-out event? [Coverage, Spec §FR-027]
- [ ] CHK026 Is the normalized session result required to be the same shape proven in Slice 1? [Consistency, Spec §FR-013]

## Notes

- Requirements-quality audit only.
- High-signal defects: CHK001 (identity-field set may be non-exhaustive), CHK006 (semantically-invalid fixtures), CHK009 (transport vs. conversation fixture ambiguity), CHK023 (disposition set not centrally enumerated).
