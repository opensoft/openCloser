# Data Model: Slice 2 — Mock Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Created**: 2026-05-22

Slice 2 reuses every Slice 1 entity unchanged. It **adds** two local SQLite tables (for CRM
correlation and resume), one discovered mapping artifact, one config file, and a set of
additive Pydantic models. Dataverse-side records are described as the adapter's translation
targets — they are **not** stored locally.

---

## 1. Local SQLite additions

The Slice 1 schema (`src/opencloser/state/schema.sql`) is unchanged. Two tables are appended
(`CREATE TABLE IF NOT EXISTS`); all timestamps are ISO 8601 / UTC / ms strings.

### `crm_correlations`

One row per Dataverse record the adapter creates or confirms — the local record of the
CRM correlation identifier (FR-024). It ties a session to its Dataverse records and carries
the idempotency key.

| Column | Type | Notes |
|---|---|---|
| `session_id` | TEXT NOT NULL | FK → `sessions.session_id` |
| `record_kind` | TEXT NOT NULL | `phone_call_activity` \| `task` \| `queue_status` |
| `idempotency_key` | TEXT NOT NULL | the session ID (or derived key) stamped on the Dataverse record |
| `dataverse_record_id` | TEXT | Dataverse GUID; NULL until the write is confirmed |
| `write_status` | TEXT NOT NULL | `pending` \| `confirmed` \| `failed` |
| `created_at` / `updated_at` | TEXT NOT NULL | |

Primary key: (`session_id`, `record_kind`). `record_kind` is single-valued per session
because Slice 2 emits at most one of each per session.

### `writeback_progress`

One row per session — the resume ledger (FR-023, SC-014). Records which of the four
write-back operations have completed so a resume run replays only the missing ones.

| Column | Type | Notes |
|---|---|---|
| `session_id` | TEXT NOT NULL PRIMARY KEY | FK → `sessions.session_id` |
| `phone_call_activity_done` | INTEGER NOT NULL DEFAULT 0 | 0/1 |
| `queue_status_update_done` | INTEGER NOT NULL DEFAULT 0 | 0/1 |
| `task_done` | INTEGER NOT NULL DEFAULT 0 | 0/1 (also set when no Task is required) |
| `run_status` | TEXT NOT NULL | `in_progress` \| `completed` \| `resume_needed` \| `blocked` |
| `last_error` | TEXT | last transient/permanent error summary (no secrets, no CRM contents) |
| `updated_at` | TEXT NOT NULL | |

#### State machine for `run_status` (T050 — addresses CHK068/CHK069)

The four states are mutually exclusive and exhaustive — every persisted `writeback_progress`
row is in exactly one of them at any instant.

**Mutually exclusive entry criteria**:

- `in_progress` — at least one `emit_*` attempted and **no** terminal event has fired. The
  only non-terminal state. New-progress placeholder is written at the first emit.
- `completed` — every required `emit_*` for the session's final disposition completed
  successfully and `adapter.finalize_progress(..., RunStatus.COMPLETED)` was called.
  Terminal.
- `resume_needed` — at least one `emit_*` raised `TransientDataverseError` after the
  bounded retry budget was exhausted (FR-023); the runner's catch block stamped
  `flush_pending_failures(failure_run_status=RESUME_NEEDED)`. A later `--resume`
  invocation routes to `slice2/resume.py`.
- `blocked` — EITHER `final_disposition=BLOCKED` from eligibility/metadata
  (`finalize_progress(..., RunStatus.BLOCKED)`), OR a permanent error mid-write-back
  (`PermanentDataverseError`, `CrmConflictError` from T045 mid-run conflict detection,
  `MappingError`, `DataverseWriteBackError` other than `TransientDataverseError`). Terminal
  under normal CLI flow; the T045 conflict variant requires manual reconciliation in
  Dynamics + a fresh `run-crm` invocation (which creates a NEW session row with its own
  state machine).

**Allowed transitions and triggering events**:

| From            | To              | Trigger event                                                                                                          |
|-----------------|-----------------|------------------------------------------------------------------------------------------------------------------------|
| (new row)       | `in_progress`   | First `emit_*` call writes the new-progress row.                                                                       |
| `in_progress`   | `completed`     | All required `emit_*` succeeded; `finalize_progress(..., COMPLETED)`.                                                  |
| `in_progress`   | `resume_needed` | Retry budget exhausted on `TransientDataverseError`; `flush_pending_failures(RESUME_NEEDED)`.                          |
| `in_progress`   | `blocked`       | `final_disposition=BLOCKED` (eligibility/metadata) → `finalize_progress(..., BLOCKED)`. OR permanent CRM error mid-write-back (`CrmConflictError` per T045, `PermanentDataverseError`, `MappingError`) → `flush_pending_failures(BLOCKED)`. |
| `resume_needed` | `completed`     | Resume coordinator replayed all missing `emit_*`; `finalize_progress(..., COMPLETED)`.                                 |
| `resume_needed` | `resume_needed` | Resume replay itself re-exhausted retry budget; `flush_pending_failures(RESUME_NEEDED)` (idempotent self-loop).        |
| `resume_needed` | `blocked`       | Resume replay hit a permanent error or a re-detected T045 conflict (CHK061); `flush_pending_failures(BLOCKED)`.        |
| `completed`     | (no transition) | Terminal. Re-invocation returns `no-resume-needed` (FR-021 idempotent re-invocation); the row is never overwritten.    |
| `blocked`       | (no transition) | Terminal under normal CLI flow. For the T045 conflict variant, manual reconciliation + a fresh `run-crm` creates a NEW session row (the original row is preserved as audit evidence per FR-035). |

The full operator-visible `run_status` → CLI exit-status mapping lives in
[`contracts/cli-slice2.md`](./contracts/cli-slice2.md#run_status--cli-exit-status-mapping)
to keep the exit-code contract in one place.

---

## 2. Mapping artifact — `config/dataverse_mapping.json`

Produced/refreshed by `discover-crm` (FR-001, FR-004); read by every run. PR review of this
file is the "approval" gate referenced by FR-024.

```jsonc
{
  "_meta": {
    "schema_version": "slice2-mapping-v1",
    "discovered_at": "2026-05-22T00:00:00.000Z",
    "dataverse_env_url": "https://example.crm.dynamics.com",
    "approved": false                       // flipped to true by human PR review
  },
  "entities": {
    // `logical_name` is the singular metadata name used by `EntityDefinitions(...)`;
    // `entity_set_name` is the (often plural) name used in record CRUD URLs
    // (`/api/data/v9.2/<entity_set>`). The two MAY differ for custom tables — keep
    // both explicit. `entity_set_name` falls back to `logical_name` when omitted.
    "queue_item": { "logical_name": "<discovered>", "entity_set_name": "<discovered>", "primary_id": "<discovered>" },
    "phone_call_activity": { "logical_name": "phonecall", "entity_set_name": "phonecalls" },
    "task": { "logical_name": "task", "entity_set_name": "tasks" },
    "account": { "logical_name": "account", "entity_set_name": "accounts", "primary_id": "accountid" }
  },
  "fields": {
    // conceptual field -> Dataverse attribute
    "queue.status":        { "entity": "queue_item", "logical_name": "<discovered>",
                             "type": "optionset", "approved_update_field": true },
    "queue.attempt_count": { "entity": "queue_item", "logical_name": "<discovered>",
                             "type": "integer", "approved_update_field": true },
    "queue.dnc":           { "entity": "queue_item", "logical_name": "<discovered>",
                             "type": "boolean", "approved_update_field": true },
    "queue.last_disposition": { "entity": "queue_item", "logical_name": "<discovered>",
                                "type": "string", "approved_update_field": true },
    "queue.last_session_id":  { "entity": "queue_item", "logical_name": "<discovered>",
                                "type": "string", "approved_update_field": true },
    "queue.last_error":       { "entity": "queue_item", "logical_name": "<discovered>",
                                "type": "string", "approved_update_field": true },
    "phone_call.idempotency_key": { "entity": "phone_call_activity",
                                    "logical_name": "<discovered>", "type": "string" },
    "task.idempotency_key":       { "entity": "task",
                                    "logical_name": "<discovered>", "type": "string" }
    // ... Account/Contact/Campaign lookups, owner/team, etc.
  },
  "option_sets": {
    // conceptual queue status -> Dataverse option-set integer value
    "queue_status.ready":     { "field": "queue.status", "value": 0 },
    "queue_status.completed": { "field": "queue.status", "value": 1 },
    "queue_status.blocked":   { "field": "queue.status", "value": 2 },
    "queue_status.dnc":       { "field": "queue.status", "value": 3 }
  },
  "preserve_if_present": ["<logical names of high-confidence fields to never overwrite>"]
}
```

`<discovered>` placeholders are filled by `discover-crm`. The literal logical names and
option-set integers are environment-specific and intentionally not spec-level decisions
(spec §Assumptions).

---

## 3. Config — `config/slice2.toml`

```toml
[run]
default_mode = "dry-run"          # FR-031: dry-run unless --write is passed
campaign = ""                     # default ALF campaign selector (overridable on CLI)

[dataverse]
# env_url is intentionally NOT here — it lives only in the DATAVERSE_ENV_URL
# env var so the runtime has a single source of truth for the connection target.
mapping_artifact = "config/dataverse_mapping.json"
callable_status = "ready"         # FR-011: the queue status that is eligible to call

[retry]                           # FR-023
max_retries = 3
backoff_seconds = [1, 2, 4]
retry_after_cap_seconds = 30

[task_owners]                     # FR-025: default owner per task kind
callback = "<dataverse owner/team id>"
review   = "<dataverse owner/team id>"

[redaction]                       # FR-028..FR-030
policy = "regex"                  # "regex" (default) | "noop"
retention = "full"                # "full" | "summary-only"
# `patterns` is intentionally omitted: defaults live in
# `opencloser.models._BUILTIN_REDACTION_PATTERNS` (phone + email) and are
# applied by `RedactionPolicyConfig`'s default_factory. Keeping the list in
# code as the single source of truth avoids the TOML-vs-code drift that the
# inline example previously caused (Copilot PR #3 LOW, closed by commit
# `0a5b3b7`). Operators wanting custom patterns add them explicitly:
#   patterns = ["\\bMRN-\\d{6}\\b", ...]
```

Secrets are **never** in this file — `DATAVERSE_TENANT_ID`, `DATAVERSE_CLIENT_ID`,
`DATAVERSE_CLIENT_SECRET`, `DATAVERSE_ENV_URL` come from environment variables (FR-005).

---

## 4. New Pydantic models (`src/opencloser/models.py`, additive only)

| Model | Fields (brief) | Purpose |
|---|---|---|
| `RunMode` | enum: `dry_run` \| `write_enabled` | FR-031 |
| `DataverseMapping` | parsed `dataverse_mapping.json` (`_meta`, `entities`, `fields`, `option_sets`, `preserve_if_present`) | FR-004; the adapter's translation source |
| `MetadataVerificationReport` | `ok: bool`, `missing: list[str]`, `drift: list[str]`, `checked_at` | FR-001/FR-002 output |
| `CrmCorrelation` | mirrors `crm_correlations` row | FR-024 |
| `WriteBackProgress` | mirrors `writeback_progress` row | FR-023 resume ledger |
| `RedactionPolicyConfig` | `policy`, `retention`, `patterns` | FR-028 |
| `DataQualityWarning` | `code`, `field`, `message` | FR-034 phone-quality warning |

**Reused unchanged** (Slice 1 — `contracts/*` + `models.py`): `QueueItem`,
`EligibilityDecision`, `Session`, `MockCallEvent`, `NormalizedResult`,
`PhoneCallActivityPayload`, `QueueStatusUpdatePayload`, `TaskPayload`, `WriteBack`,
idempotency-key composition, and the transport/conversation fixture formats. The
`DataverseWriteBackAdapter` consumes the exact `*Payload` shapes — `TaskPayload.assigned_to`
(optional in Slice 1) is now populated from `[task_owners]` (design.md decision #5).

---

## 5. Dataverse-side records (translation targets — not locally stored)

| Conceptual payload | Dataverse target | Translation owner |
|---|---|---|
| `PhoneCallActivityPayload` | `phonecall` activity (POST), idempotency key stamped on the mapped column | `DataverseWriteBackAdapter.emit_phone_call_activity` |
| `QueueStatusUpdatePayload` | queue-item row (PATCH) — status / attempt / DNC / last-disposition / last-session / last-error fields | `emit_queue_status_update` |
| `TaskPayload` | `task` activity (POST), `assigned_to` → `ownerid` lookup, idempotency key stamped | `emit_task` |

Only fields in the mapping artifact's `approved_update_field` set are written; everything in
`preserve_if_present` (and any non-mapped field) is left untouched and absent from the PATCH
body (FR-003).

---

## 6. Deferred Slice 1 cleanup (optional, low priority)

`specs/001/contracts/transport.md` notes a deferred cleanup: splitting a session-less
`TransportEvent` type out of the shared `MockCallEvent`. It is **not** required for Slice 2
correctness and is **not** a Slice 1 contract change that FR-014 forbids — it is recorded
here only so `/speckit-tasks` can optionally schedule it as low-priority hygiene.
