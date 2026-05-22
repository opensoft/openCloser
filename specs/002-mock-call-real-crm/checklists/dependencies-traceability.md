# Dependencies, Assumptions & Traceability Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that dependencies and assumptions are documented and validatable, that
requirements are traceable and consistently named, and that open ambiguities/conflicts are
surfaced. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Dependencies, assumptions & traceability domain · **Audience**: PR reviewer / spec author

## Dependencies

- [ ] CHK001 Is the dependency on a reachable, correctly-configured Dataverse environment stated explicitly? [Gap, Dependency]
- [ ] CHK002 Is the dependency on Slice 1 contracts/artifacts pinned to a locatable version or path? [Dependency, Spec §Assumptions]
- [ ] CHK003 Is the dependency on transport/conversation fixtures documented with their required schema? [Dependency, Spec §FR-012]
- [ ] CHK004 Is the GitHub issue #2 dependency stated with a clear, testable closure condition? [Assumption, Spec §Assumptions]
- [ ] CHK005 Are external-dependency failure modes (Dataverse unavailable, throttled, schema-mismatched) each acknowledged? [Coverage, Gap]
- [ ] CHK006 Is the dependency on deployment-provided configuration (task owners, run mode) separated from spec-level requirements? [Clarity, Spec §Assumptions]

## Assumptions Validation

- [ ] CHK007 Are all Assumptions stated as validatable claims rather than unresolved open questions? [Clarity, Spec §Assumptions]
- [ ] CHK008 Are assumptions that defer decisions to "metadata discovery" clearly marked as discovery outputs, not spec gaps? [Clarity, Spec §Assumptions]
- [ ] CHK009 Is the assumption that Dataverse is the source of truth reconciled with every local-state requirement? [Consistency, Spec §Assumptions]
- [ ] CHK010 Is each out-of-scope exclusion paired with the slice or phase that will own it? [Completeness, Spec §Assumptions]
- [ ] CHK011 Is the non-E.164 warn-not-block assumption supported by a stated rationale (the mock transport does not dial)? [Traceability, Spec §Assumptions]
- [ ] CHK012 Is the `preferred_callback_window` free-text assumption (no structured due date) stated with its deferral rationale? [Clarity, Spec §Assumptions]
- [ ] CHK013 Is the demo-posture assumption (dry-run default, dedicated test record, manual cleanup) complete and actionable? [Completeness, Spec §Assumptions]

## Traceability & Identifiers

- [ ] CHK014 Does ≥80% of requirements carry a stable identifier (FR/SC/US) usable for traceability? [Traceability, Spec §Requirements]
- [ ] CHK015 Is every Key Entity referenced by at least one functional requirement? [Traceability, Spec §Key Entities]
- [ ] CHK016 Are the Clarifications session Q&A entries traceable to the specific FRs they modified? [Traceability, Spec §Clarifications]
- [ ] CHK017 Is each Edge Case traceable to a functional requirement or explicitly marked as deferred? [Traceability, Spec §Edge Cases]
- [ ] CHK018 Is a requirement-and-acceptance-criteria ID scheme established and consistently applied? [Traceability, Spec §Requirements]

## Terminology Consistency

- [ ] CHK019 Is there a single glossary or canonical-term source for CRM-domain terms (queue item, write-back, disposition)? [Gap, Terminology]
- [ ] CHK020 Are "queue-status update", "queue-status transition", and "`new_status`" used consistently to mean the same concept? [Consistency, Terminology]
- [ ] CHK021 Are "mapping artifact", "CRM Field Mapping Artifact", and "Slice 2 mapping artifact" one consistently-named entity? [Consistency, Spec §Key Entities]
- [ ] CHK022 Are the four write-back operations named identically across FR-015, the Constitution Alignment boundary list, and Key Entities? [Consistency, Spec §FR-015]
- [ ] CHK023 Is "write-enabled mode" never conflated with "write-back" in a way that changes meaning? [Consistency, Spec §FR-031]

## Open Ambiguities & Conflicts

- [x] CHK024 Is the disposition-set conflict between SC-003 (`interested_email_captured`) and the US1 scenarios surfaced and resolved? [Conflict, Spec §SC-003] — Resolved by US1 scenario 2.
- [x] CHK025 Is the attempt-count increment-timing ambiguity (FR-008 vs. FR-021) flagged as an open clarification rather than silently assumed? [Ambiguity, Spec §FR-008] — Resolved by the `Attempt consumed` definition and FR-021.
- [x] CHK026 Are undefined terms ("high-confidence value", "transient error", "lightweight verification", "operator-visible") collected as a clarification backlog? [Ambiguity, Spec §Requirements] — Resolved by Definitions.
- [ ] CHK027 Are unresolved design questions explicitly labeled so they are not mistaken for finalized requirements? [Ambiguity, Spec §Assumptions]
- [ ] CHK028 Are all ambiguity/conflict items across this checklist set resolved or explicitly accepted before `/speckit.plan`? [Completeness, Spec §Clarifications]

## Notes

- Requirements-quality audit only.
- Resolved in this pass: CHK024 (disposition-set conflict), CHK025 (attempt-count increment timing), CHK026 (undefined terms).
- Remaining high-signal defects: CHK001/CHK005 (Dataverse dependency and failure modes), CHK019 (canonical glossary coverage beyond the added Definitions section).
