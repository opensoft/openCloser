# Cross-Artifact Alignment Checklist: Slice 2 — Mock Call, Real CRM

**Purpose**: Validate that `spec.md`, `plan.md`, and `tasks.md` are mutually consistent,
fully cross-covered, and traceable before implementation — a requirements-quality audit of
*alignment* (the Consistency / Coverage / Traceability dimensions), not of implementation.
**Created**: 2026-05-22
**Verified**: 2026-05-22 against `spec.md`, `plan.md`, `tasks.md`, `research.md`,
`data-model.md`, `contracts/` — corroborated by `/speckit.analyze` (0 findings).
**Re-verified**: 2026-05-24 against post-`45a2356` spec/plan/tasks (see `reverification.md`).
**Feature**: [spec.md](../spec.md)
**Depth**: Release-gate · **Breadth**: spec ↔ plan ↔ tasks alignment · **Audience**: PR reviewer / spec author

## Spec → Plan Alignment

- [x] CHK001 Does the plan address every spec requirement area (metadata verification, queue intake, write-back adapter, idempotency/recovery, redaction, run modes/CLI)? [Coverage] — plan §Summary + §Technical Context + §Project Structure cover all six.
- [x] CHK002 Does the plan's Technical Context account for every external dependency the spec implies (Dataverse, mock transport, transport/conversation fixtures)? [Completeness] — plan §Technical Context table.
- [x] CHK003 Does the plan's Constitution Check address every principle the spec's §Constitution Alignment invokes? [Consistency] — plan §Constitution Check covers all 5 principles + architecture + delivery workflow.
- [x] CHK004 Is every spec §Key Entity represented in the plan's `data-model.md`? [Consistency] — data-model.md §1/§4; the **Write-Back Progress Ledger** entity ↔ `writeback_progress` table.
- [x] CHK005 Does the plan record a design decision for each spec §Clarifications session answer (retry model, idempotency anchor, default mode, metadata structure)? [Traceability] — research.md §6/§7, §3/§4, §5.
- [x] CHK006 Are the spec's deferred/out-of-scope items (§Assumptions) consistent with the plan's non-goals and Complexity Tracking? [Consistency] — plan §Constitution Check row II + empty §Complexity Tracking.

## Spec → Tasks Coverage

- [x] CHK007 Does every functional requirement FR-001–FR-035 map to at least one task? [Coverage] — verified 1:1; see tasks.md task-to-FR references and `/speckit.analyze` coverage table.
- [x] CHK008 Does every Success Criterion SC-001–SC-015 map to a verifying task? [Coverage] — SC→task mapping complete (T017, T023, T027, T030, T034, T036, T039, T040).
- [x] CHK009 Is every spec User Story US1–US6 represented by a dedicated task phase? [Coverage] — tasks.md Phases 3–8, one per story, in priority order.
- [x] CHK010 Is each spec Edge Case covered by a task or an explicitly documented acceptance? [Coverage] — edge cases map to FRs (FR-002/009/023/034) and the documented C2 deferral.
- [x] CHK011 Does each test-verified Success Criterion (SC-006, SC-010, SC-011) have a corresponding test task? [Coverage] — SC-006→T036, SC-010→T040, SC-011→T017.
- [x] CHK012 Does each User Story task phase carry that story's Independent Test from the spec? [Consistency] — every tasks.md story phase has a `Goal` + `Independent Test` line drawn from the spec.

## Plan → Tasks Alignment

- [x] CHK013 Does every NEW module in the plan's §Project Structure have a creating task? [Coverage] — `crm/dataverse/{errors,auth,client,mapping,metadata,queue_loader,adapter}`, `redaction/layer`, `slice2/{runner,resume}` → T008/T010/T011/T012/T013/T014/T018, T037, T019/T032.
- [x] CHK014 Does every file the plan marks MODIFIED have a modifying task? [Consistency] — `models.py`→T005, `state/*`→T006/T007, `core/config.py`→T009, `transport/mock.py`→T035, `artifacts/writer.py`→T026/T038/T041, `cli.py`→T020/T021/T033.
- [x] CHK015 Do the Setup-phase tasks introduce exactly the dependencies named in the plan (only `httpx`)? [Consistency] — T001 adds `httpx`; no other runtime dependency in any task.
- [x] CHK016 Is each of the plan's six `contracts/` files referenced by an implementing or test task? [Traceability] — dataverse-adapter→T017/T018, queue-loader→T014, metadata→T013, redaction→T037, transport-fixture-validation→T035, cli-slice2→T019/T021/T033.
- [x] CHK017 Are the plan's research decisions (auth, mapping-artifact format, retry, resume, Dataverse fake) each reflected in a task? [Traceability] — auth→T010, mapping JSON→T003/T012, retry→T011, resume→T032, fake→T015.
- [x] CHK018 Does the plan's §Phase 2 task-grouping preview correspond to the actual `tasks.md` phase structure? [Consistency] — the 12 plan groupings map onto Setup/Foundational/US1–US6/Polish; integration tests are correctly distributed per-story per the tasks methodology.

## Task Traceability

- [x] CHK019 Does every task reference a spec FR/SC or a plan artifact / file path? [Traceability] — all 44 tasks cite an FR/SC, a contract, or an exact file path.
- [x] CHK020 Are non-requirement tasks (Setup, Foundational infra, Polish) clearly scoped as infrastructure rather than left as orphaned work? [Clarity] — grouped into labelled Setup/Foundational/Polish phases with stated purpose.
- [x] CHK021 Is the `[Story]` label applied to exactly the user-story tasks (and omitted from Setup/Foundational/Polish)? [Consistency] — verified across T001–T044.
- [x] CHK022 Do task IDs run sequentially in execution order with no gaps or duplicates? [Consistency] — T001–T044 contiguous.

## Cross-Artifact Terminology & Naming

- [x] CHK023 Are module and file names consistent across plan §Project Structure, `contracts/`, and `tasks.md` file paths? [Consistency] — `src/opencloser/crm/dataverse/*`, `redaction/layer.py`, `slice2/*` identical across all three.
- [x] CHK024 Is the Dataverse write-back adapter named consistently (concept vs. `DataverseWriteBackAdapter` class) across spec, plan, contracts, and tasks? [Consistency] — consistent.
- [x] CHK025 Are the run modes (`dry-run` / `write-enabled`) named consistently across spec, plan, and tasks? [Consistency] — consistent.
- [x] CHK026 Is the mapping artifact named consistently — `config/dataverse_mapping.json` (plan/data-model/tasks) ↔ "CRM Field Mapping Artifact" (spec)? [Consistency] — consistent.

## Constitution Alignment Across Artifacts

- [x] CHK027 Does `tasks.md` include the unit/contract/integration verification tasks the constitution §Delivery Workflow mandates? [Consistency] — 9 test tasks incl. the SC-011 contract test (T017).
- [x] CHK028 Do the tasks avoid introducing anything the constitution defers (Celery/Redis/Kubernetes, multiple CRM adapters, frontend)? [Consistency] — no such task; only `httpx` added.
- [x] CHK029 Is FR-014 (Slice 1 contracts unchanged) honored by the task list — no task modifies the orchestrator, eligibility evaluator, or persona, and only `transport/mock.py` is modified (per the FR-019 exception)? [Consistency] — verified; T040 boundary test enforces it.

## Dependency & Sequencing Consistency

- [x] CHK030 Does `tasks.md` §Dependencies reflect the real plan dependencies (Setup → Foundational → user stories → Polish)? [Consistency] — phase order and per-story dependency notes match.
- [x] CHK031 Are cross-story shared-file edit points documented (notably `artifacts/writer.py` edited by T026/T038/T041)? [Consistency] — tasks.md §Dependencies calls this out explicitly.
- [x] CHK032 Is the `tasks.md` MVP scope consistent with the spec's priority order (MVP = US1, the headline P1 story)? [Consistency] — MVP = Phase 1+2+3 (US1); US2 (also P1) sequenced as the immediate next increment.
- [x] CHK033 Is the task ordering free of contradictions (no integration/story task placed before its foundational prerequisite without a dependency note)? [Consistency] — Foundational phase precedes all story phases; cross-phase deps are noted.

## Notes

- Requirements-quality audit of *alignment* — every item asks whether the three artifacts are mutually consistent, fully cross-covered, and traceable; none test implementation behavior.
- **Result: 33/33 aligned.** `spec.md`, `plan.md`, and `tasks.md` are mutually consistent and cross-covered; corroborated by `/speckit.analyze` returning 0 findings on the same artifacts.
- This checklist supersedes no other — the 10 domain checklists test requirement quality *within* the spec; this one tests alignment *across* the spec/plan/tasks set.
