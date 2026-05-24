# Quickstart: Slice 2 — Mock Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Created**: 2026-05-22 · **Finalized**: 2026-05-24 (T042 demo runbook)

Operator/developer quickstart for running one Dataverse-owned ALF queue item through the
Slice 2 loop. The **dry-run** path needs no write permissions and is the default and the
safe demo posture; the **write-enabled** path mutates one dedicated test record in Dynamics.

> **Phase status (2026-05-24)** — Phases 1–8 + Phase 9 polish (T040, T041, T042, T047,
> T049, T050) shipped. The CLI commands (`opencloser discover-crm`, `opencloser run-crm`,
> `run-crm --resume <session-id>`) and the test suites referenced in §10 are all wired
> end-to-end. Live Dataverse demo posture is documented in §6 (write-enabled) + §8 (manual
> cleanup); CI uses an in-process Dataverse fake — no live Dataverse calls in test runs.

---

## 1. Prerequisites

- Python 3.12+, `uv`, the repo installed: `uv sync`.
- A Dynamics 365 / Dataverse environment with one test ALF campaign and **one dedicated
  test queue record** in `ready` status. Use a record you own and can roll back manually
  per §8.
- A Microsoft Entra ID app registration (service principal) with Dataverse access — at
  minimum, read/write on the queue-item table, the Phone Call activity table, the Task
  table, the Account table (lookup), and read on `systemuser` / `team` for owner
  verification.

## 2. Configure secrets (environment variables)

```bash
export DATAVERSE_ENV_URL="https://<org>.crm.dynamics.com"
export DATAVERSE_TENANT_ID="<tenant-guid>"
export DATAVERSE_CLIENT_ID="<app-registration-client-id>"
export DATAVERSE_CLIENT_SECRET="<app-registration-secret>"
```

Secrets MUST come from the environment — never `config/slice2.toml`, never logs or artifacts
(FR-005, FR-035). Dry-run does not require these (FR-031 / spec §Edge Cases "Dry-run
requested but write credentials are absent"). The contract test
`tests/contract/test_no_secrets_in_artifacts.py` (T047) enforces this property by grepping
every produced artifact for known-secret env values.

## 3. One-time: discover & verify CRM metadata

```bash
opencloser discover-crm
```

Inspects the live Dataverse schema and writes `config/dataverse_mapping.json` (FR-001/FR-004).
**Review that file in a PR** and set `_meta.approved = true` — this is the approval gate for
write-enabled runs (FR-024). If a required table/field/lookup/option-set or an
idempotency-key field cannot be verified, discovery fails and names the gap (FR-002, SC-007,
SC-015) — fix the mapping or the environment and re-run.

The mapping artifact also lists `preserve_if_present` field logical names — high-confidence
fields the adapter MUST NOT overwrite (FR-003). The mid-run conflict detector (T045) uses
this list to detect human edits between claim and the final write; see §7.

## 4. Configure the run

Edit `config/slice2.toml`: set the ALF `campaign`, `callable_status`, the `[task_owners]`
callback/review owner IDs, and the `[redaction]` policy. See
[data-model.md §3](./data-model.md#3-config--configslice2toml) for the full schema.

For a first-time demo, leave `[retry]` at its defaults (`max_retries = 3`, backoff
`[1, 2, 4]`, `retry_after_cap_seconds = 30`) per FR-023.

## 5. Dry-run rehearsal (zero CRM writes — default)

```bash
opencloser run-crm --queue-item-id <dataverse-guid> \
  --transport-fixture tests/fixtures/transport_events/connected.json \
  --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json
```

No `--write` flag ⇒ dry-run (FR-031, SC-013). The run validates the mapping, exercises
eligibility + mock call + persona, and writes **planned** write-back artifacts locally
(`artifacts/{session_id}/`) — and creates/updates **zero** Dataverse records (SC-002).
Inspect:

- `artifacts/{session_id}/session-result.json` — the normalized result.
- `artifacts/{session_id}/writeback.json` — the planned Phone Call activity + queue-status
  update + Task payloads (the adapter captured what a write-enabled run WOULD have sent).
- `artifacts/{session_id}/dry-run-marker.json` — the FR-031 marker so an inspector knows
  no Dataverse writes occurred.

Confirm in Dynamics that the queue record is unchanged.

## 6. Write-enabled run (mutates one test record)

```bash
opencloser run-crm --write --queue-item-id <dataverse-guid> \
  --transport-fixture tests/fixtures/transport_events/connected.json \
  --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json
```

`--write` is required for any CRM mutation. The run performs metadata verification, captures
the T045 conflict-detection baseline, claims the item, runs the mock loop, and writes back:

- A **Phone Call activity** stamped with the session ID on `medx_idempotencykey` (per the
  mapping artifact).
- The queue row's **status / attempt-count / DNC / last-disposition / last-session / last-error**
  fields (per the mapping's `approved_update_field` set; non-approved fields including any
  `preserve_if_present` value are absent from the PATCH per FR-003).
- A **callback or review Task** assigned to the configured owner (SC-003) — `interested_*`
  and `needs_human_review` dispositions create a Task; `not_interested`, `wrong_number`,
  `do_not_call`, `failed`, and `blocked` do not (per spec FR-017 + the Slice 1 emission map).

Verify in Dynamics:

- The queue item's status / attempt-count / last-disposition / last-session fields updated.
- Exactly one Phone Call activity for the session, with `medx_idempotencykey` = session ID.
- At most one Task (callback/review) owned by the configured owner.
- The local `artifacts/{session_id}/` directory contains `session-result.json`,
  `writeback.json`, `task.json` (if applicable), and `transcript.txt` (when the redaction
  retention mode is `"full"`).
- SQLite `crm_correlations` and `writeback_progress` tables both have rows for the session
  (queryable via `sqlite3 <state-db> "SELECT * FROM crm_correlations WHERE session_id = '<sid>';"`).

## 7. Recovery flows

### Transient failure → `resume_needed` → resume

If a write-enabled run exits with `resume_needed` (the retry budget was exhausted mid-write-
back), re-invoke with the `--resume <session-id>` flag:

```bash
opencloser run-crm --resume ses_<timestamp>_<queue-id>
```

The resume coordinator (`slice2/resume.py`) reads `writeback_progress` + the persisted
`writeback.json`, replays only the missing `emit_*` operations through the adapter's
idempotency pre-query (FR-024), and snapshots a **fresh conflict-detection baseline** at
resume start (CHK061) so a human change during the pause window also blocks. Result:
exactly one of each record in Dynamics — no duplicate Phone Call activity, Task, queue-
status transition, or attempt increment (FR-023, SC-014).

A re-invocation of an already-`completed` session is a clean no-op (FR-021 idempotent
re-invocation).

### Mid-run CRM conflict (T045) → `blocked` → manual reconciliation

If a human edited the queue row in Dynamics between when the run loaded it and the final
queue-status PATCH (e.g. moved the status to `Completed`, edited a `preserve_if_present`
field), the adapter detects the conflict, refuses the final PATCH, and the runner exits
`blocked` with `message="conflict_detected: ..., conflicting fields: ..."`. The run-report's
`block_reason` field disambiguates this from an eligibility/metadata block.

Recovery steps:

1. Inspect `artifacts/{session_id}/` and the SQLite `writeback_progress` row for the
   session — the `last_error` column carries the conflict description.
2. In Dynamics, reconcile the queue record: either restore the in-progress state the
   session expected, or accept the human change and abandon the run (the persisted
   `writeback_progress` row remains as audit evidence per FR-035).
3. If reconciling for re-processing: issue a fresh `run-crm` invocation (NOT `--resume`).
   A re-invocation of a `blocked`-by-conflict session does not auto-resume; the conflict
   re-check runs first.

See [contracts/cli-slice2.md](./contracts/cli-slice2.md#behavior--resume) for the full
resume-and-conflict behavior.

## 8. Demo cleanup / rollback

The write-enabled demo mutates one dedicated test queue record. To roll back the **CRM
state**:

1. In Dynamics, reset the demo queue record's status / attempt-count / last-disposition /
   last-session / last-error fields to their pre-demo values.
2. Delete the demo Phone Call activity (find it by `medx_idempotencykey = <session_id>`).
3. Delete the demo Task (find it by `medx_idempotencykey = <session_id>`).
4. If the demo set the DNC flag, clear it.

Manual cleanup is the only supported path — Slice 2 does not provide a CLI rollback
subcommand (spec §Assumptions §"Demo posture", §"Out-of-scope: operator pruning
workflow"). Slice 1 mock behavior is unaffected by any of the above.

To preserve **local audit artifacts** for inspection: leave them in place. Per FR-035, local
audit artifacts and FR-023 `crm_correlations` / `writeback_progress` rows are retained for
≥ 90 days (deployments MAY configure longer); the application never auto-deletes them
(see `tests/contract/test_retention_contract.py` — T041 — for the enforcement). Manual CRM
cleanup does NOT sweep the local artifacts; they remain as audit evidence.

If you DO want to remove local artifacts (e.g. between demos), delete the
`artifacts/{session_id}/` directory by hand. The SQLite rows can be left as-is — they
carry no secrets (FR-005 / T047).

## 9. CLI exit statuses

| Status              | Exit code | Meaning                                                                                                    |
|---------------------|----------:|------------------------------------------------------------------------------------------------------------|
| `completed`         | 0         | the loop finished; write-back done (or planned, in dry-run)                                                |
| `blocked`           | 1         | eligibility/metadata blocked the run OR mid-run CRM conflict (T045 — `block_reason` field disambiguates)   |
| `no-callable-item`  | 0         | empty queue — clean no-op (FR-009)                                                                         |
| `resume_needed`     | 2         | transient failure exhausted the retry budget — re-invoke with `--resume <session-id>` to resume            |
| `failed`            | 2         | malformed fixture or permanent error before claim — no attempt consumed (SC-006). Carries `configured_campaign_not_found:` prefix when the configured campaign GUID resolves to zero queue items in Dataverse (T051) |
| `no-resume-needed`  | 0         | `--resume` invoked against an already-completed session (FR-021 idempotent re-invocation)                  |

Full state-machine + run-report schema: [contracts/cli-slice2.md](./contracts/cli-slice2.md).

## 10. Tests

```bash
uv run pytest                                # all tests
uv run pytest tests/unit                     # focused unit suites (incl. T048 adapter)
uv run pytest tests/contract                 # contracts (adapter, boundary T040, no-secrets T047, retention T041)
uv run pytest tests/integration              # US1–US6 + T046 conflict detection against the in-process Dataverse fake
uv run ruff check src/ tests/                # lint
```

No live Dataverse is used by the test suite — integration tests run against an in-process
Dataverse fake (research.md §10; `tests/fixtures/dataverse/fake.py`). The boundary test
(`tests/contract/test_boundary_isolation.py` — T040) enforces SC-010: zero Dataverse vendor
names in the orchestrator / eligibility / transport / persona modules.

## 11. GitHub issue #2

GH issue [opensoft/openCloser#2](https://github.com/opensoft/openCloser/issues/2)
(malformed-fixture pre-validation) was resolved by T035 + T036
(`src/opencloser/transport/mock.py` + the orchestrator `pre_validate_fixture` hook + the
US5 unit + integration tests) and **closed on 2026-05-24** via T043. The closure comment
references PR #4 (US5/US6 foundation) and this section.
