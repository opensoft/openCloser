# Phase 0 Research: Slice 3 — Real Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Created**: 2026-05-25

Each decision below resolves a dependency choice, integration pattern, or deferred-to-plan
item not already pinned by the spec. The spec's 2026-05-25 clarification sessions (Round 1
×5 + Round 2 ×9) already resolved every behavioral unknown that would otherwise be a
`NEEDS CLARIFICATION` — no such marker remained entering Phase 0.

---

## 1. SignalWire outbound dial + callback surface

- **Decision**: Use the `signalwire` Python SDK (`signalwire>=2.0,<3.0`) for the outbound dial
  request (`Client.calls.create(...)`) and the SWML dial plan. Use `httpx` (already in the
  Slice 2 dep set) for the signature-verification side channel on inbound status / media
  callbacks. The callback receiver is a small `FastAPI`-style ASGI app embedded in the
  Slice 3 runner — but we run it through `uvicorn` only when the CLI invocation enters
  real-call / write-enabled mode (rehearsal mode does not bind a port). Constitution §Architecture
  names FastAPI in the default stack; this is the first slice that activates that part.
- **Rationale**: The `signalwire` SDK matches SignalWire's documented Python entrypoint and
  isolates SWML / TwiML generation behind a vendor-vetted surface. Embedding a tiny callback
  receiver in-process keeps Slice 3 single-process and avoids introducing Celery / Redis /
  a job queue (constitution §Architecture explicitly forbids those for the MVP).
- **Alternatives rejected**: raw `httpx` against the SignalWire REST API (re-implements SWML
  / TwiML and signature verification ourselves); standing up a separate webhook receiver
  service (multi-process, adds operator burden); using Twilio / a multi-provider abstraction
  (forbidden by constitution §Architecture — "MUST avoid... multiple telephony providers").

## 2. SignalWire signature verification + rejected-by-authentication audit log

- **Decision**: Verify SignalWire's documented HMAC-SHA256 signature header on every inbound
  callback (status + media) using a deployment-provided shared signing secret loaded from
  `SIGNALWIRE_SIGNING_SECRET`. Verification happens in `transport/signalwire/signature.py`
  before any orchestrator hand-off. A failed-signature callback is rejected with HTTP `401`
  and recorded in a distinct `rejected_auth_callbacks` SQLite table with columns
  `(received_at, source_metadata_json, http_status)` — explicitly NOT the verification secret
  and NOT the callback body content. The run report (FR-036) surfaces a count of rejected-auth
  callbacks per session.
- **Rationale**: Round 2 Q9 pinned Option B (distinct audit log, no secret, no body, run-report
  count). HMAC-SHA256 is SignalWire's documented signature mechanism. A distinct table makes
  the count trivially queryable and keeps the existing `callbacks_audit_log` keyed by
  `(session_id, provider_event_id)` semantics clean.
- **Alternatives rejected**: silent rejection (Round 2 Q9 Option A — loses operator-visible
  signal); shared audit log with a `rejected_by_authentication` tag (Round 2 Q9 Option C —
  loses duplicate / forgery distinction); deferring the policy to deployment (Round 2 Q9
  Option D — pushes a baseline security policy out of the spec).

## 3. Real-time AI provider surface

- **Decision**: Deployment-configured provider selected by `SLICE3_REALTIME_PROVIDER` env var.
  The Pipecat pipeline (§5) consumes a thin `RealtimeAIProvider` protocol with three methods:
  `start_session(session_context) → SessionHandle`, `stream_audio(handle, audio_chunk) →
  AsyncIterator[AudioChunk | ExtractionEvent]`, `end_session(handle)`. The first development
  /CI fake implementation is `runtime/pipecat/provider_fake.py`. The first production-supported
  provider's adapter is chosen at deploy time; the provider name + model version are recorded
  on every session per FR-016. Credentials come from env vars (`SLICE3_REALTIME_API_KEY` and
  provider-specific variants); never logged.
- **Rationale**: The spec explicitly defers the specific provider to deployment configuration
  (`Deferred to Implementation Plan → Runtime and live-model details`). Wrapping the provider
  behind a 3-method protocol keeps `runtime/pipecat/` provider-agnostic and matches the
  Slice 1 `Persona` / `CallTransport` contract style. The fake implementation lets CI exercise
  the entire Pipecat pipeline without burning real-provider tokens.
- **Alternatives rejected**: hardcoding a specific provider in `runtime/pipecat/runtime.py`
  (violates constitution §III boundary separation); requiring the provider's SDK directly in
  `core/` or `orchestrator/` (same violation); deferring all integration to runtime without a
  protocol shape (makes contract tests impossible).

## 4. Shadow STT provider and discrepancy policy

- **Decision**: Deployment-configured shadow STT provider behind a `ShadowSTTProvider`
  protocol with two methods: `transcribe(audio_stream) → AsyncIterator[TranscriptSegment]`
  and `close(session_id)`. Provider selected by `SLICE3_SHADOW_STT_PROVIDER` env var; if
  the env var is unset OR equal to `"disabled"`, the shadow lane is no-op and FR-032's
  "Slice 3 demonstrable loop completes without it" guarantee is satisfied. Discrepancy
  policy is a deployment-configurable JSON file `config/shadow_stt_discrepancy_policy.json`
  with two sections: `benign_rules` (case-insensitive equality, whitespace normalization,
  phonetic-spelling tolerance for names) and `uncertain_rules` (semantically different
  emails, callback windows that differ by > 1 day, opt-out vs. interest disagreement).
- **Rationale**: The spec defers both provider choice and discrepancy policy to deployment
  (§Deferred to Implementation Plan → Shadow STT details). A protocol-bounded provider
  matches the same pattern as §3. Splitting the policy into `benign_rules` (silent) and
  `uncertain_rules` (escalation → `shadow_stt_discrepancy` review Task per FR-031) keeps
  the policy file inspectable and operator-editable without code changes.
- **Alternatives rejected**: hardcoded policy (operators cannot tune false-positive rate);
  defaulting shadow STT to enabled (forces a provider dependency on every deployment);
  policy in TOML (less natural for nested rule structures than JSON).

## 5. Pipecat pipeline topology

- **Decision**: Single-pipeline topology with three stages connected via Pipecat's standard
  `FrameProcessor` chain:
  1. `SignalWireMediaInput` (Pipecat `Transport` subclass adapting our SignalWire
     `media_stream` callback to Pipecat audio frames).
  2. `RealtimeAIProviderBridge` (Pipecat `FrameProcessor` that delegates to the configured
     `RealtimeAIProvider` from §3; emits `TranscriptSegment` and `ExtractionEvent` frames).
  3. `PersonaSink` (delivers transcript + extraction events to the orchestrator's persona
     module so the deterministic disposition precedence selects the final disposition per
     FR-014; the live model never sets the disposition).
  Audio codec: μ-law 8 kHz (matches SignalWire's default voice codec). Turn-taking: VAD-driven
  per the real-time AI provider's built-in turn-taking, with a fallback silence-after-speech
  threshold of 800 ms.
- **Rationale**: A linear pipeline matches Pipecat's idiomatic shape and keeps the boundary
  between SignalWire (transport) and the real-time AI provider (runtime) crisp.
  `PersonaSink` is the single point where Pipecat / runtime concerns hand off to the
  persona module — preserving constitution §III boundary separation.
- **Alternatives rejected**: branching pipelines (one for live, one for shadow STT — Pipecat
  supports it, but the shadow lane runs OUTSIDE Pipecat in `shadow_stt/lane.py` so the live
  pipeline can stay simple and non-blocking-by-construction); custom audio runtime (re-invents
  Pipecat's value).

## 6. Shadow STT lane topology

- **Decision**: The shadow lane consumes the same caller audio via a `tee` at the
  `SignalWireMediaInput` boundary (one branch into the Pipecat pipeline, one branch into
  `shadow_stt/lane.py`). The lane runs in a separate `asyncio.Task` and feeds audio frames
  into the configured `ShadowSTTProvider` (§4). The lane writes its transcript to
  `artifacts/<session_id>/shadow_transcript.txt` (subject to redaction per FR-033 / FR-034)
  and emits discrepancy events to `shadow_stt/discrepancy.py` for policy classification.
  The orchestrator MUST NOT await the lane's `asyncio.Task` before finalization (FR-029) —
  see §7 for the grace-window mechanism.
- **Rationale**: A `tee` at the transport boundary is the simplest construction that
  satisfies "shadow STT MUST listen to the same caller audio" (FR-028) without coupling the
  shadow lane to Pipecat internals. Running the lane in a separate `asyncio.Task` (not a
  thread or subprocess) keeps single-process scheduling simple and matches the rest of the
  CLI's async model.
- **Alternatives rejected**: running shadow STT inside the Pipecat pipeline (couples the
  shadow lane's failure modes to the live conversation path — violates FR-029 non-blocking
  guarantee by construction); separate subprocess (over-engineered for one-item-per-invocation).

## 7. Timeouts and grace window (live-call abandonment, silence-after-connection, post-finalization)

- **Decision**: Three distinct, deployment-configurable timeouts:
  - **`SLICE3_ABANDONMENT_TIMEOUT_SEC`** (default `90`): live-call abandonment per FR-026
    (no normalized terminal event received). Round 2 Q6: resume on `answered`-but-no-terminal
    finalizes immediately as `failed`/`live_call_abandonment` regardless of this timeout.
  - **`SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC`** (default `30`): live-runtime
    degradation trigger per FR-013 (Round 1 Q4). Fires only AFTER `connected`; finalizes
    as `needs_human_review` / `script_truncated`.
  - **`SLICE3_GRACE_WINDOW_SEC`** (default `3`): post-finalization grace window per FR-029
    (Round 2 Q7). The orchestrator finalizes the session immediately on terminal event but
    holds the CRM write-back for this window so a late shadow-STT discrepancy MAY participate.
    Configurable to `0` (write-back immediately; shadow always becomes `shadow_lane_truncated`)
    or any positive integer (no spec-mandated maximum; deployment may bound it).
  Defaults documented in `config/slice3.toml` and referenced by `slice3/runner.py`.
- **Rationale**: Round 2 Q7 picked Option B (configurable grace window). The three timeouts
  govern strictly different states (in-flight call without terminal event; live runtime
  silent while connected; post-finalization shadow drain) and MUST be tracked independently
  per the spec. Defaults are conservative pilot values — production deployments will tune them.
- **Alternatives rejected**: collapsing abandonment + silence into one timeout (different
  triggers, different dispositions — would silently merge two distinct failure modes);
  hardcoding the grace window (Round 2 Q7 Option A — loses the discrepancy-participation
  affordance; Round 2 Q7 Option C — violates FR-029 by allowing blocking finalization).

## 8. CLI flag and configuration-file shape

- **Decision**: Extend the existing `opencloser` Typer CLI with a `run3` subcommand that
  takes the following options:
  - `--campaign-id <id>` (required): campaign selector
  - `--queue-item-id <id>` (required): queue-item selector
  - `--real-call` / `--write` (required for any Dataverse mutation; absence → rehearsal
    mode; required again on every resume invocation per Round 2 Q13)
  - `--shadow-stt / --no-shadow-stt` (defaults to deployment config from `config/slice3.toml`)
  - `--operator-id <id>` (optional; defaults to `$USER` per Round 1 Q3 + Round 2 Q12)
  - `--resume <session_id>` (optional; resumes the named session; requires `--real-call`
    for any Dataverse mutation per Round 2 Q13)
  - `--config <path>` (optional; defaults to `config/slice3.toml`)
  Non-secret config lives in `config/slice3.toml`; secrets live in env vars only.
- **Rationale**: Matches the Slice 2 CLI style (`opencloser run2`). The `--real-call` /
  `--write` choice is required on EVERY mutating invocation (no sticky / session-inherited
  promotion) — a per-invocation gate that operators must consciously supply, satisfying the
  Round 2 Q13 safety posture.
- **Alternatives rejected**: a single `opencloser run` command that auto-detects slice
  (couples slices and breaks the Slice 1 / Slice 2 / Slice 3 isolation that the constitution
  thin-slice principle requires); env-var-driven real-call flag (loses the per-invocation
  operator opt-in signal).

## 9. Run-report file format + naming

- **Decision**: One JSON file per session at `artifacts/<session_id>/run_report.json`. Schema:
  ```json
  {
    "session_id": "...",
    "run_mode": "rehearsal" | "real_call",
    "operator_identity": {"current": "...", "original": "..."},
    "real_provider_call_id": "..." | null,
    "persona_version": "...",
    "runtime_identity": {"runtime": "pipecat", "version": "...", "provider": "...", "model": "..."},
    "final_disposition": "...",
    "human_review_reason": "..." | null,
    "blocked_reason": "..." | null,
    "telephony_readiness_summary": [{"check": "...", "result": "pass" | "fail", "detail": "..."}],
    "per_writeback_operation_status": [{"operation": "...", "status": "planned" | "completed" | "resume-needed" | "blocked"}],
    "shadow_stt": {"enabled": true, "discrepancy_summary": "...", "lane_truncated": false},
    "callbacks_audit_row_count": 0,
    "conflicting_callbacks_audit_row_count": 0,
    "rejected_auth_callbacks_count": 0,
    "started_at": "...", "ended_at": "..."
  }
  ```
  Per-session subdirectory grouping (`artifacts/<session_id>/...`) carries forward from Slice 2.
- **Rationale**: JSON is machine-readable, supports the FR-036 + Round 2 amendments
  enumerated above, and matches the existing Slice 2 artifact pattern.
- **Alternatives rejected**: TOML (less natural for nested arrays); a human-readable text
  report only (operators want both — text comes from a `format` step over the JSON).

## 10. Callbacks audit log + rejected-auth audit log + shadow STT artifact file formats

- **Decision**:
  - `callbacks_audit.jsonl` — one JSON object per line per received callback (incl. duplicates
    and out-of-order), keyed by `(session_id, provider_event_id)` (FR-007, FR-021, FR-027).
  - `rejected_auth_callbacks.jsonl` — distinct file per session per Round 2 Q9; columns
    `(received_at, source_metadata, http_status)`, no secret, no body.
  - `shadow_transcript.txt` — redacted shadow transcript per FR-033 / FR-034.
  - `shadow_discrepancies.jsonl` — one JSON object per discrepancy event with `(session_id,
    field, live_value, shadow_value, classification, review_task_reason)`.
  - `shadow_lane_truncated.json` — single JSON file per session if (and only if) the lane
    was truncated post-finalization per Round 2 Q7.
  - `conflicting_callbacks_audit.jsonl` — late-after-finalization callbacks per FR-027.
- **Rationale**: JSONL is line-readable, append-friendly, easy to grep / jq, and matches the
  Slice 2 audit-log style. Distinct filenames per artifact make the file taxonomy navigable.
- **Alternatives rejected**: a single combined audit log (loses the rejected-auth distinction
  Round 2 Q9 requires); CSV (poor fit for nested fields like `source_metadata`).

## 11. Configuration surface

- **Decision**: `config/slice3.toml` (non-secret deployment config) plus the env vars listed
  below (secrets only). The TOML file extends the Slice 1 / Slice 2 pattern.
  - **`config/slice3.toml`** (non-secret): `[signalwire]` (source caller-id, callback URL
    template), `[realtime_ai]` (provider name, model version), `[shadow_stt]` (enabled
    default, discrepancy policy path), `[timeouts]` (abandonment, silence-after-connection,
    grace window), `[retention]` (transcript mode), `[redaction]` (default policy).
  - **Env vars (secrets)**: `SIGNALWIRE_PROJECT_ID`, `SIGNALWIRE_API_TOKEN`,
    `SIGNALWIRE_SIGNING_SECRET`, `SLICE3_REALTIME_API_KEY`, `SLICE3_SHADOW_STT_API_KEY`,
    `DATAVERSE_TENANT_ID`, `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`,
    `DATAVERSE_ENV_URL` (Slice 2 vars reused).
- **Rationale**: Matches Slice 1 / Slice 2 pattern; constitution §Architecture mandates env-only
  secrets and forbids secrets in logs / artifacts (also FR-035).
- **Alternatives rejected**: secrets in TOML (forbidden); single config file collapsing all
  three slices (couples slices in violation of constitution §II thin-slice principle).

## 12. Testing strategy

- **Decision**:
  - **Contract tests** in `tests/contract/`: verify the `signalwire-transport`,
    `pipecat-runtime`, `shadow-stt-lane`, `crm-writeback-dnc-first`, and
    `rejected-auth-audit-log` contracts. Each adapter has a fake (in-package) that the
    contract test exercises against the documented protocol.
  - **Integration tests** in `tests/integration/`: per-user-story tests for US1–US7 +
    Round 2 amendment scenarios (Q6 resume-after-answered-but-no-terminal, Q7 grace-window
    in-window + truncation, Q9 auth-rejected-callback, Q11 PHI-volunteered + redaction,
    Q12 multi-operator resume, Q13 flag-absent-on-resume, Q14 DNC-first ordering with
    partial-failure). Each test runs the full stack with fakes for SignalWire / Pipecat /
    real-time AI provider / shadow STT / Dataverse (the same Dataverse fake from Slice 2).
  - **Unit tests** in `tests/unit/`: per-module isolation tests (FR-033 module marker)
    extended to `slice3/`, `runtime/pipecat/`, `transport/signalwire/`, `shadow_stt/`.
  - **Real-call posture** (not in CI): a manual `make slice3-real-call-smoke` against a
    controlled SignalWire dev tenant + a controlled Dataverse dev environment + a recorded
    test contact who has opted in to test calls. NOT run automatically.
- **Rationale**: Matches the Slice 1 / Slice 2 test taxonomy (90% coverage floor per
  `pyproject.toml`). Fixture-replay through the SignalWire transport + recorded-audio
  playback through the Pipecat runtime are explicitly named in the spec's Deferred-to-Plan
  "Test posture" section.
- **Alternatives rejected**: live SignalWire calls in CI (cost + regulatory + flakiness);
  no fakes (forces every developer to set up SignalWire / real-time AI / shadow STT
  credentials before running tests — bad ergonomics).

## 13. Pre-pilot demo-evidence checklist

- **Decision**: `docs/slice3/demo-evidence-checklist.md` (new) enumerates the artifacts an
  operator MUST collect for a real-call demo: Dataverse queue item before/after screenshots,
  Phone Call activity record screenshot, callback / review Task screenshot, local
  `run_report.json`, redacted `transcript.txt`, `callbacks_audit.jsonl`,
  `rejected_auth_callbacks.jsonl` (if non-empty), `shadow_transcript.txt` (if enabled),
  `shadow_discrepancies.jsonl` (if any), `shadow_lane_truncated.json` (if truncated),
  `conflicting_callbacks_audit.jsonl` (if any). One line per item with the FR / SC it satisfies.
- **Rationale**: The spec's Deferred-to-Plan "Test posture" + FR-038 "demonstrable loop
  exercisable without a custom openCloser UI" require a single canonical artifact list
  the operator can walk a stakeholder through.
- **Alternatives rejected**: leaving the demo list ad-hoc (loses repeatability); auto-generating
  it from `run_report.json` (operators want a paper-trail checklist they can mark off
  manually as well).

## 14. Reused Slice 1 / Slice 2 decisions (no re-research)

The following Slice 1 / Slice 2 plan decisions are reused unchanged for Slice 3 — no new
research needed:

- SQLite as the local state store (Slice 1 §Data model).
- `httpx` synchronous client for Dataverse OAuth + Web API (Slice 2 §1).
- OAuth2 client-credentials flow for Dataverse (Slice 2 §2).
- `config/dataverse_mapping.json` discovery + verification (Slice 2 §4).
- Idempotency-key stamping on Phone Call activity and Task (Slice 2 §6).
- Bounded retry: initial + 3 retries, 1s / 2s / 4s default backoff, `Retry-After` ≤ 30s
  (Slice 2 §7).
- Resume coordinator behavior (Slice 2 §8), extended for Slice 3 per Round 2 Q6 / Q12 / Q13.
- Default-on transcript redaction (Slice 2 §10), extended for Slice 3 per Round 2 Q10 / Q11
  to cover summary + shadow transcript + shadow discrepancy records.
- Local artifact retention floor ≥ 90 days (Slice 2 §11).

## Open items (NONE blocking entry to Phase 1)

All research items above resolve with the Slice 3 spec amendments already in place. No
`NEEDS CLARIFICATION` remains. Phase 1 may proceed.
