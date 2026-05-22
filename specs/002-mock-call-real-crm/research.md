# Phase 0 Research: Slice 2 — Mock Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Created**: 2026-05-22

Each decision below resolves a dependency choice or integration pattern not already pinned
by the spec. The spec's 2026-05-22 clarification session and Definitions section already
resolved the behavioral unknowns; no `NEEDS CLARIFICATION` remained entering Phase 0.

---

## 1. Dataverse Web API access

- **Decision**: Use **`httpx`** (synchronous `httpx.Client`) directly against the Dataverse
  **Web API** (OData v4, `https://{org}.crm.dynamics.com/api/data/v9.2/`). No Dataverse SDK.
- **Rationale**: The constitution explicitly names `httpx` in the default stack. Slice 2 is
  a single-item, single-process CLI — it needs a handful of GET/POST/PATCH calls and full
  control over transient-error classification and the idempotency pre-query. A thin client
  keeps the new dependency surface to exactly one package.
- **Alternatives rejected**: third-party Dataverse SDKs (heavier, opaque retry behavior,
  another dependency); raw `urllib` (no connection reuse, weaker timeout ergonomics).

## 2. Dataverse authentication

- **Decision**: **OAuth2 client-credentials** flow (Microsoft Entra ID app registration /
  service principal). Acquire a token by POSTing to
  `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token` with `scope={org}/.default`,
  using `httpx`. Cache the token in-process for the run lifetime. Secrets — `DATAVERSE_TENANT_ID`,
  `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`, `DATAVERSE_ENV_URL` — come from environment
  variables only (FR-005).
- **Rationale**: Client-credentials is the standard non-interactive Dataverse auth for
  automation. A single CLI run needs one token; in-process caching is sufficient — no refresh
  machinery required.
- **Alternatives rejected**: `msal` library (adds a dependency for token caching/refresh that
  a one-shot CLI does not need — revisit if a long-lived service is built later); username/
  password and device-code flows (interactive / deprecated for automation).

## 3. Metadata discovery & verification

- **Decision**: Two phases (FR-001).
  - **One-time discovery** (`opencloser discover-crm`): query Dataverse metadata endpoints —
    `EntityDefinitions`, `EntityDefinitions({id})/Attributes`, `GlobalOptionSetDefinitions` —
    to inspect the queue-item table, Account, Contact, Campaign, Phone Call activity, Task,
    owner/team, status/DNC/attempt/disposition/session/error fields, and the idempotency-key
    fields. Discovery **writes/refreshes** `config/dataverse_mapping.json` (FR-004).
  - **Per-run lightweight verification**: before any write-enabled run, re-query only the
    mapped entities/attributes/option-sets and confirm they still exist and match the
    artifact. Read-only; never regenerates the artifact (spec Definitions §"Lightweight live
    verification"). Any mismatch, missing field, or unreachable Dataverse → fail per FR-002.
- **Rationale**: Separates the human-reviewed mapping artifact from a fast per-run guard, as
  decided in clarification Q4. Verification stays cheap (a bounded set of metadata GETs).
- **Alternatives rejected**: full re-discovery every run (slow, conflates the reviewed
  artifact with runtime); trust-the-artifact-forever (violates the constitution's
  "verify before any write" rule).

## 4. Mapping artifact format

- **Decision**: A single JSON file, **`config/dataverse_mapping.json`**, checked into the
  repo and reviewed in a PR. It records, per conceptual field: Dataverse logical name, entity,
  attribute type, lookup target, option-set values, whether it is an *approved Slice 2 update
  field*, and `preserve_if_present` flags. A top-level `_meta` block records the discovery
  timestamp, Dataverse environment URL, and a schema version.
- **Rationale**: JSON is stdlib read **and** write (the discovery step must write it) —
  consistent with Slice 1's JSON artifacts and adding no dependency. It is small and flat
  enough to review by eye, satisfying FR-004's "documented" requirement; PR review is the
  "approval" gate referenced by FR-024.
- **Alternatives rejected**: TOML (stdlib cannot *write* TOML — would need `tomli-w`); YAML
  (needs `pyyaml`); a Markdown doc (not machine-readable for the adapter).

## 5. Configuration surface

- **Decision**: Non-secret Slice 2 config lives in **`config/slice2.toml`** (stdlib
  `tomllib`, env-var override — same loader pattern as `slice1.toml`). Keys: default run
  mode, callable status value, task-owner-per-kind map, redaction policy + retention mode,
  retry tunables (max retries, base backoff, `Retry-After` cap), Dataverse environment URL.
  Secrets stay in env vars (§2). The discovered field mapping stays in
  `dataverse_mapping.json` (§4) — config and mapping artifact are deliberately separate files
  (config = deployment knobs; mapping = discovered schema truth).
- **Rationale**: Mirrors the established Slice 1 config approach; keeps "deployment chooses"
  separate from "discovery found".
- **Alternatives rejected**: one combined file (mixes reviewed-schema with tunable-knobs);
  env-only config (nested task-owner map is awkward in env vars).

## 6. Transient-error classification, retry & resume

- **Decision**: Classify per the spec Definitions section. **Transient** → `httpx` timeout/
  transport errors and HTTP 408/429/5xx; retry with the FR-023 budget (initial + 3 retries,
  1s/2s/4s backoff; HTTP 429 `Retry-After` may replace the next delay, capped 30s).
  **Permanent** → 400/401/403/404, option-set mismatch, missing mapping, metadata drift; fail
  the operation with no retry. Retry/classification live inside `crm/dataverse/client.py`.
  - **Resume**: when the retry budget is exhausted mid-write-back, the run exits with a
    `resume_needed` status; `crm_correlations` + `writeback_progress` record which write-back
    operations succeeded. A re-invocation is handled by a **Slice 2 resume coordinator**
    (`slice2/resume.py`) that re-issues only the missing `emit_*` calls from the **already-
    persisted** write-back payloads — it does **not** re-run `process_one_queue_item`. This
    keeps the Slice 1 orchestrator contract unchanged (FR-014) and makes resume rely on
    Dataverse as the source of truth (the adapter pre-queries before each create).
- **Rationale**: Simple inline retry — bounded, no scheduler/queue — satisfies FR-023 without
  the "advanced retry orchestration" the constitution defers. Driving resume from persisted
  payloads (not a re-run) avoids re-placing the mock call and avoids any orchestrator change.
- **Alternatives rejected**: re-running the whole orchestrator on resume (would re-place the
  call and depends on fragile local-idempotency-key timing); a background retry worker
  (Celery/queue — constitution-excluded).

## 7. Idempotency-key field & pre-query

- **Decision**: Stamp the **session ID** onto a metadata-verified custom Dataverse column on
  every Phone Call activity and Task the adapter creates (logical name discovered and recorded
  in the mapping artifact). Before each create, the adapter issues a pre-query
  (`GET {entity}?$filter={keyfield} eq '{session_id}'&$select={keyfield}&$top=1`); a hit means
  the record already exists → no-op. If the idempotency-key field cannot be verified,
  write-enabled processing is blocked (FR-024 / FR-002 / SC-015).
- **Rationale**: Makes Dataverse itself the duplicate-detection authority (clarification Q2,
  option A) — robust across retries, re-invocations, and loss of local state. A filterable
  custom column is the simplest reliable carrier.
- **Alternatives rejected**: free text in the activity description (not reliably queryable —
  explicitly forbidden by FR-024); a Dataverse **alternate key** on the entity (more robust
  but needs extra schema setup — recorded as a future hardening, not Slice 2 scope);
  local-store-only correlation (loses authority if local state is lost).

## 8. Transcript redaction layer

- **Decision**: A `RedactionLayer` in `src/opencloser/redaction/` invoked by
  `artifacts/writer.py` immediately before any transcript disk write. Policies:
  `RegexRedactionPolicy` (default — replaces configured sensitive patterns, e.g. phone numbers
  and emails, with `[REDACTED]`), `NoOpPolicy`, and a **summary-only** retention mode (writes
  no full transcript file at all). Policy + mode are selected in `slice2.toml`; default-on,
  and cannot be silently disabled (an explicit `policy = "noop"` is required to turn it off).
- **Rationale**: Satisfies FR-028–FR-030 and the Slice 1 forward-looking carry-over. Placing
  it at the writer boundary preserves the Slice 1 summary + transcript-pointer artifact
  contract (FR-029).
- **Alternatives rejected**: redacting inside the persona (couples safety policy to
  conversation logic); redacting after disk write (raw text would touch disk first).

## 9. Mock-transport fixture pre-validation

- **Decision**: Add `validate_fixture()` to the mock transport, called **inside `place_call`**
  before it returns a `mock_provider_call_id` and before the orchestrator mutates any state.
  It validates JSON parse, presence of an `events` array, and each event's `type`/`event_id`/
  `timestamp`; a failure raises a typed `MalformedFixtureError`. This is the **only**
  permitted change to the transport module (FR-014 / FR-019).
- **Rationale**: Resolves GitHub issue #2 at the exact point that prevents a consumed attempt
  or partial session — `place_call` runs before the orchestrator's state mutations.
- **Alternatives rejected**: validating after `event_stream` (error surfaces too late — state
  already mutated); validating in the CLI (the transport owns fixture loading, so duplicate
  knowledge would drift).

## 10. Testing strategy

- **Decision**: Unit tests per new module. **Contract tests** assert
  `DataverseWriteBackAdapter` satisfies `specs/001/contracts/crm-writeback.md` unchanged
  (per-disposition emission map + `new_status` table — SC-011). **Integration tests** run
  US1–US6 end-to-end against an **in-process Dataverse fake** — a small fixture-backed
  double of the Web API surface (metadata, queue GET, activity/Task POST, queue PATCH,
  idempotency pre-query, injectable transient/permanent failures). No live Dataverse in CI.
- **Rationale**: A fake keeps CI deterministic and offline while still exercising the adapter,
  retry, resume, and idempotency paths. Live Dataverse is reserved for the manual demo.
- **Alternatives rejected**: live Dataverse in CI (non-deterministic, credential-bound, slow,
  mutates a real environment); mocking only at the `httpx` layer (too low-level to express
  metadata/option-set behavior cleanly).

## Resolved unknowns summary

| Unknown | Resolution |
|---|---|
| Dataverse API client | `httpx` direct to Web API (OData v4) |
| Auth | OAuth2 client-credentials, env-var secrets, in-process token cache |
| Metadata model | one-time `discover-crm` → artifact; per-run lightweight verification |
| Mapping artifact | `config/dataverse_mapping.json`, PR-reviewed |
| Config | `config/slice2.toml` (non-secret) + env-var secrets |
| Retry / resume | inline bounded retry; resume coordinator replays persisted payloads |
| Idempotency anchor | session ID stamped on a verified custom column + pre-query |
| Redaction | `RedactionLayer` at the artifact-writer boundary, default-on |
| Fixture validation | `validate_fixture()` inside `place_call` |
| Testing | in-process Dataverse fake; contract + integration tests |
