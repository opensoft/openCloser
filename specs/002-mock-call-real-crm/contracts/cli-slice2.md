# Contract: Slice 2 CLI & Run Coordination

> Python-flavored pseudo-code for readability; the authoritative contract is the prose.

**Module boundary**: spec FR-031–FR-033, FR-007; constitution principle II
**Implementation**: `src/opencloser/cli.py` (modified) + `src/opencloser/slice2/runner.py`
+ `src/opencloser/slice2/resume.py`
**Owns**: the Slice 2 CLI commands, run-mode selection, and the coordination that calls the
**unchanged** Slice 1 orchestrator and drives resume
**MUST NOT contain**: Dataverse logical names (those stay in `crm/dataverse/`), persona/
eligibility logic, or any modification to the orchestrator contract (FR-014)

---

## Commands

```text
opencloser discover-crm
    # One-time metadata discovery → writes config/dataverse_mapping.json (FR-001/FR-004).

opencloser run-crm [--write] (--queue-item-id ID | --next-ready)
                   [--campaign C]
                   --transport-fixture PATH --conversation-fixture PATH
    # Processes exactly one Dataverse queue item (FR-032).
```

**Run mode (FR-031)**: no `--write` ⇒ **dry-run** (the default — validate mapping, produce
planned write-back artifacts, zero CRM writes). `--write` ⇒ **write-enabled**. There is no
way to mutate CRM without `--write` (SC-013).

**Required inputs (FR-032)**: campaign selector, queue-item selector (explicit ID or
`--next-ready`), transport fixture, conversation fixture, run mode (defaulted).

---

## Behavior — `run-crm`

`slice2/runner.py` coordinates, calling the Slice 1 orchestrator unchanged:

1. Startup/readiness validation — config + (write mode only) secrets (FR-007).
2. `verify` Dataverse metadata; on failure, fail before any write (FR-002).
3. `DataverseQueueLoader.load(selector)` — empty queue ⇒ exit `no-callable-item`, no-op (FR-009).
4. Construct the boundary objects: the existing `EligibilityEvaluator`, the existing mock
   `CallTransport`, the existing `Persona`, and — as the `WriteBackAdapter` — the
   `DataverseWriteBackAdapter` (write mode) or a dry-run capture adapter (dry-run mode).
5. Call `process_one_queue_item(...)` — the orchestrator is **unchanged** (FR-014); it sees
   only the contract interfaces.
6. Map the `RunReport` to a CLI exit status; write the local session-result + (redacted)
   transcript artifacts.

## Behavior — resume

When a write-enabled run exits `resume_needed` (retry budget exhausted mid-write-back),
re-invoking the same command triggers `slice2/resume.py`:

- It reads `writeback_progress` + `crm_correlations` + the persisted write-back payloads,
  and re-issues **only** the missing `emit_*` calls through the `DataverseWriteBackAdapter`
  (whose idempotency pre-query makes each replay safe).
- It does **not** re-run `process_one_queue_item` and does not re-place the mock call —
  keeping the orchestrator contract untouched and producing no duplicate records (FR-023,
  SC-014).
- A re-invocation for an already-`completed` session is a clean no-op (FR-021).
- A re-invocation for a `blocked`-by-conflict session (T045) does NOT auto-resume — the conflict re-read runs first; if the conflict is still present, the run exits `blocked` again with the same `block_reason`. The operator reconciles the Dataverse record manually (restoring the session-owned in-progress state if appropriate, or accepting the human change) before a fresh `run-crm` invocation can complete the missing writes. Abandonment is the absence of a follow-up run; the persisted `writeback_progress` row remains as audit evidence per FR-035.

> **Known limitation (tracked as T052)**: the Slice 1 orchestrator persists
> `writeback.json` only AFTER every `emit_*` succeeds. A natural
> `TransientDataverseError` retry-exhaust mid-write-back therefore leaves
> NO `writeback.json` on disk and `resume_session` raises
> `ResumeError("writeback.json missing")`. The runner-side
> `TransientDataverseError → RESUME_NEEDED` branch is correct and verified
> by `test_us4_natural_transient_exhaust_yields_resume_needed`; the
> orchestrator-side fix (persist a `planned-writeback.json` sidecar before
> emit_* attempts) is **deferred** as T052 — out-of-scope for the Slice 2
> audit-remediation cycle.

---

## Exit-status contract

| Status | Meaning |
|---|---|
| `completed` | loop finished; write-back done (or planned, in dry-run) |
| `blocked` | eligibility/metadata block (SC-008) — no call placed — OR mid-run CRM-state conflict (T045) — partial `writeback_progress` persisted, already-completed approved writes preserved, human-changed values left unchanged. The run-report `block_reason` field disambiguates conflict from eligibility/metadata. |
| `no-callable-item` | empty queue — clean no-op (FR-009) |
| `resume_needed` | transient failure exhausted retry budget — re-invoke to resume |
| `failed` | malformed fixture or permanent error — no attempt consumed (SC-006). Includes `configured_campaign_not_found:` prefix when the configured campaign GUID resolves to zero queue items in Dataverse (spec §Edge Cases "Configured campaign not found", T051). |

All non-`completed` statuses are operator-visible per the spec Definitions §"Operator-visible"
(CLI result + exit status + local run report), never leaking secrets or CRM record contents.

---

## Write-Back Progress State Machine (T050)

The `writeback_progress.run_status` column ([data-model.md §1](../data-model.md#writeback_progress))
takes exactly one of four values at any instant. Entry criteria are mutually exclusive and
exhaustive — every persisted row matches exactly one of the four. The state machine governs
which run-time path (initial run, resume, or no-op) the CLI takes when re-invoked.

### States — mutually exclusive, exhaustive entry criteria

| `run_status`     | Entry criterion (true only of this state)                                                                                                       |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `in_progress`   | The session row exists, at least one `emit_*` has been attempted (or the new-progress placeholder was written at first emit), and **no** terminal event has fired. This is the only non-terminal state. |
| `completed`     | All required `emit_*` for the session's final disposition have completed successfully and `finalize_progress(..., RunStatus.COMPLETED)` has been called. Terminal — no further writes for this session. |
| `resume_needed` | At least one `emit_*` raised a `TransientDataverseError` after the bounded retry budget was exhausted; `flush_pending_failures(failure_run_status=RESUME_NEEDED)` stamped this row. Re-invocation routes to the resume coordinator (`slice2/resume.py`). |
| `blocked`       | EITHER eligibility/metadata permanently failed before any CRM write (orchestrator returned `final_disposition=BLOCKED`, runner mapped to this state) OR a permanent CRM error occurred mid-write-back (`PermanentDataverseError` other than `TransientDataverseError`, `CrmConflictError` from T045 mid-run conflict detection, `MappingError`, `DataverseWriteBackError`). Terminal under normal CLI flow — manual operator reconciliation required for the conflict variant. |

### Allowed transitions

```text
                    ┌──────────────┐
                    │ in_progress  │ ← initial state for any session that issues at least one emit_*
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┬─────────────────┐
            │              │              │                 │
            ▼              ▼              ▼                 ▼
      ┌──────────┐  ┌──────────────┐  ┌─────────┐    (no other targets)
      │completed │  │resume_needed │  │ blocked │
      └──────────┘  └──────┬───────┘  └─────────┘
       (terminal)          │              (terminal under normal CLI flow;
                           │               operator may reset for conflict
                           ▼               via manual reconciliation + new run)
                    ┌──────────────┐
                    │  completed   │ ← resume-replay success
                    └──────────────┘
                           OR
                    ┌──────────────┐
                    │   blocked    │ ← conflict re-detected on resume (CHK061)
                    └──────────────┘
                           OR
                    ┌──────────────┐
                    │resume_needed │ ← replay re-exhausted retry budget (loops)
                    └──────────────┘
```

Exhaustive transition table:

| From              | To               | Trigger event                                                                                                                                          |
|-------------------|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| (new row)         | `in_progress`    | First `emit_*` call writes the new-progress row.                                                                                                       |
| `in_progress`     | `completed`      | All required `emit_*` succeeded; runner calls `adapter.finalize_progress(..., COMPLETED)`.                                                              |
| `in_progress`     | `resume_needed`  | `emit_*` raised `TransientDataverseError` after retry budget exhausted; runner's catch block flushes pending failures with `RESUME_NEEDED`.             |
| `in_progress`     | `blocked`        | Orchestrator returned `final_disposition=BLOCKED` (eligibility/metadata) → `finalize_progress(..., BLOCKED)`. OR adapter raised `CrmConflictError` / `PermanentDataverseError` → runner stamps `BLOCKED`. |
| `resume_needed`   | `completed`      | Resume coordinator replayed all missing `emit_*` successfully; calls `finalize_progress(..., COMPLETED)`.                                              |
| `resume_needed`   | `resume_needed`  | Resume replay itself re-exhausted retry budget; `flush_pending_failures(RESUME_NEEDED)` stamps the row again (idempotent, fires another resume window). |
| `resume_needed`   | `blocked`        | Resume replay hit a permanent error (`PermanentDataverseError`, `CrmConflictError` on resume per CHK061, `MappingError`). Escalates to permanent terminal. |
| `completed`       | (no transition)  | Re-invocation returns `no-resume-needed` (FR-021 idempotent re-invocation); the row is never overwritten.                                              |
| `blocked`         | (no transition)  | Re-invocation returns `blocked` again with the original `block_reason`. For the T045 conflict variant: manual reconciliation in Dynamics + a fresh `run-crm` invocation (not `--resume`) creates a NEW session row with its own state machine. |

### `run_status` → CLI exit-status mapping

| `run_status`     | CLI exit-status (`run-crm` or `--resume`)                                                                                              |
|------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| `in_progress`    | Not surfaced as a terminal exit (a `run-crm` that crashes mid-flight leaves this state behind; a `--resume` against it returns `failed` per `resume.py` "refuse to race"). |
| `completed`      | `completed` (exit 0). Re-invocation: `no-resume-needed` (exit 0).                                                                       |
| `resume_needed`  | `resume_needed` (exit 2). Re-invocation routes to `slice2/resume.py`.                                                                  |
| `blocked`        | `blocked` (exit 1). The run-report's `block_reason` field disambiguates the variant (eligibility/metadata vs T045 conflict_detected).   |

### Operator-visible distinction (CHK052)

Every state surfaces an operator-visible label via the run report's `message` and the
process exit status. Specifically:

- `in_progress` rows are not normally observed because the runner always transitions out
  before returning. If observed (orphan from a crash), `--resume` returns `failed` with the
  message `session ... is in 'in_progress' — refuse to replay rather than racing`.
- `completed` surfaces as exit code 0 with `message="..."` confirming the loop finished.
- `resume_needed` surfaces as exit code 2 with `message="dataverse write failed: ..."` and
  the resume invocation message lists which operations were replayed.
- `blocked` surfaces as exit code 1 with `message` carrying either the eligibility/metadata
  block reason OR `conflict_detected: queue item ..., conflicting fields: ...` (T045).
  The two variants are distinguishable by the `conflict_detected` prefix.

---

## Run Report (T049 — addresses CHK046-CHK049)

The **run report** is the runner's structured outcome record. Its canonical Python
representation is `CrmRunReport` (a dataclass in `slice2/runner.py`); its on-disk
manifestation today is the existing per-session artifacts
([`session-result.json`](#cross-artifact-consistency-chk049), `writeback.json`,
`task.json`, the `crm_correlations`/`writeback_progress` SQLite rows) plus the CLI's
stdout serialization of the dataclass on exit. Future operator tooling MAY persist the
dataclass directly as `run-report.json` under the session's artifact directory; doing so
MUST conform to the JSON shape below.

### Required content (spec §Constitution Alignment §Auditability)

Every processed Dataverse queue item MUST produce a traceable record carrying:

1. **Session ID** — the stable identifier linking every artifact, every Dataverse
   correlation row, and every log line for this run.
2. **Eligibility decision** — the orchestrator's `EligibilityDecision` (allow / blocked +
   reason codes). Carried in the Slice 1 `session-result.json` as the
   `final_disposition` + `blocked_reason` fields.
3. **Mock provider call ID** — populated only when a call was placed (no-callable-item,
   blocked, and dry-run-without-call paths leave this absent).
4. **Persona version** — the `alf-appointment-setter@<semver>` identifier the persona
   contract supplies on every emit_* payload.
5. **Started / ended timestamps** — ISO 8601 UTC millisecond strings matching the
   `UtcMs` model type (`YYYY-MM-DDTHH:MM:SS.sssZ`); identical format across every
   artifact for grep-friendly correlation.
6. **Final disposition** — one of the 11 dispositions enumerated by FR-013.
7. **CRM correlation identifiers** — the `crm_correlations` rows' `idempotency_key` +
   `dataverse_record_id` per `record_kind`. Present only in write-enabled mode.

### JSON shape

> **Implementation note (2026-05-24 Pass 1C + audit-pass)**: the shape below is
> the canonical "future on-disk `run-report.json`" schema. As of this commit
> the `CrmRunReport` dataclass carries `exit_status`, `session_id`,
> `final_disposition`, `artifact_dir`, `queue_item_id`, `metadata_report`,
> `warnings`, `message`, and `block_reason` directly. The remaining documented
> fields (`schema_version`, `started_at`/`ended_at`, `persona_version`,
> `mock_provider_call_id`, `eligibility_decision`, `run_mode`, `crm_correlations`,
> `writeback_progress`) are reconstructable today from `session-result.json`,
> `writeback.json`, `task.json`, and the `crm_correlations` / `writeback_progress`
> SQLite rows. A future `write_run_report(...)` writer in
> `artifacts/writer.py` would compose them into a single JSON artifact per
> this contract.

```jsonc
{
  "schema_version": "slice2-run-report-v1",
  "exit_status": "completed | blocked | no-callable-item | resume_needed | failed",
  "session_id": "ses_2026-05-22T19-00-00Z_q-test-0001",  // null when no session was created
  "queue_item_id": "22222222-2222-2222-2222-222222222222",  // null only on hard pre-claim failures
  "final_disposition": "interested_callback_requested",  // null when no call was placed
  "started_at": "2026-05-22T19:00:00.000Z",
  "ended_at": "2026-05-22T19:00:12.345Z",
  "persona_version": "alf-appointment-setter@0.1.0",
  "mock_provider_call_id": "call_2026-05-22_q-test-0001",  // null when no call was placed
  "eligibility_decision": {
    "allowed": true,
    "blocked_reason": null
  },
  "metadata_report": {                       // FR-001 verify() report
    "ok": true,
    "missing": [],
    "drift": [],
    "checked_at": "2026-05-22T19:00:00.500Z"
  },
  "warnings": [                               // FR-034 data-quality warnings (any mode)
    {"code": "non_e164_phone", "field": "queue.phone", "message": "..."}
  ],
  "message": "completed",                     // operator-visible summary; for `blocked` carries
                                              // `conflict_detected: ...` or the eligibility/metadata reason
  "block_reason": null,                       // populated for `blocked` exits: `eligibility | metadata | conflict_detected | permanent_other` (Pass 1C)
  "artifact_dir": "/var/openCloser/artifacts/ses_2026-05-22T19-00-00Z_q-test-0001",
  "run_mode": "write_enabled | dry_run",
  "crm_correlations": [                       // write-enabled ONLY (see field-set table below)
    {
      "record_kind": "phone_call_activity",
      "idempotency_key": "ses_2026-05-22T19-00-00Z_q-test-0001",
      "dataverse_record_id": "00000000-0000-0000-0000-000000000001",
      "write_status": "confirmed"
    },
    {"record_kind": "queue_status", "idempotency_key": "ses_...", "dataverse_record_id": "22222222-...", "write_status": "confirmed"},
    {"record_kind": "task",         "idempotency_key": "ses_...", "dataverse_record_id": "00000000-...000002", "write_status": "confirmed"}
  ],
  "writeback_progress": {                     // write-enabled ONLY
    "phone_call_activity_done": true,
    "queue_status_update_done": true,
    "task_done": true,
    "run_status": "completed",
    "last_error": null
  }
}
```

### Worked examples — non-completed `writeback_progress.run_status` (Pass 2B)

`resume_needed` (transient retry budget exhausted mid-write-back; later
re-invocation routes to `slice2/resume.py`):

```jsonc
"writeback_progress": {
  "phone_call_activity_done": true,
  "queue_status_update_done": false,
  "task_done": false,
  "run_status": "resume_needed",
  "last_error": "dataverse write failed: Dataverse returned HTTP 503 for POST <env>/api/data/v9.2/tasks"
}
```

`blocked` (T045 conflict-stop variant — manual reconciliation required;
`exit_status="blocked"`, `block_reason="conflict_detected"`):

```jsonc
"writeback_progress": {
  "phone_call_activity_done": true,
  "queue_status_update_done": false,
  "task_done": false,
  "run_status": "blocked",
  "last_error": "mid-run CRM-state conflict on queue item 'q-test-0001': the following field(s) changed since load: medx_lastsessionid, medx_priority"
}
```

### Dry-run vs write-enabled field set (CHK048)

| Field                                         | Dry-run | Write-enabled |
|-----------------------------------------------|:-------:|:-------------:|
| `schema_version`, `exit_status`, `session_id`, `queue_item_id`, `started_at`, `ended_at` | ✓ | ✓ |
| `final_disposition`, `persona_version`, `mock_provider_call_id`, `eligibility_decision`  | ✓ | ✓ |
| `metadata_report`                              | ✓ (write-enabled may fail; dry-run tolerates per `_is_dry_run_tolerable_verify_failure`) | ✓ |
| `warnings`, `message`, `block_reason`, `artifact_dir` | ✓ | ✓ |
| `run_mode`                                     | ✓ (`"dry_run"`) | ✓ (`"write_enabled"`) |
| `crm_correlations`                             | absent (no CRM writes) | ✓ |
| `writeback_progress`                           | absent (no resume ledger row written) | ✓ |

A missing field in dry-run is therefore not a defect — operators inspecting the report can
distinguish the two modes by the presence/absence of `crm_correlations` /
`writeback_progress`, or directly via `run_mode`.

### Cross-artifact consistency (CHK049)

The same `session_id` MUST appear in every artifact this run produces, in every Dataverse
record stamped via the idempotency key, and in every persisted SQLite row for the session:

| Artifact                     | session-id field            | correlation-id field                  | timestamp format |
|------------------------------|-----------------------------|---------------------------------------|------------------|
| Run report (this contract)   | `session_id`                | `crm_correlations[].dataverse_record_id` | ISO ms UTC `YYYY-MM-DDTHH:MM:SS.sssZ` |
| `session-result.json` (FR-014) | `session_id`              | n/a (Slice 1 artifact)                | ISO ms UTC                         |
| `writeback.json` (Slice 1)   | each payload's `session_id` | implicit (Dataverse records carry the idempotency key) | ISO ms UTC          |
| `crm_correlations` row       | `session_id`                | `dataverse_record_id`                 | `created_at` / `updated_at` ISO ms UTC |
| `writeback_progress` row     | `session_id`                | n/a (linkage is via session_id)       | `updated_at` ISO ms UTC            |
| Dataverse record (PCA, Task) | `medx_idempotencykey` = session_id | the record's primary id        | n/a (Dataverse-owned)               |

Implementation pointer: `CrmRunReport` is defined at `src/opencloser/slice2/runner.py` and
its docstring links back to this contract; any future on-disk serializer
(e.g. `write_run_report(...)` in `artifacts/writer.py`) MUST emit the shape above.

---

## Dependencies

- **Allowed**: `opencloser.slice2.*`, `opencloser.core.orchestrator` (call only, unchanged),
  `opencloser.crm.dataverse.*`, `opencloser.crm.base`, `opencloser.redaction`,
  `opencloser.transport`, `opencloser.eligibility`, `opencloser.persona`,
  `opencloser.artifacts`, `opencloser.state`, `typer`.
- **Forbidden**: modifying the orchestrator/eligibility/persona/transport contracts;
  Dataverse logical names outside `crm/dataverse/` (SC-010).
