---
description: "Task list for Slice 2 — Mock Call, Real CRM"
---

# Tasks: Slice 2 — Mock Call, Real CRM

**Input**: Design documents from `specs/002-mock-call-real-crm/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — the openCloser Constitution (§Delivery Workflow) and plan
§Constitution Check require unit, contract, integration, and fixture verification;
SC-006/SC-010/SC-011 are explicitly test-verified.

**Organization**: Tasks are grouped by user story. US1 is the MVP. US5 and US6 touch
no Dataverse code and may be implemented in parallel with US1–US4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US6 (user-story phases only)

## Path Conventions

Single project — `src/opencloser/`, `tests/` at repository root (per plan.md §Project Structure).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization for the Slice 2 additions.

- [X] T001 Add the `httpx` runtime dependency to `pyproject.toml` and refresh `uv.lock`; bump the project description to mention Slice 2
- [X] T002 [P] Create `config/slice2.toml` with `[run]`, `[dataverse]`, `[retry]`, `[task_owners]`, `[redaction]` sections per data-model.md §3
- [X] T003 [P] Create `tests/fixtures/dataverse/` — fake-CRM seed records (one `ready` queue item, Account) and a verified fixture mapping artifact `dataverse_mapping.json`
- [X] T004 [P] Create package skeletons: `src/opencloser/crm/dataverse/__init__.py`, `src/opencloser/redaction/__init__.py`, `src/opencloser/slice2/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared Dataverse plumbing, state, config, and the test fake. Every Dataverse-touching user story (US1–US4) depends on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add the Slice 2 Pydantic models to `src/opencloser/models.py` — `RunMode`, `DataverseMapping`, `MetadataVerificationReport`, `CrmCorrelation`, `WriteBackProgress`, `RedactionPolicyConfig`, `DataQualityWarning` (data-model.md §4)
- [X] T006 [P] Add the `crm_correlations` and `writeback_progress` tables to `src/opencloser/state/schema.sql` per data-model.md §1
- [X] T007 Extend `src/opencloser/state/store.py` with DAO functions for `crm_correlations` and `writeback_progress` (insert/update/read by `session_id`)
- [X] T008 [P] Create `src/opencloser/crm/dataverse/errors.py` — `TransientDataverseError` / `PermanentDataverseError` and a classifier mapping httpx/HTTP outcomes per spec §Definitions
- [X] T009 [P] Extend `src/opencloser/core/config.py` to load `config/slice2.toml` (non-secret) and Dataverse secrets from environment variables (`DATAVERSE_TENANT_ID/CLIENT_ID/CLIENT_SECRET/ENV_URL`)
- [X] T010 Create `src/opencloser/crm/dataverse/auth.py` — OAuth2 client-credentials token acquisition via `httpx` with in-process token caching (research.md §2)
- [X] T011 Create `src/opencloser/crm/dataverse/client.py` — `DataverseClient` (httpx Web API client) with bounded transient retry: initial attempt + 3 retries, 1s/2s/4s backoff, `Retry-After` capped at 30s (FR-023)
- [X] T012 [P] Create `src/opencloser/crm/dataverse/mapping.py` — `DataverseMapping` loader for `config/dataverse_mapping.json` plus conceptual-field → Dataverse-field translation (data-model.md §2)
- [X] T013 Create `src/opencloser/crm/dataverse/metadata.py` — `discover()` and read-only `verify()` per contracts/metadata-discovery-verification.md
- [X] T014 Create `src/opencloser/crm/dataverse/queue_loader.py` — `DataverseQueueLoader.load(selector)` mapping a Dataverse row → the unchanged `QueueItem` contract, including translating the Dataverse status so the reused eligibility evaluator records a blocked result for an item not in the configured callable status (FR-011); deterministic next-ready ordering; empty queue → `None` (FR-008, FR-011, contracts/dataverse-queue-loader.md)
- [X] T015 [P] Create the in-process Dataverse fake for tests in `tests/fixtures/dataverse/fake.py` — metadata, queue GET, activity/Task POST, queue PATCH, idempotency pre-query, and injectable transient/permanent failures (research.md §10)
- [X] T016 [P] Unit tests for foundational modules in `tests/unit/` — `test_dataverse_errors.py`, `test_dataverse_mapping.py`, `test_dataverse_client_retry.py`, `test_slice2_config.py`

**Checkpoint**: Foundation ready — user-story implementation can begin.

---

## Phase 3: User Story 1 — Process one Dataverse queue item end-to-end with real CRM write-back (Priority: P1) 🎯 MVP

**Goal**: One Dataverse-owned ALF queue item moves `ready` → final disposition with the outcome written back to Dynamics (Phone Call activity, queue-status/attempt/DNC/last-* updates, owner-assigned callback/review Task).

**Independent Test**: With a verified mapping and one `ready` test queue item, run `run-crm --write` with an interested-callback fixture; confirm in the Dataverse fake the queue fields updated, one Phone Call activity, one callback Task to the configured owner, plus the local session-result artifact and transcript pointer.

### Tests for User Story 1

- [X] T017 [P] [US1] Contract test — `DataverseWriteBackAdapter` satisfies `specs/001-mock-call-mock-crm/contracts/crm-writeback.md` (per-disposition emission map + `new_status` for all 11 dispositions) in `tests/contract/test_dataverse_adapter_contract.py` (SC-011)
- [X] T023 [P] [US1] Integration test — US1 write-enabled happy path for `interested_callback_requested`, `interested_email_captured`, `needs_human_review`, `do_not_call`, and blocked, against the Dataverse fake, in `tests/integration/test_us1_write_enabled.py` (SC-001, SC-003, SC-004, SC-008)
- [ ] T048 [P] [US1] Unit tests for `src/opencloser/crm/dataverse/adapter.py` in `tests/unit/test_dataverse_adapter.py` — focused coverage that the contract + integration tests don't surface granularly: owner-override decision logic for the "Approved owner override" definition (mapped source → active enabled user/team → permitted for the Task kind; invalid override falls back to default with a warning), idempotency-key stamping field selection from the verified mapping, dry-run capture path (no POST/PATCH issued; planned payloads returned), and `preserve_if_present` filtering of the write-back payload (FR-003, FR-015–FR-018, FR-024, FR-025)

### Implementation for User Story 1

- [X] T018 [US1] Implement `src/opencloser/crm/dataverse/adapter.py` — `DataverseWriteBackAdapter` write path: `emit_phone_call_activity` / `emit_queue_status_update` / `emit_task` / `build_writeback`, translating conceptual payloads via `DataverseMapping` and writing only approved update fields. `emit_task` resolves Task ownership from the `[task_owners]` default mapping, applies an approved owner override only when it meets the spec §Definitions "Approved owner override" criteria (mapped override source → active enabled Dataverse user/team → permitted for the Task kind), and falls back to the configured default owner with an operator-visible warning otherwise — never writing an unverified owner/team ID (FR-003, FR-015–FR-018, FR-025; contracts/dataverse-adapter.md)
- [X] T019 [US1] Implement `src/opencloser/slice2/runner.py` write-enabled path — readiness → `verify()` → `DataverseQueueLoader` → construct the existing eligibility/transport/persona boundary objects → call the unchanged `process_one_queue_item` (FR-014; contracts/cli-slice2.md)
- [X] T020 [US1] Add the `discover-crm` command to `src/opencloser/cli.py` — run `discover()` and write/refresh `config/dataverse_mapping.json` (FR-001/FR-004)
- [X] T021 [US1] Add the `run-crm` command (write-enabled path, explicit `--write` flag) to `src/opencloser/cli.py` — operator inputs per FR-032, exit-status mapping per contracts/cli-slice2.md
- [X] T022 [P] [US1] Record the FR-034 non-E.164 data-quality warning into the run report and the queue-status payload without changing exit status, in `src/opencloser/slice2/runner.py`

**Checkpoint**: MVP — the end-to-end write-enabled loop is demonstrable against the Dataverse fake.

---

## Phase 4: User Story 2 — Rehearse the run in dry-run mode with zero CRM writes (Priority: P1)

**Goal**: The same queue item runs in dry-run mode, producing planned write-back artifacts locally with zero Dataverse creates/updates.

**Independent Test**: Run `run-crm` with no `--write` against one queue item; confirm planned Phone Call activity / queue-status / Task artifacts are written locally and the Dataverse fake recorded zero creates/updates.

### Tests for User Story 2

- [X] T027 [P] [US2] Integration test — US2 dry-run produces planned artifacts with zero Dataverse writes; an incomplete mapping still surfaces the gap; and a dry-run with `DATAVERSE_CLIENT_SECRET` / write credentials absent still succeeds (per spec §Edge Cases "Dry-run requested but write credentials are absent" and FR-007's "for the selected run mode"), in `tests/integration/test_us2_dry_run.py` (SC-002, SC-013)

### Implementation for User Story 2

- [X] T024 [US2] Add the dry-run capture path to `src/opencloser/crm/dataverse/adapter.py` — `emit_*` translate and capture planned payloads, issuing zero POST/PATCH (FR-031; contracts/dataverse-adapter.md)
- [X] T025 [US2] Add the dry-run path to `src/opencloser/slice2/runner.py` — dry-run is the default when no `--write` flag is supplied; never claims/mutates the CRM queue item (FR-010, FR-031)
- [X] T026 [US2] Wire planned write-back artifact writing into `src/opencloser/artifacts/writer.py` — planned Phone Call activity / queue-status update / Task as inspectable local artifacts

**Checkpoint**: Dry-run rehearsal works; the write-enabled run (US1) is now safe to demo.

---

## Phase 5: User Story 3 — Block write-enabled processing when Dataverse metadata cannot be verified (Priority: P2)

**Goal**: Write-enabled processing is blocked, with an operator-visible report and zero CRM records touched, whenever required metadata cannot be verified.

**Independent Test**: Point the system at a Dataverse fake missing one required field / option-set / credential / campaign, or unreachable; confirm setup/readiness fails before any write and names the gap.

### Tests for User Story 3

- [ ] T030 [P] [US3] Integration tests — US3 block behaviors: missing field, missing option-set value, missing credentials, configured-campaign-not-found, Dataverse-unreachable-at-start, and unverifiable idempotency-key field, in `tests/integration/test_us3_metadata_block.py` (SC-007, SC-015)

### Implementation for User Story 3

- [ ] T028 [US3] Implement startup/readiness validation (FR-007) in `src/opencloser/slice2/runner.py` — config, secrets, redaction-policy, and metadata checks with an operator-visible failure message per spec §Definitions §Operator-visible. Readiness validates **for the selected run mode**: dry-run requires the non-secret mapping configuration and redaction-policy validity but MUST NOT fail when Dataverse write credentials are absent; write-enabled additionally requires credentials and live metadata verification (FR-001, FR-002, FR-007; spec §Edge Cases "Dry-run requested but write credentials are absent")
- [ ] T029a [US3] Wire the FR-002 **metadata** failure behaviors into `src/opencloser/slice2/runner.py` — unverifiable table/field/lookup/option-set/owner-team/idempotency-key, metadata drift, and partial metadata all block before any write with zero CRM records (FR-002, FR-024; spec §Edge Cases)
- [ ] T029b [US3] Wire the FR-002 **operational** failure behaviors into `src/opencloser/slice2/runner.py` — configured-campaign-not-found (permanent readiness failure, distinct from FR-009's empty-queue no-op) and Dataverse-unreachable-at-start (retryable startup failure) both block before any write with zero CRM records (FR-002; spec §Edge Cases "Configured campaign not found" and "Dataverse unreachable at run start")

**Checkpoint**: The metadata gate protects every write-enabled run.

---

## Phase 6: User Story 4 — Idempotent CRM write-back across duplicate events and retries (Priority: P2)

**Goal**: Duplicate mock events, repeated CLI invocations, and write-back retries never create duplicate Dynamics records; an exhausted retry budget resumes cleanly.

**Independent Test**: For a duplicate event ID, a repeated CLI run, and a forced transient write failure + retry, confirm the Dataverse fake holds exactly one Phone Call activity, at most one Task, one queue-status transition, one attempt increment.

### Tests for User Story 4

- [ ] T034 [P] [US4] Integration tests — US4: duplicate mock event no-op, transient-failure retry reuses correlation, resume after exhausted retry budget, and re-invocation of a finalized session, in `tests/integration/test_us4_idempotency.py` (SC-005, SC-014)
- [ ] T046 [P] [US4] Integration test — the spec §Edge Cases "Dataverse queue item changed by a human between claim and write-back" scenario: force the Dataverse fake to mutate the in-progress queue item's status (or a `preserve_if_present` field) between claim and the final queue-status write, and assert the run stops before the final status update, writes only the approved Slice 2 update fields completed so far, leaves the human-changed values unchanged, and surfaces an operator-visible conflict result in `tests/integration/test_us4_idempotency.py` (FR-003, FR-021; spec §Edge Cases)

### Implementation for User Story 4

- [ ] T031 [US4] Add the idempotency pre-query and `crm_correlations` recording to `src/opencloser/crm/dataverse/adapter.py` — stamp the session ID on the verified idempotency-key field and pre-query Dataverse before each create (FR-024)
- [ ] T032 [US4] Implement `src/opencloser/slice2/resume.py` — the resume coordinator replaying only the missing `emit_*` operations from persisted write-back payloads and `writeback_progress`, without re-running `process_one_queue_item` (FR-023)
- [ ] T033 [US4] Add resume detection to the `run-crm` command in `src/opencloser/cli.py` — a re-invocation of a `resume_needed` session routes to the resume coordinator (contracts/cli-slice2.md)
- [ ] T045 [US4] Implement the mid-run CRM-state conflict detection in `src/opencloser/slice2/runner.py` (and supporting checks in `src/opencloser/crm/dataverse/adapter.py`): before the final queue-status / DNC / attempt write, re-read the mapped queue fields and the `preserve_if_present` set; when a human change is detected (the queue is no longer in the session-owned in-progress state, or a `preserve_if_present` value changed), stop before the final status write, leave the human-changed values unchanged, persist the partial `writeback_progress`, and surface an operator-visible conflict result via the run report and exit status (FR-003, FR-021; spec §Edge Cases "Dataverse queue item changed by a human between claim and write-back")

**Checkpoint**: Idempotency and recovery hold against the real-CRM-shaped fake.

---

## Phase 7: User Story 5 — Reject malformed mock transport fixtures before any state or attempt is consumed (Priority: P2)

**Goal**: A malformed transport fixture is rejected during call placement, before any session/queue/attempt mutation (resolves GitHub issue #2).

**Independent Test**: Run `run-crm` with an invalid-JSON fixture, a fixture with no `events` array, and one whose event lacks `type`/`event_id`/`timestamp`; confirm each fails with no session row, no consumed attempt, no Dataverse queue change.

### Tests for User Story 5

- [X] T036 [P] [US5] Tests — US5: invalid JSON, missing `events` array, event missing an identity field, and a missing fixture file → no session row, no attempt consumed, no Dataverse queue change, in `tests/unit/test_transport_fixture_validation.py` and `tests/integration/test_us5_malformed_fixture.py` (SC-006)

### Implementation for User Story 5

- [X] T035 [US5] Add `validate_fixture()` and `MalformedFixtureError` to `src/opencloser/transport/mock.py`, called inside `place_call` so a malformed fixture cannot reach the orchestrator's state-mutating path; add a side-effect-free `pre_validate_fixture(fixture_id)` hook to the `CallTransport` protocol (`src/opencloser/transport/base.py`) and have the orchestrator (`src/opencloser/core/orchestrator.py`) call it before session-row creation so a malformed fixture leaves no session row, no attempt consumed, and no CRM queue change (FR-019/FR-020; contracts/transport-fixture-validation.md). These three edits — mock.py, transport/base.py, and orchestrator.py — are the FR-014 allowed exception for fixture pre-validation; no other Slice-2-specific behavior is added to those modules.

**Checkpoint**: GitHub issue #2 is resolved; malformed fixtures consume no attempt.

---

## Phase 8: User Story 6 — Redact transcript artifacts before they are written to disk (Priority: P3)

**Goal**: Transcript text passes through a default-on redaction layer before any disk write; summary-only retention writes no transcript file.

**Independent Test**: Run a scripted conversation whose transcript contains a redaction-policy match; confirm the written artifact stores `[REDACTED]`. Re-run with summary-only retention; confirm no transcript file is written while the session-result summary remains.

### Tests for User Story 6

- [X] T039 [P] [US6] Tests — US6: `[REDACTED]` replacement, summary-only retention writes no transcript file, no-op policy preserves the Slice 1 artifact contract, and a malformed redaction policy fails readiness, in `tests/unit/test_redaction.py` and `tests/integration/test_us6_redaction.py` (SC-009)

### Implementation for User Story 6

- [X] T037 [P] [US6] Implement `src/opencloser/redaction/layer.py` — `RedactionLayer` with `RegexRedactionPolicy` (default `[REDACTED]`), `NoOpPolicy`, and summary-only retention (FR-028–FR-030; contracts/redaction-layer.md)
- [X] T038 [US6] Route transcript text through `RedactionLayer` in `src/opencloser/artifacts/writer.py` before any transcript disk write, honoring summary-only retention and preserving the Slice 1 summary + transcript-pointer contract

**Checkpoint**: The transcript artifact path is privacy-hardened.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting verification and release readiness.

- [ ] T040 [P] Boundary test — assert 0 Dataverse-specific field names / vendor payload shapes in the orchestrator, eligibility evaluator, transport, and persona, in `tests/contract/test_boundary_isolation.py` (SC-010)
- [ ] T041 [P] Enforce both retention floors and the no-secrets-retained rule: the FR-035 local audit-artifact retention default (≥90 days, configurable longer; no auto-delete; no secrets retained) in `src/opencloser/artifacts/writer.py`, **and** the FR-023 retention floor for `crm_correlations` / `writeback_progress` rows (≥90 days, or the configured audit-artifact retention if longer) enforced in `src/opencloser/state/store.py` — so a later CLI re-invocation can resume a partial write-back within the documented window
- [ ] T042 [P] Finalize `specs/002-mock-call-real-crm/quickstart.md` as the demo runbook, including manual cleanup/rollback for the demo CRM record
- [ ] T043 [P] Close GitHub issue #2 once FR-019/FR-020 behavior is implemented and tested (reference T035/T036)
- [ ] T047 [P] Negative-assertion test — run a write-enabled flow with known-secret values for `DATAVERSE_TENANT_ID` / `DATAVERSE_CLIENT_ID` / `DATAVERSE_CLIENT_SECRET` / `DATAVERSE_ENV_URL`, then grep every produced local audit artifact (run report, planned/actual write-back payloads, redacted transcript file, `crm_correlations` / `writeback_progress` rows) for those exact values and fail if any appears, in `tests/contract/test_no_secrets_in_artifacts.py` (FR-005, FR-035)
- [ ] T049 [P] Document the run-report schema in `specs/002-mock-call-real-crm/contracts/cli-slice2.md` — required fields per spec §Constitution Alignment §Auditability (session ID, eligibility decision, mock provider call ID, persona version, started/ended timestamps, final disposition, CRM correlation identifiers), the artifact format (JSON), and the dry-run vs write-enabled field sets (CRM correlation IDs present only in write-enabled). Reference the schema from the run-report writer in `src/opencloser/slice2/runner.py` and ensure it is consistent across the run report, planned write-back artifacts, and `writeback_progress` records (same session-ID linkage, same correlation-ID wording, same timestamp format). Addresses reverification CHK046–CHK052 (observability requirements first-class)
- [ ] T050 [P] Document the write-back progress state machine in `specs/002-mock-call-real-crm/data-model.md` §1 and the exit-status mapping in `specs/002-mock-call-real-crm/contracts/cli-slice2.md` — the four resume states (`in_progress` / `completed` / `resume_needed` / `blocked`) with mutually exclusive, exhaustive criteria; the allowed transitions; and the events that trigger each transition (transient error budget exhausted → `resume_needed`; conflict stop per T045 → `blocked`; final write success → `completed`). Addresses reverification CHK068–CHK069 (state-transition specification)
- [ ] T044 Run `ruff` lint/format and the full `uv run pytest` suite; resolve any failures

---

## Dependencies

**Phase order**: Setup (P1) → Foundational (P2) → user stories → Polish (P9).

**Critical path**: Phase 1 → Phase 2 → US1 (MVP).

**Story dependencies**:

- **US1** depends on Phase 2 (all foundational modules).
- **US2** depends on US1 (extends `adapter.py` and `runner.py`).
- **US3** depends on US1 (wires readiness/failure behavior into `runner.py`).
- **US4** depends on US1 (extends `adapter.py`) and Phase 2 (`client.py` retry). T045 (mid-run CRM-state conflict detection) also depends on US3 (T028) since conflict detection re-uses the metadata-verified mapping.
- **US5** depends only on Phase 2 — touches `transport/mock.py`; no Dataverse code. Can run in parallel with US1–US4.
- **US6** depends only on Phase 2 — touches `redaction/` and `artifacts/writer.py`; no Dataverse code. Can run in parallel with US1–US4.
- **`artifacts/writer.py` is edited by three tasks** — T026 (US2, planned-artifact writing), T038 (US6, redaction routing), and T041 (Polish, retention). Sequence or merge these edits so they do not conflict.
- **`src/opencloser/slice2/runner.py` is edited by multiple tasks** — T019 (US1 write-enabled path), T022 (US1 FR-034 warning), T025 (US2 dry-run path), T028 (US3 readiness), T029a / T029b (US3 failure behaviors), and T045 (US4 conflict detection). Sequence or merge these edits so they do not conflict.
- **`src/opencloser/crm/dataverse/adapter.py` is edited by multiple tasks** — T018 (US1 write-back implementation), T024 (US2 dry-run capture path), T031 (US4 idempotency pre-query + `crm_correlations` recording), and T045 (US4 conflict-detection supporting checks). T048 reads it via unit tests but does not modify it. Sequence or merge these edits so they do not conflict.

**Within Phase 2**: T005 and T007 are sequential (T007 uses T006's schema); T010 → T011 (client uses auth); T013 and T014 depend on T011/T012. `[P]`-marked tasks touch separate files.

## Parallel Execution Examples

- **Phase 1**: T002, T003, T004 run in parallel after T001.
- **Phase 2**: T006, T008, T009, T012 in parallel; then T015, T016 in parallel once their targets exist.
- **Phase 3 (US1)**: T017 and T023 (tests) can be written in parallel with each other; T022 in parallel with T020/T021.
- **Cross-story**: US5 (T035–T036) and US6 (T037–T039) can be implemented in parallel with the US1–US4 track by a second contributor.

## Implementation Strategy

- **MVP** = Phase 1 + Phase 2 + Phase 3 (US1): the end-to-end write-enabled loop against the Dataverse fake — the constitution's CRM-first principle made operational.
- **Increment 2** = US2 (dry-run) — makes the write-enabled demo safe to run.
- **Increment 3** = US3 + US4 — hardens the metadata gate and idempotency/recovery.
- **Increment 4** = US5 + US6 — fixture hardening and transcript redaction (parallelizable earlier).
- **Release** = Phase 9 — boundary test, retention enforcement, demo runbook, issue #2 closure, full lint+test pass.

## Task Summary

- **Total tasks**: 51 (T001–T044 plus T045 conflict-stop, T046 conflict-stop integration test, T047 secrets-not-in-artifacts test, T048 adapter unit tests, T049 run-report schema, T050 write-back state machine; T029 split into T029a + T029b)
- **Per phase**: Setup 4 · Foundational 12 · US1 8 (T017–T023 + T048) · US2 4 · US3 4 (T028 + T029a + T029b + T030) · US4 6 (T031–T034 + T045 + T046) · US5 2 · US6 3 · Polish 8 (T040–T044 + T047 + T049 + T050)
- **Test tasks**: T016, T017, T023, T027, T030, T034, T036, T039, T040, T046, T047, T048 (unit, contract, integration, boundary)
- **Parallel opportunities**: 28 tasks marked `[P]`; US5 and US6 are fully parallel to the US1–US4 track.
- **Deliberately not scheduled**: the optional Slice 1 `TransportEvent` / `MockCallEvent` type split (data-model.md §6) — explicitly optional, non-blocking hygiene; intentionally deferred out of Slice 2 scope.
- **Findings addressed by the post-implement `/speckit-analyze` pass**: T045 + T046 (G1 — mid-run CRM-state conflict edge case), T047 (G2 — FR-005 no-secrets-in-artifacts assertion), T027/T028 description tightening (G3/I3 — dry-run readiness vs write-enabled readiness), T041 description expansion (G4 — FR-023 row retention), T029 split into T029a/T029b (U2), T048 (U1 — adapter unit tests).
- **Gaps addressed by the post-checklist `reverification.md` pass**: T049 (CHK046–CHK052 — observability requirements first-class: run-report schema, dry-run vs write-enabled field set, cross-artifact session-ID linkage), T050 (CHK068–CHK069 — write-back progress state-machine specification).
