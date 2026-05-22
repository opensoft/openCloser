# Quickstart: Slice 2 — Mock Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Created**: 2026-05-22

Operator/developer quickstart for running one Dataverse-owned ALF queue item through the
Slice 2 loop. The **dry-run** path needs no write permissions and is the default and the
safe demo posture; the **write-enabled** path mutates one dedicated test record in Dynamics.

---

## 1. Prerequisites

- Python 3.12+, `uv`, the repo installed: `uv sync`.
- A Dynamics 365 / Dataverse environment with one test ALF campaign and one `ready` test
  queue record.
- A Microsoft Entra ID app registration (service principal) with Dataverse access.

## 2. Configure secrets (environment variables)

```bash
export DATAVERSE_ENV_URL="https://<org>.crm.dynamics.com"
export DATAVERSE_TENANT_ID="<tenant-guid>"
export DATAVERSE_CLIENT_ID="<app-registration-client-id>"
export DATAVERSE_CLIENT_SECRET="<app-registration-secret>"
```

Secrets MUST come from the environment — never `config/slice2.toml`, never logs or artifacts
(FR-005). Dry-run does not require these (FR-031 / spec §Edge Cases).

## 3. One-time: discover & verify CRM metadata

```bash
opencloser discover-crm
```

Inspects the live Dataverse schema and writes `config/dataverse_mapping.json` (FR-001/FR-004).
**Review that file in a PR** and set `_meta.approved = true` — this is the approval gate for
write-enabled runs (FR-024). If a required table/field/lookup/option-set or an
idempotency-key field cannot be verified, discovery fails and names the gap (FR-002, SC-007,
SC-015) — fix the mapping or the environment and re-run.

## 4. Configure the run

Edit `config/slice2.toml`: set the ALF `campaign`, `callable_status`, the `[task_owners]`
callback/review owner IDs, and the `[redaction]` policy. See
[data-model.md §3](./data-model.md#3-config--configslice2toml).

## 5. Dry-run rehearsal (zero CRM writes — default)

```bash
opencloser run-crm --queue-item-id <dataverse-guid> \
  --transport-fixture tests/fixtures/transport_events/<id>.json \
  --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json
```

No `--write` flag ⇒ dry-run (FR-031, SC-013). The run validates the mapping, exercises
eligibility + mock call + persona, and writes **planned** write-back artifacts locally
(`artifacts/{session_id}/`) — and creates/updates **zero** Dataverse records (SC-002). Inspect
the planned Phone Call activity, queue-status update, and Task; confirm in Dynamics that
nothing changed.

## 6. Write-enabled run (mutates one test record)

```bash
opencloser run-crm --write --queue-item-id <dataverse-guid> \
  --transport-fixture tests/fixtures/transport_events/<id>.json \
  --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json
```

`--write` is required for any CRM mutation. The run performs metadata verification, claims
the item, runs the mock loop, and writes back: a Phone Call activity, queue-status/attempt/
DNC/last-* field updates, and (when the disposition warrants) a callback or review Task
assigned to the configured owner (SC-001, SC-003).

Verify in Dynamics: the queue item's status/attempt/last-disposition/last-session fields,
one Phone Call activity, and at most one Task — plus the local `artifacts/{session_id}/`
session result and the (redacted) transcript pointer (SC-012).

## 7. Resume after a transient failure

If a write-enabled run exits with `resume_needed` (the retry budget was exhausted mid-write-
back), simply re-invoke the **same** command. The resume coordinator replays only the missing
write-back operations from the persisted payloads — no duplicate Phone Call activity, Task,
queue-status transition, or attempt increment (FR-023, SC-014).

## 8. Demo cleanup / rollback

The write-enabled demo mutates one dedicated test queue record. To roll back: reset that
record's status/attempt/DNC/last-* fields to their pre-demo values, and delete the
demo-created Phone Call activity and Task. Operational rollback only — Slice 1 mock behavior
is unaffected (design.md §Migration Plan).

## 9. CLI exit statuses

| Status | Meaning |
|---|---|
| `completed` | the loop finished; write-back done (or planned, in dry-run) |
| `blocked` | eligibility/metadata blocked the run; no call placed |
| `no-callable-item` | empty queue — clean no-op (FR-009) |
| `resume_needed` | transient failure exhausted the retry budget — re-invoke to resume |
| `failed` | malformed fixture or permanent error — no attempt consumed |

## 10. Tests

```bash
uv run pytest                       # all tests
uv run pytest tests/contract        # adapter vs. contracts/crm-writeback.md (SC-011)
uv run pytest tests/integration     # US1–US6 against the in-process Dataverse fake
```

No live Dataverse is used by the test suite — integration tests run against an in-process
Dataverse fake (research.md §10).
