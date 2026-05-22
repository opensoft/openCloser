# Dependencies, Assumptions & Traceability Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that dependencies and assumptions are documented and validatable, that
requirements are traceable and consistently named, and that open ambiguities/conflicts are
surfaced. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-22 against `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Dependencies, assumptions & traceability domain · **Audience**: PR reviewer / spec author

## Dependencies

- [x] CHK001 Is the dependency on a reachable, correctly-configured Dataverse environment stated explicitly? [Gap, Dependency] — Resolved: plan §Technical Context + quickstart §1 prerequisites + FR-002 (unreachable-at-start handling).
- [x] CHK002 Is the dependency on Slice 1 contracts/artifacts pinned to a locatable version or path? [Dependency, Spec §Assumptions] — Resolved: plan + contracts pin `specs/001-mock-call-mock-crm/contracts/*`.
- [x] CHK003 Is the dependency on transport/conversation fixtures documented with their required schema? [Dependency, Spec §FR-012] — Resolved: FR-020 + contracts/transport-fixture-validation.md (transport fixture structure); conversation fixture format inherited from Slice 1.
- [x] CHK004 Is the GitHub issue #2 dependency stated with a clear, testable closure condition? [Assumption, Spec §Assumptions] — Resolved: §Assumptions §GitHub issue #2 + SC-006.
- [x] CHK005 Are external-dependency failure modes (Dataverse unavailable, throttled, schema-mismatched) each acknowledged? [Coverage, Gap] — Resolved: Definitions (transient/permanent) + FR-002 (unreachable/drift/partial) + FR-023 (throttling/429).
- [x] CHK006 Is the dependency on deployment-provided configuration (task owners, run mode) separated from spec-level requirements? [Clarity, Spec §Assumptions] — Resolved: §Assumptions §Task ownership + data-model §3 (`slice2.toml`).

## Assumptions Validation

- [x] CHK007 Are all Assumptions stated as validatable claims rather than unresolved open questions? [Clarity, Spec §Assumptions] — Resolved: §Assumptions entries are concrete claims, not open questions.
- [x] CHK008 Are assumptions that defer decisions to "metadata discovery" clearly marked as discovery outputs, not spec gaps? [Clarity, Spec §Assumptions] — Resolved: §Assumptions §Dataverse queue representation / §Dataverse field logical names ("implementation-discovery output, not a spec-level decision").
- [x] CHK009 Is the assumption that Dataverse is the source of truth reconciled with every local-state requirement? [Consistency, Spec §Assumptions] — Resolved: §Assumptions §Source of truth + data-model §1 + Key Entities.
- [x] CHK010 Is each out-of-scope exclusion paired with the slice or phase that will own it? [Completeness, Spec §Assumptions] — Resolved: §Assumptions pairs exclusions with their owning slice/phase (non-E.164 → Slice 3, callback-window parsing → later scheduling integration, etc.).
- [x] CHK011 Is the non-E.164 warn-not-block assumption supported by a stated rationale (the mock transport does not dial)? [Traceability, Spec §Assumptions] — Resolved: §Assumptions §Non-E.164 phone numbers.
- [x] CHK012 Is the `preferred_callback_window` free-text assumption (no structured due date) stated with its deferral rationale? [Clarity, Spec §Assumptions] — Resolved: §Assumptions §`preferred_callback_window`.
- [x] CHK013 Is the demo-posture assumption (dry-run default, dedicated test record, manual cleanup) complete and actionable? [Completeness, Spec §Assumptions] — Resolved: §Assumptions §Demo posture + quickstart §8.

## Traceability & Identifiers

- [x] CHK014 Does ≥80% of requirements carry a stable identifier (FR/SC/US) usable for traceability? [Traceability, Spec §Requirements] — Resolved: FR-001–035, SC-001–015, US1–6 all carry stable IDs.
- [x] CHK015 Is every Key Entity referenced by at least one functional requirement? [Traceability, Spec §Key Entities] — Resolved: each Key Entity maps to an FR (Queue Item→FR-008, Mapping Artifact→FR-004, Adapter→FR-015/016, Task Owner Mapping→FR-025, Redaction→FR-028, Run Mode→FR-031, Correlation ID→FR-024, Preserved Slice 1 Entities→FR-014).
- [x] CHK016 Are the Clarifications session Q&A entries traceable to the specific FRs they modified? [Traceability, Spec §Clarifications] — Resolved: the session entries map to FR-001/FR-023/FR-024/FR-031.
- [x] CHK017 Is each Edge Case traceable to a functional requirement or explicitly marked as deferred? [Traceability, Spec §Edge Cases] — Resolved: each Edge Case maps to an FR or an Assumption.
- [x] CHK018 Is a requirement-and-acceptance-criteria ID scheme established and consistently applied? [Traceability, Spec §Requirements] — Resolved: the FR-/SC-/US- scheme is applied consistently.
- [x] CHK019 Is there a single glossary or canonical-term source for CRM-domain terms (queue item, write-back, disposition)? [Gap, Terminology] — Resolved: the spec §Definitions section + §Key Entities together serve as the canonical-term source.

## Terminology Consistency

- [x] CHK020 Are "queue-status update", "queue-status transition", and "`new_status`" used consistently to mean the same concept? [Consistency, Terminology] — Resolved: re-verified — "queue-status update" = the operation/payload, "`new_status`" = its field, "queue-status transition" = its effect; no contradiction.
- [x] CHK021 Are "mapping artifact", "CRM Field Mapping Artifact", and "Slice 2 mapping artifact" one consistently-named entity? [Consistency, Spec §Key Entities] — Resolved: one entity (Key Entities §CRM Field Mapping Artifact = `config/dataverse_mapping.json`), referenced consistently.
- [x] CHK022 Are the four write-back operations named identically across FR-015, the Constitution Alignment boundary list, and Key Entities? [Consistency, Spec §FR-015] — Resolved: re-verified — identical naming across FR-015, §Constitution Alignment §Boundaries, and Key Entities.
- [x] CHK023 Is "write-enabled mode" never conflated with "write-back" in a way that changes meaning? [Consistency, Spec §FR-031] — Resolved: "write-enabled mode" = run mode, "write-back" = the CRM write operation; used distinctly.

## Open Ambiguities & Conflicts

- [x] CHK024 Is the disposition-set conflict between SC-003 (`interested_email_captured`) and the US1 scenarios surfaced and resolved? [Conflict, Spec §SC-003] — Resolved by US1 scenario 2.
- [x] CHK025 Is the attempt-count increment-timing ambiguity (FR-008 vs. FR-021) flagged as an open clarification rather than silently assumed? [Ambiguity, Spec §FR-008] — Resolved by the `Attempt consumed` definition and FR-021.
- [x] CHK026 Are undefined terms ("high-confidence value", "transient error", "lightweight verification", "operator-visible") collected as a clarification backlog? [Ambiguity, Spec §Requirements] — Resolved by Definitions.
- [x] CHK027 Are unresolved design questions explicitly labeled so they are not mistaken for finalized requirements? [Ambiguity, Spec §Assumptions] — Resolved: discovery-deferred items are explicitly labeled in §Assumptions; no unlabeled `[NEEDS CLARIFICATION]` markers remain.
- [x] CHK028 Are all ambiguity/conflict items across this checklist set resolved or explicitly accepted before `/speckit.plan`? [Completeness, Spec §Clarifications] — Resolved: the residual checklist items are now closed by targeted spec notes in §Definitions, §Edge Cases, FR-002, FR-007, FR-020, FR-023, FR-025, FR-035, §Requirement Coverage Notes, and §Assumptions.

## Notes

- Requirements-quality audit only.
- **Re-verification result: 28/28 resolved.** The prior residual items across all 10 checklists are resolved by targeted spec notes and requirements: campaign-not-found, correlation-ID retention, malformed redaction policy, audit-artifact retention, compliance scope, approved owner override criteria, semantic fixture acceptance, and FR→SC traceability.
