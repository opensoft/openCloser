# Acceptance Criteria Quality Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that success criteria and acceptance scenarios are measurable,
technology-agnostic, traceable, and complete. Tests how the *criteria are written*, not
whether the implementation meets them.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Acceptance-criteria domain · **Audience**: PR reviewer / spec author

## Success-Criteria Measurability

- [ ] CHK001 Are SC-001–SC-012 each expressed with an objectively measurable threshold or binary outcome? [Measurability, Spec §Success Criteria]
- [ ] CHK002 Are all success criteria free of implementation detail (technology-agnostic)? [Consistency, Spec §Success Criteria]
- [ ] CHK003 Is "no manual intervention during the run" (SC-001) measurable exactly as stated? [Measurability, Spec §SC-001]
- [ ] CHK004 Can SC-002's "zero Dataverse records created or updated" be verified by a defined inspection procedure? [Measurability, Spec §SC-002]
- [ ] CHK005 Is SC-003's "exactly one callback/review Task" reconciled with dispositions that legitimately create zero Tasks? [Clarity, Spec §SC-003]
- [ ] CHK006 Is SC-005's "exactly one … at most one Task" measurable and unambiguous? [Measurability, Spec §SC-005]
- [ ] CHK007 Can SC-010's "0 Dataverse-specific field names outside the adapter" be objectively verified? [Measurability, Spec §SC-010]
- [ ] CHK008 Can SC-011's "Slice 1 contract satisfied unchanged" be verified by contract tests with a defined pass criterion? [Measurability, Spec §SC-011]
- [ ] CHK009 Can SC-012's "operator can inspect … without a custom UI" be verified with a defined inspection procedure? [Measurability, Spec §SC-012]

## Traceability to Requirements

- [ ] CHK010 Does every functional requirement trace to at least one acceptance scenario or success criterion? [Traceability, Spec §Success Criteria]
- [ ] CHK011 Does every success criterion trace back to at least one functional requirement? [Traceability, Spec §Success Criteria]
- [x] CHK012 Is there a success criterion covering the CLI default-to-dry-run behavior introduced in FR-031? [Gap, Coverage] — Resolved by SC-013.
- [x] CHK013 Is there a measurable criterion for the retry/resume behavior (FR-023) beyond the idempotency count in SC-005? [Gap, Spec §FR-023] — Resolved by SC-014.
- [x] CHK014 Is there a measurable criterion for the idempotency-key field requirement (FR-024)? [Gap, Spec §FR-024] — Resolved by SC-015.
- [ ] CHK015 Are the four Clarifications session decisions each reflected in an acceptance scenario or success criterion? [Traceability, Spec §Clarifications]

## Acceptance Scenario Quality

- [ ] CHK016 Do all User Story acceptance scenarios use complete Given/When/Then triplets? [Clarity, Spec §US1]
- [ ] CHK017 Are the acceptance scenarios free of implementation detail? [Consistency, Spec §US1]
- [ ] CHK018 Does US1 scenario 5 ("per-disposition decisions match the Slice 1 contract") reference a locatable contract? [Traceability, Spec §US1]
- [ ] CHK019 Are acceptance scenarios defined for each supported disposition (callback, email-captured, review, DNC, blocked)? [Coverage, Spec §SC-003]
- [x] CHK020 Is the `interested_email_captured` disposition covered by an acceptance scenario, given it appears in SC-003 but not in the US1 scenarios? [Conflict, Spec §SC-003] — Resolved by US1 scenario 2.
- [ ] CHK021 Are acceptance criteria for the redaction summary-only mode complete beyond SC-009? [Coverage, Spec §SC-009]
- [ ] CHK022 Are the "Independent Test" descriptions specific enough to be executed without ambiguity? [Clarity, Spec §US1]

## Coverage Gaps

- [ ] CHK023 Are acceptance criteria defined for the metadata-drift and partial-availability cases? [Gap, Coverage]
- [x] CHK024 Are acceptance criteria defined for the resume-after-failure path? [Gap, Spec §FR-023] — Resolved by US4 scenario 3 and SC-014.
- [ ] CHK025 Is a Definition-of-Done style aggregate for the slice stated (all SCs met)? [Completeness, Spec §Success Criteria]
- [ ] CHK026 Are the success criteria stable against the open ambiguities (e.g., attempt-increment timing) so they will not need rework? [Consistency, Spec §FR-008]

## Notes

- Requirements-quality audit only — tests whether criteria are well-written and measurable, not whether the system passes them.
- Resolved in this pass: CHK012/CHK013/CHK014 (SC coverage for default mode, retry/resume, and idempotency-key field), CHK020 (`interested_email_captured` scenario), CHK024 (resume-after-failure criteria).
