# Mock Transport & Slice 1 Contract Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate the *requirements* for fixture pre-validation (GitHub issue #2), mock
transport scope, Slice 1 contract preservation, and persona/disposition determinism — for
completeness, clarity, consistency, and coverage. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-22 against `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Mock transport & contract domain · **Audience**: PR reviewer / spec author

## Fixture Pre-Validation (GitHub Issue #2)

- [x] CHK001 Is the complete set of required mock-event identity fields enumerated (is `type`/`event_id`/`timestamp` exhaustive)? [Completeness, Spec §FR-020] — Resolved: FR-020 names exactly `type`/`event_id`/`timestamp` as the required identity fields; contracts/transport-fixture-validation.md.
- [x] CHK002 Is fixture validation required to run during call placement, before any session-state, queue-status, or attempt-count mutation? [Clarity, Spec §FR-019] — Resolved: FR-019 + contracts/transport-fixture-validation.md.
- [x] CHK003 Are the three malformed-fixture classes (invalid JSON; no `events` array; an event missing a required field) each backed by explicit requirements? [Completeness, Spec §FR-020] — Resolved: FR-020 + contracts/transport-fixture-validation.md.
- [x] CHK004 Does the spec require a malformed fixture to create no session row, consume no attempt, and make no Dataverse queue update? [Completeness, Spec §FR-020] — Resolved: FR-020 + Definitions §Attempt consumed.
- [x] CHK005 Are requirements defined for a fixture file that is missing entirely (not just malformed)? [Gap, Coverage, Spec §FR-020] — Resolved: contracts/transport-fixture-validation.md (a missing fixture file is a `MalformedFixtureError`, same no-mutation outcome).
- [x] CHK006 Does the spec define validation behavior for a fixture that is valid JSON but semantically inconsistent (e.g., events out of timestamp order)? [Coverage, Gap, Spec §FR-019] — Resolved: §Edge Cases and FR-020 explicitly accept structurally valid but semantically inconsistent fixtures as outside Slice 2 pre-validation; fixture semantic quality is test-authoring responsibility.
- [x] CHK007 Is it specified whether fixture pre-validation applies in both dry-run and write-enabled modes? [Coverage, Spec §FR-019] — Resolved: contracts/cli-slice2.md + US2 — the mock call runs in both modes, so fixture pre-validation applies in both.
- [x] CHK008 Is the GitHub issue #2 closure condition stated as a testable requirement? [Traceability, Spec §Assumptions] — Resolved: §Assumptions §GitHub issue #2 + SC-006.
- [x] CHK009 Is the relationship between a transport fixture and a conversation fixture defined (one artifact or two)? [Ambiguity, Spec §US1] — Resolved: FR-032 enumerates transport fixture and conversation fixture as two distinct named inputs.
- [x] CHK010 Are requirements defined for a fixture referencing a disposition not in the supported set? [Coverage, Gap, Spec §FR-013] — Resolved: FR-013 + FR-014 — the persona is deterministic and produces only the enumerated disposition set, so a fixture cannot introduce a new disposition.
- [x] CHK011 Can "100% of malformed fixtures fail before any state, attempt, or queue change" be objectively verified? [Measurability, Spec §SC-006] — Resolved: SC-006.

## Mock Transport Scope

- [x] CHK012 Does the spec require the existing fixture-driven mock transport and scripted persona, excluding SignalWire, Pipecat/live audio, real-time models, and real outbound traffic? [Completeness, Spec §FR-012] — Resolved: FR-012.
- [x] CHK013 Is it explicit that the mock transport does not dial, so hard phone-format enforcement is deferred? [Clarity, Spec §FR-034] — Resolved: FR-034 + §Edge Cases + §Assumptions §Non-E.164.
- [x] CHK014 Is the mock provider call ID required to be recorded when a call is placed? [Completeness, Spec §Constitution Alignment] — Resolved: §Constitution Alignment §Auditability + Definitions §Attempt consumed.
- [x] CHK015 Are requirements defined for the mock transport failing to initialize after eligibility passes? [Gap, Coverage] — Resolved: the mock transport's only initialization is fixture loading; malformed/missing fixtures are handled by FR-019/FR-020 + contracts/transport-fixture-validation.md (`failed` status, no attempt consumed).

## Slice 1 Contract Preservation

- [x] CHK016 Are the preserved Slice 1 module contracts (orchestrator, eligibility evaluator, transport, persona) each individually identified? [Completeness, Spec §FR-014] — Resolved: FR-014 names all four; plan §Project Structure + contracts/.
- [x] CHK017 Is "no Slice-2-specific behavior added to those modules" stated as an objectively reviewable constraint? [Measurability, Spec §FR-014] — Resolved: FR-014 + SC-010 (boundary test).
- [x] CHK018 Is the FR-019 fixture pre-validation the sole stated exception to contract preservation? [Consistency, Spec §FR-014] — Resolved: FR-014 + contracts/transport-fixture-validation.md ("the only change permitted").
- [x] CHK019 Is "the Slice 1 write-back contract" pinned to a locatable Slice 1 artifact or version? [Traceability, Spec §FR-014] — Resolved: plan + contracts pin it to `specs/001-mock-call-mock-crm/contracts/crm-writeback.md`.
- [x] CHK020 Is the queue-item contract consumed by the eligibility evaluator required to be reused unchanged? [Completeness, Spec §FR-008] — Resolved: FR-008 + FR-014 + Key Entities §Preserved Slice 1 Entities.

## Persona & Disposition Determinism

- [x] CHK021 Is the deterministic persona extraction rule referenced precisely enough to validate it is "unchanged"? [Clarity, Spec §FR-013] — Resolved: FR-013 references the Slice 1 deterministic extraction rules; FR-014 preserves the persona contract.
- [x] CHK022 Is the disposition-precedence rule specified or referenced unambiguously? [Clarity, Spec §FR-013] — Resolved: FR-013 references the Slice 1 disposition-precedence rules.
- [x] CHK023 Is the complete set of supported final dispositions enumerated in one authoritative place? [Completeness, Spec §FR-013] — Resolved: FR-013 enumerates all 11 dispositions.
- [x] CHK024 Is the persona-version identifier's format and source specified so it can be recorded reliably? [Clarity, Gap, Spec §Constitution Alignment] — Resolved: FR-014 reuses the persona unchanged; the persona-version format is inherited from Slice 1 (`alf-appointment-setter@semver`).
- [x] CHK025 Are requirements defined for the persona/transport behavior under a mid-call opt-out event? [Coverage, Spec §FR-027] — Resolved: FR-027 (mid-call opt-out) + FR-014 (persona stop behavior unchanged).
- [x] CHK026 Is the normalized session result required to be the same shape proven in Slice 1? [Consistency, Spec §FR-013] — Resolved: FR-013 + Key Entities §Preserved Slice 1 Entities.

## Notes

- Requirements-quality audit only.
- **Re-verification result: 26/26 resolved.** The plan's fixture-validation contract, Slice 1 contract-preservation references, and the explicit semantic-fixture acceptance in §Edge Cases / FR-020 close every item.
