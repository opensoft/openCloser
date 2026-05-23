# Re-verification Checklist (post-`/speckit-analyze` remediation): Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that (a) the 12 pre-existing 2026-05-22 checklists remain aligned
with the post-`45a2356` spec/plan/tasks state, (b) the new scope introduced by the
post-implement `/speckit-analyze` pass (T029a/T029b split, T045/T046 mid-run conflict
detection, T047 no-secrets-in-artifacts assertion, T048 adapter unit tests, T041 retention
extension, T027/T028 dry-run-readiness tightening) is well-specified, and (c)
previously-implicit cross-cutting domains (observability, testing-strategy, conflict-
detection) now have explicit requirements-quality coverage. Tests the *requirements*, not
the implementation.

**Created**: 2026-05-23
**Feature**: [spec.md](../spec.md)
**Anchor commit**: `45a2356` — `[Spec Kit] Slice 2 — resolve /speckit-analyze findings`

## Alignment Re-verification (per existing checklist)

- [ ] CHK001 Does `acceptance-criteria.md` (26/26 resolved 2026-05-22) remain aligned with the post-`45a2356` spec, including measurable acceptance criteria for the new conflict-stop edge case (T046) and the dry-run-missing-credentials scenario (T027)? [Consistency, Re-verification]
- [ ] CHK002 Does `alignment.md` (33/33 resolved 2026-05-22) remain accurate after the §Requirement Coverage Notes rewrite (I1) and the T029→T029a/T029b split — i.e., every FR still maps to ≥1 task and every task still maps to ≥1 FR/SC? [Consistency, Traceability]
- [ ] CHK003 Does `constitution.md` (23/23 resolved 2026-05-22) remain aligned — no constitution principle was weakened by the new T045 conflict-stop, T047 no-secrets-in-artifacts, or T041 row-retention scope? [Consistency, Re-verification]
- [ ] CHK004 Does `crm-integration.md` (38/38 resolved 2026-05-22) cover the new T048 adapter unit-test surface (owner-override decisions, idempotency-key stamping, dry-run capture, `preserve_if_present` filtering)? [Coverage, Gap]
- [ ] CHK005 Does `dependencies-traceability.md` (28/28 resolved 2026-05-22) reflect the FR-001/FR-024 attribution rewrite (I1) and the new T045/T046/T047/T048 + T029a/T029b traceability anchors? [Traceability, Re-verification]
- [ ] CHK006 Does `idempotency-recovery.md` (31/31 resolved 2026-05-22) cover the mid-run CRM-state conflict-detection requirement introduced by T045 (FR-003 + FR-021 interplay)? [Coverage, Gap]
- [ ] CHK007 Does `mock-transport.md` (26/26 resolved 2026-05-22) remain aligned — no transport-surface change in `45a2356`? [Consistency, Re-verification]
- [ ] CHK008 Does `non-functional.md` (24/24 resolved 2026-05-22) cover the FR-023 row-retention floor (`crm_correlations` / `writeback_progress` ≥ 90 days) now in T041's expanded scope? [Coverage, Gap]
- [ ] CHK009 Does `requirements.md` (21/21 resolved 2026-05-22) remain valid — i.e., no new `[NEEDS CLARIFICATION]` markers were introduced by the analyze remediation? [Clarity, Re-verification]
- [ ] CHK010 Does `run-modes-config.md` (28/28 resolved 2026-05-22) cover the dry-run vs write-enabled readiness distinction now explicit in T027/T028? [Coverage, Gap]
- [ ] CHK011 Does `scenarios-edge-cases.md` (29/29 resolved 2026-05-22) cover the requirements for the "Dataverse queue item changed by a human between claim and write-back" edge case beyond the prose entry — i.e., are conflict-detection requirements now specified with measurable behavior (T045/T046)? [Coverage, Spec §Edge Cases]
- [ ] CHK012 Does `security-privacy.md` (31/31 resolved 2026-05-22) cover the explicit "no secret values appear in produced run reports / artifacts / DB rows" requirement now backed by T047? [Coverage, Gap]
- [ ] CHK013 Does each of the 12 existing checklists have its "Re-verified" date / status line updated when material new scope is added, so a future auditor can tell which scope each checklist was last verified against? [Traceability, Convention, Gap]

## New Scope: T045 + T046 — Mid-run CRM-state Conflict Detection (G1)

- [ ] CHK014 Does the spec specify *when* the mid-run re-read of mapped queue fields + `preserve_if_present` set occurs (e.g., immediately before the final queue-status / DNC / attempt write, not earlier)? [Clarity, Spec §Edge Cases, T045]
- [ ] CHK015 Does the spec define the precise conditions that constitute a "human change" — queue no longer in session-owned in-progress state, OR a `preserve_if_present` value changed, OR an approved-update field changed by a human, OR all of the above? [Completeness, Spec §Edge Cases, T045]
- [ ] CHK016 Are the partial-write semantics of the conflict stop specified — i.e., which already-completed writes are preserved, which planned writes are abandoned, and how this state is recorded in `writeback_progress`? [Clarity, Spec §Edge Cases, T045]
- [ ] CHK017 Is the operator-visible conflict surface specified (exit status, run-report fields, the specific message format identifying the changed field(s)), per spec §Definitions §Operator-visible? [Completeness, T045]
- [ ] CHK018 Are conflict-stop requirements consistent with FR-021's idempotency requirement — a conflict-stopped session re-invoked later MUST NOT create duplicate records, but MUST surface the same conflict (not silently resume)? [Consistency, Spec §FR-021, T045]
- [ ] CHK019 Is the test scenario in T046 specified at enough depth that "force the Dataverse fake to mutate the in-progress queue item's status (or a `preserve_if_present` field) between claim and the final queue-status write" can be implemented unambiguously by a test author? [Clarity, T046]
- [ ] CHK020 Are requirements consistent on whether a conflict counts as a "consumed attempt" per spec §Definitions §Attempt consumed — given that `place_call` already succeeded, the attempt is consumed even though the final write is blocked? [Consistency, Spec §Definitions §Attempt consumed, T045]
- [ ] CHK021 Is the relationship between conflict-stop and the retry budget specified — i.e., a conflict is a permanent CRM-state error, NOT a transient that consumes retry attempts? [Clarity, Spec §Definitions §Permanent Dataverse error, T045]

## New Scope: T047 — No-Secrets-in-Artifacts Assertion (G2)

- [ ] CHK022 Does the spec enumerate *which* values are considered secrets for the negative-assertion test (tenant ID, client ID, client secret, env URL, refresh tokens, access tokens, etc.)? [Completeness, Spec §FR-005, T047]
- [ ] CHK023 Does the spec specify the inspection surface for T047 — every produced artifact type (run report, planned write-back payload, actual write-back payload, redacted transcript file, `crm_correlations` / `writeback_progress` rows)? [Coverage, T047]
- [ ] CHK024 Are requirements consistent on whether the secret-redaction property applies to ERROR artifacts too (a 401/403 response captured in a run-report error should not leak the bearer token)? [Consistency, Spec §FR-005, Gap]
- [ ] CHK025 Is the failure mode of T047 specified — i.e., a literal substring match is sufficient, OR a more sophisticated check (URL-decoded, base64-decoded, hex-encoded variants) is required? [Clarity, T047]
- [ ] CHK026 Are requirements consistent across FR-005 (secrets handling) and FR-035 (no secrets retained in audit artifacts) — i.e., no FR overrides the other, and T047 satisfies both? [Consistency, Spec §FR-005, §FR-035]

## New Scope: T027 + T028 — Dry-Run vs Write-Enabled Readiness (G3/I3)

- [ ] CHK027 Does FR-007's "for the selected run mode" clearly enumerate which validations apply to dry-run only, which to write-enabled only, and which to both? [Completeness, Spec §FR-007]
- [ ] CHK028 Is the spec §Edge Cases "Dry-run requested but write credentials are absent" entry consistent with T027's added scenario (dry-run with `DATAVERSE_CLIENT_SECRET` unset still succeeds)? [Consistency, Spec §Edge Cases, T027]
- [ ] CHK029 Does the spec specify what dry-run readiness DOES require (mapping configuration present + valid, redaction policy present + valid, fixture present + valid) vs what it skips (live metadata verification, credentials presence, Dataverse reachability)? [Clarity, T028]
- [ ] CHK030 Are requirements consistent on whether dry-run readiness performs the mapping-artifact schema validation but NOT the live Dataverse `verify()` call (the dry-run still surfaces an incomplete mapping per spec §User Story 2 §AC3)? [Consistency, Spec §FR-007, §FR-031, T028]
- [ ] CHK031 Is the spec §FR-031 "write-enabled mode MUST require an explicit flag" consistent with T028's mode-aware readiness — i.e., a write-enabled run with credentials absent fails at readiness, not at first write? [Consistency, Spec §FR-007, §FR-031, T028]
- [ ] CHK032 Does the spec specify the operator-visible error wording for the "write credentials missing in write-enabled mode" case distinctly from the "mapping invalid" case, so an operator can immediately tell which gate failed? [Clarity, Gap, T028]

## New Scope: T041 — FR-023 Row Retention (G4)

- [ ] CHK033 Does the spec specify the retention granularity for `crm_correlations` and `writeback_progress` rows — per-row, per-session, or per-run; and what "expired" means (deletable vs auto-deleted)? [Clarity, Spec §FR-023, T041]
- [ ] CHK034 Are the FR-023 (CRM correlation / write-back progress) and FR-035 (local audit artifacts) retention requirements consistent on the ≥90-day floor — i.e., taking the longer of the two retentions, not the shorter? [Consistency, Spec §FR-023, §FR-035]
- [ ] CHK035 Does the spec specify that retention deletion is a manual/operator action (not auto-delete), per FR-035's "no auto-delete" wording, and is the same rule consistent for FR-023 rows? [Clarity, Spec §FR-023, §FR-035, T041]
- [ ] CHK036 Is the spec clear that a write-back progress row in `resume_needed` state MUST be retained until the session is either resumed-completed or explicitly abandoned, even if it predates the 90-day floor's calendar window? [Clarity, Spec §FR-023, T041, Gap]
- [ ] CHK037 Does the spec specify any operator-visible inventory or report listing rows older than the floor (so the operator can decide whether to extend retention before manually pruning), or is that intentionally out of scope? [Coverage, Gap, T041]

## New Scope: T048 — Adapter Unit Tests (U1)

- [ ] CHK038 Does the spec specify the "Approved owner override" decision logic with enough precision that T048 unit tests can encode each branch (mapped source present/absent × resolves to active enabled user/team yes/no × permitted for Task kind yes/no)? [Completeness, Spec §Definitions §Approved owner override, T048]
- [ ] CHK039 Does the spec specify the dry-run-capture behavior in terms a unit test can assert (no httpx POST/PATCH issued; planned payload returned with the same conceptual content the write-enabled path would have sent)? [Clarity, Spec §FR-031, T048]
- [ ] CHK040 Does the spec specify the `preserve_if_present` filtering rule at the field-by-field level — i.e., the write-back payload omits any mapped field where the read-back current value is non-null AND not in the approved Slice 2 update set? [Clarity, Spec §FR-003, T048]
- [ ] CHK041 Does the spec specify the idempotency-key stamping rule — which field is stamped (per the mapping artifact's verified idempotency-key entry), what value (the session ID or a deterministic derivation), and whether the stamp is idempotent across retries? [Completeness, Spec §FR-024, T048]
- [ ] CHK042 Are T048 unit-test surfaces consistent with the contract-test surface (T017) and the integration surface (T023) — i.e., no overlap that creates duplicate maintenance, no gap that leaves a behavior untested? [Consistency, T017, T023, T048]

## New Scope: T029a + T029b — Metadata vs Operational Gate Split (U2)

- [ ] CHK043 Does the T029a/T029b split match the spec §FR-002 enumeration cleanly — every gate in FR-002 belongs to either T029a (metadata) or T029b (operational) with no overlap and no gap? [Completeness, Spec §FR-002, T029a, T029b]
- [ ] CHK044 Are the T029a and T029b error classifications consistent with spec §Definitions — T029a gates raise Permanent Dataverse errors; T029b's "Dataverse-unreachable-at-start" raises a *retryable* startup failure per spec §Edge Cases? [Consistency, Spec §Definitions, T029a, T029b]
- [ ] CHK045 Is the spec clear that the T029b "configured-campaign-not-found" gate is distinct from the FR-009 empty-queue clean no-op (different exit semantics, different operator-visible result)? [Clarity, Spec §Edge Cases, FR-009, T029b]

## Cross-Cutting: Observability (previously implicit)

- [ ] CHK046 Does the spec specify the minimum required content of the local run report — session ID, eligibility decision, mock provider call ID, persona version, started/ended timestamps, final disposition, CRM correlation identifiers per §Constitution Alignment §Auditability? [Completeness, Spec §Constitution Alignment, Gap]
- [ ] CHK047 Does the spec specify the format or schema of the run report (JSON / TOML / text) so a downstream tool or operator can parse it deterministically? [Clarity, Gap]
- [ ] CHK048 Does the spec specify which run-report fields are present in dry-run vs write-enabled (e.g., "Dataverse correlation IDs" exist only in write-enabled), so a missing field in dry-run is not mistaken for a defect? [Coverage, Gap]
- [ ] CHK049 Are observability requirements consistent across the run report, planned write-back artifacts, and write-back progress records — same session-ID linkage, same correlation-ID wording, same timestamps? [Consistency, Gap]
- [ ] CHK050 Does the spec specify any log-line requirements (level, structured fields, redaction rules) distinct from the run-report artifact, or are logs intentionally out of scope and the run-report is the sole observability surface? [Coverage, Gap]
- [ ] CHK051 Are requirements defined for *correlating* a Slice 2 session ID with the corresponding Dataverse Phone Call activity / Task / queue update so an operator can navigate from one to the other? [Completeness, Spec §FR-024, Gap]
- [ ] CHK052 Does the spec specify operator-visible distinction between the four resume states (`in_progress` / `completed` / `resume_needed` / `blocked`) in the run-report or progress artifact? [Clarity, Spec §Key Entities §Write-Back Progress Ledger]

## Cross-Cutting: Testing Strategy

- [ ] CHK053 Does the spec or plan specify the test pyramid for Slice 2 — what belongs in `tests/unit/` vs `tests/contract/` vs `tests/integration/` vs the fixture-driven `tests/fixtures/dataverse/fake.py` surface? [Clarity, plan §Verification Evidence, Gap]
- [ ] CHK054 Are testing requirements consistent across user stories — every user story has at least one integration test (T023, T027, T030, T034, T036, T039, T046) and the contract surface has a dedicated contract test (T017)? [Consistency, Coverage]
- [ ] CHK055 Does the spec specify what live-CRM testing (if any) is required vs. the in-process Dataverse fake — and is the fake's contract documented enough that test authors know when an assertion-against-fake is sufficient evidence for an FR? [Clarity, plan §Testing, Gap]
- [ ] CHK056 Are requirements defined for testing the metadata `discover()` step (T013/T020) — is it tested by the foundational unit suite (T016) or by the US1 integration suite (T023) or both? [Coverage, Gap]
- [ ] CHK057 Does the spec specify what happens to a test fixture under FR-019/FR-020 — is the fixture pre-validation itself unit-tested (T036) AND exercised end-to-end (test_us5_malformed_fixture.py) so both surfaces of the FR are covered? [Consistency, T035, T036]
- [ ] CHK058 Is the "test against fake" coverage consistent with the "manual demo against live Dataverse" requirement (plan §Verification Evidence) — i.e., the fake validates the contract and the manual demo validates real-CRM behavior? [Consistency, plan §Verification, SC-001]

## Cross-Cutting: Conflict Detection (post-T045)

- [ ] CHK059 Are conflict-detection requirements defined symmetrically — both for the queue-status field (the primary in-progress marker) AND for any `preserve_if_present` field changed mid-run? [Completeness, Spec §Edge Cases, T045]
- [ ] CHK060 Is the spec clear about the *cost* of the mid-run re-read (one extra GET to Dataverse before the final write) and that this extra GET is required even in retry-resume paths to detect human changes that occurred while the run was paused? [Clarity, T045, Gap]
- [ ] CHK061 Are requirements consistent on whether a conflict detected during *resume* (T032) follows the same conflict-stop semantics as a conflict detected during the initial run (T045)? [Consistency, T032, T045, Gap]
- [ ] CHK062 Does the spec specify what an operator does after a conflict stop — is the recovery path "human reconciles the CRM record and re-runs the CLI", and what evidence the run-report provides for that reconciliation? [Coverage, T045, Gap]

## Cross-Checklist Consistency

- [ ] CHK063 Are conflict-detection requirements consistently referenced across `scenarios-edge-cases.md`, `idempotency-recovery.md`, and `crm-integration.md` (the three checklists that touch this surface), or do gaps remain in any one? [Consistency, Re-verification]
- [ ] CHK064 Are dry-run-readiness requirements consistently referenced across `run-modes-config.md`, `non-functional.md` (readiness as a reliability property), and `acceptance-criteria.md`? [Consistency, Re-verification]
- [ ] CHK065 Are no-secrets-in-artifacts requirements consistently referenced across `security-privacy.md` and `non-functional.md` (data-governance dimension)? [Consistency, Re-verification]
- [ ] CHK066 Are retention requirements (FR-023 + FR-035) consistently referenced across `non-functional.md`, `idempotency-recovery.md` (for `writeback_progress` resumeability), and `security-privacy.md` (for "no secrets retained")? [Consistency, Re-verification]
- [ ] CHK067 Does any checklist still reference a pre-2026-05-23 task ID that has been renamed (T029 → T029a/T029b) or refer to a coverage-note attribution that has been rewritten (FR-001/FR-024 in I1)? [Consistency, Re-verification, Gap]

## Depth: Release-Gate Items (resilience, rollback, partial failure)

- [ ] CHK068 Are the four resume states (`in_progress` / `completed` / `resume_needed` / `blocked`) defined with mutually exclusive, exhaustive criteria so a session is always in exactly one state? [Completeness, Spec §Key Entities §Write-Back Progress Ledger]
- [ ] CHK069 Are state-transition requirements specified — which states can transition to which, what events cause each transition (transient error → resume_needed; conflict stop → blocked; etc.)? [Clarity, Gap]
- [ ] CHK070 Does the spec specify the rollback / cleanup expectations for partial failures — e.g., if the Phone Call activity is created but the queue-status write fails, what's the operator-visible state and what's the resumption story? [Coverage, Spec §Edge Cases, FR-023]
- [ ] CHK071 Are requirements defined for the demo-record cleanup path beyond the quickstart's manual cleanup — e.g., is there a "demo-mode rollback" CLI subcommand requirement, or is manual cleanup the only supported path? [Coverage, Spec §Assumptions §Demo posture, Gap]
- [ ] CHK072 Are requirements consistent on what happens to local artifacts when a CRM record is manually rolled back by the operator (demo cleanup) — do the local artifacts need a corresponding sweep, or are they retained as audit evidence? [Consistency, FR-035, Gap]

## Notes

- Requirements-quality audit only — every item asks whether the spec/plan/tasks *say* the right thing, not whether code behaves.
- This file is a **re-verification checklist** scoped to the changes introduced by commit `45a2356` (post-`/speckit-analyze` remediation). The 12 pre-2026-05-22 domain checklists remain authoritative for their domains; this file augments them with (a) per-checklist alignment items, (b) new-scope items, and (c) previously-implicit cross-cutting items (observability, testing strategy, conflict detection).
- **Result**: 72 items, **0 resolved at file creation**. Items will be marked `[x]` as each is confirmed against the post-`45a2356` spec — track this checklist's resolution alongside the next `/speckit-implement` pass.
- Domains intentionally skipped because they are genuinely inapplicable to a CLI-only Slice 2: `ux`, `accessibility` (no UI surface), `deployment` / `rollback at the infrastructure level` (no service deployment — local CLI only), `api` (no public HTTP API — the only HTTP surface is the Dataverse client, which is covered by `crm-integration.md`).
