# Quickstart: Slice 3 — Real Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Contracts**: [contracts/](./contracts/) · **Created**: 2026-05-25

This quickstart walks an operator through one Slice 3 invocation end-to-end — rehearsal
first, then real-call / write-enabled — and explains how to interpret the readiness report,
the run report, and the local audit artifacts without a custom openCloser UI (FR-038).

Slice 3 prerequisites: Slice 2's Dataverse adapter, mapping artifact, idempotency-key
stamping, bounded retry, and resume coordinator are already in place from prior work.

---

## 1. One-time setup

### 1.1 Install / build

```bash
# from the openCloser repo root
uv sync                           # installs runtime + dev deps incl. signalwire, pipecat-ai
pytest                            # confirms the Slice 1 / Slice 2 / Slice 3 test suites pass
```

### 1.2 Configure secrets (env vars only — never logged, never in artifacts)

```bash
# SignalWire (FR-008)
export SIGNALWIRE_PROJECT_ID="..."
export SIGNALWIRE_API_TOKEN="..."
export SIGNALWIRE_SIGNING_SECRET="..."      # HMAC-SHA256 shared secret

# Real-time AI provider (FR-013, FR-016)
export SLICE3_REALTIME_PROVIDER="openai-realtime"   # or "google-realtime", etc.
export SLICE3_REALTIME_API_KEY="..."

# Shadow STT (FR-028, FR-032) — set to "disabled" to skip the shadow lane
export SLICE3_SHADOW_STT_PROVIDER="deepgram"        # or "disabled"
export SLICE3_SHADOW_STT_API_KEY="..."

# Dataverse (reused from Slice 2)
export DATAVERSE_TENANT_ID="..."
export DATAVERSE_CLIENT_ID="..."
export DATAVERSE_CLIENT_SECRET="..."
export DATAVERSE_ENV_URL="https://<org>.crm.dynamics.com"
```

### 1.3 Configure non-secret deployment options

Edit `config/slice3.toml`:

```toml
[signalwire]
source_caller_id = "+15555550100"           # E.164; must be authorized for outbound dialing
status_callback_url_template = "https://your-callback.example.com/sw/status/{session_id}"
media_callback_url_template  = "https://your-callback.example.com/sw/media/{session_id}"

[realtime_ai]
# Provider/model identity recorded on every session per FR-016 (credentials live in env vars)
provider_name = "openai-realtime"
model_name    = "gpt-4o-realtime-preview"
model_version = "2024-12-17"

[shadow_stt]
enabled_default = true                       # CLI --shadow-stt / --no-shadow-stt overrides
discrepancy_policy_path = "config/shadow_stt_discrepancy_policy.json"

[timeouts]
# All three timeouts are deployment-configurable per spec §Deferred to Plan
abandonment_sec               = 90           # FR-026 (live-call abandonment)
silence_after_connection_sec  = 30           # FR-013 / Round 1 Q4 (live-runtime degradation)
grace_window_sec              = 3            # FR-029 / Round 2 Q7 (post-finalization grace)

[retention]
mode = "full_with_redaction"                 # or "summary_only" or "pointer_only"

[redaction]
# Default-on per FR-033 / Round 2 Q10; covers transcript + summary + shadow transcript +
# shadow discrepancy records; pointer metadata excluded
policy = "default"
```

### 1.4 Verify Slice 2 prerequisites are still healthy

```bash
opencloser dataverse-verify       # confirms mapping artifact + live verification still pass
```

---

## 2. Rehearsal / readiness run (always do this first)

For a real-call demo, ALWAYS start with a rehearsal run against the same queue item. This
verifies readiness without placing any call or mutating Dynamics.

```bash
opencloser run3 \
  --campaign-id   ALF-CAMP-001 \
  --queue-item-id 11111111-2222-3333-4444-555555555555 \
  --operator-id   alice@medx.example
```

Note: no `--real-call` / `--write` flag → rehearsal mode (FR-002, SC-011).

### Expected outputs

```text
artifacts/sess_2026-05-25T...Z_a7f8/
├── run_report.json                  # run_mode = "rehearsal"
├── telephony_readiness.json         # each readiness check + result
├── planned_writeback.json           # what would have been written to Dataverse
└── (no transcript, no callbacks log — no call was placed)
```

### Expected exit codes

| Exit code | Meaning |
|---|---|
| `0` | Readiness checks passed; planned write-back artifacts produced; no dial; no mutation |
| `3` | Concurrent-claim block (someone else is running against this queue item) |
| `4` | Telephony readiness failure — `telephony_readiness.json` names the failing check |
| `7` | Dataverse-unreachable-at-start (Slice 2 metadata-verification gate failed) |

### What to inspect

1. `telephony_readiness.json` — every check from FR-009 with pass/fail and a human-readable
   detail. Fix any `fail` before the real-call run.
2. `planned_writeback.json` — the Phone Call activity, queue-status update, and Task that
   WOULD have been written. Confirm the per-disposition mapping looks right for the
   expected outcomes.

If anything looks wrong, **stop here**. Do not run the real-call invocation until the
rehearsal is clean.

---

## 3. Real-call / write-enabled run

```bash
opencloser run3 \
  --campaign-id   ALF-CAMP-001 \
  --queue-item-id 11111111-2222-3333-4444-555555555555 \
  --operator-id   alice@medx.example \
  --real-call
```

The `--real-call` flag is REQUIRED for any Dataverse mutation (FR-001 / FR-022 per Round 2
Q13). There is no "sticky" promotion — every Dataverse-mutating invocation must pass this
flag, including resume.

### Expected outputs (real-call mode)

```text
artifacts/sess_<id>/
├── run_report.json                          # run_mode = "real_call"; all fields per FR-036
├── telephony_readiness.json
├── planned_writeback.json
├── actual_writeback.json                    # actually-emitted Dataverse payloads
├── transcript.txt                           # redacted per FR-033 / Round 2 Q10
├── callbacks_audit.jsonl                    # every SignalWire callback received
├── rejected_auth_callbacks.jsonl            # only if any forged callbacks received
├── conflicting_callbacks_audit.jsonl        # only if any late-after-finalization callbacks
├── shadow_transcript.txt                    # if --shadow-stt
├── shadow_discrepancies.jsonl               # if --shadow-stt and any discrepancies
└── shadow_lane_truncated.json               # if --shadow-stt and shadow lane was truncated
```

### Expected Dynamics records

| Disposition | Phone Call activity | Queue-status update | Task | DNC field |
|---|---|---|---|---|
| `interested_callback_requested` | created | updated | callback Task created | — |
| `interested_email_captured` | created | updated | follow-up Task with email | — |
| `not_interested` | created | updated | — | — |
| `call_back_later` | created | updated | callback Task | — |
| `wrong_number` | created | updated | — | — |
| `no_answer` | created | updated | — | — |
| `voicemail` | created | updated | — | — |
| **`do_not_call`** | **created** | **updated (DNC FIRST, Round 2 Q14)** | — | **updated** |
| `needs_human_review` | created | updated | review Task | — |
| `failed` | created if call connected; else skipped | updated | — | — |
| `blocked` | — | blocked-status field only | — | — |

### Expected exit codes

Same as §2 plus:
- `5` — provider-rejected dial (SignalWire 4xx). No attempt consumed; no Phone Call activity.
- `6` — live-call abandonment (no terminal event within the configured timeout). Finalized
  as `failed` / `live_call_abandonment`.

---

## 4. Inspecting the run report

`run_report.json` is the single canonical place to understand what happened. Key fields:

```json
{
  "session_id": "sess_2026-05-25T14:00:00Z_a7f8",
  "run_mode": "real_call",
  "operator_identity": {"current": "alice@medx.example", "original": null},
  "real_provider_call_id": "CA1234abcdef...",
  "persona_version": "alf_appointment_setter@1.0.0",
  "runtime_identity": {
    "runtime": "pipecat",
    "version": "0.0.x",
    "provider": "openai-realtime",
    "model_name": "gpt-4o-realtime-preview",
    "model_version": "2024-12-17"
  },
  "final_disposition": "interested_callback_requested",
  "telephony_readiness_summary": [
    {"check": "signalwire_credentials", "result": "pass", "detail": "..."},
    {"check": "source_caller_id_authorized", "result": "pass", "detail": "..."},
    ...
  ],
  "per_writeback_operation_status": [
    {"operation": "phone_call_activity", "status": "completed"},
    {"operation": "queue_status_update.normal", "status": "completed"},
    {"operation": "task", "status": "completed"}
  ],
  "shadow_stt": {
    "enabled": true,
    "discrepancy_summary": "0 discrepancies",
    "lane_truncated": false
  },
  "callbacks_audit_row_count": 5,
  "conflicting_callbacks_audit_row_count": 0,
  "rejected_auth_callbacks_count": 0,
  "started_at": "2026-05-25T14:00:00Z",
  "ended_at":   "2026-05-25T14:03:42Z"
}
```

On a `do_not_call` outcome, `per_writeback_operation_status[0].operation` is
`queue_status_update.dnc` (Round 2 Q14 DNC-first ordering).

On a resume re-invocation by a different operator, `operator_identity.original` is the
original operator's identifier and `operator_identity.current` is the resuming operator's.

---

## 5. Resume re-invocation (recovering from partial write-back)

If a real-call run failed partway through write-back (Dataverse transient error, orchestrator
crash, etc.), resume the same session:

```bash
opencloser run3 \
  --campaign-id   ALF-CAMP-001 \
  --queue-item-id 11111111-2222-3333-4444-555555555555 \
  --operator-id   bob@medx.example \
  --resume        sess_2026-05-25T14:00:00Z_a7f8 \
  --real-call                                           # REQUIRED per Round 2 Q13
```

The resume coordinator (reused from Slice 2):
- Reads `writeback_progress` to find the last completed step.
- Re-runs only the missing writes, with idempotency-key stamping preventing duplicates.
- On a session that previously received `answered` but no terminal event (Round 2 Q6):
  immediately finalizes as `failed` / `live_call_abandonment` and then completes any
  partial write-back.

If `--real-call` is omitted on resume, the resume runs in rehearsal mode and surfaces what
WOULD have been written — no mutation occurs.

The resuming operator's identity is recorded on the run report alongside the original
operator's (Round 2 Q12).

---

## 6. Toggling shadow STT

The shadow STT lane (FR-028 – FR-032) listens to the same caller audio as the live
conversation path and emits discrepancy events for high-value fields without blocking the
live call.

```bash
opencloser run3 ... --shadow-stt           # explicit enable
opencloser run3 ... --no-shadow-stt        # explicit disable
opencloser run3 ...                        # uses config/slice3.toml [shadow_stt].enabled_default
```

When disabled, the Slice 3 demonstrable loop still completes (FR-032); the run report
records `shadow_stt.enabled = false`.

---

## 7. Demo-evidence checklist (pre-pilot)

For a real-call demo to a stakeholder, collect:

- [ ] Dataverse queue item screenshot **before** the run (status = `ready`, attempt count = N)
- [ ] Dataverse queue item screenshot **after** the run (status, attempt count = N+1,
      last_disposition, last_session_id, DNC fields if `do_not_call`)
- [ ] Phone Call activity screenshot (with `provider_call_id` = SignalWire SID, summary,
      timestamps)
- [ ] Callback or review Task screenshot (assigned to configured owner, with reason if
      `needs_human_review`)
- [ ] Local `run_report.json` (the single canonical narrative)
- [ ] Local redacted `transcript.txt` (subject to retention mode)
- [ ] Local `callbacks_audit.jsonl` (proves callback handling + dedup)
- [ ] Local `rejected_auth_callbacks.jsonl` (if non-empty — proves forgery detection)
- [ ] Local `shadow_transcript.txt` + `shadow_discrepancies.jsonl` (if shadow STT enabled)
- [ ] Local `shadow_lane_truncated.json` (if the shadow lane was truncated)

Map each artifact to the FR / SC it satisfies (the demo-evidence checklist in
`docs/slice3/demo-evidence-checklist.md` enumerates this mapping — `[research.md §13]`).

---

## 8. Common readiness failures and remedies

| Failing check | Likely cause | Remedy |
|---|---|---|
| `signalwire_credentials` | Missing `SIGNALWIRE_PROJECT_ID` / `SIGNALWIRE_API_TOKEN` | Set the env vars |
| `source_caller_id_authorized` | `source_caller_id` in `slice3.toml` not authorized for outbound dialing | Authorize the number in SignalWire dashboard or change the config value |
| `destination_phone_e164` | Queue item phone is missing, blank, or non-E.164 (FR-010) | Fix the contact phone in Dynamics; do NOT proceed with malformed numbers |
| `status_callback_url_configured` / `media_callback_url_configured` | URL missing in `slice3.toml` or unreachable | Configure the receiver and confirm reachability from SignalWire |
| `campaign_persona_runtime_mapping` | Campaign in Dynamics is not mapped to a persona/runtime | Update the campaign mapping (see Slice 2 mapping artifact) |
| `dataverse_metadata_verified` | Live Dataverse mapping verification failed | Run `opencloser dataverse-verify` and fix the reported metadata drift |
| `task_owner_mapping_resolved` | Callback or review Task owner/team not set | Configure the owner/team in the mapping artifact |
| `eligibility` | Slice 1 eligibility rule blocks (DNC, attempt cap, call window, etc.) | This is the expected blocked-status outcome; no remediation needed |

---

## 9. Cross-references

- **Spec**: [spec.md](./spec.md)
- **Plan**: [plan.md](./plan.md)
- **Research / decisions**: [research.md](./research.md)
- **Data model**: [data-model.md](./data-model.md)
- **Contracts**:
  - [signalwire-transport.md](./contracts/signalwire-transport.md)
  - [pipecat-runtime.md](./contracts/pipecat-runtime.md)
  - [shadow-stt-lane.md](./contracts/shadow-stt-lane.md)
  - [crm-writeback-dnc-first.md](./contracts/crm-writeback-dnc-first.md)
  - [rejected-auth-audit-log.md](./contracts/rejected-auth-audit-log.md)
  - [cli-slice3.md](./contracts/cli-slice3.md)
- **Slice 1 / Slice 2 prerequisites**:
  - `specs/001-mock-call-mock-crm/plan.md`
  - `specs/002-mock-call-real-crm/plan.md`
