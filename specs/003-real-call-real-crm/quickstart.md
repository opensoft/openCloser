# Quickstart: Slice 3 — Real Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Contracts**: [contracts/](./contracts/) · **Created**: 2026-05-25

This quickstart walks an operator through one Slice 3 invocation end-to-end — rehearsal
first, then real-call / write-enabled — and explains how to interpret the readiness report,
the run report, and the local audit artifacts without a custom openCloser UI (FR-038).

Slice 3 prerequisites: Slice 2's Dataverse adapter, mapping artifact, idempotency-key
stamping, bounded retry, and resume coordinator are already in place from prior work.

---

## 1. One-time setup

### 1.0 Cold-start checklist (R4-Q35)

Before the first Slice 3 invocation on a fresh checkout, complete the cold-start steps below
in order. Each is required for a real-call run; rehearsal mode (§2) exercises the same
readiness gates without dialing.

1. **Install provider clients** — `uv sync` (see §1.1) installs the `signalwire` and
   `pipecat-ai` extras alongside the runtime + dev deps; no separate provider-client install
   step is needed.
2. **Place the shadow-STT discrepancy-policy file** — drop the policy JSON at
   `config/shadow_stt_discrepancy_policy.json` (the `[shadow_stt].discrepancy_policy_path`
   value in §1.3). When shadow STT is enabled, a missing or malformed policy file is a
   readiness failure (exit `4`, FR-009 / R4-Q2) — it is never silently treated as
   all-benign or all-uncertain.
3. **Initialize / migrate the SQLite store** — run the Slice 3 migration to add the additive
   columns and the three new tables (`CallEvent`, `CallbacksAuditLog`, plus the Slice 3
   session columns); Slice 3 is forward-only (R4-Q31):

   ```bash
   opencloser db-migrate            # applies the additive Slice 3 schema (backward-compatible)
   ```

   `db-migrate` is idempotent and safe to re-run (R7): running it against an already-migrated
   or partially-migrated SQLite store is a no-op for already-present columns/tables and never
   errors or loses data. Each additive step (`ALTER ADD COLUMN`, `CREATE TABLE`) is applied
   conditionally (add-if-missing), so if a first run is interrupted you simply re-run
   `opencloser db-migrate` and it completes the remaining steps — no manual SQL and no need to
   reset the store.

4. **Provision the FastAPI callback receiver** — real-call mode binds a port via `uvicorn` to
   receive SignalWire status/media callbacks. The callback-URL templates in §1.3 must be
   reachable from the SignalWire side over TLS (HTTPS); terminate TLS at your ingress and
   forward to the receiver. Signature verification (FR-008) runs on every callback, so the
   ingress must preserve the SignalWire signature header.
5. **Verify Slice 2 prerequisites** — confirm the Dataverse mapping artifact exists and live
   verification passes (see §1.4). The Slice 2 Dataverse adapter, mapping artifact,
   idempotency-key stamping, bounded retry, and resume coordinator must already be in place.

### 1.1 Install / build

```bash
# from the openCloser repo root
uv sync                           # installs runtime + dev deps incl. signalwire, pipecat-ai extras
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

**Configuration precedence (Round 3)**: for any overlapping non-secret setting the order is
**CLI flag > environment variable > `config/slice3.toml` > built-in default**. The three
timeouts below are the documented defaults; a set `SLICE3_ABANDONMENT_TIMEOUT_SEC` /
`SLICE3_SILENCE_AFTER_CONNECTION_TIMEOUT_SEC` / `SLICE3_GRACE_WINDOW_SEC` env var overrides
the corresponding `[timeouts]` value. Secrets (§1.2) are env-var-only and have no TOML surface.

Edit `config/slice3.toml`:

```toml
[signalwire]
transport = "real"                           # "real" (default) or "fixture"; "fixture" is debug-only (R4-Q4)
source_caller_id = "+15555550100"           # E.164; must be authorized for outbound dialing
status_callback_url_template = "https://your-callback.example.com/sw/status/{session_id}"
media_callback_url_template  = "https://your-callback.example.com/sw/media/{session_id}"

[realtime_ai]
# Provider/model identity recorded on every session per FR-016 (credentials live in env vars)
provider_name = "openai-realtime"
model_name    = "gpt-4o-realtime-preview"
model_version = "2024-12-17"
disclosure_pause_ms = 1500                    # FR-015 / R4-Q10: pause after the disclosure; absence of opt-out within it = implicit acknowledgment

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
# `policy` is a distinct knob from the default-on `[REDACTED]` / `[PHI-REDACTED]` coverage:
#   - "default"  → default-on redaction across transcript + summary + shadow transcript +
#                  shadow discrepancy records (pointer metadata excluded).
#   - a configured replacement string → same coverage, different marker.
#   - "disabled" → turns default-on redaction ENTIRELY OFF. This is the ONLY value that
#                  fully disables redaction, and it is never silent: the run emits a PROMINENT
#                  warning on BOTH surfaces (R4-Q18) — (1) a startup warning on stderr and
#                  (2) a warning recorded in `run_report.json` — so a reviewer can always tell
#                  from either the console or the artifact that redaction was off.
# Redaction is never silently off; absence of `policy` or any value other than "disabled"
# keeps redaction on.
```

### 1.4 Verify Slice 2 prerequisites are still healthy

```bash
opencloser dataverse-verify       # confirms mapping artifact + live verification still pass
```

The Slice 2 verified-mapping prerequisite is EXTENDED for Slice 3 (R4-Q34): the same live
verification step additionally confirms that Dynamics accepts the additive
`shadow_stt_discrepancy` review-task reason value (option-set membership) before any real-call
dial. So the verified-mapping deployment artifact is NOT silently assumed unchanged from
Slice 2 — if you have enabled shadow STT, register the `shadow_stt_discrepancy` reason in the
Dynamics review-task reason option set first, or the readiness check fails (exit `4`).

---

## 2. Rehearsal / readiness run (always do this first)

For a real-call demo, ALWAYS start with a rehearsal run against the same queue item. This
verifies readiness without placing any call or mutating Dynamics.

**Non-interactive / CI invocation (R4-Q38)**: every input is supplied via flags or
`config/slice3.toml` — the CLI never prompts interactively, so both rehearsal and real-call
runs are safe to drive from CI or a non-interactive shell. The rehearsal-resume disclosure
("what would have been written") surfaces in `run_report.json`, not in stdout-dependent
prompts.

```bash
opencloser run3 \
  --campaign-id   ALF-CAMP-001 \
  --queue-item-id 11111111-2222-3333-4444-555555555555 \
  --operator-id   alice@medx.example
```

Note: no `--real-call` / `--write` flag → rehearsal mode (FR-002, SC-011).

### Stdout run-mode echo (R4-Q36)

At the very start of every invocation — before any readiness check, dial, or mutation — the
CLI prominently echoes the resolved run mode on stdout so a first-time operator can confirm
the mode *before* a real call could dial. A rehearsal run prints:

```text
=== openCloser run3 ===
RUN MODE: REHEARSAL (no --real-call / --write flag) — no call will be placed, no Dataverse mutation
session_id: sess_2026-05-25T14:00:00Z_a7f8
campaign: ALF-CAMP-001  queue-item: 11111111-2222-3333-4444-555555555555  operator: alice@medx.example
```

This banner is the single human-readable confirmation surface; the canonical machine-readable
run mode is `run_report.json` `run_mode` (R4-Q37). The banner is emitted regardless of how the
CLI is invoked, including non-interactive / CI shells.

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
| `1` | Unexpected error — an uncaught exception mapped after redaction-safe logging; check stderr (R4-Q9) |
| `2` | Bad usage — the operator message names the offending / missing argument (R4-Q9) |
| `3` | Concurrent-claim block (someone else is running against this queue item) |
| `4` | Telephony readiness failure — `telephony_readiness.json` names the failing check |
| `7` | Dataverse-unreachable-at-start (Slice 2 metadata-verification gate failed) |

Exit `2` (bad usage) also covers resume-selector misuse (R4-Q39): `--resume` against an
unknown session id exits `2` with a named message, and `--resume` combined with
`--campaign-id` / `--queue-item-id` validates the selectors against the resumed session —
the resume session id wins, and a selector mismatch exits `2`.

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

In real-call mode the same start-of-run stdout banner (R4-Q36, see §2) instead reads:

```text
=== openCloser run3 ===
RUN MODE: REAL_CALL (--real-call) — a real SignalWire call WILL be placed and Dataverse WILL be mutated
session_id: sess_2026-05-25T14:00:00Z_a7f8
campaign: ALF-CAMP-001  queue-item: 11111111-2222-3333-4444-555555555555  operator: alice@medx.example
```

The differing `RUN MODE:` line lets the operator visually confirm a real call is about to dial
before it happens.

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

The `operator_identity` block has two literal shapes; both are shown so you can recognize
each at a glance.

**First-invocation shape** (no resume): `operator_identity.original` is literally `null` and
there is no `resumed_by_summary`. This is the common case — a fresh real-call or rehearsal run
that has never been resumed. Only the `operator_identity` block differs from the full example
below; every other field is identical.

```json
{
  "session_id": "sess_2026-05-25T14:00:00Z_a7f8",
  "run_mode": "real_call",
  "operator_identity": {
    "current": "alice@medx.example",
    "original": null,
    "chain": ["alice@medx.example"]
  }
}
```

**Resume shape** (the full example below) is a resume run (Q44):
`operator_identity.original` is non-null and the report carries the human-readable
"resumed by X, original operator Y" string.

```json
{
  "session_id": "sess_2026-05-25T14:00:00Z_a7f8",
  "run_mode": "real_call",
  "operator_identity": {
    "current": "bob@medx.example",
    "original": "alice@medx.example",
    "chain": ["alice@medx.example", "bob@medx.example"],
    "resumed_by_summary": "resumed by bob@medx.example, original operator alice@medx.example"
  },
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
  "redaction_applied": true,
  "no_phi_no_clinical_reminder": "Slice 3 collects no PHI and makes no clinical claims; review artifacts confirm this.",
  "grace_window_sec": 3,
  "abandonment_timeout_sec": 90,
  "config_identity": {
    "redaction_policy_version": "redaction@1.0.0+sha256:ab12...",
    "retention_policy_version": "retention@1.0.0+sha256:cd34...",
    "disclosure_policy_version": "disclosure@1.0.0+sha256:ef56..."
  },
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
    "discrepancy_summary": {
      "fields_compared": 7,
      "discrepancies": 0,
      "uncertain": 0,
      "per_field": [
        {"field": "captured_email", "classification": "match"},
        {"field": "final_disposition", "classification": "match"}
      ]
    },
    "lane_truncated": false,
    "lane_failed": false,
    "failure_detail": null
  },
  "callbacks_audit_row_count": 5,
  "conflicting_callbacks_audit_row_count": 0,
  "rejected_auth_callbacks_count": 0,
  "started_at": "2026-05-25T14:00:00Z",
  "ended_at":   "2026-05-25T14:03:42Z"
}
```

Field notes:
- `redaction_applied` (R4-Q40) — positive `true|false` indicator that the redaction passes ran.
- `no_phi_no_clinical_reminder` (R4-Q40) — static operator reminder line, always present.
- `abandonment_timeout_sec` (R4-Q14) — the live-call abandonment timeout in effect; on an
  abandonment outcome the report additionally records the elapsed condition.
- `shadow_stt.failure_detail` (R4-Q14) — `{failure_type, at}` when `shadow_stt.lane_failed`
  is `true`, else `null`; reported independently of `lane_truncated` (late-but-present output).
- `shadow_stt.discrepancy_summary` (R4-Q15) — structured
  `{fields_compared, discrepancies, uncertain, per_field:[{field, classification}]}`, not a
  free-form string.
- `config_identity` (R4-Q46) — version/hash of the redaction, retention, and disclosure
  policies so policy changes are themselves auditable. Together with the per-artifact
  `retention_mode` / `created_at` markers below, this is the configuration-audit surface: a
  deployment can confirm which policy version produced each artifact and detect policy drift.
- Per-artifact retention markers (R4-Q46) — every retained artifact additionally carries its
  own `retention_mode` (the `[retention].mode` in effect when it was written) and `created_at`
  timestamp, so the retention posture of each file is self-describing and auditable
  independently of the run report. The run report records the same pair under
  `retention_markers`, for example:

  ```json
  "retention_markers": {
    "transcript.txt":          {"retention_mode": "full_with_redaction", "created_at": "2026-05-25T14:03:40Z"},
    "shadow_discrepancies.jsonl": {"retention_mode": "full_with_redaction", "created_at": "2026-05-25T14:03:41Z"}
  }
  ```

  Because each marker is stamped at write time, changing `[retention].mode` or the redaction
  policy later does NOT retroactively re-stamp already-written artifacts — each file keeps the
  posture it was written under.

On a `do_not_call` outcome, `per_writeback_operation_status[0].operation` is
`queue_status_update.dnc` (Round 2 Q14 DNC-first ordering).

On a resume re-invocation by a different operator (as shown in the example above),
`operator_identity.original` is the original operator's identifier (never null on a resume)
and `operator_identity.current` is the resuming operator's; `operator_identity.resumed_by_summary`
carries the human-readable "resumed by X, original operator Y" string (R4-Q44).
When a session is resumed more than once, `operator_identity.chain` lists every operator in
order (e.g., `["alice", "bob", "carol"]`) so no intermediate resumer is lost. On a resume
run, each `telephony_readiness_summary` entry shows `result: "skipped (resume)"` because
resume never re-dials. `grace_window_sec` shows the FR-029 grace window that applied (set it
to `0` in config to force immediate write-back).

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

Resume-selector rules (R4-Q39):
- `--resume` against an unknown session id exits `2` with a named message.
- `--resume` combined with `--campaign-id` / `--queue-item-id` validates the selectors for
  consistency with the resumed session — the resume session id wins, and a selector mismatch
  exits `2`.

A resume that finalizes a previously-abandoned session (received `answered` but no terminal
event) exits `6` (live-call abandonment), not `0` (R4-Q8).

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

### Non-readiness exit codes (R4-Q9)

These exits are not tied to a specific readiness check:

| Exit code | Meaning | Remedy |
|---|---|---|
| `1` | Unexpected error — an uncaught exception mapped after redaction-safe logging | Check stderr for the redacted error detail; if it recurs, capture stderr + `run_report.json` and file a bug |
| `2` | Bad usage — the operator message names the offending / missing argument | Fix the named argument and re-run; for resume, see the resume-selector rules in §5 (unknown session id or selector mismatch both exit `2`) |

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

---

## Round 4 — Checklist-Residual Alignment (2026-06-01)

This quickstart was updated to propagate the spec's Round 4 (checklist residual closure)
decisions. Changes:

- **§1.0 (new) cold-start checklist (R4-Q35)** — documents provider-client install (covered
  by `uv sync` extras), shadow-policy file placement at
  `config/shadow_stt_discrepancy_policy.json`, the SQLite migration/init command
  (`opencloser db-migrate`), the FastAPI callback-receiver ingress/TLS expectations (real-call
  mode binds a `uvicorn` port for SignalWire callbacks over HTTPS), and the Slice 2
  prerequisite list (mapping + verify).
- **§1.3 [signalwire] (R4-Q4)** — added `transport = "real"` with a note that `"fixture"` is
  debug-only.
- **§1.3 [redaction] (R4-Q18)** — noted that `policy = "disabled"` emits a prominent startup +
  run-report warning; redaction is never silently off.
- **§2 (R4-Q38)** — noted non-interactive / CI invocation is supported (all inputs via
  flags/config; no interactive prompts).
- **§2/§8 exit codes (R4-Q9/Q39)** — added exit `1` (unexpected error — check stderr) and
  exit `2` (bad usage — names the offending/missing arg) to the exit-code table and added
  remedy rows in §8; documented `--resume` against an unknown session id → exit `2`, and
  `--resume` combined with `--campaign-id` / `--queue-item-id` (resume session id wins;
  selector mismatch → exit `2`).
- **§4 run-report example (R4-Q40/Q14/Q15/Q46)** — added `redaction_applied`, a static
  `no_phi_no_clinical_reminder` line, `abandonment_timeout_sec`, `shadow_stt.failure_detail`,
  a structured `shadow_stt.discrepancy_summary`, and a `config_identity` block.
- **§4/§5 resume identity (R4-Q44)** — the example now shows a non-null
  `operator_identity.original` and the human-readable "resumed by X, original operator Y"
  string.
- **§5 (R4-Q8)** — noted a resume that finalizes a previously-abandoned session exits `6`.

---

## Round 7 — Checklist-Residual Alignment (2026-06-02)

This quickstart was extended to close the Round 7 net-new operator-documentation gaps:

- **§1.0 step 3 db-migrate idempotency (deployment CHK141)** — documented that
  `opencloser db-migrate` is idempotent and safe to re-run against an already-migrated or
  partially-migrated store (add-if-missing steps; interrupted runs are re-runnable, no data
  loss, no manual SQL).
- **§1.3 [redaction] full-disable knob (configuration CHK140)** — expanded the `[redaction].policy`
  comment so `"disabled"` is enumerated as a distinct knob with its mandatory
  "never silently off" dual-warning contract (PROMINENT startup-stderr warning AND a
  `run_report.json` warning).
- **§1.4 verified-mapping Slice-3 extension (configuration CHK142)** — documented that the
  Slice 2 live verification is EXTENDED (R4-Q34) to confirm Dynamics accepts the additive
  `shadow_stt_discrepancy` review-task reason (option-set membership) before any real-call dial.
- **§2/§3 stdout run-mode echo (ux CHK177)** — added literal example stdout banners for both
  REHEARSAL and REAL_CALL run modes (R4-Q36) so a first-time operator can recognize the
  run-mode confirmation before a real call dials.
- **§4 first-invocation run-report shape (ux CHK165)** — added a literal `"original": null`
  first-invocation `operator_identity` JSON example co-present with the existing non-null
  resume example, so both shapes are shown as literal JSON, not prose.
- **§4 per-artifact retention markers + config-audit surface (configuration CHK141)** —
  documented the per-artifact `retention_mode` / `created_at` markers and the run-report
  `retention_markers` block alongside `config_identity` as the configuration-audit surface
  (which policy version produced each artifact; non-retroactive on later policy change).
