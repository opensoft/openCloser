# Tasks: Slice 1 — Mock Call, Mock CRM

**Feature**: `001-mock-call-mock-crm`
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md) · **Data Model**: [data-model.md](./data-model.md) · **Quickstart**: [quickstart.md](./quickstart.md)
**Contracts**: [orchestrator](./contracts/orchestrator.md) · [eligibility](./contracts/eligibility.md) · [transport](./contracts/transport.md) · [persona](./contracts/persona.md) · [crm-writeback](./contracts/crm-writeback.md)
**Created**: 2026-05-19

## Overview

Slice 1 introduces the first Python package layout for openCloser and implements the full mock product loop end-to-end against fixtures. The work is organized into 7 phases:

- **Phase 1 — Setup**: project bootstrap (deps, config, skeleton)
- **Phase 2 — Foundational**: blocking prerequisites shared by every user story (Pydantic models, SQLite schema, idempotency primitive, ID gen, artifact writer)
- **Phase 3 — User Story 1 (P1, MVP)**: happy-path end-to-end on one eligible ALF queue record
- **Phase 4 — User Story 2 (P2)**: block ineligible records before any mock call
- **Phase 5 — User Story 3 (P2)**: every call path including duplicates and conflicting late events
- **Phase 6 — User Story 4 (P3)**: operator-inspectable artifacts across every disposition
- **Phase 7 — Polish & Cross-Cutting**: CI gates, deferred Constitution doc, README, lint

**Conventions**:

- `[P]` = parallelizable with the immediately surrounding `[P]` tasks (different files, no in-phase dependency)
- `[US#]` = story label; required on every user-story phase task
- File paths are absolute-from-repo-root (the worktree is the repo root for Slice 1)
- Every test file is colocated under `tests/`; every code file under `src/opencloser/`

---

## Phase 1: Setup

- [x] T001 Create `pyproject.toml` with PEP 621 metadata, `>=3.12,<3.14` Python constraint, deps (`typer`, `pydantic>=2.7`, `pytest`, `pytest-cov`, `ruff`), and `[tool.ruff]` + `[tool.pytest.ini_options]` config sections per research.md §Tooling
- [x] T002 Create empty package skeleton: `src/opencloser/__init__.py`, `src/opencloser/core/__init__.py`, `src/opencloser/eligibility/__init__.py`, `src/opencloser/transport/__init__.py`, `src/opencloser/persona/__init__.py`, `src/opencloser/crm/__init__.py`, `src/opencloser/state/__init__.py`, `src/opencloser/artifacts/__init__.py`
- [x] T003 [P] Create `.gitignore` excluding `artifacts/`, `state/*.db`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `config/slice1.local.toml`
- [x] T004 [P] Create `config/slice1.toml` with the default Slice 1 configuration per research.md §Configuration surface (`[call_window]`, `[eligibility]`, `[artifacts]`, `[persona]` sections)
- [x] T005 [P] Create empty `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, and `tests/fixtures/__init__.py`
- [x] T006 [P] Create fixture sub-directories: `tests/fixtures/queue_items/`, `tests/fixtures/conversations/`, `tests/fixtures/transport_events/` (one `.gitkeep` per dir)
- [x] T007 [P] Create a minimal `README.md` linking to `specs/001-mock-call-mock-crm/quickstart.md` and naming Slice 1 as the active feature

**Checkpoint**: `uv sync` succeeds, `uv run pytest` runs (zero tests yet, exits 5 = no tests collected).

---

## Phase 2: Foundational (blocking prerequisites)

Every user story below depends on these. Foundational unit tests are included because the entities and DAO must be solid before any story exercises them.

- [x] T008 Define every Pydantic v2 entity model per data-model.md §Pydantic models in `src/opencloser/models.py`: `CallableStatus`, `Disposition`, `HumanReviewReason`, `UtcMs`, `QueueItem`, `EligibilityDecision`, `Session`, `NormalizedResult`, `PhoneCallActivityPayload`, `QueueStatusUpdatePayload`, `TaskPayload`, `WriteBack`, `ConflictingEventAuditRecord`, `ExportedEligibilityDecision`. Include the `_exclusive_email_fields` + `_kind_invariants` validators.
- [x] T009 Write the full SQLite schema in `src/opencloser/state/schema.sql` per data-model.md §Schema (all 12 tables + indexes + CHECK constraints + `schema_meta`). Apply PRAGMAs (`journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`) at the head as a comment block for the connector to apply at runtime.
- [x] T010 Implement the state-store DAO in `src/opencloser/state/store.py`: connection factory (applies PRAGMAs), `init_schema()` (idempotent `CREATE TABLE IF NOT EXISTS` via reading `schema.sql`), per-table CRUD functions for every entity, and a `transaction()` context manager.
- [x] T011 [P] Implement ID generation in `src/opencloser/core/ids.py`: `new_session_id()` (UUID4 hex, prefixed `ses_`), `new_mock_provider_call_id()` (UUID4 hex, prefixed `call_`), `new_decision_id()`, `new_task_id()`, `new_audit_id()`. All globally unique per FR-007 / FR-019.
- [x] T012 [P] Implement the `Clock` protocol + `SystemClock` + `FrozenClock` in `src/opencloser/core/clock.py` with `now_utc_ms()` returning the canonical ISO 8601 / UTC / millisecond string per FR-014.
- [x] T013 [P] Implement the idempotency-key helper in `src/opencloser/core/idempotency.py`: `compute_key(session_id, mock_provider_call_id, event_id, write_back_kind) -> tuple`, `is_duplicate(store, key) -> bool`, `record_applied(store, key, applied_at) -> None`. Atomic-write semantics per research.md §Cross-cutting decisions.
- [x] T014 [P] Implement the configuration loader in `src/opencloser/core/config.py`: read `config/slice1.toml` via stdlib `tomllib`, layer `OPENCLOSER_*` env-var overrides, return a `SliceConfig` Pydantic model. Validation errors surface clearly per the FR-027 operator output mandate.
- [x] T015 [P] Implement the artifact writer in `src/opencloser/artifacts/writer.py`: `write_session_artifacts(session_id, normalized_result, writeback, exported_eligibility_decision, conflicting_events=None) -> ArtifactPaths`. Uses 2-space indented, sorted-keys, UTF-8 / LF JSON via `pydantic.BaseModel.model_dump(mode='json')` + `json.dumps(..., sort_keys=True, indent=2, ensure_ascii=False)`. Atomic writes via `tempfile + os.replace`. Filenames per research.md §Artifact directory & filenames (`session-result.json`, `writeback.json`, `task.json`, `transcript.txt`, `eligibility-decision.json`, `conflicting-events.json`).
- [x] T016 [P] Write unit tests for foundational modules:
  - `tests/unit/test_models.py` — round-trip every Pydantic model through `model_dump_json` / `model_validate_json`; assert the email-mutual-exclusion validator and the task-kind invariants.
  - `tests/unit/test_state_store.py` — INSERT + SELECT round-trip for every table; FK cascade behavior; CHECK constraint enforcement.
  - `tests/unit/test_idempotency.py` — `compute_key` determinism; `is_duplicate` true/false paths; UNIQUE-constraint-as-no-op semantics.
  - `tests/unit/test_artifacts_writer.py` — deterministic output (re-run produces byte-identical files; supports SC-005).

**Checkpoint**: `uv run pytest tests/unit/` passes for every foundational test. No story-specific code exists yet.

---

## Phase 3: User Story 1 — Run the full mock loop on one eligible ALF queue record (P1) — MVP

**Story goal**: A developer or sales operator loads one eligible ALF prospect record, invokes `opencloser run-one`, and observes a final disposition, a normalized session result JSON, a mock CRM write-back JSON, a callback task payload, and a transcript file on disk — all produced by walking the entire boundary stack (eligibility → transport → persona → crm-writeback → orchestrator → artifacts) end-to-end against fixtures.

**Independent Test (matches spec.md Story 1 Independent Test)**: Load `tests/fixtures/queue_items/alf-prospect-001.json` (callable, no DNC, in-window) into the state store; run `uv run opencloser run-one --queue-item-id alf-prospect-001 --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json --transport-fixture tests/fixtures/transport_events/connected.json`; assert (a) `final_disposition == "interested_callback_requested"`, (b) one session row + connected/completed event rows persisted, (c) `phone_call_activities` row exists, (d) `queue_status_updates` row exists with `new_status='ready'`, (e) `task_payloads` row exists with `task_kind='callback'` and the captured `preferred_callback_window`, (f) `artifacts/<session>/{session-result,writeback,task,transcript,eligibility-decision}.json` all exist.

### Module interfaces and base classes

- [x] T017 [P] [US1] Define the `EligibilityEvaluator` ABC in `src/opencloser/eligibility/__init__.py` per contracts/eligibility.md §Public surface
- [x] T018 [P] [US1] Define the `CallTransport` ABC in `src/opencloser/transport/base.py` per contracts/transport.md §Public surface (`place_call`, `event_stream`)
- [x] T019 [P] [US1] Define the `Persona` ABC in `src/opencloser/persona/base.py` per contracts/persona.md §Public surface (`version` property + `run` method)
- [x] T020 [P] [US1] Define the `WriteBackAdapter` ABC in `src/opencloser/crm/base.py` per contracts/crm-writeback.md §Public surface (`emit_phone_call_activity`, `emit_queue_status_update`, `emit_task`)

### Eligibility module (all 6 FR-004 rules, needed even on the happy path)

- [x] T021 [US1] Implement `BuiltinEligibilityEvaluator` in `src/opencloser/eligibility/evaluator.py` per contracts/eligibility.md §Behavior. Evaluates all 6 rules without short-circuit, applies the default-timezone fallback, returns an `EligibilityDecision` with `failing_rules` populated when blocked. Pure (no state-store writes).
- [x] T022 [P] [US1] Unit tests for eligibility in `tests/unit/test_eligibility.py` @pytest.mark.module("eligibility"): one passing-case test (all 6 rules pass), one test per failing rule (a/b/c/d/e/f), one test for multi-rule failure (asserts `failing_rules` lists all in canonical order), one test for the default-timezone fallback recording.

### Mock transport (fixture-driven happy path)

- [x] T023 [US1] Implement `FixtureDrivenTransport` in `src/opencloser/transport/mock.py` per contracts/transport.md §Slice 1 mock implementation. Reads transport-fixture JSON, allocates a `mock_provider_call_id` (FR-007), yields events in fixture order. No state-store writes.
- [x] T024 [P] [US1] Unit tests for transport in `tests/unit/test_transport_mock.py` @pytest.mark.module("transport"): `place_call` returns a unique ID; `event_stream` yields fixture events in order; duplicate `event_id` in fixture is yielded verbatim (no dedup at transport level); unknown `event_type` is yielded verbatim (Edge Case "Mock transport emits an unknown event type" — dedup/discard is the orchestrator's job, not the transport's); a transport instantiated with a `FrozenClock` that crosses the call-window boundary between `place_call` and the first event still yields the event (Edge Case "Call window expires mid-call" — the in-flight semantics are upheld by the orchestrator, not the transport).

### Persona module (deterministic; FR-034 / FR-035 / FR-036 all needed for US1 because FR-036's precedence list is a single deterministic function)

- [x] T025 [P] [US1] Implement the FR-034 extraction schema in `src/opencloser/persona/extraction.py`: `Extraction` Pydantic class + a deterministic `extract_from_turns(turns: list[ConversationTurn]) -> Extraction` function. No randomness, no clock.
- [x] T026 [P] [US1] Implement the FR-035 escalation reason-code enum in `src/opencloser/persona/escalation.py` matching the 9-code enumeration. (This is also exported from `opencloser.models.HumanReviewReason` — make this module the canonical reference + provide a `derive_escalation_reason(extraction, turns) -> HumanReviewReason | None` helper.)
- [x] T027 [US1] Implement FR-036 disposition rules in `src/opencloser/persona/disposition_rules.py`: a `decide_disposition(extraction, escalation_reason) -> Disposition` function applying the 10-rule precedence list (first match wins). Deterministic. No I/O.
- [x] T028 [US1] Implement the `ALFAppointmentSetterPersona` class in `src/opencloser/persona/alf_appointment_setter.py` per contracts/persona.md. `version = "alf-appointment-setter@0.1.0"`. `run()` reads the conversation fixture, validates the disclosure first-turn pattern, calls `extract_from_turns` + `derive_escalation_reason` + `decide_disposition`, returns `PersonaOutput`.
- [x] T029 [P] [US1] Unit tests for persona in `tests/unit/test_persona_rules.py` @pytest.mark.module("persona"): each FR-036 rule (#1–#10) gets a test asserting first-match-wins; disclosure validator passes/fails per fixture; extraction deterministic across reruns.

### Mock CRM write-back adapter

- [x] T030 [US1] Implement `MockWriteBackAdapter` in `src/opencloser/crm/mock.py` per contracts/crm-writeback.md. `emit_phone_call_activity` / `emit_queue_status_update` / `emit_task` each INSERT into the corresponding table and append to an in-memory `WriteBack` aggregate held per session. `emit_task` no-ops if disposition is in FR-018's exclusion set (belt-and-suspenders).
- [x] T031 [P] [US1] Unit tests for write-back in `tests/unit/test_crm_writeback.py` @pytest.mark.module("crm"): each `emit_*` round-trips through SQLite; payload Pydantic validation rejects malformed input; FR-018 belt-and-suspenders test for excluded dispositions.

### Interaction Core / Orchestrator (happy-path wiring only)

- [x] T032 [US1] Implement the orchestrator's happy-path flow in `src/opencloser/core/orchestrator.py::process_one_queue_item(...)` per contracts/orchestrator.md §Behavior steps 1–6 for the "allow" branch. Idempotency-key checks for every state mutation. Attempt-count increment on first event for a new `mock_provider_call_id`. Apply FR-031 + FR-032 to decide which write-back payloads to emit and which `new_status` to set. Set `session.state='finalized'` and `ended_at` at end. Block path is deferred to US2.
- [x] T033 [P] [US1] Unit tests for orchestrator happy-path in `tests/unit/test_orchestrator_happy.py` @pytest.mark.module("core"): a fixture-driven end-to-end through stubbed eligibility + transport + persona + crm. Asserts idempotency-key INSERTs happen at the right boundaries.

### CLI (run-one for the MVP demo)

- [x] T034 [US1] Implement the Typer CLI in `src/opencloser/cli.py` with three subcommands: `init-state` (creates `state/slice1.db` and applies schema), `load-queue-item --file PATH` (INSERT a queue-item from a JSON fixture), `run-one --queue-item-id ID [--conversation-fixture PATH] [--transport-fixture PATH]` (calls `process_one_queue_item` and prints the FR-027 output surface: eligibility decision, final disposition, mock_provider_call_id, artifact paths, and `wall_time_ms` measured by starting a timer at command entry and stopping after the last artifact is written). T034 fully owns the wall-time instrumentation and CLI output line; T068 only adds the integration-test gate.

### Fixtures and integration test for US1

- [x] T035 [P] [US1] Create `tests/fixtures/queue_items/alf-prospect-001.json` — an eligible record (`callable_status='ready'`, `dnc_flag=false`, `attempt_count=0`, valid timezone, valid phone)
- [x] T036 [P] [US1] Create `tests/fixtures/conversations/interested_callback_requested.json` per research.md §Persona fixture format. Conversation ends with the contact requesting a callback on Thursday at 14:00. `expected_disposition: "interested_callback_requested"`.
- [x] T037 [P] [US1] Create `tests/fixtures/transport_events/connected.json` per research.md §Mock transport fixture format. Sequence: one `connected` event followed by one `completed` event.
- [x] T038 [US1] End-to-end integration test in `tests/integration/test_us1_happy_path.py` @pytest.mark.integration: load `alf-prospect-001`, run the orchestrator, assert every (a)–(f) bullet in the Independent Test above. Uses real state-store + real artifact writer; only the clock is frozen.

**Checkpoint US1**: `uv run opencloser run-one --queue-item-id alf-prospect-001 ...` produces all 5 artifact files. `uv run pytest tests/integration/test_us1_happy_path.py` passes. The MVP is demoable.

---

## Phase 4: User Story 2 — Block an ineligible record before any mock call (P2)

**Story goal**: A queue record that fails one or more FR-004 rules MUST be blocked before any mock call, with a clear block decision recorded and a `blocked`-state session row persisted (per the Phase 1 Clarifications decision and FR-005).

**Independent Test (matches spec.md Story 2 Independent Test)**: For each disqualifying condition (DNC flag, call-window, max-attempts, missing-phone), load a fixture queue record carrying only that condition and run `opencloser run-one`. Assert (a) a session row exists in `state='blocked'` with `final_disposition='blocked'` and `mock_provider_call_id IS NULL`, (b) `eligibility-decision.json` lists every failing rule in `failing_rules`, (c) no `phone_call_activities` row exists, (d) `queue_items.attempt_count` is unchanged, (e) the CLI prints "blocked: <rule names>" and the operator can read the block reason from `eligibility-decision.json`.

- [x] T039 [US2] Extend `process_one_queue_item` in `src/opencloser/core/orchestrator.py` to handle the `block` branch per contracts/orchestrator.md §Behavior step 4: create a session with `state='blocked'`, `final_disposition='blocked'`, copy `failing_rules` to the session's `blocked_reason`, call `crm.emit_queue_status_update(...)` only (FR-029 mandate), do NOT call `transport.place_call`, do NOT increment `attempt_count`.
- [x] T040 [P] [US2] Create `tests/fixtures/queue_items/alf-prospect-dnc.json` — `dnc_flag=true`, everything else valid
- [x] T041 [P] [US2] Create `tests/fixtures/queue_items/alf-prospect-after-hours.json` — record's local time outside call window (encoded via timezone selection that places "now" outside `[09:00, 20:00]` in tests via `FrozenClock`)
- [x] T042 [P] [US2] Create `tests/fixtures/queue_items/alf-prospect-max-attempts.json` — `attempt_count=5` (== configured max)
- [x] T043 [P] [US2] Create `tests/fixtures/queue_items/alf-prospect-missing-phone.json` — `phone_number=null`
- [x] T044 [P] [US2] Create `tests/fixtures/queue_items/alf-prospect-not-ready.json` — `callable_status='in_progress'` (per FR-004(f) — only `ready` allows)
- [x] T045 [US2] End-to-end integration test in `tests/integration/test_us2_blocked.py` @pytest.mark.integration with one parametrized case per blocking condition (DNC, call-window, max-attempts, missing-phone, callable-status, multi-rule failure). Asserts (a)–(e) of the Independent Test.

**Checkpoint US2**: Running against any of the 5 blocking fixtures produces a `blocked` session and emits only the queue-status update payload. US1 still passes.

---

## Phase 5: User Story 3 — Simulate every Slice 1 call path, including duplicates (P2)

**Story goal**: Exercise every transport path — `connected`, `no_answer`, `voicemail`, `failed`, `completed` — plus duplicate-event redelivery and conflicting late events. Idempotency (FR-019) and conflicting-event audit (FR-020) must hold across all of these.

**Independent Test (matches spec.md Story 3 Independent Test)**: For each transport-path fixture, run the orchestrator and verify (a) the session's `final_disposition` matches the path, (b) the FR-031 write-back shape is correct, (c) attempt-count increments exactly once per `mock_provider_call_id`, (d) re-running with a duplicate-event fixture leaves all state and artifacts byte-identical (SC-005), (e) re-running with a conflicting-late-event fixture preserves the original disposition AND inserts one `conflicting_event_audit_records` row.

- [x] T046 [US3] Extend `process_one_queue_item` in `src/opencloser/core/orchestrator.py` for non-connected terminal events (`no_answer`, `voicemail`, `failed`) — finalize the session with the matching disposition; emit Phone Call activity + queue-status update; no Task payload (FR-018 + FR-031).
- [x] T047 [US3] Add the FR-019 duplicate-event no-op path to `process_one_queue_item`: every event-driven state mutation first attempts INSERT into `idempotency_keys` and skips on UNIQUE-violation. Covers session-state, attempt-count, write-back, and exported-artifact write surfaces.
- [x] T048 [US3] Add the FR-020 conflicting-late-event handler to `process_one_queue_item`: when an event arrives that would change the disposition of an already-`finalized` session, INSERT into `conflicting_event_audit_records` instead of mutating session state. The `conflicting_events.json` artifact is emitted at end-of-run if any such rows exist.
- [x] T049 [P] [US3] Create `tests/fixtures/transport_events/no_answer.json` — single `no_answer` event
- [x] T050 [P] [US3] Create `tests/fixtures/transport_events/voicemail.json` — single `voicemail` event
- [x] T051 [P] [US3] Create `tests/fixtures/transport_events/failed.json` — single `failed` event
- [x] T052 [P] [US3] Create `tests/fixtures/transport_events/duplicate_connected.json` — `connected` + `completed` + repeated `connected` with same `event_id` + repeated `completed` with same `event_id`
- [x] T053 [P] [US3] Create `tests/fixtures/transport_events/duplicate_callback_requested.json` — `connected` + `callback_requested` + `completed` + repeated `callback_requested` with same `event_id`
- [x] T054 [P] [US3] Create `tests/fixtures/transport_events/conflicting_failed_after_completed.json` — `connected` + `completed` + late `failed` with a distinct `event_id`
- [x] T055 [US3] Unit tests for idempotency in `tests/unit/test_idempotency_orchestrator.py` @pytest.mark.module("core"): every write-back kind no-ops on duplicate event_id; attempt-count increments exactly once across duplicate redeliveries.
- [x] T056 [US3] End-to-end integration test in `tests/integration/test_us3_paths.py` @pytest.mark.integration: one parametrized case per transport path (no_answer, voicemail, failed) + a duplicate-event byte-identity check + a conflicting-late-event audit-row check. Asserts the Independent Test's (a)–(e).

**Checkpoint US3**: Every transport-path fixture produces the FR-031 shape; duplicate-event reruns are byte-identical; conflicting-event audit row exists. US1 and US2 still pass.

---

## Phase 6: User Story 4 — Inspect normalized results and follow-up task payloads (P3)

**Story goal**: An operator who did not implement the feature can open the exported JSON artifacts and explain the outcome of any disposition — including `needs_human_review`, `do_not_call`, `wrong_number`, `not_interested`, `call_back_later`, `interested_email_captured`, and the Q5 captured-email-AND-callback edge case — without consulting source code.

**Independent Test (matches spec.md Story 4 Independent Test, expanded for SC-003 coverage)**: For at least one fixture per remaining disposition in FR-013's 11-value enum, run the orchestrator and open the exported `session-result.json`. Assert each required FR-014 field is present (with the "when applicable" rules satisfied) and human-readable. For `needs_human_review`, assert the `human_review_reason` is one of FR-035's 9 codes. For the Q5 case, assert the callback task payload carries both `preferred_callback_window` AND `captured_email`.

- [x] T057 [P] [US4] Create `tests/fixtures/conversations/interested_email_captured.json` — verified email captured, no callback request
- [x] T058 [P] [US4] Create `tests/fixtures/conversations/interested_email_and_callback.json` — verified email AND callback request (Q5 Clarification case)
- [x] T059 [P] [US4] Create `tests/fixtures/conversations/needs_human_review_uncertain_role.json` — contact's role is ambiguous; persona escalates with `uncertain_role`
- [x] T060 [P] [US4] Create `tests/fixtures/conversations/needs_human_review_email_invalid.json` — contact gives a syntactically valid but un-confirmed email, no callback → FR-036 rule #7 → `captured_email_invalid_no_callback`
- [x] T061 [P] [US4] Create `tests/fixtures/conversations/do_not_call_mid_call.json` — contact states DNC mid-conversation; triggers Edge Case "DNC stated mid-conversation"
- [x] T062 [P] [US4] Create `tests/fixtures/conversations/wrong_number.json` — contact states wrong number
- [x] T063 [P] [US4] Create `tests/fixtures/conversations/not_interested.json` — contact explicitly declines
- [x] T064 [P] [US4] Create `tests/fixtures/conversations/call_back_later.json` — contact asks to be called back later with no specific window
- [x] T065 [P] [US4] Create `tests/fixtures/conversations/script_truncated.json` — conversation ends without a clear signal (FR-036 rule #10)
- [x] T066 [US4] End-to-end integration test in `tests/integration/test_us4_artifact_readability.py` @pytest.mark.integration: parametrized over every fixture from T035–T065; for each, run the orchestrator and assert the FR-014 field presence/absence per disposition + the FR-031 write-back-shape per disposition + the FR-032 `new_status` per disposition. Includes a dedicated Q5 assertion that the callback task payload carries both `preferred_callback_window` and `captured_email`.

**Checkpoint US4**: Every disposition in FR-013's 11-value enum is reachable via a fixture and produces operator-readable artifacts (SC-003 satisfied). US1, US2, and US3 still pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T067 Implement the SC-009 module-isolation gate via a dependency-direction lint in `tests/test_imports.py`: walks each module's `import` statements via the `ast` module and asserts only the allowed dependencies per the contracts (`core` may import any boundary module; boundary modules may import `models` and `state` but NOT each other). Fails CI on violation.
- [x] T068 Add the SC-001 wall-time **gate test** in `tests/integration/test_sc001_budget.py` @pytest.mark.integration: parametrized over every Slice 1 conversation + transport fixture combination, run the CLI and assert the emitted `wall_time_ms < 60000` (the 60-second SC-001 budget). The CLI line itself is owned by T034; this task only adds the integration assertion.
- [x] T069 [P] Add an SC-005 deterministic-JSON property test in `tests/integration/test_sc005_determinism.py`: run any US1 fixture twice in isolated temp directories; assert byte-identity of every exported artifact across the two runs.
- [x] T070 [P] Add an SC-006 false-positive test in `tests/integration/test_sc006_no_false_activity.py`: run the no_answer / voicemail / failed fixtures and assert no `phone_call_activities` row falsely claims a connected conversation (e.g., `summary` does NOT contain words the persona would only say on a connected call).
- [x] T071 [P] Enforce a 90% coverage floor in `pyproject.toml` `[tool.pytest.ini_options]` via `--cov=src/opencloser --cov-fail-under=90`.
- [x] T072 Verify `.specify/memory/constitution.md` (authored 2026-05-19 during /speckit.analyze remediation) remains in sync with the spec's `## Constitution Alignment` section. If Slice 1 implementation surfaced any principle refinement, amend the constitution and record a Rationale section per its Governance clause.
- [x] T073 [P] Update `README.md` with a 20-line "what is Slice 1" section linking to quickstart.md and the 5 contract files.
- [x] T074 [P] Run `uv run ruff check . && uv run ruff format .` and resolve any findings; commit lint config in `pyproject.toml` if not already.
- [x] T075 Verify SC-008's plan-time review: walk the 5 `contracts/*.md` files and confirm each public surface is documented language-neutrally and is plausibly satisfiable by the future SignalWire / Dataverse / real-persona substitutions. Record findings in `specs/001-mock-call-mock-crm/SC008_REVIEW.md`.

**Checkpoint Polish**: All 9 success criteria measurable from CI + artifacts. The codebase has lint + coverage gates. Constitution doc exists. SC-008 review is on record.

---

## Dependencies

### Phase-level

```text
Phase 1 (Setup) ──> Phase 2 (Foundational) ──> Phase 3 (US1) ──> Phase 4 (US2)
                                                                       │
                                                                       ├──> Phase 5 (US3)
                                                                       │
                                                                       └──> Phase 6 (US4)
                                                          (Phases 4, 5, 6 are independent
                                                           of each other once US1 is done)
                                                                                          │
                                                                                          └──> Phase 7 (Polish)
```

- Phase 2 (T008–T016) is foundational: every story below depends on it.
- Phase 3 (US1) is the MVP gate: all five module skeletons are introduced here, so US2/US3/US4 ADD behaviors rather than introducing new modules.
- Phases 4, 5, 6 are mutually independent — each extends a different aspect of the orchestrator (block path; idempotency + duplicate/conflict handling; additional dispositions/fixtures).
- Phase 7 is post-stories cross-cutting work.

### Story-level

```text
US1 (T017–T038) ──> US2 (T039–T045)
                 ├──> US3 (T046–T056)
                 └──> US4 (T057–T066)
```

US2/US3/US4 each depend ONLY on US1, not on each other.

### Task-level critical path

```text
T001 → T002 → T008 → T009 → T010 → T013 → T015          (foundational write surface)
T008 → T011 (ids)                                        (foundational ids)
T010 → T016 (foundational tests)                         (state-store tests)
T015 → T016 (foundational tests)                         (artifact-writer tests)
T011 → T032 (orchestrator)                               (ids feed session creation)
T013 → T032 (orchestrator)                               (idempotency feeds state mutations)
T015 → T032 (orchestrator)                               (artifact writes at end)
T021 → T032 (orchestrator)                               (eligibility feeds the allow/block branch)
T023 → T032 (orchestrator)                               (transport feeds events)
T028 → T032 (orchestrator)                               (persona feeds disposition)
T030 → T032 (orchestrator)                               (crm-writeback emits payloads)
T032 → T034 → T038                                        (orchestrator → CLI → US1 integration test)
T032 → T039 → T045                                        (orchestrator block path → US2 integration)
T032 → T046 → T047 → T048 → T056                          (US3 path + idempotency + conflict + integration)
T032 → T066                                               (US4 integration over fixtures)
```

---

## Parallel Execution Examples

### Phase 1 parallel batch (after T001 + T002)

```text
T003 [P] .gitignore
T004 [P] config/slice1.toml
T005 [P] tests/__init__.py + sub-dirs
T006 [P] fixture sub-directories
T007 [P] README.md placeholder
```

### Phase 2 parallel batch (after T008 + T009 + T010)

```text
T011 [P] core/ids.py
T012 [P] core/clock.py
T013 [P] core/idempotency.py
T014 [P] core/config.py
T015 [P] artifacts/writer.py
T016 [P] foundational unit tests
```

### Phase 3 parallel batch — module ABCs (right after Phase 2 lands)

```text
T017 [P] eligibility ABC
T018 [P] transport ABC
T019 [P] persona ABC
T020 [P] crm ABC
```

### Phase 3 parallel batch — persona submodules (after T019)

```text
T025 [P] persona/extraction.py
T026 [P] persona/escalation.py
```

(Then T027 depends on both; T028 depends on T027 + the disclosure validator.)

### Phase 3 parallel batch — unit tests + fixtures (after each module lands)

```text
T022 [P] eligibility unit tests
T024 [P] transport unit tests
T029 [P] persona unit tests
T031 [P] crm unit tests
T033 [P] orchestrator unit tests
T035 [P] queue-item fixture
T036 [P] conversation fixture
T037 [P] transport fixture
```

### Phase 4 parallel batch — fixtures (after T039)

```text
T040–T044 [P] one [P] fixture per blocking condition
```

### Phase 5 parallel batch — transport fixtures (after T046–T048)

```text
T049–T054 [P] one [P] fixture per transport path / duplicate / conflict variant
```

### Phase 6 parallel batch — conversation fixtures

```text
T057–T065 [P] all nine remaining-disposition conversation fixtures in parallel
```

### Phase 7 parallel batch (after T067 + T068)

```text
T069 [P] SC-005 determinism test
T070 [P] SC-006 false-positive test
T071 [P] coverage floor enforcement
T073 [P] README update
T074 [P] lint pass
```

---

## Implementation Strategy

### MVP-first (recommended)

1. **Phase 1 + Phase 2 + Phase 3** = the MVP. After T038 passes, the team can demo the full happy-path loop end-to-end against fixtures and ship Slice 1's reference behavior to stakeholders. This is the smallest valuable deliverable.
2. **Phase 4** = safety/eligibility hardening. Eligibility is the cheapest and most important safety gate — implement it second.
3. **Phase 5** = idempotency/audit hardening. Required for forward-compatibility with real telephony (Slice 2's SignalWire).
4. **Phase 6** = coverage of remaining dispositions. Demonstrable to non-engineer stakeholders (SC-007).
5. **Phase 7** = CI gates, lint, constitution doc, SC-008 review.

### Incremental delivery checkpoints

- **After Phase 3**: demo-ready MVP. Run `quickstart.md` step 3 in front of stakeholders.
- **After Phase 4**: safety gate proved. DNC + call-window + max-attempts protections in place.
- **After Phase 5**: idempotency invariants proved. Safe to plan Slice 2 (real telephony) on top.
- **After Phase 6**: every disposition in FR-013 reachable + readable. SC-003 + SC-007 met.
- **After Phase 7**: every success criterion enforceable in CI. Slice 1 ready to hand off / archive.

### Risk-driven sequencing notes

- **Highest-risk module**: the orchestrator (T032 + T039 + T046–T048). It's the single coordination point across all five boundaries. Allocate the most review time here.
- **Lowest-risk modules**: eligibility (pure function) and artifact writer (deterministic JSON write). Build these first to free up review attention for the orchestrator.
- **Most parallelizable module**: persona (extraction + escalation + disposition_rules are mostly independent submodules).

---

## Format Validation

All 75 tasks follow the strict checklist format: `- [ ] T### [P?] [US#?] Description with file path`.

- Tasks in Phase 1 (Setup) and Phase 2 (Foundational): no story label, file paths absolute-from-repo-root.
- Tasks in Phases 3–6: every task has a `[US#]` label.
- Tasks in Phase 7 (Polish): no story label.
- `[P]` markers used only where the task can run in parallel with surrounding `[P]` tasks (different file, no in-phase dependency on incomplete work).

---

## Out-of-Scope (carried forward from spec.md and plan.md)

Tasks for the following are intentionally absent — they belong to later slices:

- Real telephony (SignalWire) — Slice 2
- Real CRM (Dataverse) — Slice 2
- Live LLM-driven persona — Slice 3+
- Pipecat integration — Slice 2+
- Admin UI / React / Next.js — deferred
- Multi-worker scaling, Redis, Celery, Kubernetes — out of MVP
- Clinical personas, PHI handling — explicitly excluded
- Batch processing, claim-and-lock — out of Slice 1
