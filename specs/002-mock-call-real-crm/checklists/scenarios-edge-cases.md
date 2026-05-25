# Scenario & Edge Case Coverage Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that *requirements* exist and are well-formed for every scenario class
(primary, alternate, exception, recovery, non-functional), the listed edge cases, and
phone-number data quality. Tests the spec, not the implementation.
**Created**: 2026-05-22
**Re-verified**: 2026-05-24 against `plan.md`, `research.md`, `data-model.md`, `contracts/` (post-`45a2356` audit pass; see `reverification.md`)
**Feature**: [spec.md](../spec.md)
**Depth**: Maximum (release-gate) · **Breadth**: Scenario & edge-case domain · **Audience**: PR reviewer / spec author

## Scenario-Class Coverage

- [x] CHK001 Are primary-flow requirements complete for the end-to-end write-enabled path? [Coverage, Spec §US1] — Resolved: US1 + FR-008–FR-018.
- [x] CHK002 Are alternate-flow requirements complete for the dry-run rehearsal path? [Coverage, Spec §US2] — Resolved: US2 + FR-031.
- [x] CHK003 Are exception-flow requirements complete for a blocked-by-eligibility item? [Coverage, Spec §US1] — Resolved: US1 scenario 5 + FR-011 + FR-018 + SC-008.
- [x] CHK004 Are exception-flow requirements complete for malformed transport fixtures? [Coverage, Spec §US5] — Resolved: US5 + FR-019/FR-020 + SC-006.
- [x] CHK005 Are exception-flow requirements complete for unverifiable Dataverse metadata? [Coverage, Spec §US3] — Resolved: US3 + FR-002 + SC-007.
- [x] CHK006 Are recovery-flow requirements complete for transient mid-write-back failure plus retry/resume? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases + FR-023 + US4 scenario 3 + SC-014.
- [x] CHK007 Are requirements defined for Dataverse being entirely unreachable at run start (distinct from failing mid-run)? [Gap, Coverage] — Resolved by US3 scenario 4, FR-002, and Edge Cases.
- [x] CHK008 Are non-functional scenario requirements (e.g., a slow Dataverse response) addressed or explicitly excluded? [Gap, Coverage] — Resolved: a slow Dataverse manifests as an httpx timeout = transient error → bounded retry (Definitions + FR-023).
- [x] CHK009 Is each scenario class (primary / alternate / exception / recovery) represented by at least one acceptance scenario? [Completeness, Spec §US1] — Resolved: Primary US1, Alternate US2, Exception US3/US5, Recovery US4.
- [x] CHK010 Are requirements defined for a mid-call opt-out scenario as distinct from a `do_not_call` final disposition? [Coverage, Spec §FR-027] — Resolved: FR-027 + US1 scenario 4 both name "(or a mid-call opt-out)" distinctly.

## User Story Independence

- [x] CHK011 Is each User Story's "Independent Test" actually independently executable without the other stories? [Coverage, Spec §US1] — Resolved: each US carries a self-contained Independent Test.
- [x] CHK012 Do the acceptance scenarios use complete Given/When/Then triplets with no implied steps? [Clarity, Spec §US1] — Resolved: re-verified across US1–US6.
- [x] CHK013 Are the priority assignments (P1/P2/P3) justified and consistent with the stated dependency order? [Consistency, Spec §US3] — Resolved: each US carries a "Why this priority" rationale.
- [x] CHK014 Does each User Story state a standalone, demonstrable outcome? [Measurability, Spec §US1] — Resolved: each US states a demonstrable outcome.

## Edge Case Coverage

- [x] CHK015 Is each of the ten listed Edge Cases backed by at least one functional requirement? [Traceability, Spec §Edge Cases] — Resolved: each Edge Case maps to an FR or Assumption (transient→FR-023, unreachable→FR-002, status-change→FR-003, empty queue→FR-009, multiple items→FR-008, etc.).
- [x] CHK016 Are requirements defined for a queue-item status changed by a human between claim and write-back (a status change, not only a field overwrite)? [Gap, Spec §Edge Cases] — Resolved by Edge Cases.
- [x] CHK017 Are requirements defined for a Phone Call/Task field required by the environment but absent from the mapping? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases ("caught by metadata verification (Story 3)") + FR-002.
- [x] CHK018 Are requirements defined for a queue item with no usable timezone (default applied and recorded)? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases (configured default timezone applied and recorded).
- [x] CHK019 Are requirements defined for the redaction policy and summary-only retention being configured together? [Coverage, Gap, Spec §FR-030] — Resolved: data-model §3 (`policy` and `retention` are independent keys) + contracts/redaction-layer.md (summary-only writes no transcript file regardless of policy).
- [x] CHK020 Are requirements defined for detecting local session/audit state diverging from CRM business state? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases + §Assumptions §Source of truth + contracts/dataverse-adapter.md (the Dataverse pre-query reconciles to Dataverse as the authority).
- [x] CHK021 Are requirements defined for a duplicate `callback_requested` mock event for a CRM-backed session? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases (original callback Task retained).
- [x] CHK022 Are requirements defined for dry-run requested without write credentials present? [Coverage, Spec §Edge Cases] — Resolved: §Edge Cases + FR-031.
- [x] CHK023 Are edge cases distinguished as in-scope-handled vs. intentionally-deferred so reviewers can tell them apart? [Clarity, Spec §Edge Cases] — Resolved: handled edge cases describe behavior; deferred ones say so explicitly (e.g. non-E.164 → Slice 3).
- [x] CHK024 Are requirements defined for the empty-queue and multi-item selection cases (not currently listed among the edge cases)? [Gap, Coverage] — Resolved by FR-008, FR-009, and Edge Cases.
- [x] CHK025 Is the blocked-by-eligibility edge case consistent with FR-011, FR-018, and SC-008? [Consistency, Spec §Edge Cases] — Resolved: re-verified consistent across §Edge Cases, FR-011, FR-018, SC-008.

## Phone-Number Data Quality

- [x] CHK026 Is the non-E.164 warn-and-continue behavior bounded (does any disposition still get blocked)? [Clarity, Spec §FR-034] — Resolved: FR-034 — the warning does not change exit status; a missing/blank number remains a blocked eligibility failure.
- [x] CHK027 Is "data-quality warning" defined (where surfaced, what format, whether it affects exit status)? [Clarity, Spec §FR-034] — Resolved: FR-034 (recorded in the run report + queue-status payload, does not change exit status) + data-model §4 (`DataQualityWarning`).
- [x] CHK028 Is the deferral of hard E.164 enforcement to Slice 3 stated as an explicit, traceable assumption? [Traceability, Spec §Assumptions] — Resolved: §Assumptions §Non-E.164 phone numbers.
- [x] CHK029 Are requirements defined for a missing (not just malformed) phone number on the CRM record? [Gap, Coverage, Spec §FR-034] — Resolved by FR-011 and FR-034.

## Mid-Run CRM-State Conflict (T045/T046 — added 2026-05-24)

- [x] CHK030 Is the "Dataverse queue item changed by a human between claim and write-back" edge case specified with measurable behavior — the re-read timing (before final queue-status / DNC / attempt write), the detection conditions (queue no longer in session-owned in-progress state, or a `preserve_if_present` value changed), and the conflict-stop semantics (only already-completed approved writes preserved, partial `writeback_progress` persisted, operator-visible conflict result)? [Coverage, Spec §Edge Cases, T045, T046] — Resolved: spec §Edge Cases prose + spec §Definitions §Permanent Dataverse error (mid-run conflict explicitly classified) + T045 task description + T046 integration test scenario.

## Notes

- Requirements-quality audit only — checks that requirements *exist and are well-formed* for each scenario, not that scenarios pass.
- **Re-verification result: 30/30 resolved.** The spec's expanded Edge Cases + FR-034 + the plan's transient-error/redaction design + T045/T046 conflict-detection scenario close every scenario- and edge-case item — no open defects in this domain.
