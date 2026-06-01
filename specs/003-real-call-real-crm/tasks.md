---

description: "Slice 3 implementation tasks"
---

# Tasks: Slice 3 — Real Call, Real CRM

**Input**: Design documents from `/specs/003-real-call-real-crm/`

**Prerequisites**: [plan.md](./plan.md) (required), [spec.md](./spec.md) (required for user stories), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: REQUIRED per Constitution Principle IV ("Automation Is Auditable and Idempotent") and the spec's testing-strategy contract — Slice 3 changes queue / CRM write-back / duplicate-event / eligibility / persona-result / safety behavior, all of which the constitution mandates focused verification for. Tests are written before implementation; the 64 contract tests enumerated in `contracts/` are the gate that every implementation task must satisfy.

**Organization**: Tasks are grouped by user story (US1 – US7 from spec.md User Scenarios). The five P1 stories together form the demonstrable MVP loop; US6 and US7 are P2 additions.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3); omitted for Setup, Foundational, and Polish phases
- Include exact file paths in descriptions

## Path Conventions

Single-project Python CLI. All paths are relative to repository root unless otherwise noted:

- Source: `src/opencloser/...`
- Tests: `tests/contract/...`, `tests/integration/...`, `tests/unit/...`, `tests/fixtures/...`
- Config: `config/...`
- Docs: `docs/slice3/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Slice 3 specific package skeletons + dependency updates. The Slice 1 + Slice 2 setup is already complete and reused.

- [X] T001 Add Slice 3 runtime dependencies to `pyproject.toml`: `signalwire>=2.0,<3.0`, `pipecat-ai`, `fastapi`, `uvicorn` (only used by the embedded callback receiver, started only in real-call mode per [research.md §1](./research.md#1-signalwire-outbound-dial--callback-surface))
- [X] T002 [P] Create empty package skeletons for the four new Slice 3 packages: `src/opencloser/transport/signalwire/__init__.py`, `src/opencloser/runtime/__init__.py`, `src/opencloser/runtime/pipecat/__init__.py`, `src/opencloser/shadow_stt/__init__.py`, `src/opencloser/slice3/__init__.py`
- [X] T003 [P] Create `config/slice3.toml` with the six sections from [research.md §11](./research.md#11-configuration-surface): `[signalwire]`, `[realtime_ai]`, `[shadow_stt]`, `[timeouts]`, `[retention]`, `[redaction]` — with the defaults from [research.md §7](./research.md#7-timeouts-and-grace-window) (abandonment=90, silence-after-connection=30, grace-window=3)
- [X] T004 [P] Create `config/shadow_stt_discrepancy_policy.json` with the two-section policy from [research.md §4](./research.md#4-shadow-stt-provider-and-discrepancy-policy): `benign_rules` and `uncertain_rules`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation. This includes the SQLite schema additions, new model classes, foundational Protocols, and the slice3/runner skeleton.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Extend `src/opencloser/state/store.py` with three new SQLite tables (`rejected_auth_callbacks`, `shadow_stt_discrepancies`, `shadow_lane_truncated_events`) and eight new columns on `sessions` (`runtime_identity_json`, `operator_identity_current`, `operator_identity_original`, `run_mode`, `grace_window_sec`, `shadow_stt_enabled`, `finalized_at`, `cm_writeback_started_at`) per [data-model.md §3](./data-model.md). The §1.1 conceptual rename `provider_call_id` is stored on-disk in the existing `mock_provider_call_id` column — no schema-level rename so Slice 1 / Slice 2 reads stay interpretable. Add forward migration that preserves Slice 2 data.
- [X] T006 [P] Extend `src/opencloser/models.py` with Slice 3 Pydantic models: `CallEvent` (rename from `MockCallEvent`), `ProviderCallId` (rename from `mock_provider_call_id`), `DialPlan` (rename from `fixture_id`), `RejectedAuthCallback`, `ShadowSTTDiscrepancyRecord`, `ShadowLaneTruncatedEvent`, `TelephonyReadinessReport`, `RunReport`, `RealtimeProviderSession`, `QueueStatusUpdateVariant` enum per [data-model.md §1, §2](./data-model.md). Preserve backwards-compat aliases for pre-Slice-3 names.
- [X] T007 [P] Create `src/opencloser/runtime/base.py` defining the `PersonaRuntime` Protocol per [contracts/pipecat-runtime.md](./contracts/pipecat-runtime.md) (foundational interface; Pipecat impl lands in US1+US5)
- [X] T008 [P] Create `src/opencloser/shadow_stt/base.py` defining the `ShadowSTTProvider` and `ShadowSTTLane` Protocols per [contracts/shadow-stt-lane.md](./contracts/shadow-stt-lane.md) (foundational interface; impl lands in US6)
- [X] T009 [P] Extend `src/opencloser/redaction/layer.py` to cover the four derivative-artifact types (full transcript + session-result summary + shadow STT transcript + shadow STT discrepancy records) per FR-033 + Round 2 Q10. Add a PHI tag-and-redact pre-write hook callable from `persona/extraction.py` per Round 2 Q11. Pointer metadata is explicitly excluded.
- [X] T010 [P] Extend `src/opencloser/persona/escalation.py` to add the additive `shadow_stt_discrepancy` entry to the `human_review_reason` enumeration per FR-031. No other Slice 1 reason is replaced or removed.
- [X] T011 Create `src/opencloser/slice3/__init__.py` and a stub `src/opencloser/slice3/runner.py` that exposes a `run_slice3(args) → exit_code` entry point. Real-mode + rehearsal-mode branches land in US1 + US2.
- [X] T012 Extend `src/opencloser/cli.py` with a `run3` Typer subcommand stub per [contracts/cli-slice3.md](./contracts/cli-slice3.md) — declares the seven options (`--campaign-id`, `--queue-item-id`, `--real-call/--write`, `--shadow-stt/--no-shadow-stt`, `--operator-id`, `--resume`, `--config`) and dispatches to `slice3.runner.run_slice3`. Real argument parsing + exit-code mapping land in US1.

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Process one Dataverse queue item end-to-end through a real SignalWire call (Priority: P1) 🎯 MVP

**Goal**: One eligible Dataverse-owned ALF queue item moves from `ready` to a final disposition after a real SignalWire outbound call. SignalWire → Pipecat → real-time AI → ALF persona → normalized result → Dynamics write-back (Phone Call activity + queue-status / DNC / attempt fields + callback or review Task) — the entire MVP loop.

**Independent Test**: With a verified Dataverse mapping, configured SignalWire credentials + source caller-id, one `ready` test queue item with a valid E.164 destination phone, and a live test caller, run `opencloser run3 --campaign-id <id> --queue-item-id <id> --real-call --operator-id <id>`. Confirm in Dynamics: the queue-status / attempt / last-disposition / last-session fields are updated; a Phone Call activity is created with the SignalWire SID, the persona-authored summary, and connected-call timestamps; a callback or review Task is created and assigned to the configured owner (when warranted). Confirm locally: `artifacts/<session_id>/run_report.json` contains every FR-036 field; `transcript.txt` is redacted per FR-033.

### Tests for User Story 1 (write first; must fail before implementation)

- [X] T013 [P] [US1] Contract test for SignalWire transport in `tests/contract/test_signalwire_transport.py` — implements all 10 assertions from [contracts/signalwire-transport.md](./contracts/signalwire-transport.md) (place_call returns ProviderCallId, normalization, dedup, out-of-order, late-after-finalization, signature verification rejection, no-secret-no-body audit, E.164 pre-dial block, 4xx no-attempt-consumed, no-vendor-leak). **TDD red verified 2026-05-25**: all 10 tests fail with `NotImplementedError` from `src/opencloser/transport/signalwire/` stubs; supporting changes — `MockCallEvent.{is_duplicate, out_of_order, late_after_finalization}` fields (Q1), `signalwire_callbacks` SQLite audit surface pinned (Q2), `adapter.ingest_callback(...)` test entrypoint (Q3), `FakeSignalWireClient` injected (Q4), `tests/contract/conftest.py` shared fixtures (Q10), `pytest-asyncio` strict mode (Q6), `test_boundary_isolation.py` extended with 10 SignalWire forbidden patterns over 13 boundary modules (Q9). 1058/1058 non-T013 tests still pass; coverage 90.07% (transport/signalwire stubs in `[tool.coverage.run].omit` until T022-T026 land). See [t013-clarify-questions.md](./t013-clarify-questions.md).
- [X] T013b [P] [US1] Contract test for rejected-by-authentication audit log in `tests/contract/test_rejected_auth_audit_log.py` — implements all 8 assertions from [contracts/rejected-auth-audit-log.md](./contracts/rejected-auth-audit-log.md) (record appends row to both JSONL + SQLite; distinct from `callbacks_audit.jsonl`; schema excludes verification secret and callback body; unassociated callback has `session_id=null` and lands in `artifacts/_unassociated/...`; `http_status` is 401 with the CHECK constraint enforcing it; `count_for_session(sid)` matches the JSONL line count; `run_report.json` surfaces `rejected_auth_callbacks_count`; grep across all `artifacts/**/rejected_auth_callbacks.jsonl` files contains 0 substrings matching `SIGNALWIRE_SIGNING_SECRET` per SC-018). Per `/speckit-analyze` L1 finding (2026-05-25). **TDD red verified 2026-05-25**: all 8 tests fail with `NotImplementedError` from `src/opencloser/artifacts/rejected_auth_log.py` stub (writer lands in T032).
- [X] T014 [P] [US1] Contract test for Pipecat runtime in `tests/contract/test_pipecat_runtime.py` — implements all 11 assertions from [contracts/pipecat-runtime.md](./contracts/pipecat-runtime.md) (first utterance disclosure, no-acknowledgment-required, deterministic disposition precedence, disallowed claim escalation, PHI escalate+redact, three runtime degradation triggers, identity recorded no credentials, no Pipecat leak). **TDD red verified 2026-05-25**: all 11 tests fail with `NotImplementedError` from `src/opencloser/runtime/pipecat/runtime.py` stub (real impl lands in T030 / T064 / T065 / T066 / T067). Supporting: `runtime/pipecat/errors.py` (3 exception types — RealtimeProviderError, PipecatRuntimeError, SilenceAfterConnectionTimeout); `tests/fixtures/pipecat/` (FakeRealtimeAIProvider scriptable for happy path / raise-on-start / raise-during-stream / silent-after-connection modes, FakeLiveConversationInput, FakeSessionHandle).
- [X] T015 [P] [US1] Contract test for CRM write-back Slice 3 extensions in `tests/contract/test_crm_writeback_slice3.py` — implements the 11 assertions from [contracts/crm-writeback-dnc-first.md](./contracts/crm-writeback-dnc-first.md) (real provider call ID on payload, connected-call timestamps, DNC-first ordering on do_not_call, four-operation count preserved, queue-status variants, blocked / dial-blocked variants, idempotency preserved, resume rehearsal no-mutation, no operator identity in Dataverse). **TDD red verified 2026-05-25**: all 11 tests fail at the existing Slice 2 `DataverseWriteBackAdapter` boundary — each via `inspect.signature` / `hasattr` checks that point T031 at the specific gap to fill (`provider_call_id` kwarg, `connected_call_timestamps` kwarg, `variant: QueueStatusUpdateVariant` kwarg, `assemble_writeback` method, DNC-first ordering on `do_not_call`, four-operation count preservation, no operator-identity leakage).
- [X] T016 [P] [US1] Contract test for `opencloser run3` CLI in `tests/contract/test_cli_slice3.py` — implements the 11 assertions from [contracts/cli-slice3.md](./contracts/cli-slice3.md) (default invocation rehearsal, real-call flag required for mutation, real-call required on resume, resume preserves original operator, concurrent claim exit 3, readiness failure exit 4, provider-rejected exit 5, live-call abandonment exit 6, run report fields, DNC-first reflected, no secrets in stdout/report). **TDD red verified 2026-05-25**: all 11 tests use Typer's `CliRunner` to invoke `opencloser run3`; all fail because `run_slice3` raises `NotImplementedError` (will turn green incrementally as T034 / T038 / T046 / T047 / T048 / T056 / T057 / T087 / T088 / T033 land). Test fixture pre-loads `SIGNALWIRE_SIGNING_SECRET` + `DATAVERSE_CLIENT_SECRET` env vars with sentinel values to assert SC-018 no-secret-leak via stdout + run_report scan.
- [X] T017 [P] [US1] Integration test US1 `interested_callback_requested` happy path in `tests/integration/test_us1_real_call_callback.py` — full stack with fakes for SignalWire / Pipecat / real-time AI / Dataverse; assert Phone Call activity + queue-status update + callback Task created in Dataverse fake; assert run_report.json contains all FR-036 fields. **TDD red verified 2026-05-31**: drives the new injectable `run_one_real_call` seam (added as a T034 stub in `slice3/runner.py`, mirroring Slice 2's `run_one_crm_item`); fails red on `report is not None` (naming T034). Shared driver `tests/fixtures/slice3_configs.py` (`run_real_call` / `find_run_report` / `created_of` / `queue_patches`) reuses the Slice 2 Dataverse fake + mapping + seed.
- [X] T018 [P] [US1] Integration test US1 `interested_email_captured` in `tests/integration/test_us1_real_call_email.py` — assert exactly one follow-up Task with captured email; queue-status / attempt updated per Slice 1 write-back contract. **TDD red verified 2026-05-31**: asserts the captured email (`director@sunset.example.com`) appears in the single Task payload and queue status moves to `completed` (2); red on `report is not None` (T034).
- [X] T019 [P] [US1] Integration test US1 terminal states `no_answer` / `voicemail` / `failed` in `tests/integration/test_us1_real_call_terminal_states.py` — assert no false connected-call Phone Call activity; per-disposition write-back map preserved; no follow-up Task per Slice 1. **TDD red verified 2026-05-31**: parametrized ×3 (mirrors Slice 1 SC-006); asserts no Task, no connected-call markers on any Phone Call activity, and the per-disposition queue PATCH; red on `report is not None` (T034).
- [X] T020 [P] [US1] Integration test US1 `do_not_call` disposition in `tests/integration/test_us1_real_call_dnc.py` — assert DNC / opt-out + queue-status fields updated; **DNC field write is FIRST in the write-back sequence per Round 2 Q14**; no callback or review Task. **TDD red verified 2026-05-31**: asserts `medx_donotcall is True` + status `dnc` (4), no Task, and `run_report.per_writeback_operation_status[0].operation == queue_status_update.dnc`; red on `report is not None` (T034).
- [X] T021 [P] [US1] Integration test US1 `needs_human_review` disposition in `tests/integration/test_us1_real_call_review.py` — assert exactly one review Task assigned to configured review owner with a reason code from the Slice 1 enumerated set. **TDD red verified 2026-05-31**: asserts the single Task routes to `OWNER_REVIEW`, queue status 3, and `run_report.human_review_reason` is an enumerated `HumanReviewReason`; red on `report is not None` (T034).

### Implementation for User Story 1

- [X] T022 [P] [US1] Implement `src/opencloser/transport/signalwire/signature.py` — HMAC-SHA256 signature verification per [research.md §2](./research.md#2-signalwire-signature-verification--rejected-by-authentication-audit-log); rejected callbacks raise `SignatureVerificationError` and trigger the rejected-auth audit log writer (audit log writer itself lands in T032). **Completed 2026-05-25**: `verify_signature(headers, body, signing_secret)` computes HMAC-SHA256 over `body` keyed by `signing_secret`, base64-encodes, constant-time compares against `X-SignalWire-Signature` (case-insensitive). Missing/empty/mismatched header → `SignatureVerificationError` (http_status=401). Exception message excludes secret and body (FR-008, FR-035, Round 2 Q9). Audit log writer integration deferred to T032; `ingest_callback` wiring deferred to T025. 9 focused unit tests in `tests/unit/test_signalwire_signature.py` (valid, lowercase header, bad sig, missing header, empty header, body tampering, wrong secret, no-secret-in-exception, header candidate pin) — all 9 pass.
- [X] T023 [P] [US1] Implement `src/opencloser/transport/signalwire/errors.py` — exception hierarchy: `TelephonyReadinessError`, `RealDialPhoneValidationError`, `ProviderRejectedDialError`, `SignatureVerificationError`, `LiveCallAbandonmentError` per [contracts/signalwire-transport.md](./contracts/signalwire-transport.md). **Completed 2026-05-31**: the five exception types are real (scaffolded during T013/T022 supporting work); `RealDialPhoneValidationError` subclasses `TelephonyReadinessError` so `place_call` callers catching the latter also catch the E.164 pre-dial failure (contract §Raises); `SignatureVerificationError` pins `http_status=401`, `ProviderRejectedDialError` carries `http_status` + optional `provider_message`. Removed the stale "stub" docstring; added 13 focused unit tests in `tests/unit/test_signalwire_errors.py` covering every constructor, the inheritance/distinctness contract, and the FR-008/FR-035 no-secret/no-body invariant on `SignatureVerificationError`. errors.py now **100% covered** (was 52% — constructors were unreached because the T013 contract tests that raise them are still TDD-red); full suite 1080 passed / 58 TDD-red by design; total coverage 91.30%.
- [X] T024 [US1] Implement `src/opencloser/transport/signalwire/dial.py` — outbound dial via `signalwire` SDK + SWML dial-plan construction + E.164 / provider-acceptable destination phone validation (raises `RealDialPhoneValidationError` pre-dial per FR-010); 4xx responses raise `ProviderRejectedDialError` per FR-012; depends on T022, T023. **Completed 2026-05-31**: `place_outbound_call(*, client, queue_item, dial_plan, source_caller_id)` validates the destination via `is_e164(...)` and raises `RealDialPhoneValidationError` BEFORE any `client.create_call` (FR-010); a 4xx surfaces as `ProviderRejectedDialError` from the injected client (FR-012). Added `build_swml_dial_plan(...)` (opaque serialized SWML, kept inside the transport boundary). `SignalWireClient` Protocol unchanged (constructor-injected per Q4). 12 unit tests in `tests/unit/test_signalwire_dial.py` (is_e164 matrix, happy-path SID, invalid-phone-blocks-before-dial ×4, provider-4xx, SWML builder). Removed from coverage omit list; dial.py now **100% covered**.
- [X] T025 [US1] Implement `src/opencloser/transport/signalwire/callbacks.py` — status + media callback handlers; normalize SignalWire intermediate states (ringing/answered/in-progress/busy/canceled/failed) into the six `CallEvent.event_type` values per FR-005; dedup by `(session_id, provider_event_id)` per FR-007/FR-021; mark `out_of_order` and `late_after_finalization` per FR-027; depends on T022. **Completed 2026-05-31**: `SignalWireCallbackNormalizer` (one per provider call) + stateless `parse_callback` / `normalize_status` primitives. Pre-connection intermediates (queued/ringing/in-progress) and unknown statuses normalize to `None` (absorbed, never emitted) so no vendor state name leaks (SC-015); answered→connected, completed→completed, busy/canceled/failed→failed, no-answer→no_answer, voicemail→voicemail. Dedup by `provider_event_id`; out-of-order via connection-vs-terminal rank; `late_after_finalization` once the adapter calls `mark_finalized()`. Emitted `CallEvent.payload` is empty (no-leak). 14 unit tests in `tests/unit/test_signalwire_callbacks.py`. Removed from coverage omit list; callbacks.py now **100% covered**. The adapter (T026) owns finalization signaling + audit-log writes + `ingest_callback`/`event_stream`, so the T013 contract suite stays red until T026.
- [X] T026 [US1] Implement `src/opencloser/transport/signalwire/adapter.py` — assemble the `CallTransport` Protocol with `place_call` and `event_stream` per [contracts/signalwire-transport.md](./contracts/signalwire-transport.md); depends on T024, T025. **Completed 2026-05-31**: `SignalWireTransport` wires `place_call` → `dial.place_outbound_call` (T024); `ingest_callback` → per-call `SignalWireCallbackNormalizer` (T025) buffering emitted `CallEvent`s keyed by `provider_call_id`; `event_stream` drains the buffer in order and `mark_finalized()` after a terminal event so later callbacks flag `late_after_finalization` (FR-027). **Greens 7 of 10 T013 assertions** (place_call returns SID, normalize ringing→in_progress→answered→completed = [connected, completed], dedup, out-of-order, E.164 pre-dial block, provider-4xx, no-leak). **Assertions 5/6/7 deferred to T032** (signature *enforcement* + `rejected_auth_callbacks` write + `conflicting_callbacks_audit.jsonl`): strict HMAC verification would reject the contract test's placeholder-signature normal-path callbacks too, so enforcement is paired with the rejected-auth/conflicting audit writers T032 adds; late events are tracked in-memory (`_late_events`) for T032 to flush. Removed from coverage omit; adapter.py now **100% covered**. Full suite 1124 passed / 51 TDD-red by design; total cov 91.59%.
- [X] T027 [P] [US1] Implement `src/opencloser/runtime/pipecat/identity.py` — records `{runtime_name, runtime_version, provider_name, model_name, model_version}` on every session per FR-016; **excludes credentials** per FR-035. **Completed 2026-05-31**: `build_runtime_identity(provider, *, runtime_version=None) -> RealtimeProviderSession` stamps `runtime_name="pipecat"` + `pipecat_runtime_version()` (from `importlib.metadata.version("pipecat-ai")`) and copies the 3 FR-016 fields from `provider.identity`. The `RealtimeProviderSession` model is `extra="forbid"` (structural credential guard); `build_runtime_identity` additionally raises `ValueError` if `provider.identity` exposes any credential-bearing key (key/token/secret/password/credential/authorization/bearer) per FR-035, or is missing a required field. 6 unit tests in `tests/unit/test_pipecat_identity.py`; identity.py **100% covered** (not in omit). Consumed by the T030 runtime (which greens T014 assertion 10); building block only — no T014 assertion greens at T027. Full suite 1130 passed / 51 TDD-red by design; total cov 91.65%.
- [X] T028 [P] [US1] Implement `src/opencloser/runtime/pipecat/provider.py` — `RealtimeAIProvider` Protocol adapter (3 methods: `start_session`, `stream_audio`, `end_session`) per [research.md §3](./research.md#3-real-time-ai-provider-surface); plus `provider_fake.py` for CI fixtures. **Completed 2026-05-31**: `provider.py` defines the vendor-neutral frame types (`TranscriptSegment{text,speaker}`, `ExtractionEvent{field,value,confidence}`, `AudioChunk{data}`) consumed by the pipeline (T029)/runtime (T030), `ProviderSessionHandle` (impl of the `SessionHandle` Protocol), and `select_realtime_provider(env)` — the `SLICE3_REALTIME_PROVIDER` deploy-time seam (default `fake-realtime`; unknown name raises `ValueError`, real adapters wired at deploy time). `provider_fake.py` is the in-tree CI fake implementing the 3-method `RealtimeAIProvider` contract (scriptable frame replay) with a credential-free identity (FR-035); distinct from the richer error-injection fake in `tests/fixtures/pipecat/` used by T014. 7 unit tests in `tests/unit/test_pipecat_provider.py` (frame types, handle, provider selection ×3, fake lifecycle+replay, identity integrates with T027 `build_runtime_identity`). provider.py + provider_fake.py both **100% covered**. Building block (T030 wires it into the runtime); no T014 assertion greens at T028. Full suite 1137 passed / 51 TDD-red by design; total cov 91.80%.
- [X] T029 [US1] Implement `src/opencloser/runtime/pipecat/pipeline.py` — single Pipecat pipeline with three `FrameProcessor` stages (`SignalWireMediaInput` → `RealtimeAIProviderBridge` → `PersonaSink`) per [research.md §5](./research.md#5-pipecat-pipeline-topology); μ-law 8 kHz; VAD-driven turn-taking with 800 ms silence fallback. **Completed 2026-06-01**: real Pipecat (1.2.1) `FrameProcessor` chain — `SignalWireMediaInput` (media bytes → `InputAudioRawFrame`), `RealtimeAIProviderBridge` (delegates audio to the T028 `RealtimeAIProvider`, wraps `TranscriptSegment`/`ExtractionEvent` in custom `PersonaTranscriptFrame`/`PersonaExtractionFrame`), `PersonaSink` (collects persona frames into `sink.collected` for the T030 runtime). `PipelineConfig` pins μ-law / 8 kHz / 1 ch / 800 ms VAD fallback. `build_pipeline(provider, handle, config?) -> BuiltPipeline` assembles `Pipeline([...])`. Pure helpers (`media_bytes_to_audio_frame`, `provider_frame_to_persona_frame` — unknown frames absorbed → `None`, no leak) + config + assembly are unit-tested (8 tests in `tests/unit/test_pipecat_pipeline.py`). pipeline.py **coverage-omitted** (like runtime.py): `FrameProcessor.process_frame` delivery needs Pipecat's live pipeline setup (StartFrame/task manager), exercised by integration/manual runs, not unit tests. Building block for T030; no T014 assertion greens at T029. Full suite 1144 passed / 51 TDD-red by design; total cov 91.80%.
- [X] T030 [US1] Implement `src/opencloser/runtime/pipecat/runtime.py` — `PersonaRuntime` impl that wires the pipeline (T029) to the persona module and delivers `PersonaOutput`; preserves deterministic Slice 1 disposition precedence (live model never sets disposition) per FR-014; depends on T028, T029. **Completed 2026-06-01**: `PipecatRuntime.run` opens a provider session, streams caller audio through the provider, collects transcript frames (duck-typed; `ExtractionEvent`s are dropped so the live model never reaches the disposition path — FR-014), records runtime/model identity via T027, and delegates the transcript to the default `ALFAppointmentSetterPersona` whose deterministic Slice 1 rules select the disposition. Imports no Pipecat types (SC-015 no-leak). **Greens 4 of 11 T014 assertions** (#1 disclosure, #3 deterministic-disposition-precedence — the FR-014 core, #10 identity-no-credentials, #11 no-Pipecat-leak). **#2 (no-ack), #4 (disallowed-claim escalation), #5 (PHI), #6-#9 (runtime degradation) are deferred to US5** (T064 degradation.py + T065 wiring; T066 PHI hook + T067 escalation wiring) per the stub's documented split. runtime.py stays coverage-omitted (US5 adds the degradation/PHI branches). Full suite 1149 passed / 47 TDD-red by design; total cov 91.84%.
- [X] T031 [US1] Extend `src/opencloser/crm/dataverse/adapter.py` — add the Slice 3 Phone Call activity payload fields (`provider_call_id`, optional `connected_call_timestamps {answered_at, completed_at}`) per FR-020 + [contracts/crm-writeback-dnc-first.md](./contracts/crm-writeback-dnc-first.md); preserve Slice 2 idempotency-key stamping (FR-021), bounded retry (FR-022), four-operation count (Round 2 Q8 — queue-status variants are field-level). **Completed 2026-06-01**: `emit_phone_call_activity` gained additive keyword-only `provider_call_id` + `connected_call_timestamps` (threaded into `_phone_call_body`: real SID under `medx_providercallid`, `answered_at`/`completed_at` override `actualstart`/`actualend`); `emit_queue_status_update` gained the `variant: QueueStatusUpdateVariant` kwarg (default NORMAL — field-level variants preserve the four-op count); new `assemble_writeback(result) -> list[WriteBackStep]` orchestration method with **DNC-first ordering** on `do_not_call` (Round 2 Q14, no Task per FR-024), BLOCKED-only on `blocked`, and phone+queue+task on normal/terminal. Added `WriteBackStep` model. All Slice 2 callers unaffected (new params default). **Greens all 11 T015 assertions.** Also fixed a T015 test-fixture bug (`blocked_reason="rule_d_dnc_pass"` → `["d"]`; the field is `list[RuleCode]`). Full suite 1160 passed / 36 TDD-red by design; total cov 91.74% (adapter.py 93%; assemble_writeback normal path covered by the T017-T021 integration tests at T034).
- [ ] T032 [US1] Extend `src/opencloser/artifacts/writer.py` — add writers for `callbacks_audit.jsonl`, `rejected_auth_callbacks.jsonl` (per [contracts/rejected-auth-audit-log.md](./contracts/rejected-auth-audit-log.md): no secret, no body, only `received_at + source_metadata + http_status=401`), `conflicting_callbacks_audit.jsonl`, `telephony_readiness.json`, `actual_writeback.json`, redacted `transcript.txt`. **Also (per /speckit-analyze M1, 2026-05-31): wire signature ENFORCEMENT into `SignalWireTransport.ingest_callback`** — call `signature.verify_signature(...)` (T022) on every inbound callback; on failure raise `SignatureVerificationError` AND append the `rejected_auth_callbacks` row (SQLite + JSONL); on the late-after-finalization path flush the in-memory `_late_events` (tracked by T026) to `conflicting_callbacks_audit.jsonl`. This greens the 3 remaining T013 assertions (5 conflicting-log, 6 signature-reject, 7 rejected-auth-no-leak). **Because strict HMAC verification would also reject the T013 normal-path callbacks, this task MUST update `tests/contract/test_signalwire_transport.py::_build_callback_headers` to compute a VALID HMAC signature over the body with the test signing secret on the normal path** (keep the explicit `forged` signature only in `test_signature_verification_rejects_bad_signature`), otherwise the 7 currently-green T013 assertions regress. **Owns the US1 `conflicting_callbacks_audit.jsonl` write** (T055 only *verifies* it via the US4 dedup test; the write itself lands here).
- [ ] T033 [US1] Implement `src/opencloser/slice3/run_report.py` — `RunReport` builder per FR-036 (Round 2-amended) including telephony_readiness_summary, rejected_auth_callbacks_count, per_writeback_operation_status (reflects DNC-first ordering on `do_not_call`), shadow_stt.{enabled, discrepancy_summary, lane_truncated}, operator_identity {current, original}; writes `artifacts/<session_id>/run_report.json` per [research.md §9](./research.md#9-run-report-file-format--naming)
- [ ] T034 [US1] Implement `src/opencloser/slice3/runner.py` real-call branch — claim queue item via Slice 2 queue-claim semantics → run readiness (US3 stub for now; real check lands in T046) → dial via T026 → bridge audio via T030 → persona deterministic disposition → CRM write-back via T031 → write artifacts via T032 → build run report via T033; wires `cli.py run3` to a real-call invocation end-to-end

**Checkpoint**: User Story 1 fully functional — one real call produces one Dynamics record set and one local artifact set.

---

## Phase 4: User Story 2 — Rehearse the real-call run with zero dial and zero CRM mutation (Priority: P1)

**Goal**: The operator runs the same Slice 3 command in rehearsal / readiness mode and produces a readiness report + planned write-back artifacts WITHOUT placing a SignalWire call OR mutating Dataverse.

**Independent Test**: Run `opencloser run3 --campaign-id <id> --queue-item-id <id>` (no `--real-call`). Confirm in Dataverse (via the fake or live): zero records created or updated. Confirm locally: `artifacts/<session_id>/run_report.json` has `run_mode = "rehearsal"`; `telephony_readiness.json` enumerates each readiness check; `planned_writeback.json` contains the payloads that WOULD have been written.

### Tests for User Story 2

- [ ] T035 [P] [US2] Integration test US2 rehearsal-by-default in `tests/integration/test_us2_rehearsal_default.py` — invocation without `--real-call` places zero SignalWire calls and creates / updates zero Dataverse records (FR-002, SC-002, SC-011)
- [ ] T036 [P] [US2] Integration test US2 planned write-back artifacts in `tests/integration/test_us2_planned_writeback.py` — `planned_writeback.json` contains the same payload content (Phone Call activity, queue-status update, Task when applicable) a real-call run would have sent, with `provider_call_id` marked as not-yet-assigned (US2 acceptance scenario #2)
- [ ] T037 [P] [US2] Integration test US2 readiness failure surfacing in `tests/integration/test_us2_readiness_fail_surfaces.py` — incomplete Dataverse mapping OR missing SignalWire credentials surface in the readiness report and do NOT silently pass (US2 acceptance scenario #3)

### Implementation for User Story 2

- [ ] T038 [US2] Implement rehearsal-mode branch in `src/opencloser/slice3/runner.py` — parses absence of `--real-call` flag → runs readiness → produces planned write-back artifacts via `artifacts/writer.py` → exits with code 0 WITHOUT dialing or mutating Dataverse
- [ ] T039 [US2] Extend `src/opencloser/artifacts/writer.py` with a `planned_writeback.json` writer — emits the planned Phone Call activity, queue-status update, and Task payloads for inspection
- [ ] T040 [US2] Ensure `src/opencloser/slice3/run_report.py` populates `run_mode = "rehearsal"` correctly for non-`--real-call` invocations and omits real-only fields (`real_provider_call_id` = null, `actual_writeback.json` not written)

**Checkpoint**: Operators can safely rehearse Slice 3 against a production-shaped tenant without risk of a real call or mutation.

---

## Phase 5: User Story 3 — Block unsafe or unready real dialing before the SignalWire call starts (Priority: P1)

**Goal**: For each readiness failure category enumerated in FR-009, the real-call run exits before dial with no Phone Call activity, no attempt consumed, and the failing check named in the readiness report.

**Independent Test**: For each of the eight readiness categories (a-h), run the real-call command with that category broken and confirm: exit code 4 OR 5; `telephony_readiness.json` names the failing check; Dataverse shows no Phone Call activity; queue's attempt count is unchanged.

### Tests for User Story 3

- [ ] T041 [P] [US3] Integration test US3 per-readiness-category exit-before-dial in `tests/integration/test_us3_readiness_categories.py` — parameterized over the 8 FR-009 categories: SignalWire credentials missing, source caller-id unauthorized, destination phone non-E.164 (covered by T042 too), callback URLs missing, persona/runtime mapping missing, Dataverse mapping unverified, callback owner mapping missing, eligibility blocked; each case asserts exit code 4, named failing check in readiness report, no dial, no attempt consumed
- [ ] T042 [P] [US3] Integration test US3 E.164 hard pre-dial block in `tests/integration/test_us3_e164_block.py` — missing / blank / malformed destination phone → exit code 4; no SignalWire call placed; no attempt consumed; no Phone Call activity (FR-010, US3 acceptance scenario #3)
- [ ] T043 [P] [US3] Integration test US3 provider-rejected dial in `tests/integration/test_us3_provider_rejected.py` — SignalWire 4xx pre-placement → exit code 5; no attempt consumed; no Phone Call activity (FR-012)
- [ ] T044 [P] [US3] Integration test US3 real-call flag absence in `tests/integration/test_us3_flag_required.py` — invocation without `--real-call` runs in rehearsal mode 100% of the time (SC-011)

### Implementation for User Story 3

- [ ] T045 [P] [US3] Implement `src/opencloser/slice3/readiness.py` — `TelephonyReadinessChecker` with the 8 checks from FR-009; returns a `TelephonyReadinessReport` (data-model §1.9) with per-check `pass` / `fail` + detail string; the `eligibility` check reuses the existing Slice 1 evaluator
- [ ] T046 [US3] Wire the readiness checker into `src/opencloser/slice3/runner.py` so it runs BEFORE any dial and gates the run; on `fail`, write `telephony_readiness.json`, write the blocked-status field via the existing queue-status update operation per FR-011 (where applicable), and exit with code 4
- [ ] T047 [US3] Add provider-4xx → exit code 5 mapping in `src/opencloser/slice3/runner.py` — catches `ProviderRejectedDialError` from T024 / T026 and emits the dial-blocked variant via `crm/dataverse/adapter.py` (queue-status update field-level variant per Round 2 Q8)
- [ ] T048 [US3] Add concurrent-claim → exit code 3 mapping in `src/opencloser/slice3/runner.py` — Round 1 Q5: second invocation observes claim and exits before dial; reuse Slice 2 queue-claim semantics

**Checkpoint**: Every readiness failure category produces a safe, observable exit; no real call ever happens when readiness is incomplete.

---

## Phase 6: User Story 4 — Handle SignalWire callbacks, duplicates, and provider failures idempotently (Priority: P1)

**Goal**: Duplicate, out-of-order, late-after-finalization, and provider-failure callbacks all produce sane normalized outcomes without duplicate Dynamics records.

**Independent Test**: For each of the 8 cases (duplicate status callback, duplicate media callback, out-of-order delivery, provider `failed`/`busy`/`canceled`, mid-conversation hangup, normal completion, transient Dataverse error + retry, orchestrator restart mid-call), drive the path and confirm: exactly one Phone Call activity, at most one Task, one queue-status transition, one attempt increment per session; finalized disposition preserved; callbacks audit log + conflicting-events audit log capture every callback (including duplicates).

### Tests for User Story 4

- [ ] T049 [P] [US4] Integration test US4 duplicate status callback in `tests/integration/test_us4_duplicate_callbacks.py` — same `provider_event_id` delivered twice → no-op for state / attempt count / write-back; recorded in `callbacks_audit.jsonl` with `is_duplicate=true` on the second (US4 acceptance scenario #1)
- [ ] T050 [P] [US4] Integration test US4 out-of-order callbacks in `tests/integration/test_us4_out_of_order.py` — `completed` arriving before `answered` → coherent normalized stream; run report records out-of-order delivery (US4 acceptance scenario #2)
- [ ] T051 [P] [US4] Integration test US4 conflicting-late callbacks in `tests/integration/test_us4_late_after_finalization.py` — callback after finalization → disposition unchanged, no new CRM payload, recorded in `conflicting_callbacks_audit.jsonl` (FR-027)
- [ ] T052 [P] [US4] Integration test US4 provider `failed` / `busy` / `canceled` in `tests/integration/test_us4_provider_failure.py` — no false connected-call Phone Call activity; queue updated; attempt count incremented exactly once (US4 acceptance scenario #3)
- [ ] T053 [P] [US4] Integration test US4 orchestrator restart mid-call in `tests/integration/test_us4_restart_mid_call.py` — answered-but-no-terminal followed by process restart → resume immediately finalizes as `failed` / `live_call_abandonment` per **Round 2 Q6**; queue does not remain `in_progress`; no false connected-call Phone Call activity
- [ ] T054 [P] [US4] Integration test US4 transient Dataverse error + in-run retry in `tests/integration/test_us4_dataverse_retry_resume.py` — bounded retry budget recovers without duplicates (Slice 2 FR-022 reused)

### Implementation for User Story 4

- [ ] T055 [US4] Verify `src/opencloser/transport/signalwire/callbacks.py` (T025) dedup logic via the contract test from T013; verify the `conflicting_callbacks_audit.jsonl` write for late-after-finalization callbacks per FR-027 (the write itself is owned by T032 per /speckit-analyze M1; this US4 task adds the dedup/late-callback integration coverage, not the writer)
- [ ] T056 [US4] Implement live-call abandonment timeout handling in `src/opencloser/slice3/runner.py` per FR-026 — configurable `SLICE3_ABANDONMENT_TIMEOUT_SEC` (default 90s); on timeout finalize as `failed` / `live_call_abandonment`; queue leaves `in_progress`
- [ ] T057 [US4] Create `src/opencloser/slice3/resume.py` — implements the **Round 2 Q6** resume-on-answered-but-no-terminal contract: immediate finalization as `failed` / `live_call_abandonment`; no callback wait, no media reconnect; applies Slice 2 resume contract for any partial write-back

**Checkpoint**: SignalWire delivery anomalies and orchestrator restarts produce idempotent, auditable outcomes.

---

## Phase 7: User Story 5 — Run the live Pipecat / real-time AI conversation while preserving ALF persona safety (Priority: P1)

**Goal**: The live conversation path preserves the canonical AI disclosure, refuses out-of-allowed-claim / PHI / out-of-scope topics, honors immediate opt-out, runs the deterministic Slice 1 disposition precedence (not the live model), and degrades safely on runtime failure.

**Independent Test**: Run the connected-call path against fakes simulating each persona-policy branch — interested caller + callback, interested + email only, not interested, clear opt-out / DNC, wrong number, caller asks for clinical advice, ambiguous caller, caller volunteers PHI. Confirm disclosure on every connected call; persona refuses PHI / out-of-scope; extraction events match Slice 1 schema; final disposition selected by deterministic precedence; persona / runtime / model identity recorded.

### Tests for User Story 5

- [ ] T058 [P] [US5] Integration test US5 disclosure on every connected call in `tests/integration/test_us5_disclosure_every_call.py` — persona's first connected utterance contains the canonical AI-on-behalf-of-Medx disclosure (FR-015, US5 acceptance scenario #1); applies even when caller silent or non-acknowledging (Round 1 Q1)
- [ ] T059 [P] [US5] Integration test US5 disallowed-claim escalation in `tests/integration/test_us5_disallowed_claim.py` — live model attempts out-of-allowed-claim utterance → persona escalates `needs_human_review` with the matching reason; conversation ends safely (US5 acceptance scenario #2)
- [ ] T060 [P] [US5] Integration test US5 clear opt-out → `do_not_call` in `tests/integration/test_us5_opt_out.py` — persona observes Slice 1 DNC trigger → finalize as `do_not_call`; Dataverse DNC / opt-out + queue-status fields updated; no callback or review Task (US5 acceptance scenario #3, FR-024)
- [ ] T061 [P] [US5] Integration test US5 deterministic disposition precedence in `tests/integration/test_us5_deterministic_disposition.py` — live model emits an `ExtractionEvent` whose extracted state would deterministically map to disposition X; assert final disposition equals deterministic-rule output X, NOT a live-model-chosen value (FR-014, SC-014)
- [ ] T062 [P] [US5] Integration test US5 runtime degradation triggers in `tests/integration/test_us5_degradation_triggers.py` — for each of the three triggers from FR-013 Round 1 Q4: (a) `RealtimeProviderError`, (b) `PipecatRuntimeError`, (c) silence-after-connection timeout — assert correct disposition mapping (post-connected → `needs_human_review` / `script_truncated`; pre-connected (a)/(b) → `failed` with runtime-failure reason)
- [ ] T063 [P] [US5] Integration test US5 caller-volunteered PHI in `tests/integration/test_us5_phi_volunteered.py` — caller emits PHI utterance → persona escalates `needs_human_review` with `phi_collection_risk`; the PHI utterance is tagged and redacted in all four artifact types (transcript, summary, shadow transcript, shadow discrepancy records) BEFORE write per **Round 2 Q11**

### Implementation for User Story 5

- [ ] T064 [P] [US5] Implement `src/opencloser/runtime/pipecat/degradation.py` — detector for the three FR-013 triggers (provider error / Pipecat crash / configurable silence-after-connection timeout); fires the correct exception type into `runtime/pipecat/runtime.py` (T030); silence timeout default from `SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC=30`
- [ ] T065 [US5] Wire degradation triggers into `src/opencloser/runtime/pipecat/runtime.py` (T030) with the disposition mapping from [contracts/pipecat-runtime.md](./contracts/pipecat-runtime.md) Required-Behavior #5: pre-connected `failed`+runtime-failure reason; post-connected `needs_human_review` / `script_truncated`
- [ ] T066 [P] [US5] Extend `src/opencloser/persona/extraction.py` with PHI-volunteered detection hook — when the live model's extraction event or the caller's utterance contains a PHI signal, emit `phi_collection_risk` escalation event AND invoke the redaction layer's PHI tag-and-redact pass (from T009) on the in-flight transcript / summary / shadow transcript / shadow discrepancy buffer before any artifact write per Round 2 Q11
- [ ] T067 [US5] Wire the persona module's escalation events (including `phi_collection_risk` and the Slice 1 enumerated set) from `src/opencloser/persona/escalation.py` into `src/opencloser/core/orchestrator.py`'s deterministic disposition precedence so the live model cannot override the disposition per FR-014

**Checkpoint** (MVP COMPLETE): All five P1 user stories are independently functional. The Slice 3 demonstrable loop now works end-to-end with rehearsal + real-call modes, full readiness gates, idempotent callback handling, and a safe live conversation path. Ready for pilot demo.

---

## Phase 8: User Story 6 — Record shadow STT discrepancies without blocking the live call (Priority: P2)

**Goal**: A non-blocking shadow STT lane listens to the same caller audio, emits discrepancy events for high-value fields, escalates uncertain discrepancies to `needs_human_review`, and survives lane failure without affecting the live call.

**Independent Test**: Run a connected call with `--shadow-stt`. Confirm the live call's turn cadence is statistically indistinguishable from a `--no-shadow-stt` run (SC-013); shadow transcript + discrepancy records honor the same retention policy as the live transcript; uncertain discrepancies create exactly one `needs_human_review` review Task with `shadow_stt_discrepancy` reason; `--no-shadow-stt` still completes the demonstrable loop.

### Tests for User Story 6

- [ ] T068 [P] [US6] Contract test for shadow STT lane in `tests/contract/test_shadow_stt_lane.py` — implements all 13 assertions from [contracts/shadow-stt-lane.md](./contracts/shadow-stt-lane.md) (non-blocking, asyncio.Task separation, high-value fields, no CRM write, in-window uncertain escalates, benign no-escalation, late shadow → truncated event, disabled completes loop, lane failure does not abort, retention parity, redaction covers shadow artifacts, PHI redacts shadow, run report states enabled flag)
- [ ] T069 [P] [US6] Integration test US6 non-blocking guarantee in `tests/integration/test_us6_non_blocking.py` — paired runs with shadow enabled vs. disabled; assert live turn cadence p95 latency delta ≤ `[performance].shadow_lane_p95_latency_tolerance_ms` from `config/slice3.toml` (default 50 ms; pinned per `/speckit-analyze` A1 remediation 2026-05-25). The spec defers the numeric threshold (spec §Deferred to Implementation Plan → "Performance and latency targets"); the config value is the CI default and is deployment-configurable. Satisfies SC-013.
- [ ] T070 [P] [US6] Integration test US6 uncertain discrepancy escalation in `tests/integration/test_us6_uncertain_escalation.py` — shadow lane emits `uncertain` discrepancy inside the grace window → session disposition becomes `needs_human_review` / `shadow_stt_discrepancy`; exactly one review Task created (FR-031)
- [ ] T071 [P] [US6] Integration test US6 grace window in-window + truncation in `tests/integration/test_us6_grace_window.py` — `SLICE3_GRACE_WINDOW_SEC=3`: case 1 shadow finishes in 1s → participates in disposition; case 2 shadow takes 10s → `shadow_lane_truncated.json` written; disposition unchanged; no new CRM payload per **Round 2 Q7**
- [ ] T072 [P] [US6] Integration test US6 shadow disabled in `tests/integration/test_us6_disabled.py` — `SLICE3_SHADOW_STT_PROVIDER=disabled` OR `--no-shadow-stt` → Slice 3 demonstrable loop completes; run report records `shadow_stt.enabled = false` (FR-032)
- [ ] T073 [P] [US6] Integration test US6 lane failure does not abort live call in `tests/integration/test_us6_lane_failure.py` — shadow lane raises mid-call → live call still finalizes normally; run report records shadow-lane failure (FR-029)

### Implementation for User Story 6

- [ ] T074 [P] [US6] Implement `src/opencloser/shadow_stt/lane.py` — `ShadowSTTLane` implementation; consumes `tee`'d audio from `transport/signalwire/callbacks.py` `SignalWireMediaInput` boundary per [research.md §6](./research.md#6-shadow-stt-lane-topology); runs in separate `asyncio.Task` so orchestrator never `await`s it before finalization
- [ ] T075 [P] [US6] Implement `src/opencloser/shadow_stt/discrepancy.py` — high-value field comparison + policy classification (benign vs uncertain) per FR-030 and the JSON policy from T004; emits `DiscrepancyEvent` for the orchestrator to consume; covers the 7 logical high-value categories from FR-030 stored as 9 atomic enum values per [data-model.md §1.7](./data-model.md) storage normalization
- [ ] T076 [P] [US6] Implement `src/opencloser/shadow_stt/truncation.py` — `ShadowLaneTruncatedEvent` writer for late shadow output that arrives after the post-finalization grace window per Round 2 Q7; writes `shadow_lane_truncated.json`; audit-only — never mutates the finalized disposition or emits a new CRM payload
- [ ] T077 [US6] Implement `src/opencloser/slice3/grace_window.py` — post-finalization grace window for CRM write-back per Round 2 Q7; configurable `SLICE3_GRACE_WINDOW_SEC` (default 3s); holds write-back until either a `DiscrepancyEvent` arrives (then may escalate to `shadow_stt_discrepancy`) or the window elapses (then write back without it; any later shadow output triggers T076)
- [ ] T078 [US6] Wire shadow lane into `src/opencloser/slice3/runner.py` — start lane at `connected` event; stop lane at session finalization; never await lane before finalization (FR-029); on `--no-shadow-stt` OR `SLICE3_SHADOW_STT_PROVIDER` unset / `"disabled"`, skip lane entirely
- [ ] T079 [US6] Extend `src/opencloser/redaction/layer.py` (T009) to apply default-on redaction to the shadow transcript file AND each shadow discrepancy record's `live_value` / `shadow_value` fields per FR-033 / FR-034 / Round 2 Q10; pointer metadata excluded

**Checkpoint**: Shadow STT runs without slowing the live call, escalates uncertain discrepancies, and writes audit-only truncation events without affecting CRM write-back.

---

## Phase 9: User Story 7 — Recover from transient provider or CRM failures without duplicating records (Priority: P2)

**Goal**: Transient Dataverse errors, transient SignalWire callback delivery failures, partial write-backs, and orchestrator restarts all recover without duplicate Phone Call activities / Tasks / queue-status transitions / attempt-count increments — including multi-operator resume scenarios.

**Independent Test**: For each transient failure mode, drive the path and confirm Dynamics ends with exactly one Phone Call activity, at most one Task, one queue-status transition, one attempt-count increment per session. For multi-operator resume: operator A starts a partially-written-back run; operator B resumes; assert both operator identities appear in the run report ("resumed by B, original operator A") and the resume requires `--real-call` for any mutation.

### Tests for User Story 7

- [ ] T080 [P] [US7] Integration test US7 transient Dataverse error on Phone Call activity in `tests/integration/test_us7_transient_phone_call.py` — bounded in-run retry recovers without duplicate Phone Call activity (FR-022)
- [ ] T081 [P] [US7] Integration test US7 resume after retry budget exhausted in `tests/integration/test_us7_resume_partial.py` — re-invocation resumes only missing writes; no duplicate of any already-written record
- [ ] T082 [P] [US7] Integration test US7 SignalWire callback retry dedup in `tests/integration/test_us7_callback_retry.py` — second delivery treated as duplicate; no-op for state / attempt / write-back; recorded in audit log
- [ ] T083 [P] [US7] Integration test US7 orchestrator restart between `completed` callback and write-back in `tests/integration/test_us7_restart_between_complete_and_writeback.py` — resume completes missing CRM writes; recorded `provider_call_id` preserved
- [ ] T084 [P] [US7] Integration test US7 review Task transient failure + retry in `tests/integration/test_us7_review_task_retry.py` — `needs_human_review` outcome where review Task create fails transiently → retry succeeds with exactly one review Task with correct reason code
- [ ] T085 [P] [US7] Integration test US7 multi-operator resume in `tests/integration/test_us7_multi_operator_resume.py` — operator A starts → partial write-back → operator B resumes with `--real-call --operator-id B`; assert `operator_identity = {current: B, original: A}` on run report (**Round 2 Q12**) and resume completes the missing writes
- [ ] T086 [P] [US7] Integration test US7 resume without flag → rehearsal in `tests/integration/test_us7_resume_no_flag.py` — `--resume` without `--real-call` runs in rehearsal mode; no mutation; surfaces planned writes in run report (**Round 2 Q13**)

### Implementation for User Story 7

- [ ] T087 [US7] Extend `src/opencloser/slice3/resume.py` (T057) to preserve original operator identity on session + audit and record resuming operator separately on run report per Round 2 Q12 ("resumed by X, original operator Y")
- [ ] T088 [US7] Extend `src/opencloser/slice3/resume.py` (T057) to require `--real-call` on every resume invocation that performs a Dataverse mutation per Round 2 Q13; absence on resume runs in rehearsal mode with planned-write surfacing
- [ ] T089 [US7] Wire DNC-first ordering into `src/opencloser/crm/dataverse/adapter.py` (T031) `assemble_writeback` — on disposition `do_not_call`, return `QueueStatusUpdateVariant.DNC` step FIRST per Round 2 Q14; idempotency-key stamping prevents duplicate DNC writes on resume

**Checkpoint**: Every transient failure path recovers with the no-duplicate guarantees from SC-008. All seven user stories independently testable.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Polish, fixtures, documentation, coverage, and constitution-sync verification across all stories.

- [ ] T090 [P] Add per-module unit tests in `tests/unit/slice3/`, `tests/unit/runtime/pipecat/`, `tests/unit/transport/signalwire/`, `tests/unit/shadow_stt/` — preserve the existing per-module isolation marker pattern from `pyproject.toml` `tool.pytest.ini_options.markers`
- [ ] T091 [P] Add SignalWire webhook fixtures in `tests/fixtures/signalwire/` — JSON payloads for each status callback (ringing, answered, in_progress, completed, no_answer, voicemail, busy, canceled, failed) plus media callback connect / hangup / error
- [ ] T092 [P] Add Pipecat audio fixtures in `tests/fixtures/pipecat/` — `*.wav` recorded test audio for each persona-policy branch (interested + callback, interested + email, not interested, opt-out, wrong number, PHI volunteered, ambiguous)
- [ ] T093 [P] Add shadow STT fixtures in `tests/fixtures/shadow_stt/` — discrepancy policy fixtures, shadow transcript fixtures, expected-discrepancy fixtures
- [ ] T094 Create `docs/slice3/demo-evidence-checklist.md` per [research.md §13](./research.md#13-pre-pilot-demo-evidence-checklist) — enumerates the artifacts an operator MUST collect for a pilot demo and maps each to the FR / SC it satisfies
- [ ] T095 Update `README.md` with Slice 3 invocation examples (rehearsal + real-call); reference `specs/003-real-call-real-crm/quickstart.md` for the full operator walkthrough
- [ ] T096 [P] Extend `pyproject.toml` `[tool.pytest.ini_options]` markers + `[tool.ruff]` config to cover the new packages (`runtime/`, `transport/signalwire/`, `shadow_stt/`, `slice3/`) without weakening the existing 90% coverage floor
- [ ] T097 Extend `tests/integration/test_constitution_sync.py` (Slice 1/2 sync check) to validate the Slice 3 CLAUDE.md SPECKIT marker points to `specs/003-real-call-real-crm/plan.md` and the Slice 3 plan's Constitution Check still passes all 5 principles
- [ ] T098 Run `pytest --cov=src/opencloser --cov-report=term-missing` and confirm: new packages (`runtime/pipecat/`, `transport/signalwire/`, `shadow_stt/`, `slice3/`) each meet the 90% coverage floor; total coverage ≥ 90%
- [ ] T099 Run the [quickstart.md](./quickstart.md) operator walkthrough end-to-end against fakes as a final acceptance smoke test — every exit code (0 – 7) reachable, every artifact written, every demo-evidence checklist item collectable
- [ ] T100 [P] Integration test for FR-033 transcript retention modes in `tests/integration/test_retention_modes.py` — per `/speckit-analyze` G1 remediation 2026-05-25. Three cases: (a) `retention.mode = "full_with_redaction"` → `transcript.txt` written and redacted; (b) `retention.mode = "summary_only"` → no `transcript.txt`, session-result still carries redacted `summary` + `retention_mode` + `persona_version` + `runtime_identity`; (c) `retention.mode = "pointer_only"` → only the machine-readable pointer artifact persisted, pointer metadata is NOT redacted (must stay machine-readable per Round 2 Q10). For each mode, also exercise resume: re-invoke the CLI on the same session and confirm resume completes the missing CRM writes without requiring a full transcript file (spec edge case "Resume after a real call when retention policy disables the transcript artifact"). Covers FR-033 + FR-034 (shadow STT retention parity) edge cases not previously test-covered.
- [ ] T101 [P] Contract test for SC-016 Slice 1 / Slice 2 preservation in `tests/contract/test_slice12_preservation.py` — per `/speckit-analyze` G2 remediation 2026-05-25. Boundary-inspection contract test verifying the Slice 1 / Slice 2 contracts SC-016 demands "verified by contract tests / boundary inspection": (1) `NormalizedResult` field set + types unchanged vs. Slice 1 (only sanctioned changes: `mock_provider_call_id` → `provider_call_id` read alias, additive `shadow_stt_discrepancy` reason); (2) per-disposition write-back emission map (Phone Call activity / queue-status / Task) unchanged for each Slice 1 disposition; (3) per-disposition `new_status` mapping unchanged; (4) idempotency-key stamping field, format, and pre-query behavior unchanged (FR-021); (5) bounded retry parameters (initial + 3 retries, 1s/2s/4s backoff, `Retry-After` honored, 30s cap) unchanged (FR-022); (6) resume re-invocation contract unchanged (FR-022); (7) Dataverse metadata two-phase verification unchanged; (8) high-confidence value preservation unchanged. Implemented as a diff against frozen Slice 1 / Slice 2 contract fixtures; failure = an unsanctioned Slice 3 change to an inherited contract.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1, T001-T004)**: No dependencies — can start immediately.
- **Foundational (Phase 2, T005-T012)**: Depends on Setup. T005 (SQLite schema) is the single sequential blocker for T006 (models reference schema). T006-T012 can mostly parallelize after T005.
- **User Stories (Phase 3+)**: All depend on Foundational complete.
- **Polish (Phase 10)**: Depends on US1-US7 substantially complete.

### User Story Dependencies (Slice 3 specifics)

- **US1 (P1, MVP)**: Depends on Foundational. Drives most of the implementation surface — the runner end-to-end, the SignalWire transport, the Pipecat runtime, the CRM write-back extensions. US1's implementation tasks (T022-T034) build the substrate every later story extends. Other stories can begin in parallel with US1 once their specific extension points are stubbed.
- **US2 (P1, rehearsal)**: Depends on Foundational + US1 T034 (runner) being importable. US2 adds the rehearsal-mode branch + planned-writeback artifact.
- **US3 (P1, readiness)**: Depends on Foundational. US3's readiness checker (T045) is wired INTO US1's runner (T046) — US1 stub'd it; US3 fully implements it.
- **US4 (P1, idempotent callbacks)**: Depends on US1 T025 (callbacks normalization) + T031 (Dataverse adapter). US4 verifies + extends the dedup contracts.
- **US5 (P1, persona safety)**: Depends on US1 T030 (Pipecat runtime) and T010 (escalation reason). US5 adds the degradation triggers (T064) and PHI handling (T066-T067).
- **US6 (P2, shadow STT)**: Depends on US1 T026 (transport adapter) + T030 (runtime) + T032 (artifacts writer) + T009 (redaction layer). US6's grace window (T077) extends US1's runner (T034) at the finalization → write-back boundary.
- **US7 (P2, recovery)**: Depends on US1 T031 (Dataverse adapter) + T034 (runner). US7's resume coordinator (T087-T088) extends the runner; DNC-first (T089) extends T031.

### Within Each User Story

- Contract tests (T013-T016, T068) MUST be written and FAIL before the implementation tasks they test.
- Integration tests for each US MUST be written and FAIL before the US's implementation tasks.
- Models / Protocols before services. Services before runner integration.
- Story complete (all integration tests pass) before moving to the next priority.

### Parallel Opportunities

- All Setup tasks (T002, T003, T004) marked [P] can run in parallel after T001.
- All Foundational tasks marked [P] (T006, T007, T008, T009, T010) can run in parallel after T005.
- Within US1: T013–T016 can run in parallel (contract tests, different files); T017-T021 can run in parallel (integration tests, different files); T022, T023 can run in parallel (leaf signalwire/ files); T027, T028 can run in parallel (leaf pipecat/ files); T030, T031, T032, T033 sequential after their deps.
- Within US6: T068-T073 (tests) all parallel; T074, T075, T076 (lane / discrepancy / truncation, different files) all parallel.
- Across stories (with team capacity): once Foundational is done, US3 / US4 / US5 / US6 / US7 implementation can proceed in parallel by different developers, each gating on their specific US1 dependencies as listed above.

---

## Parallel Example: User Story 1 (MVP)

```bash
# Launch all US1 contract + integration tests in parallel (different files, no deps):
Task: "Contract test for SignalWire transport in tests/contract/test_signalwire_transport.py"
Task: "Contract test for rejected-by-authentication audit log in tests/contract/test_rejected_auth_audit_log.py"
Task: "Contract test for Pipecat runtime in tests/contract/test_pipecat_runtime.py"
Task: "Contract test for CRM write-back Slice 3 in tests/contract/test_crm_writeback_slice3.py"
Task: "Contract test for opencloser run3 CLI in tests/contract/test_cli_slice3.py"
Task: "Integration test US1 interested_callback_requested in tests/integration/test_us1_real_call_callback.py"
Task: "Integration test US1 interested_email_captured in tests/integration/test_us1_real_call_email.py"
Task: "Integration test US1 terminal states in tests/integration/test_us1_real_call_terminal_states.py"

# Launch parallel SignalWire transport leaf modules:
Task: "Implement transport/signalwire/signature.py (HMAC-SHA256 verification)"
Task: "Implement transport/signalwire/errors.py (exception hierarchy)"

# Launch parallel Pipecat runtime leaf modules:
Task: "Implement runtime/pipecat/identity.py (runtime/model identity recording per FR-016)"
Task: "Implement runtime/pipecat/provider.py (RealtimeAIProvider adapter + fake)"
```

---

## Implementation Strategy

### MVP First (P1 stories — US1 through US5)

1. Complete Phase 1: Setup (T001-T004).
2. Complete Phase 2: Foundational (T005-T012). **CRITICAL** — blocks all stories.
3. Complete Phase 3: US1 (T013-T034) end-to-end. **VALIDATE**: run the US1 Independent Test — one real call moves one queue item through the loop.
4. Complete Phase 4: US2 (T035-T040). **VALIDATE**: rehearsal-mode invocation places zero calls / zero mutations.
5. Complete Phase 5: US3 (T041-T048). **VALIDATE**: each readiness category blocks before dial.
6. Complete Phase 6: US4 (T049-T057). **VALIDATE**: callback duplicates / out-of-order / restart all produce idempotent results.
7. Complete Phase 7: US5 (T058-T067). **VALIDATE**: persona safety preserved on every connected call.
8. **MVP COMPLETE** — the Slice 3 demonstrable loop works end-to-end with all five P1 stories. Pilot-ready.

### Incremental P2 additions

9. Complete Phase 8: US6 (T068-T079). **VALIDATE**: shadow STT runs without slowing the live call; uncertain discrepancies escalate.
10. Complete Phase 9: US7 (T080-T089). **VALIDATE**: multi-operator resume preserves audit chain.

### Polish

11. Complete Phase 10: T090-T099. Final coverage + constitution-sync + quickstart smoke test.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (synchronization point).
2. Once Foundational is done:
   - Developer A: US1 — the largest story; produces the substrate.
   - Developer B: US2 + US3 (smaller, depend on US1's runner skeleton).
   - Developer C: US5 — Pipecat runtime + persona safety (depends on US1's runtime skeleton).
   - Developer D: US4 + US7 — callback idempotency + recovery (depend on US1's transport + adapter).
   - Developer E: US6 — shadow STT (depends on US1's runtime + transport).
3. Stories complete and integrate independently; final integration testing in Phase 10.

---

## Notes

- **Total tasks**: 102 — Setup 4 + Foundational 8 + US1 23 + US2 6 + US3 8 + US4 9 + US5 10 + US6 12 + US7 10 + Polish 12. (US1 grew from 22 → 23 with T013b per `/speckit-analyze` L1 remediation 2026-05-25; Polish grew from 10 → 12 with T100 [G1 retention modes] + T101 [G2 SC-016 preservation contract] per `/speckit-analyze` 2026-05-25.)
- **Tests REQUIRED** per Constitution Principle IV and the spec's testing-strategy — Slice 3 changes core queue / CRM write-back / duplicate-event / eligibility / persona-result / safety behavior. 64 contract tests (across the 6 contract files) + 30+ integration tests + per-module unit tests.
- **Coverage target**: ≥90% per existing `pyproject.toml` configuration; new packages must each meet this floor.
- **MVP scope**: the five P1 stories (US1-US5) deliver the complete demonstrable Slice 3 loop. US6 + US7 are P2 enhancements that harden audit posture and recovery.
- **Round 1 + Round 2 clarifications fully wired in**: Q1 disclosure-ack (T058), Q2 raw-audio deferred (out of scope, no task), Q3 operator identity local (T033), Q4 degradation triggers (T064, T065), Q5 concurrent claim (T048), Q6 resume-abandonment (T053, T057), Q7 grace window (T071, T077, T076), Q8 four-op preservation (T031), Q9 rejected-auth audit log (T022, T032, T033), Q10 redaction scope (T009, T079), Q11 PHI tag-and-redact (T009, T066, T067), Q12 multi-operator resume (T085, T087), Q13 flag on every mutation (T044, T086, T088), Q14 DNC-first (T020, T089).
- **[P] tasks** = different files, no dependencies on incomplete tasks.
- **[Story] label** maps task to specific user story for traceability.
- **File paths are absolute** relative to repository root; all paths exist in the [plan.md Project Structure](./plan.md#project-structure).
- Verify contract + integration tests FAIL before implementing.
- Commit after each task or logical group; the existing `before_implement` hook from `.specify/extensions.yml` will offer auto-commit.
- Stop at any checkpoint (especially the MVP COMPLETE checkpoint after US5) to validate stories independently before continuing.
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence beyond the documented US1-stub-pattern.
