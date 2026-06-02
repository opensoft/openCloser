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
- **Transport selection (Round 4 R4-Q4)**: fixture-replay vs. the real SignalWire transport is a
  non-secret `[signalwire].transport = "real" | "fixture"` setting (default `real`); the fixture
  path is debug-only. The live `signalwire` SDK dial path is exercised only when `transport =
  "real"`. See §11.
- **Callback-URL templates (Round 4 R4-Q3)**: the configured status / media callback-URL templates
  honor ONLY the `{session_id}` placeholder; any other placeholder token is a configuration error
  surfaced at pre-dial readiness (exit 4), so a malformed callback URL never reaches SignalWire.
- **Signing-secret loading (Round 4 R4-Q20)**: see §2 — the callback signing secret is loaded from
  the environment ONLY, at signature-module init; loading it from disk or CLI argv is forbidden.
- **Rationale**: The `signalwire` SDK matches SignalWire's documented Python entrypoint and
  isolates SWML / TwiML generation behind a vendor-vetted surface. Embedding a tiny callback
  receiver in-process keeps Slice 3 single-process and avoids introducing Celery / Redis /
  a job queue (constitution §Architecture explicitly forbids those for the MVP).
- **Alternatives rejected**: raw `httpx` against the SignalWire REST API (re-implements SWML
  / TwiML and signature verification ourselves); standing up a separate webhook receiver
  service (multi-process, adds operator burden); using Twilio / a multi-provider abstraction
  (forbidden by constitution §Architecture — "MUST avoid... multiple telephony providers").

## 2. SignalWire signature verification + rejected-by-authentication audit log

- **Decision**: Verify SignalWire's HMAC-SHA256 signature header
  `[Assumption — pending vendor-doc confirmation]` on every inbound
  callback (status + media) using a deployment-provided shared signing secret loaded from
  `SIGNALWIRE_SIGNING_SECRET`. Per Round 4 R4-Q20 the signing secret (and every other secret) is
  loaded from the ENVIRONMENT ONLY, at signature-module init — never from disk and never from CLI
  argv (reinforces FR-035). Verification happens in `transport/signalwire/signature.py`
  before any orchestrator hand-off. The signature comparison in `signature.py` MUST use a
  CONSTANT-TIME / timing-safe equality (R7) — e.g. `hmac.compare_digest(expected, received)`
  — NEVER a naive `==` byte comparison, so an attacker cannot recover the expected signature
  (and thereby the signing secret) through a timing side channel by observing how quickly a
  forged signature is rejected. A failed-signature callback is rejected with HTTP `401`
  and recorded in a distinct `rejected_auth_callbacks` SQLite table with columns
  `(received_at, source_metadata_json, http_status)` — explicitly NOT the verification secret
  and NOT the callback body content. `source_metadata_json` is restricted to an allow-list of
  non-caller-controlled fields (provider source identifier(s) + remote IP / transport metadata)
  and bounded at ≤ 1 KB / ≤ 16 keys (Round 3), so a forged callback cannot stuff payload into
  the audit log. On a verification failure the ASGI receiver drops the request body buffer
  without persisting it (Round 3). A rejection that cannot be matched to a known session is
  written under `artifacts/_unassociated/rejected_auth_callbacks.jsonl`, which honors the same
  ≥ 90-day retention floor as session-scoped artifacts (Round 3). The run report (FR-036)
  surfaces a count of rejected-auth callbacks per session, and operator tooling surfaces a
  deployment-level `rejected_auth_unassociated_count` for the null-session rejections.
- **Rationale**: Round 2 Q9 pinned Option B (distinct audit log, no secret, no body, run-report
  count). The specific signature algorithm — HMAC-SHA256 — is recorded here as an
  `[Assumption — pending vendor-doc confirmation]`: we cannot verify a vendor URL from this
  research context, so the plan MUST confirm the exact algorithm and canonicalization (header
  name, signed-string construction, encoding) against SignalWire's PUBLISHED signature-verification
  documentation BEFORE real-call enablement, and pin the doc title + version + URL when confirmed.
  If the published mechanism differs (algorithm or canonical-string shape), `signature.py` is
  corrected to match before any live callback is trusted. A distinct table makes
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
- **Credential readiness (Round 4 R4-Q1)**: a missing real-time AI provider credential at
  invocation is a hard pre-dial telephony readiness failure (FR-009 `realtime_ai_credentials`
  check) — the run exits 4 before dial, consumes no attempt, and creates no Phone Call activity.
- **Error model (Round 4 R4-Q5)**: the provider protocol raises `RealtimeProviderError` carrying
  a `transient: bool` flag. A transient PRE-connection provider error is retried within the
  connect budget; a terminal pre-connection error finalizes per FR-013. Once the call has
  connected, ANY provider error (transient or not) is a degradation trigger per FR-013 and is
  recorded as the distinct `provider_error` run-report failure-reason code.
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
  "Slice 3 demonstrable loop completes without it" guarantee is satisfied. **Empty-string /
  whitespace normalization (R7)**: the provider value is normalized by trimming surrounding
  whitespace before selection, so an empty-string or whitespace-only `SLICE3_SHADOW_STT_PROVIDER`
  normalizes to "unset" — i.e. it is treated EXACTLY like unset / `"disabled"` (lane no-op, never
  a readiness error and never an attempt to load a provider named `""`). Only a non-empty,
  non-`"disabled"` trimmed value selects a real provider. Discrepancy
  policy is a deployment-configurable JSON file `config/shadow_stt_discrepancy_policy.json`
  with two sections: `benign_rules` (case-insensitive equality, whitespace normalization,
  phonetic-spelling tolerance for names) and `uncertain_rules` (semantically different
  emails, callback windows that differ by > 1 day, opt-out vs. interest disagreement).
  **Per-field rule coverage (R7 — illustrative, not exhaustive)**: the `benign_rules` /
  `uncertain_rules` examples above are ILLUSTRATIVE only — they show the rule SHAPE, not the
  complete per-field rule set. The exhaustive per-field classification rules — explicitly
  including `person_reached_role`, `wrong_number`, `final_disposition`, and `interest_level`
  disagreements, plus email-casing-vs-domain distinctions — are DEFERRED to the
  `config/shadow_stt_discrepancy_policy.json` policy file itself and to the plan, which owns
  enumerating one rule path per FR-030 high-value field and the default classification for any
  field not otherwise matched. Research §4 fixes the two-section structure; the plan/policy file
  fixes the per-field contents.
- **Shadow credential readiness (Round 4 R4-Q1)**: a missing shadow-STT credential FAILS the
  run via the FR-009 `shadow_stt_credentials` readiness check (exit 4) only when shadow is
  EXPLICITLY enabled via `--shadow-stt`. When shadow is only default-on-from-config, a missing
  key DISABLES the lane with a run-report warning instead of blocking the demonstrable loop
  (FR-032 "loop completes without it").
- **Discrepancy-policy readiness (Round 4 R4-Q2)**: when shadow STT is enabled, a missing or
  malformed `discrepancy_policy_path` (the `config/shadow_stt_discrepancy_policy.json` file) is a
  refuse-to-start readiness failure (exit 4) with a named check — the run never silently treats
  all discrepancies as benign nor all as uncertain.
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
- **SC-013 non-blocking measurement (R7 — acceptable deferral)**: SC-013 ("no observable
  slowdown attributable to the shadow lane") is verified qualitatively at the research layer and
  by the `test_lane_does_not_block_live_turns` contract test, which asserts the live-turn cadence
  is "statistically indistinguishable" between shadow-enabled and shadow-disabled runs. The exact
  performance harness — sampling method, sample size, the chosen statistic, and the numeric
  indistinguishability threshold that operationalizes "no observable slowdown" — is intentionally
  DEFERRED to the plan's "Performance and latency targets" subsection. This is an accepted
  deferral, not a research gap: the non-blocking guarantee is enforced structurally (separate
  `asyncio.Task`, no `await` on the lane before finalization per §7), and the numeric threshold is
  a tuning choice that belongs with the other latency budgets in the plan.
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
    Configurable to `0` (the force-immediate-write path — write-back proceeds at once; shadow
    always becomes `shadow_lane_truncated`) or any positive integer (no spec-mandated maximum;
    deployment may bound it). The in-effect value is recorded on the session and surfaced in the
    run report as `grace_window_sec` (Round 3) so an operator can see which window applied.
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
    "operator_identity": {"current": "...", "original": "..." | null, "chain": ["..."]},
    "real_provider_call_id": "..." | null,
    "persona_version": "...",
    "runtime_identity": {"runtime": "pipecat", "version": "...", "provider": "...", "model_name": "...", "model_version": "..."},
    "final_disposition": "...",
    "human_review_reason": "..." | null,
    "blocked_reason": "..." | null,
    "failure_reason": "..." | null,
    "grace_window_sec": 3,
    "abandonment_timeout_sec": 90,
    "abandonment_elapsed_condition": "..." | null,
    "redaction_applied": true,
    "operator_reminder": "Slice 3 collects no PHI and performs no clinical workflow.",
    "config_identity": {
      "redaction_policy_version": "...", "redaction_policy_hash": "...",
      "retention_policy_version": "...", "retention_policy_hash": "...",
      "disclosure_policy_version": "...", "disclosure_policy_hash": "..."
    },
    "telephony_readiness_summary": [{"check": "...", "result": "pass" | "fail" | "skipped (resume)", "detail": "..."}],
    "per_writeback_operation_status": [{"operation": "...", "status": "planned" | "completed" | "resume-needed" | "blocked"}],
    "shadow_stt": {
      "enabled": true,
      "lane_truncated": false,
      "lane_failed": false,
      "failure_detail": {"failure_type": "..." | null, "at": "..." | null},
      "discrepancy_summary": {
        "fields_compared": 0,
        "discrepancies": 0,
        "uncertain": 0,
        "per_field": [{"field": "...", "classification": "benign" | "uncertain"}]
      }
    },
    "callbacks_audit_row_count": 0,
    "conflicting_callbacks_audit_row_count": 0,
    "rejected_auth_callbacks_count": 0,
    "started_at": "...", "ended_at": "..."
  }
  ```
  Per-session subdirectory grouping (`artifacts/<session_id>/...`) carries forward from Slice 2.
  The `runtime_identity` object uses `model_name` + `model_version` (the single canonical
  shape, matching data-model §1.12 and the CLI contract). `operator_identity.chain` is the
  full ordered list of operators that ran the session (Round 3); `original` is the first
  authorizer, `current` the latest. `grace_window_sec` records the FR-029 grace window in
  effect (Round 3). `shadow_stt.lane_truncated` and `shadow_stt.lane_failed` are reported
  INDEPENDENTLY (Round 3): truncated = late-after-grace-window output; failed = the lane
  crashed / timed out and produced no usable result. The deployment-level
  `rejected_auth_unassociated_count` for null-session forged callbacks lives in operator
  tooling, not the per-session run report (the unassociated rejections are not session-scoped).
- **Round 4 run-report additions**:
  - **Distinct runtime-failure reason codes (R4-Q13)**: the FR-013 triggers are recorded as
    DISTINCT `failure_reason` codes — `provider_error` (real-time AI provider error),
    `runtime_crash` (Pipecat runtime / adapter crash), and `silence_timeout` (silence-after-
    connection / no-extraction-event timeout) — so observability can tell the three triggers
    apart (joining the existing `live_call_abandonment`, `redaction_failed`, `dnc_write_failed`
    reasons).
  - **`abandonment_timeout_sec` (R4-Q14)**: the live-call abandonment timeout value in effect,
    plus an `abandonment_elapsed_condition` describing the elapsed condition on an actual
    abandonment finalization.
  - **`shadow_stt.failure_detail {failure_type, at}` (R4-Q14)**: carried alongside
    `shadow_stt.lane_failed` to record WHY and WHEN the lane failed.
  - **Structured `shadow_stt.discrepancy_summary` (R4-Q15)**: a defined shape
    `{fields_compared, discrepancies, uncertain, per_field:[{field, classification}]}` (counts +
    per-field classification) rather than a free-form string.
  - **`redaction_applied: true|false` + static operator reminder (R4-Q40)**: a positive indicator
    of whether redaction ran, plus a static no-PHI / no-clinical operator reminder line.
  - **`config_identity` block (R4-Q46)**: records a version/hash of the redaction, retention, and
    disclosure policies so policy changes are themselves auditable; pairs with the per-artifact
    `retention_mode` + `created_at` markers.
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
- **JSONL line-format constraint (R7)**: every `.jsonl` artifact above
  (`callbacks_audit.jsonl`, `rejected_auth_callbacks.jsonl`, `shadow_discrepancies.jsonl`,
  `conflicting_callbacks_audit.jsonl`) MUST emit exactly ONE complete JSON object per physical
  line, serialized in COMPACT form with NO embedded newlines inside any object — i.e. each record
  is written with a newline-free serializer (e.g. `json.dumps(obj)` with no `indent=` and
  `\n`-escaped string values) and terminated by a single `\n`. This is a hard requirement, not a
  stylistic preference: it is what makes the files line-readable by `grep` / `jq -c` / `wc -l` and
  makes one line == one record for append-and-count tooling. Pretty-printed / multi-line JSON
  objects are forbidden in these artifacts.
- **Redaction-pass scope (Round 4 R4-Q52)**: the default-on redaction pass runs over the FULL
  four-artifact set — the full transcript, the session-result `summary`, the shadow STT
  transcript, and the shadow STT discrepancy records — before any of them is written to disk. The
  CUMULATIVE redaction-pass latency therefore spans all four artifacts (not the transcript alone);
  the numeric budget is deferred to the plan's "Performance and latency targets" subsection.
- **Rationale**: JSONL is line-readable, append-friendly, easy to grep / jq, and matches the
  Slice 2 audit-log style. Distinct filenames per artifact make the file taxonomy navigable.
- **Alternatives rejected**: a single combined audit log (loses the rejected-auth distinction
  Round 2 Q9 requires); CSV (poor fit for nested fields like `source_metadata`).

## 11. Configuration surface

- **Decision**: `config/slice3.toml` (non-secret deployment config) plus the env vars listed
  below (secrets only). The TOML file extends the Slice 1 / Slice 2 pattern.
  - **`config/slice3.toml`** (non-secret): `[signalwire]` (source caller-id, callback URL
    template, `transport`), `[realtime_ai]` (provider name, model version), `[shadow_stt]`
    (enabled default, discrepancy policy path), `[timeouts]` (abandonment, silence-after-connection,
    grace window), `[retention]` (transcript mode), `[redaction]` (default policy).
  - **Retention default (Round 4 R4-Q2)**: `[retention].mode` is OPTIONAL; when omitted it
    defaults to `full_with_redaction` (never silently pointer-only or summary-only). The three
    retention modes (`full_with_redaction`, `summary_only`, `pointer_only`) remain the supported
    set per FR-033.
  - **`[signalwire].transport` (Round 4 R4-Q4)**: a non-secret setting `transport = "real" |
    "fixture"`, default `real`. The `fixture` value selects the Slice 1 / Slice 2 fixture-replay
    transport for debug-only use; `real` selects the live SignalWire outbound-dial path. This is
    the explicit, non-secret toggle between fixture-replay and the real transport — not an env-var
    or implicit selection.
  - **`[signalwire]` callback-URL templates (Round 4 R4-Q3)**: the status / media callback-URL
    templates honor EXACTLY one placeholder, `{session_id}`. Any other placeholder token in a
    callback-URL template is a configuration error surfaced as a readiness failure (exit 4) at
    pre-dial readiness; the run refuses to start in real-call mode rather than dialing with a
    malformed callback URL.
  - **`[realtime_ai]` / `[shadow_stt]` credential readiness (Round 4 R4-Q1)**: the `[realtime_ai].*`
    block names the live real-time AI provider; its credentials (env-var-only) are verified by the
    FR-009 `realtime_ai_credentials` readiness check (a miss fails before dial, exit 4, no attempt).
    The `[shadow_stt].*` block names the shadow provider and `discrepancy_policy_path`; a missing
    shadow credential FAILS the run (`shadow_stt_credentials` readiness check) only when shadow is
    explicitly enabled via `--shadow-stt`, and otherwise (default-on-from-config) DISABLES the lane
    with a run-report warning rather than blocking the demonstrable loop (FR-032).
  - **`discrepancy_policy_path` readiness (Round 4 R4-Q2)**: when shadow STT is enabled, a missing
    or malformed `[shadow_stt].discrepancy_policy_path` is a refuse-to-start readiness failure
    (exit 4) with a named check — the run never silently treats all discrepancies as benign nor all
    as uncertain.
  - **Disabling default-on redaction (Round 4 R4-Q18)**: default-on transcript redaction can be
    disabled ENTIRELY only via the explicit `[redaction].policy = "disabled"` setting. When set,
    the run MUST emit a PROMINENT warning at startup (stderr) AND in the run report; redaction is
    never silently off. Any other `[redaction].policy` value keeps the default-on `[REDACTED]` /
    `[PHI-REDACTED]` coverage intact.
  - **Env vars (secrets)**: `SIGNALWIRE_PROJECT_ID`, `SIGNALWIRE_API_TOKEN`,
    `SIGNALWIRE_SIGNING_SECRET`, `SLICE3_REALTIME_API_KEY`, `SLICE3_SHADOW_STT_API_KEY`,
    `DATAVERSE_TENANT_ID`, `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`,
    `DATAVERSE_ENV_URL` (Slice 2 vars reused).
  - **Configuration precedence (Round 3)**: for any overlapping NON-secret setting the order
    is **CLI flag > environment variable > `config/slice3.toml` > built-in default**. This
    resolves the apparent duplication of the three timeouts between this section's
    `SLICE3_*_SEC` env vars (§7) and the `[timeouts]` block in `config/slice3.toml`
    (quickstart §1.3): the `[timeouts]` TOML block is the documented default surface, and a
    set `SLICE3_ABANDONMENT_TIMEOUT_SEC` / `SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC` /
    `SLICE3_GRACE_WINDOW_SEC` env var overrides the corresponding TOML value when present.
    The shadow-STT toggle follows the same rule (`--shadow-stt` / `--no-shadow-stt` overrides
    `[shadow_stt].enabled_default`). Secrets remain env-var-only with no TOML or CLI surface.
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
  - **FR-to-coverage map** (R4-Q51, closes requirements CHK163): which FRs rely on integration-only coverage vs. contract-test coverage — **Contract-test-covered**: FR-004–FR-008 (signalwire-transport), FR-013–FR-016 (pipecat-runtime), FR-017/FR-018/FR-023/FR-025 (slice12-preservation per T101), FR-020/FR-021/FR-024 (crm-writeback-dnc-first), FR-028–FR-032 (shadow-stt-lane), FR-008/FR-035 (rejected-auth-audit-log), FR-001/FR-002/FR-003/FR-036/FR-037 (cli-slice3). **Integration-only-covered** (exercised end-to-end through the runner, not a single contract): FR-009–FR-012 (telephony readiness gating across US3), FR-022/FR-026/FR-027 (resume + abandonment + conflicting-late callbacks across US4/US7), FR-033/FR-034 (retention modes across T100), FR-038 (demo-without-UI across US1/US2/US6/US7).
- **Coverage measurement (R7)**:
  - **Repo-wide floor, per-package check manual (CHK127)**: the accepted measure is the
    repo-wide **90% coverage floor** configured in `pyproject.toml` — the SAME single repo-wide
    gate used by Slice 1 / Slice 2. Task T098 performs a MANUAL per-package check that each new
    Slice 3 package (`transport/signalwire/`, `runtime/pipecat/`, `shadow_stt/`, `slice3/`) is at
    or above the floor, but ENFORCED per-package coverage thresholds are intentionally DEFERRED to
    the plan (which may add `[tool.coverage]` per-package gates if it chooses). The CI gate remains
    the repo-wide 90% number; per-package is a manual T098 spot-check, not a pinned threshold.
  - **In-package fakes excluded from the measurement (CHK128)**: the in-package fakes
    (`runtime/pipecat/provider_fake.py` per §3, the `ShadowSTTProvider` fake per §4, and the
    SignalWire transport fake) are TEST ARTIFACTS, not production code. Their own line coverage is
    EXCLUDED from the 90% measurement (via the coverage config `omit` / exclusion list), so the
    90% floor reflects PRODUCTION code only. The fakes still EXERCISE production code through the
    contract tests — they count toward covering production lines — but their own lines do not count
    toward (nor dilute) the production-code coverage number.
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

## Round 4 — Checklist-Residual Alignment (2026-06-01)

Propagation of the spec's "Session 2026-06-01 (Round 4 — checklist residual closure)" decisions
and amended FRs into the research/decisions doc. Additive only — §1–§14 and the prior Round 1–3
notes are preserved. What changed:

- **§11 (config surface)**: added `[retention].mode` default `full_with_redaction` when omitted
  (R4-Q2); added the `[signalwire].transport = "real" | "fixture"` non-secret toggle, default
  `real` (R4-Q4); pinned callback-URL templates to the single `{session_id}` placeholder, any
  other placeholder a readiness-failure config error (R4-Q3); documented `[realtime_ai].*` /
  `[shadow_stt].*` credential readiness and the `discrepancy_policy_path` refuse-to-start failure
  while shadow enabled (R4-Q1/Q2); documented `[redaction].policy = "disabled"` as the ONLY way to
  turn default-on redaction off, with a mandatory prominent startup + run-report warning (R4-Q18).
- **§3 (real-time AI provider)**: missing real-time AI creds → `realtime_ai_credentials` readiness
  failure (R4-Q1); `RealtimeProviderError.transient: bool` with transient pre-connection retry in
  the connect budget (R4-Q5).
- **§4 (shadow STT)**: missing shadow creds fail only under explicit `--shadow-stt` else
  disable-with-warning (R4-Q1); missing/malformed `discrepancy_policy_path` → refuse-to-start
  (R4-Q2).
- **§1 (SignalWire surface)**: cross-referenced the `transport` toggle (R4-Q4), the `{session_id}`-
  only callback placeholder rule (R4-Q3), and env-only signing-secret loading (R4-Q20).
- **§2 (signature verification)**: signing secret loaded from env ONLY at signature-module init —
  never disk/argv (R4-Q20).
- **§9 (run-report schema + example)**: added distinct `provider_error` / `runtime_crash` /
  `silence_timeout` failure reasons (R4-Q13); added `abandonment_timeout_sec` (+ elapsed
  condition), `shadow_stt.failure_detail {failure_type, at}`, structured
  `shadow_stt.discrepancy_summary {fields_compared, discrepancies, uncertain, per_field:[{field,
  classification}]}`, `redaction_applied`, a static no-PHI/no-clinical reminder line, and a
  `config_identity` block with redaction/retention/disclosure policy version+hash (R4-Q14/Q15/Q40/
  Q46). JSON example updated accordingly.
- **§10 (artifact formats)**: noted the cumulative redaction-pass latency spans the four-artifact
  set (transcript + summary + shadow transcript + shadow discrepancy records) (R4-Q52).

## Round 7 — Checklist-Residual Closure (2026-06-02)

Additive-only closure of R7 requirements-quality checklist gaps. §1–§14 and the Round 1–4
notes are preserved. What changed:

- **§10 (artifact formats)**: pinned the JSONL line-format constraint — each `.jsonl` record is
  one complete, compact, embedded-newline-free JSON object per physical line, terminated by `\n`
  (grep / `jq -c` / `wc -l` line-readability) (observability CHK118).
- **§2 (signature verification)**: marked the HMAC-SHA256 algorithm claim as
  `[Assumption — pending vendor-doc confirmation]` and required the plan to confirm it against
  SignalWire's published signature docs (title/version/URL) before real-call enablement
  (security CHK128); required `signature.py` to use a CONSTANT-TIME / timing-safe comparison
  (`hmac.compare_digest`) rather than naive `==` to close the timing-side-channel gap
  (security CHK171).
- **§6 (shadow lane topology)**: recorded SC-013's non-blocking harness / numeric threshold as an
  accepted deferral to the plan's Performance subsection, with structural non-blocking enforced by
  construction (shadow-stt CHK002).
- **§4 (shadow STT + discrepancy policy)**: stated the `benign_rules` / `uncertain_rules` examples
  are illustrative only and deferred the exhaustive per-field rule set (`person_reached_role`,
  `wrong_number`, `final_disposition`, `interest_level`) to the policy file / plan
  (shadow-stt CHK138); specified that empty-string / whitespace-only `SLICE3_SHADOW_STT_PROVIDER`
  normalizes to "unset" (lane no-op), same as unset / `"disabled"` (shadow-stt CHK151).
- **§12 (testing strategy)**: recorded repo-wide 90% as the accepted coverage measure with T098's
  manual per-package check and per-package enforcement deferred to the plan (testing CHK127); and
  stated the in-package fakes are test artifacts excluded from the production-code coverage
  measurement (testing CHK128).

## Open items (NONE blocking entry to Phase 1)

All research items above resolve with the Slice 3 spec amendments already in place. No
`NEEDS CLARIFICATION` remains. Phase 1 may proceed.
