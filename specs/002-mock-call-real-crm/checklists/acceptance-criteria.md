# Acceptance Criteria Quality Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that success criteria and acceptance scenarios are measurable,
technology-agnostic, traceable, and complete. Tests how the *criteria are written*, not
whether the implementation meets them.
**Created**: 2026-05-22
**Re-verified**: 2026-05-22 against `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Acceptance-criteria domain · **Audience**: PR reviewer / spec author

## Success-Criteria Measurability

- [x] CHK001 Are SC-001–SC-012 each expressed with an objectively measurable threshold or binary outcome? [Measurability, Spec §Success Criteria] — Resolved: SC-001–SC-015 each state a binary or counted outcome.
- [x] CHK002 Are all success criteria free of implementation detail (technology-agnostic)? [Consistency, Spec §Success Criteria] — Resolved: SCs describe CRM-level outcomes, not implementation.
- [x] CHK003 Is "no manual intervention during the run" (SC-001) measurable exactly as stated? [Measurability, Spec §SC-001] — Resolved: SC-001 is binary-checkable per run.
- [x] CHK004 Can SC-002's "zero Dataverse records created or updated" be verified by a defined inspection procedure? [Measurability, Spec §SC-002] — Resolved: SC-002 ("verified by inspecting Dynamics") + quickstart §5.
- [x] CHK005 Is SC-003's "exactly one callback/review Task" reconciled with dispositions that legitimately create zero Tasks? [Clarity, Spec §SC-003] — Resolved: SC-003 is scoped to Task-producing dispositions; SC-005's "at most one Task" covers zero-Task dispositions.
- [x] CHK006 Is SC-005's "exactly one … at most one Task" measurable and unambiguous? [Measurability, Spec §SC-005] — Resolved: SC-005 states counted outcomes per record type.
- [x] CHK007 Can SC-010's "0 Dataverse-specific field names outside the adapter" be objectively verified? [Measurability, Spec §SC-010] — Resolved: SC-010 ("verifiable by inspection / boundary test") + plan §Verification.
- [x] CHK008 Can SC-011's "Slice 1 contract satisfied unchanged" be verified by contract tests with a defined pass criterion? [Measurability, Spec §SC-011] — Resolved: SC-011 + plan §Verification evidence + contracts/dataverse-adapter.md.
- [x] CHK009 Can SC-012's "operator can inspect … without a custom UI" be verified with a defined inspection procedure? [Measurability, Spec §SC-012] — Resolved: SC-012 + quickstart §6.

## Traceability to Requirements

- [x] CHK010 Does every functional requirement trace to at least one acceptance scenario or success criterion? [Traceability, Spec §Success Criteria] — Resolved: §Requirement Coverage Notes maps FR groups, including FR-006 and FR-035, to the governing user stories, edge cases, and success criteria.
- [x] CHK011 Does every success criterion trace back to at least one functional requirement? [Traceability, Spec §Success Criteria] — Resolved: re-verified — each SC-001…015 maps to FRs (e.g. SC-013→FR-031, SC-014→FR-023, SC-015→FR-024).
- [x] CHK012 Is there a success criterion covering the CLI default-to-dry-run behavior introduced in FR-031? [Gap, Coverage] — Resolved by SC-013.
- [x] CHK013 Is there a measurable criterion for the retry/resume behavior (FR-023) beyond the idempotency count in SC-005? [Gap, Spec §FR-023] — Resolved by SC-014.
- [x] CHK014 Is there a measurable criterion for the idempotency-key field requirement (FR-024)? [Gap, Spec §FR-024] — Resolved by SC-015.
- [x] CHK015 Are the four Clarifications session decisions each reflected in an acceptance scenario or success criterion? [Traceability, Spec §Clarifications] — Resolved: Q1→SC-014/US4.3, Q2→SC-015/US4.2, Q3→SC-013, Q4→US3/SC-007.

## Acceptance Scenario Quality

- [x] CHK016 Do all User Story acceptance scenarios use complete Given/When/Then triplets? [Clarity, Spec §US1] — Resolved: US1–US6 scenarios use complete Given/When/Then.
- [x] CHK017 Are the acceptance scenarios free of implementation detail? [Consistency, Spec §US1] — Resolved: scenarios are behavioral.
- [x] CHK018 Does US1 scenario 5 ("per-disposition decisions match the Slice 1 contract") reference a locatable contract? [Traceability, Spec §US1] — Resolved: plan + contracts/dataverse-adapter.md pin the Slice 1 write-back contract to `specs/001/contracts/crm-writeback.md`.
- [x] CHK019 Are acceptance scenarios defined for each supported disposition (callback, email-captured, review, DNC, blocked)? [Coverage, Spec §SC-003] — Resolved: US1 scenarios 1–5 cover callback/email/review/DNC/blocked; scenario 6 covers "any disposition".
- [x] CHK020 Is the `interested_email_captured` disposition covered by an acceptance scenario, given it appears in SC-003 but not in the US1 scenarios? [Conflict, Spec §SC-003] — Resolved by US1 scenario 2.
- [x] CHK021 Are acceptance criteria for the redaction summary-only mode complete beyond SC-009? [Coverage, Spec §SC-009] — Resolved: SC-009 + US6 scenario 2.
- [x] CHK022 Are the "Independent Test" descriptions specific enough to be executed without ambiguity? [Clarity, Spec §US1] — Resolved: each US Independent Test names concrete inputs and observable outcomes.

## Coverage Gaps

- [x] CHK023 Are acceptance criteria defined for the metadata-drift and partial-availability cases? [Gap, Coverage] — Resolved: drift and partial availability are subsumed under "cannot be verified" — US3 scenario 1 + SC-007 + FR-002.
- [x] CHK024 Are acceptance criteria defined for the resume-after-failure path? [Gap, Spec §FR-023] — Resolved by US4 scenario 3 and SC-014.
- [x] CHK025 Is a Definition-of-Done style aggregate for the slice stated (all SCs met)? [Completeness, Spec §Success Criteria] — Resolved: plan §Constitution Check §"Verification evidence required before completion" aggregates the completion bar.
- [x] CHK026 Are the success criteria stable against the open ambiguities (e.g., attempt-increment timing) so they will not need rework? [Consistency, Spec §FR-008] — Resolved: the attempt-timing ambiguity is closed (FR-021 + Definitions §Attempt consumed), so the SCs no longer depend on an open ambiguity.

## Notes

- Requirements-quality audit only — tests whether criteria are well-written and measurable, not whether the system passes them.
- **Re-verification result: 26/26 resolved.** SC-013/014/015, the plan, and §Requirement Coverage Notes close every item.
