# Contract: Slice 3 CLI (`opencloser run3`)

**Slice 3** · **FR-001, FR-002, FR-003, FR-022, FR-036, FR-037, FR-038** (+ Round 1 Q5 + Round 2 Q12, Q13) · [plan.md](../plan.md) · [research.md §8, §9, §11](../research.md)

The Slice 3 CLI extends the existing `opencloser` Typer entrypoint with a `run3`
subcommand. It processes exactly one Dataverse-owned ALF queue item per invocation, with
two run modes: rehearsal / readiness (default) and real-call / write-enabled (requires the
explicit `--real-call` / `--write` flag on EVERY invocation — including resume).

## Command shape

```bash
opencloser run3 \
  --campaign-id <id> \
  --queue-item-id <id> \
  [--real-call | --write] \
  [--shadow-stt | --no-shadow-stt] \
  [--operator-id <id>] \
  [--resume <session_id>] \
  [--config <path>]
```

### Options

| Option | Type | Default | Notes |
|---|---|---|---|
| `--campaign-id` | str | (required) | The campaign selector |
| `--queue-item-id` | str | (required) | The Dataverse queue-item selector |
| `--real-call` / `--write` | flag | absent → rehearsal mode | Required for ANY Dataverse mutation, including resume (Round 2 Q13). No sticky / session-inherited promotion. |
| `--shadow-stt` / `--no-shadow-stt` | flag | from `config/slice3.toml` `[shadow_stt].enabled_default` | Toggles the shadow STT lane (FR-032) |
| `--operator-id` | str | `$USER` env var | Captured locally only (FR-016, Round 1 Q3, Round 2 Q12) — never propagated to Dataverse |
| `--resume` | str | (none) | Resumes the named session. The same `--real-call` flag rule applies. |
| `--config` | path | `config/slice3.toml` | Non-secret config file |

## Required behaviors

### Run-mode default (FR-001 / FR-002, SC-011)

Absence of `--real-call` / `--write` → rehearsal / readiness mode:
- Telephony readiness check runs.
- Planned write-back artifacts are produced locally.
- ZERO SignalWire calls placed.
- ZERO Dataverse records created or updated.
- Run report explicitly states `run_mode = "rehearsal"`.

### Single queue item per invocation (FR-003)

The CLI MUST process exactly one queue item per invocation. Batch / multi-item handling
is out of scope.

### Concurrent same-item invocation (FR-003 per Round 1 Q5)

When the queue item is already claimed (`in_progress` or otherwise not `ready`), the CLI
MUST exit with a blocked-by-claim message. NO dial, NO attempt consumed, NO Phone Call
activity, NO Task. The first invocation is unaffected.

### Real-call flag on every Dataverse-mutating invocation (Round 2 Q13)

`--resume` re-invocations MUST supply `--real-call` if they perform any Dataverse mutation.
Absence on a resume invocation:
- Runs in rehearsal mode.
- Surfaces what would have been written in the run report.
- Exits without mutation.

There is no "sticky" or session-inherited flag promotion.

### Resume operator identity (Round 2 Q12)

When `--resume <session_id>` is supplied and the original session's operator identity
differs from the current operator's identity:
- The local session record's `operator_identity_original` field is preserved.
- The `operator_identity_current` field is set to the resuming operator.
- The run report contains `operator_identity: {current: <X>, original: <Y>, chain: [...]}` and the
  resuming operator's identity is also surfaced in a human-readable `resumed_by_summary` field
  ("resumed by X, original operator Y") — this is the canonical run-report key for that string.
- The resume MUST still satisfy `--real-call` per Round 2 Q13.

### Schema-migration subcommand (`opencloser db-migrate`)

The Slice 3 forward-only schema migration (the additive `sessions` columns + the `call_events`
/ `callbacks_audit` / `rejected_auth_callbacks` / `shadow_stt_discrepancies` /
`shadow_lane_truncated_events` tables, and the `cm_`→`crm_writeback_started_at` rename, per
data-model §3) is applied by a distinct `opencloser db-migrate` subcommand — separate from
`run3`. It is additive and backward-compatible (Slice 2 reads ignore the new columns/tables);
the documented rollback posture is restoring a pre-migration database snapshot (R4-Q31). This
is the canonical spelling referenced by quickstart §1.0 and tasks T116.

### Required readiness checks before any dial (FR-009 – FR-012)

For real-call / write-enabled runs, the CLI MUST run the telephony readiness check before
any SignalWire dial. The check MUST cover:
- SignalWire credentials present
- Source caller-id configured and authorized for outbound dialing
- Destination phone number passing E.164 / SignalWire-acceptable validation (FR-010)
- SignalWire status + media callback URLs configured (and reachable when verifiable)
- Real-time AI provider credentials present (`realtime_ai_credentials`) — fails before dial,
  exit 4, no attempt (Round 4 R4-Q1)
- Shadow-STT credentials present (`shadow_stt_credentials`) — checked and fails the run ONLY
  when shadow is explicitly enabled via `--shadow-stt`; when shadow is only default-on from
  config, a missing key disables the lane with a run-report warning instead of blocking the
  demonstrable loop (Round 4 R4-Q1)
- Callback signing-secret present and signature verifiability confirmed — if signature
  verification is unavailable in the deployment, the real-call run refuses to start
  (fail-closed) with a named readiness failure (Round 4 R4-Q1 / R4-Q23)
- Campaign → persona/runtime mapping resolved
- Verified Dataverse mapping (Slice 2 live verification)
- Callback / review Task owner/team mapping resolved
- Local call-window / DNC / attempt eligibility (Slice 1 six rules)

A telephony readiness failure exits before dial, no attempt consumed, no Phone Call
activity, with the failing check named in the readiness report and the run report (FR-011).

A `--resume` invocation NEVER places a new dial (Slice 3 is one dial per session), so the
pre-dial telephony readiness checks are NOT re-evaluated on resume; each readiness entry in
the resume run report is labeled `skipped (resume)` (Round 3). Resume still re-checks the
`--real-call` gate per Round 2 Q13.

### Run report (FR-036, see [research.md §9](../research.md#9-run-report-file-format--naming))

Every invocation MUST produce `artifacts/<session_id>/run_report.json`. Minimum fields per
FR-036 amended by Round 2:
- `run_mode`
- `session_id`
- `operator_identity: {current, original, chain}` — `chain` is the full ordered operator list
  (Round 3); no intermediate resumer dropped
- `real_provider_call_id` (when assigned)
- `persona_version`
- `runtime_identity: {runtime, version, provider, model_name, model_version}`
- `final_disposition`
- `grace_window_sec` — the FR-029 grace window in effect (Round 3)
- `per_writeback_operation_status` (planned / completed / resume-needed / blocked) — ordered;
  reflects DNC-first ordering on `do_not_call` (Round 2 Q14)
- `shadow_stt: {enabled, discrepancy_summary, lane_truncated, lane_failed, failure_detail}` —
  `lane_truncated` and `lane_failed` reported independently (Round 3); `failure_detail` is
  `{failure_type, at}` alongside `lane_failed` (Round 4 R4-Q14); `discrepancy_summary` is the
  structured shape `{fields_compared, discrepancies, uncertain, per_field:[{field, classification}]}`
  — NOT a free-form string (Round 4 R4-Q15 / R4-Q40)
- `abandonment_timeout_sec` — the live-call abandonment timeout value in effect; on abandonment,
  the elapsed condition is also recorded (Round 4 R4-Q14 / R4-Q40)
- `redaction_applied: true|false` — positive indicator that the default-on redaction pass ran,
  plus a static no-PHI / no-clinical operator reminder line (Round 4 R4-Q40)
- `config_identity` — a config-identity block recording a version / hash of the redaction,
  retention, and disclosure policies so policy changes are themselves auditable (Round 4 R4-Q40 / R4-Q46)
- `telephony_readiness_summary` (each readiness check + result; `result` is `skipped (resume)`
  on a resume invocation, which never re-dials — Round 3)
- `callbacks_audit_row_count`
- `conflicting_callbacks_audit_row_count`
- `rejected_auth_callbacks_count`
- `started_at`, `ended_at`
- Any failure or blocked reason (including `redaction_failed` per FR-015 and
  `live_call_abandonment` per FR-026)

### Demo evidence without a custom UI (FR-038)

The CLI MUST provide enough operator evidence — via CLI stdout, the run report, the local
audit artifacts, and the resulting Dynamics records — that an operator can explain a Slice 3
outcome to a stakeholder without a custom openCloser UI. See
[research.md §13](../research.md#13-pre-pilot-demo-evidence-checklist) for the pre-pilot
demo-evidence checklist.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success (run completed; outcome may be any of: real call finalized, rehearsal completed, readiness failure surfaced) |
| `1` | Unexpected error — any uncaught exception, mapped AFTER redaction-safe logging (the global exception handler redacts before any write; check stderr). MUST emit a named operator message (Round 4 R4-Q9). |
| `2` | Bad CLI usage (missing required arg, conflicting flags). ALWAYS emits an operator message naming the offending / missing argument (Round 4 R4-Q9). |
| `3` | Concurrent-claim block (Round 1 Q5) |
| `4` | Telephony readiness failure (FR-009 – FR-011) |
| `5` | Provider-rejected dial (FR-012) |
| `6` | Live-call abandonment (FR-026 / Round 2 Q6) |
| `7` | Dataverse-unreachable-at-start (Slice 2 metadata verification gate) |

Each non-zero exit code corresponds to a specific named outcome in the run report.

### Exit-code behaviors (Round 4 R4-Q9 / R4-Q39)

- **Exit `1` (unexpected)** maps ANY uncaught exception. It is raised only AFTER
  redaction-safe logging — the global exception handler redacts the exception
  message and stack trace before any write (FR-035 / FR-017) — and it MUST emit a
  named operator message.
- **Exit `2` (bad usage)** ALWAYS emits an operator message naming the offending
  or missing argument; it never exits silently.
- **`--resume <session_id>` against an unknown session id** → exit `2` with a named
  message identifying the unknown session id.
- **`--resume` combined with `--campaign-id` / `--queue-item-id`** → the resume
  session id wins; the supplied selectors are validated for consistency against the
  resumed session. A selector mismatch → exit `2` with a named message identifying
  the inconsistent selector.

### Error-message remediation classification (Round 4 R4-Q41)

Operator error messages MUST classify the remediation path as one of `config` /
`transient_provider` / `ineligible`, so the operator knows whether to retry the run
as-is (transient provider), fix configuration first (config), or stop because the
queue item is not eligible (ineligible).

## Contract test summary (`tests/contract/test_cli_slice3.py`)

| Test | Assertion |
|---|---|
| `test_default_invocation_is_rehearsal_mode` | `opencloser run3 --campaign-id X --queue-item-id Y` (no `--real-call`) places 0 SignalWire calls and 0 Dataverse mutations |
| `test_real_call_flag_required_for_mutation` | Real-call invocation without `--real-call` exits in rehearsal mode |
| `test_real_call_flag_required_on_resume` | Resume invocation without `--real-call` runs in rehearsal mode; the run report surfaces planned writes; no mutation occurs |
| `test_resume_preserves_original_operator` | Operator A starts a real-call run; operator B re-invokes with `--resume <sid> --real-call --operator-id B` → run report contains `operator_identity = {current: B, original: A}` |
| `test_resume_preserves_full_operator_chain` | A → B → C resume sequence yields `operator_identity = {current: C, original: A, chain: [A, B, C]}`; no intermediate resumer dropped (Round 3) |
| `test_resume_labels_readiness_checks_skipped` | A resume run report labels each `telephony_readiness_summary` entry `skipped (resume)`; no new dial placed (Round 3) |
| `test_config_precedence_cli_over_env_over_toml` | For an overlapping non-secret setting, a CLI flag overrides an env var, which overrides `config/slice3.toml`, which overrides the built-in default (Round 3) |
| `test_concurrent_claim_exits_with_code_3` | Same `--queue-item-id` invoked while already claimed exits with code 3; no dial, no attempt consumed |
| `test_telephony_readiness_failure_exits_with_code_4` | Each FR-009 readiness check individually failing exits with code 4; readiness report names the failing check |
| `test_provider_rejected_dial_exits_with_code_5` | SignalWire 4xx on dial exits with code 5; no attempt consumed; no Phone Call activity |
| `test_live_call_abandonment_exits_with_code_6` | Configured abandonment timeout elapses → exits with code 6; finalized as `failed`/`live_call_abandonment` |
| `test_run_report_includes_all_required_fields` | After any invocation, `run_report.json` contains all FR-036 (Round 2-amended) fields |
| `test_dnc_first_reflected_in_per_writeback_operation_status` | On a `do_not_call` outcome, `per_writeback_operation_status[0].operation` is `queue_status_update.dnc` |
| `test_no_secrets_in_stdout_or_run_report` | grep for any credential env-var value across stdout + run report returns 0 matches (SC-018) |
| `test_unknown_resume_session_exits_2` | `--resume <unknown_sid>` exits with code 2 and emits a named message identifying the unknown session id (Round 4 R4-Q39) |
| `test_resume_with_selectors_validates_consistency` | `--resume <sid>` combined with `--campaign-id` / `--queue-item-id` resolves to the resumed session (resume wins); a selector that mismatches the resumed session exits with code 2 naming the inconsistent selector (Round 4 R4-Q39) |
| `test_exit_1_and_2_emit_named_messages` | Exit 1 (uncaught exception, after redaction-safe logging) and exit 2 (bad usage) each emit an operator message naming the failure / offending arg; exit 1 message + stderr contain no secret (Round 4 R4-Q9) |

## Round 4 — Checklist-Residual Alignment (2026-06-01)

Propagated from spec §"Session 2026-06-01 (Round 4 — checklist residual closure)":
- R4-Q9 / R4-Q39: exit `1` (uncaught exception, mapped after redaction-safe logging) and
  exit `2` (bad usage, always names the offending/missing arg) behaviors specified;
  `--resume` unknown session id → exit 2; `--resume` + selectors → resume wins, selectors
  validated (mismatch → exit 2). Added `test_unknown_resume_session_exits_2`,
  `test_resume_with_selectors_validates_consistency`, `test_exit_1_and_2_emit_named_messages`.
- R4-Q40: run-report minimum fields extended with `redaction_applied` + no-PHI/no-clinical
  reminder, `abandonment_timeout_sec`, `shadow_stt.failure_detail`, structured
  `shadow_stt.discrepancy_summary`, and a `config_identity` block.
- R4-Q1: readiness checks extended with `realtime_ai_credentials`, `shadow_stt_credentials`
  (when `--shadow-stt`), and signing-secret / signature-verifiability.
- R4-Q41: operator error messages classify remediation as `config` / `transient_provider` /
  `ineligible`.
