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

- [ ] T001 Add the `httpx` runtime dependency to `pyproject.toml` and refresh `uv.lock`; bump the project description to mention Slice 2
- [ ] T002 [P] Create `config/slice2.toml` with `[run]`, `[dataverse]`, `[retry]`, `[task_owners]`, `[redaction]` sections per data-model.md §3
- [ ] T003 [P] Create `tests/fixtures/dataverse/` — fake-CRM seed records (one `ready` queue item, Account) and a verified fixture mapping artifact `dataverse_mapping.json`
- [ ] T004 [P] Create package skeletons: `src/opencloser/crm/dataverse/__init__.py`, `src/opencloser/redaction/__init__.py`, `src/opencloser/slice2/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared Dataverse plumbing, state, config, and the test fake. Every Dataverse-touching user story (US1–US4) depends on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Add the Slice 2 Pydantic models to `src/opencloser/models.py` — `RunMode`, `DataverseMapping`, `MetadataVerificationReport`, `CrmCorrelation`, `WriteBackProgress`, `RedactionPolicyConfig`, `DataQualityWarning` (data-model.md §4)
- [ ] T006 [P] Add the `crm_correlations` and `writeback_progress` tables to `src/opencloser/state/schema.sql` per data-model.md §1
- [ ] T007 Extend `src/opencloser/state/store.py` with DAO functions for `crm_correlations` and `writeback_progress` (insert/update/read by `session_id`)
- [ ] T008 [P] Create `src/opencloser/crm/dataverse/errors.py` — `TransientDataverseError` / `PermanentDataverseError` and a classifier mapping httpx/HTTP outcomes per spec §Definitions
- [ ] T009 [P] Extend `src/opencloser/core/config.py` to load `config/slice2.toml` (non-secret) and Dataverse secrets from environment variables (`DATAVERSE_TENANT_ID/CLIENT_ID/CLIENT_SECRET/ENV_URL`)
- [ ] T010 Create `src/opencloser/crm/dataverse/auth.py` — OAuth2 client-credentials token acquisition via `httpx` with in-process token caching (research.md §2)
- [ ] T011 Create `src/opencloser/crm/dataverse/client.py` — `DataverseClient` (httpx Web API client) with bounded transient retry: initial attempt + 3 retries, 1s/2s/4s backoff, `Retry-After` capped at 30s (FR-023)
- [ ] T012 [P] Create `src/opencloser/crm/dataverse/mapping.py` — `DataverseMapping` loader for `config/dataverse_mapping.json` plus conceptual-field → Dataverse-field translation (data-model.md §2)
- [ ] T013 Create `src/opencloser/crm/dataverse/metadata.py` — `discover()` and read-only `verify()` per contracts/metadata-discovery-verification.md
- [ ] T014 Create `src/opencloser/crm/dataverse/queue_loader.py` — `DataverseQueueLoader.load(selector)` mapping a Dataverse row → the unchanged `QueueItem` contract, including translating the Dataverse status so the reused eligibility evaluator records a blocked result for an item not in the configured callable status (FR-011); deterministic next-ready ordering; empty queue → `None` (FR-008, FR-011, contracts/dataverse-queue-loader.md)
- [ ] T015 [P] Create the in-process Dataverse fake for tests in `tests/fixtures/dataverse/fake.py` — metadata, queue GET, activity/Task POST, queue PATCH, idempotency pre-query, and injectable transient/permanent failures (research.md §10)
- [ ] T016 [P] Unit tests for foundational modules in `tests/unit/` — `test_dataverse_errors.py`, `test_dataverse_mapping.py`, `test_dataverse_client_retry.py`, `test_slice2_config.py`

**Checkpoint**: Foundation ready — user-story implementation can begin.

---

## Phase 3: User Story 1 — Process one Dataverse queue item end-to-end with real CRM write-back (Priority: P1) 🎯 MVP

**Goal**: One Dataverse-owned ALF queue item moves `ready` → final disposition with the outcome written back to Dynamics (Phone Call activity, queue-status/attempt/DNC/last-* updates, owner-assigned callback/review Task).

**Independent Test**: With a verified mapping and one `ready` test queue item, run `run-crm --write` with an interested-callback fixture; confirm in the Dataverse fake the queue fields updated, one Phone Call activity, one callback Task to the configured owner, plus the local session-result artifact and transcript pointer.

### Tests for User Story 1

- [ ] T017 [P] [US1] Contract test — `DataverseWriteBackAdapter` satisfies `specs/001-mock-call-mock-crm/contracts/crm-writeback.md` (per-disposition emission map + `new_status` for all 11 dispositions) in `tests/contract/test_dataverse_adapter_contract.py` (SC-011)
- [ ] T023 [P] [US1] Integration test — US1 write-enabled happy path for `interested_callback_requested`, `interested_email_captured`, `needs_human_review`, `do_not_call`, and blocked, against the Dataverse fake, in `tests/integration/test_us1_write_enabled.py` (SC-001, SC-003, SC-004, SC-008)

### Implementation for User Story 1

- [ ] T018 [US1] Implement `src/opencloser/crm/dataverse/adapter.py` — `DataverseWriteBackAdapter` write path: `emit_phone_call_activity` / `emit_queue_status_update` / `emit_task` / `build_writeback`, translating conceptual payloads via `DataverseMapping` and writing only approved update fields. `emit_task` resolves Task ownership from the `[task_owners]` default mapping, applies an approved owner override only when it meets the spec §Definitions "Approved owner override" criteria (mapped override source → active enabled Dataverse user/team → permitted for the Task kind), and falls back to the configured default owner with an operator-visible warning otherwise — never writing an unverified owner/team ID (FR-003, FR-015–FR-018, FR-025; contracts/dataverse-adapter.md)
- [ ] T019 [US1] Implement `src/opencloser/slice2/runner.py` write-enabled path — readiness → `verify()` → `DataverseQueueLoader` → construct the existing eligibility/transport/persona boundary objects → call the unchanged `process_one_queue_item` (FR-014; contracts/cli-slice2.md)
- [ ] T020 [US1] Add the `discover-crm` command to `src/opencloser/cli.py` — run `discover()` and write/refresh `config/dataverse_mapping.json` (FR-001/FR-004)
- [ ] T021 [US1] Add the `run-crm` command (write-enabled path, explicit `--write` flag) to `src/opencloser/cli.py` — operator inputs per FR-032, exit-status mapping per contracts/cli-slice2.md
- [ ] T022 [P] [US1] Record the FR-034 non-E.164 data-quality warning into the run report and the queue-status payload without changing exit status, in `src/opencloser/slice2/runner.py`

**Checkpoint**: MVP — the end-to-end write-enabled loop is demonstrable against the Dataverse fake.

---

## Phase 4: User Story 2 — Rehearse the run in dry-run mode with zero CRM writes (Priority: P1)

**Goal**: The same queue item runs in dry-run mode, producing planned write-back artifacts locally with zero Dataverse creates/updates.

**Independent Test**: Run `run-crm` with no `--write` against one queue item; confirm planned Phone Call activity / queue-status / Task artifacts are written locally and the Dataverse fake recorded zero creates/updates.

### Tests for User Story 2

- [ ] T027 [P] [US2] Integration test — US2 dry-run produces planned artifacts with zero Dataverse writes, and an incomplete mapping still surfaces the gap, in `tests/integration/test_us2_dry_run.py` (SC-002, SC-013)

### Implementation for User Story 2

- [ ] T024 [US2] Add the dry-run capture path to `src/opencloser/crm/dataverse/adapter.py` — `emit_*` translate and capture planned payloads, issuing zero POST/PATCH (FR-031; contracts/dataverse-adapter.md)
- [ ] T025 [US2] Add the dry-run path to `src/opencloser/slice2/runner.py` — dry-run is the default when no `--write` flag is supplied; never claims/mutates the CRM queue item (FR-010, FR-031)
- [ ] T026 [US2] Wire planned write-back artifact writing into `src/opencloser/artifacts/writer.py` — planned Phone Call activity / queue-status update / Task as inspectable local artifacts

**Checkpoint**: Dry-run rehearsal works; the write-enabled run (US1) is now safe to demo.

---

## Phase 5: User Story 3 — Block write-enabled processing when Dataverse metadata cannot be verified (Priority: P2)

**Goal**: Write-enabled processing is blocked, with an operator-visible report and zero CRM records touched, whenever required metadata cannot be verified.

**Independent Test**: Point the system at a Dataverse fake missing one required field / option-set / credential / campaign, or unreachable; confirm setup/readiness fails before any write and names the gap.

### Tests for User Story 3

- [ ] T030 [P] [US3] Integration tests — US3 block behaviors: missing field, missing option-set value, missing credentials, configured-campaign-not-found, Dataverse-unreachable-at-start, and unverifiable idempotency-key field, in `tests/integration/test_us3_metadata_block.py` (SC-007, SC-015)

### Implementation for User Story 3

- [ ] T028 [US3] Implement startup/readiness validation (FR-007) in `src/opencloser/slice2/runner.py` — config, secrets, redaction-policy, and metadata checks with an operator-visible failure message per spec §Definitions §Operator-visible
- [ ] T029 [US3] Wire the FR-002 failure behaviors into `src/opencloser/slice2/runner.py` — unverifiable table/field/lookup/option-set/owner-team/idempotency-key, metadata drift, partial metadata, configured-campaign-not-found, and Dataverse-unreachable-at-start all block before any write with zero CRM records (FR-002; spec §Edge Cases)

**Checkpoint**: The metadata gate protects every write-enabled run.

---

## Phase 6: User Story 4 — Idempotent CRM write-back across duplicate events and retries (Priority: P2)

**Goal**: Duplicate mock events, repeated CLI invocations, and write-back retries never create duplicate Dynamics records; an exhausted retry budget resumes cleanly.

**Independent Test**: For a duplicate event ID, a repeated CLI run, and a forced transient write failure + retry, confirm the Dataverse fake holds exactly one Phone Call activity, at most one Task, one queue-status transition, one attempt increment.

### Tests for User Story 4

- [ ] T034 [P] [US4] Integration tests — US4: duplicate mock event no-op, transient-failure retry reuses correlation, resume after exhausted retry budget, and re-invocation of a finalized session, in `tests/integration/test_us4_idempotency.py` (SC-005, SC-014)

### Implementation for User Story 4

- [ ] T031 [US4] Add the idempotency pre-query and `crm_correlations` recording to `src/opencloser/crm/dataverse/adapter.py` — stamp the session ID on the verified idempotency-key field and pre-query Dataverse before each create (FR-024)
- [ ] T032 [US4] Implement `src/opencloser/slice2/resume.py` — the resume coordinator replaying only the missing `emit_*` operations from persisted write-back payloads and `writeback_progress`, without re-running `process_one_queue_item` (FR-023)
- [ ] T033 [US4] Add resume detection to the `run-crm` command in `src/opencloser/cli.py` — a re-invocation of a `resume_needed` session routes to the resume coordinator (contracts/cli-slice2.md)

**Checkpoint**: Idempotency and recovery hold against the real-CRM-shaped fake.

---

## Phase 7: User Story 5 — Reject malformed mock transport fixtures before any state or attempt is consumed (Priority: P2)

**Goal**: A malformed transport fixture is rejected during call placement, before any session/queue/attempt mutation (resolves GitHub issue #2).

**Independent Test**: Run `run-crm` with an invalid-JSON fixture, a fixture with no `events` array, and one whose event lacks `type`/`event_id`/`timestamp`; confirm each fails with no session row, no consumed attempt, no Dataverse queue change.

### Tests for User Story 5

- [ ] T036 [P] [US5] Tests — US5: invalid JSON, missing `events` array, event missing an identity field, and a missing fixture file → no session row, no attempt consumed, no Dataverse queue change, in `tests/unit/test_transport_fixture_validation.py` and `tests/integration/test_us5_malformed_fixture.py` (SC-006)

### Implementation for User Story 5

- [ ] T035 [US5] Add `validate_fixture()` to `src/opencloser/transport/mock.py`, called inside `place_call` before any state mutation — raise `MalformedFixtureError` for invalid JSON, missing `events` array, an event missing `type`/`event_id`/`timestamp`, or a missing fixture file (FR-019/FR-020; contracts/transport-fixture-validation.md). This is the only permitted change to the transport module (FR-014).

**Checkpoint**: GitHub issue #2 is resolved; malformed fixtures consume no attempt.

---

## Phase 8: User Story 6 — Redact transcript artifacts before they are written to disk (Priority: P3)

**Goal**: Transcript text passes through a default-on redaction layer before any disk write; summary-only retention writes no transcript file.

**Independent Test**: Run a scripted conversation whose transcript contains a redaction-policy match; confirm the written artifact stores `[REDACTED]`. Re-run with summary-only retention; confirm no transcript file is written while the session-result summary remains.

### Tests for User Story 6

- [ ] T039 [P] [US6] Tests — US6: `[REDACTED]` replacement, summary-only retention writes no transcript file, no-op policy preserves the Slice 1 artifact contract, and a malformed redaction policy fails readiness, in `tests/unit/test_redaction.py` and `tests/integration/test_us6_redaction.py` (SC-009)

### Implementation for User Story 6

- [ ] T037 [P] [US6] Implement `src/opencloser/redaction/layer.py` — `RedactionLayer` with `RegexRedactionPolicy` (default `[REDACTED]`), `NoOpPolicy`, and summary-only retention (FR-028–FR-030; contracts/redaction-layer.md)
- [ ] T038 [US6] Route transcript text through `RedactionLayer` in `src/opencloser/artifacts/writer.py` before any transcript disk write, honoring summary-only retention and preserving the Slice 1 summary + transcript-pointer contract

**Checkpoint**: The transcript artifact path is privacy-hardened.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting verification and release readiness.

- [ ] T040 [P] Boundary test — assert 0 Dataverse-specific field names / vendor payload shapes in the orchestrator, eligibility evaluator, transport, and persona, in `tests/contract/test_boundary_isolation.py` (SC-010)
- [ ] T041 [P] Enforce the FR-035 local audit-artifact retention default (≥90 days, configurable longer; no auto-delete; no secrets retained) in `src/opencloser/artifacts/writer.py`
- [ ] T042 [P] Finalize `specs/002-mock-call-real-crm/quickstart.md` as the demo runbook, including manual cleanup/rollback for the demo CRM record
- [ ] T043 [P] Close GitHub issue #2 once FR-019/FR-020 behavior is implemented and tested (reference T035/T036)
- [ ] T044 Run `ruff` lint/format and the full `uv run pytest` suite; resolve any failures

---

## Dependencies

**Phase order**: Setup (P1) → Foundational (P2) → user stories → Polish (P9).

**Critical path**: Phase 1 → Phase 2 → US1 (MVP).

**Story dependencies**:

- **US1** depends on Phase 2 (all foundational modules).
- **US2** depends on US1 (extends `adapter.py` and `runner.py`).
- **US3** depends on US1 (wires readiness/failure behavior into `runner.py`).
- **US4** depends on US1 (extends `adapter.py`) and Phase 2 (`client.py` retry).
- **US5** depends only on Phase 2 — touches `transport/mock.py`; no Dataverse code. Can run in parallel with US1–US4.
- **US6** depends only on Phase 2 — touches `redaction/` and `artifacts/writer.py`; no Dataverse code. Can run in parallel with US1–US4.
- **`artifacts/writer.py` is edited by three tasks** — T026 (US2, planned-artifact writing), T038 (US6, redaction routing), and T041 (Polish, retention). Sequence or merge these edits so they do not conflict.

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

- **Total tasks**: 44
- **Per phase**: Setup 4 · Foundational 12 · US1 7 · US2 4 · US3 3 · US4 4 · US5 2 · US6 3 · Polish 5
- **Test tasks**: T016, T017, T023, T027, T030, T034, T036, T039, T040 (unit, contract, integration, boundary)
- **Parallel opportunities**: 22 tasks marked `[P]`; US5 and US6 are fully parallel to the US1–US4 track.
- **Deliberately not scheduled**: the optional Slice 1 `TransportEvent` / `MockCallEvent` type split (data-model.md §6) — explicitly optional, non-blocking hygiene; intentionally deferred out of Slice 2 scope.
