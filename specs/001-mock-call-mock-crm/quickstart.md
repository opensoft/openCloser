# Quickstart: Slice 1 — Mock Call, Mock CRM

**Plan**: [plan.md](./plan.md)
**Spec**: [spec.md](./spec.md)
**Audience**: developers + sales operators running a fixture-driven demo

> This quickstart describes the **operator surface** of Slice 1 as designed by `plan.md`. The actual implementation lands during `/speckit.implement`; running these commands before then will not succeed.

---

## Prerequisites

- Python 3.12 or 3.13
- [`uv`](https://docs.astral.sh/uv/) (one-command Python project manager)
- Git checkout of the openCloser repo, on the `001-mock-call-mock-crm` feature branch (worktree path: `../openCloser-worktrees/001-mock-call-mock-crm/`)

---

## 1. Bootstrap

```bash
cd /workspace/projects/openCloser-worktrees/001-mock-call-mock-crm

# Install deps + create venv (handled by uv)
uv sync

# Initialize the local SQLite state store (idempotent)
uv run opencloser init-state
```

This creates `./state/slice1.db`, applies `src/opencloser/state/schema.sql`, and seeds the `schema_meta` table with `slice1-v1`.

---

## 2. Load a queue fixture

A queue-item fixture is a JSON file under `tests/fixtures/queue_items/`. Example:

```json
{
  "queue_item_id": "alf-prospect-001",
  "facility_name": "Sunset Ridge ALF",
  "phone_number": "+15555550100",
  "timezone": "America/Los_Angeles",
  "email": null,
  "attempt_count": 0,
  "dnc_flag": false,
  "callable_status": "ready"
}
```

Load it into the state store:

```bash
uv run opencloser load-queue-item \
    --file tests/fixtures/queue_items/alf-prospect-001.json
```

---

## 3. Run Slice 1 end-to-end on that record

```bash
uv run opencloser run-one \
    --queue-item-id alf-prospect-001 \
    --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json \
    --transport-fixture tests/fixtures/transport_events/connected.json
```

Expected output (CLI):

```text
session_id:              ses_2026-05-19_142301_a1b2
eligibility:             allow
mock_provider_call_id:   call_2026-05-19_142301_x9
final_disposition:       interested_callback_requested
wall_time_ms:            1842
artifact_dir:            ./artifacts/ses_2026-05-19_142301_a1b2/
artifacts:
  session-result.json
  writeback.json
  task.json
  transcript.txt
  eligibility-decision.json
```

---

## 4. Inspect the exported artifacts

```bash
ls ./artifacts/ses_2026-05-19_142301_a1b2/
```

You should see five JSON files plus `transcript.txt`. The most interesting ones for SC-007 inspectability:

```bash
cat ./artifacts/ses_2026-05-19_142301_a1b2/session-result.json
# Shows: final_disposition, summary, captured_email,
#        callback_requested, preferred_callback_window,
#        transcript_pointer, started_at, ended_at, ...

cat ./artifacts/ses_2026-05-19_142301_a1b2/writeback.json
# Shows: phone_call_activity, queue_status_update, task
#        (each populated per FR-031)
```

For an `interested_callback_requested` outcome, you should see:
- `writeback.json` → `task.task_kind == "callback"`, `task.preferred_callback_window == "Thursday 14:00"`
- `writeback.json` → `queue_status_update.new_status == "ready"` (per FR-032)
- `session-result.json` → `callback_requested == true`

---

## 5. Demonstrate a blocked-by-eligibility outcome

```bash
# Load a queue record with DNC flag set
uv run opencloser load-queue-item \
    --file tests/fixtures/queue_items/alf-prospect-dnc.json

# Run it — no conversation/transport fixture needed
uv run opencloser run-one --queue-item-id alf-prospect-dnc
```

Expected:
- `final_disposition: blocked`
- `mock_provider_call_id: <none>`
- `eligibility: block`
- Artifact dir contains `eligibility-decision.json` with `failing_rules: ["d"]` and no `phone_call_activity` in `writeback.json`

---

## 6. Demonstrate idempotency (SC-005, Story 3)

Re-run the same scenario with a transport fixture that re-delivers events:

```bash
uv run opencloser run-one \
    --queue-item-id alf-prospect-001 \
    --conversation-fixture tests/fixtures/conversations/interested_callback_requested.json \
    --transport-fixture tests/fixtures/transport_events/duplicate_connected.json
```

The exported `session-result.json` and `writeback.json` MUST be byte-identical to the first run (per SC-005 + the deterministic JSON serialization decision in research.md §JSON). The `attempt_count` MUST NOT increment a second time (per FR-021).

---

## 7. Run the test suite

```bash
# All unit + integration tests
uv run pytest

# Just the module-isolation gate (SC-009)
uv run pytest -m module

# A specific module's tests with the rest stubbed out
uv run pytest -m "module(persona)"
```

The dependency-direction lint check is part of `pytest` collection (`tests/test_imports.py`); a violation fails CI.

---

## 8. Reading the artifacts (operator runbook for SC-007)

SC-007 requires that a stakeholder who did not implement Slice 1 can read the exported artifacts and explain the outcome **without consulting source code**. This walkthrough is the validation path; follow it for any session you want to audit.

Open the session directory:

```bash
cd ./artifacts/<session_id>/
```

You will see up to six files. Each is a separate audit lens:

| File | Read it to learn |
|---|---|
| `eligibility-decision.json` | Whether the call was allowed or blocked, which rules ran, and which (if any) failed |
| `session-result.json` | The persona-produced outcome: disposition, summary, extracted email, callback window, human-review reason |
| `writeback.json` | What the CRM saw: Phone Call activity + queue-status transition + Task payload (when applicable) |
| `task.json` | The standalone follow-up Task (callback or review) — duplicate of the `task` key inside `writeback.json` for convenience |
| `transcript.txt` | The full scripted conversation (one turn per line as `[ROLE] TEXT`) — open this when summary alone isn't enough |
| `conflicting-events.json` | Only present when a late-arriving event was rejected; lists each conflicting event with the disposition that was preserved |

**Step-by-step explain-an-outcome flow**:

1. **What happened first?** Open `eligibility-decision.json`. If `outcome == "block"`, read `failing_rules` — the call never went out, and that's why. Skip to the queue-status update in step 4.
2. **What did the call achieve?** Open `session-result.json`. Read `final_disposition` (one of 11 values per FR-013). The `summary` field is the human-readable one-liner; copy-paste it into a status report.
3. **What did the contact say (or not say)?** Read `session-result.json` again. The `captured_email`, `callback_requested`, `preferred_callback_window`, and `human_review_reason` fields are populated as the persona extracted them. If something is missing where you expected it, open `transcript.txt` and search the contact turns directly.
4. **What does the CRM now think?** Open `writeback.json`. The `queue_status_update` block tells you the new lifecycle state of the queue record (per FR-032). The `phone_call_activity` block tells you the call was made (absent if the run was blocked-by-eligibility per FR-017). The `task` block tells you whether a follow-up was scheduled and what kind (`callback` vs `review`).
5. **Anything weird?** If `conflicting-events.json` exists, the transport emitted a late event that would have changed the disposition but was rejected per FR-020. Read it last — it never affects the actual outcome, only the audit trail.

**Demo posture**: when running Slice 1 in front of stakeholders, walk through one happy-path run (e.g., `interested_callback_requested`) using steps 2 → 3 → 4, then walk through one blocked run using step 1 → step 4. This is the canonical Slice 1 demo and is the live-demo validation referenced by FR-026. The CLI's `wall_time_ms` line confirms the SC-001 budget was met.

---

## Configuration

The default config is `config/slice1.toml`:

```toml
[call_window]
start = "09:00"
end = "20:00"

[eligibility]
max_attempts = 5
default_timezone = "America/Los_Angeles"

[artifacts]
dir = "./artifacts"
schema_version = "slice1-v1"

[persona]
version = "alf-appointment-setter@0.1.0"
```

Override any key with an env var of the form `OPENCLOSER_<SECTION>_<KEY>`:

```bash
OPENCLOSER_ELIGIBILITY_MAX_ATTEMPTS=3 \
OPENCLOSER_ARTIFACTS_DIR=/tmp/oc-artifacts \
  uv run opencloser run-one --queue-item-id alf-prospect-001
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `QueueItemNotFound` | item wasn't loaded into the state store | `uv run opencloser load-queue-item --file …` |
| `Eligibility: block, failing_rules: ["c"]` on a record you expected to allow | local time outside call window | check `config/slice1.toml`'s `[call_window]` or override via env vars |
| No `task.json` for an `interested_*` run | persona did not extract `callback_requested` or `captured_email` | inspect `session-result.json` for the extraction shape; verify the conversation fixture's contact turns |
| `IntegrityError: UNIQUE constraint failed: mock_provider_call_id` | trying to re-run with a `mock_provider_call_id` that already exists | re-runs always allocate a fresh `mock_provider_call_id`; this indicates a fixture or test bug |

---

## What this quickstart does NOT cover

- Real telephony (deferred to Slice 2)
- Real Dataverse write-back (deferred to Slice 2)
- Live LLM-driven conversations (deferred to Slice 3+)
- Multi-record batch processing (out of Slice 1 scope, per spec §Assumptions)
- Operator UI (deferred — Slice 1 is CLI-only per FR-025)
