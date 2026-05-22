# Scenario & Edge Case Coverage Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that *requirements* exist and are well-formed for every scenario class
(primary, alternate, exception, recovery, non-functional), the listed edge cases, and
phone-number data quality. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Scenario & edge-case domain · **Audience**: PR reviewer / spec author

## Scenario-Class Coverage

- [ ] CHK001 Are primary-flow requirements complete for the end-to-end write-enabled path? [Coverage, Spec §US1]
- [ ] CHK002 Are alternate-flow requirements complete for the dry-run rehearsal path? [Coverage, Spec §US2]
- [ ] CHK003 Are exception-flow requirements complete for a blocked-by-eligibility item? [Coverage, Spec §US1]
- [ ] CHK004 Are exception-flow requirements complete for malformed transport fixtures? [Coverage, Spec §US5]
- [ ] CHK005 Are exception-flow requirements complete for unverifiable Dataverse metadata? [Coverage, Spec §US3]
- [ ] CHK006 Are recovery-flow requirements complete for transient mid-write-back failure plus retry/resume? [Coverage, Spec §Edge Cases]
- [x] CHK007 Are requirements defined for Dataverse being entirely unreachable at run start (distinct from failing mid-run)? [Gap, Coverage] — Resolved by US3 scenario 4, FR-002, and Edge Cases.
- [ ] CHK008 Are non-functional scenario requirements (e.g., a slow Dataverse response) addressed or explicitly excluded? [Gap, Coverage]
- [ ] CHK009 Is each scenario class (primary / alternate / exception / recovery) represented by at least one acceptance scenario? [Completeness, Spec §US1]
- [ ] CHK010 Are requirements defined for a mid-call opt-out scenario as distinct from a `do_not_call` final disposition? [Coverage, Spec §FR-027]

## User Story Independence

- [ ] CHK011 Is each User Story's "Independent Test" actually independently executable without the other stories? [Coverage, Spec §US1]
- [ ] CHK012 Do the acceptance scenarios use complete Given/When/Then triplets with no implied steps? [Clarity, Spec §US1]
- [ ] CHK013 Are the priority assignments (P1/P2/P3) justified and consistent with the stated dependency order? [Consistency, Spec §US3]
- [ ] CHK014 Does each User Story state a standalone, demonstrable outcome? [Measurability, Spec §US1]

## Edge Case Coverage

- [ ] CHK015 Is each of the ten listed Edge Cases backed by at least one functional requirement? [Traceability, Spec §Edge Cases]
- [x] CHK016 Are requirements defined for a queue-item status changed by a human between claim and write-back (a status change, not only a field overwrite)? [Gap, Spec §Edge Cases] — Resolved by Edge Cases.
- [ ] CHK017 Are requirements defined for a Phone Call/Task field required by the environment but absent from the mapping? [Coverage, Spec §Edge Cases]
- [ ] CHK018 Are requirements defined for a queue item with no usable timezone (default applied and recorded)? [Coverage, Spec §Edge Cases]
- [ ] CHK019 Are requirements defined for the redaction policy and summary-only retention being configured together? [Coverage, Gap, Spec §FR-030]
- [ ] CHK020 Are requirements defined for detecting local session/audit state diverging from CRM business state? [Coverage, Spec §Edge Cases]
- [ ] CHK021 Are requirements defined for a duplicate `callback_requested` mock event for a CRM-backed session? [Coverage, Spec §Edge Cases]
- [ ] CHK022 Are requirements defined for dry-run requested without write credentials present? [Coverage, Spec §Edge Cases]
- [ ] CHK023 Are edge cases distinguished as in-scope-handled vs. intentionally-deferred so reviewers can tell them apart? [Clarity, Spec §Edge Cases]
- [x] CHK024 Are requirements defined for the empty-queue and multi-item selection cases (not currently listed among the edge cases)? [Gap, Coverage] — Resolved by FR-008, FR-009, and Edge Cases.
- [ ] CHK025 Is the blocked-by-eligibility edge case consistent with FR-011, FR-018, and SC-008? [Consistency, Spec §Edge Cases]

## Phone-Number Data Quality

- [ ] CHK026 Is the non-E.164 warn-and-continue behavior bounded (does any disposition still get blocked)? [Clarity, Spec §FR-034]
- [ ] CHK027 Is "data-quality warning" defined (where surfaced, what format, whether it affects exit status)? [Clarity, Spec §FR-034]
- [ ] CHK028 Is the deferral of hard E.164 enforcement to Slice 3 stated as an explicit, traceable assumption? [Traceability, Spec §Assumptions]
- [x] CHK029 Are requirements defined for a missing (not just malformed) phone number on the CRM record? [Gap, Coverage, Spec §FR-034] — Resolved by FR-011 and FR-034.

## Notes

- Requirements-quality audit only — checks that requirements *exist and are well-formed* for each scenario, not that scenarios pass.
- Resolved in this pass: CHK007 (Dataverse-unreachable-at-start), CHK016 (status-change-during-run), CHK024 (empty queue / multi-item), CHK029 (missing phone number).
