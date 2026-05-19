# Plan Quality Checklist: Slice 1 — Mock Call, Mock CRM

**Purpose**: Validate the quality, clarity, and completeness of the plan-phase artifacts (`plan.md`, `research.md`). Unit tests for the *plan writing*, not for the implementation.

**Created**: 2026-05-19
**Plan**: [plan.md](../plan.md) ; [research.md](../research.md)

## Plan Completeness

- [x] CHK001 - Does `plan.md` include a complete Technical Context table covering language, build, CLI, state store, validation, config, fixtures, artifacts, JSON style, schema versioning, timestamps, persona-version format, tests, and tooling? [Completeness, Plan §Technical Context]
- [x] CHK002 - Does the Constitution Check section evaluate every binding principle from the spec's `## Constitution Alignment` (CRM control plane, thin slice, five boundaries, safety, auditability)? [Completeness, Plan §Constitution Check]
- [x] CHK003 - Is the Project Structure tree complete (every FR-033 module has a corresponding package; every fixture category has a directory; every test category has a file)? [Completeness, Plan §Project Structure]
- [x] CHK004 - Does `research.md` resolve every item in spec.md's `## Deferred to Implementation Plan` section? [Completeness, Plan §Phase 0 + Spec §Deferred]
- [x] CHK005 - Is the Phase 2 task-generation outline complete (one work cluster per FR-033 module + bootstrap + integration + CI + docs)? [Completeness, Plan §Phase 2]
- [x] CHK006 - Does the Complexity Tracking table address every elevated-risk surface (multi-module coordination, idempotency correctness, forward-compat, persona determinism, cross-platform readability)? [Completeness, Plan §Complexity Tracking]
- [x] CHK007 - Is the Out-of-Scope section restated faithfully from spec.md §Assumptions (no SignalWire, no Pipecat-beyond-stub, no Dataverse, no UI, no batch, no multi-worker, no clinical persona)? [Completeness, Plan §Out-of-Scope]

## Decision Quality (research.md)

- [x] CHK008 - Does every research decision follow the Decision / Rationale / Alternatives format (≥1 alternative per decision)? [Quality, Plan §Phase 0]
- [x] CHK009 - Is the language choice (Python 3.12+) justified against at least one rejected alternative (Node, Go, Rust)? [Quality, Research §Language]
- [x] CHK010 - Is each rejected alternative cited with a concrete rejection reason (not just "rejected")? [Quality, Plan-wide]
- [x] CHK011 - Is the persona_version format (semver-prefixed) tied to FR-011's auditability mandate? [Traceability, Research §persona_version format + Spec §FR-011]
- [x] CHK012 - Is the SC-009 module-isolation gate (pytest markers + dependency-direction lint) tied to a specific tooling choice that is implementable in Slice 1? [Quality, Research §Tests + Spec §SC-009]
- [x] CHK013 - Is the JSON serialization style (sorted keys, 2-space indent, UTF-8, LF) tied to SC-005's "duplicate event leaves artifact unchanged" requirement? [Traceability, Research §JSON + Spec §SC-005]

## Consistency with Spec

- [x] CHK014 - Is the Technical Context's "state store" decision (SQLite) consistent with spec.md §Assumptions ("Local state store: SQLite")? [Consistency, Plan §Technical Context + Spec §Assumptions]
- [x] CHK015 - Is the project structure's per-module package layout consistent with FR-033's five boundary names? [Consistency, Plan §Project Structure + Spec §FR-033]
- [x] CHK016 - Is research.md's per-disposition artifact emission matrix (e.g., blocked → only queue-status payload) consistent with FR-031? [Consistency, Plan + Spec §FR-031]
- [x] CHK017 - Is the plan's "fixture per disposition" approach consistent with SC-003's "every supported disposition can be reached via a scripted fixture"? [Consistency, Plan §Project Structure + Spec §SC-003]
- [x] CHK018 - Is research.md's persona_version policy ("MAJOR bumps on FR-036 changes; MINOR on disclosure; PATCH on bug fixes") consistent with FR-011's audit-traceability mandate? [Consistency, Research + Spec §FR-011]

## Plan Clarity

- [x] CHK019 - Are absolute paths used for filesystem operations and project-relative paths for documentation references throughout the plan? [Clarity, Plan-wide]
- [x] CHK020 - Are external libraries referenced with version constraints (e.g., `pydantic >=2.7`) rather than unpinned? [Clarity, Research §Validation]
- [x] CHK021 - Is the Constitution Check evidence column specific enough to gate review (cites specific FR / SC / Edge Case numbers)? [Clarity, Plan §Constitution Check]
- [x] CHK022 - Are research.md decisions named to match the corresponding Technical Context row labels (so the plan ↔ research cross-reference is unambiguous)? [Consistency, Plan + Research]

## Forward Compatibility

- [x] CHK023 - Does the plan explicitly state which Slice 2 substitutions will hit which Slice 1 boundaries (SignalWire → transport.md contract; Dataverse → crm-writeback.md contract; real persona → persona.md contract)? [Forward-compat, Plan §Out-of-Scope + Contracts]
- [x] CHK024 - Is SC-008's "Slice 1-time verification" approach specified (interface review at plan time, not runtime check) and documented as such? [Forward-compat, Plan §Complexity Tracking + Spec §SC-008]

## Gaps & Carry-overs

- [x] CHK025 - Is the action item to author `.specify/memory/constitution.md` carried forward to a named Phase 2 task? [Traceability, Plan §Constitution Check]
- [x] CHK026 - Is the deferral list at the end of spec.md explicitly mapped to research.md sections that resolve each item? [Traceability, Plan §Phase 0 + Spec §Deferred + Research §Resolved-spec-deferrals checklist]
