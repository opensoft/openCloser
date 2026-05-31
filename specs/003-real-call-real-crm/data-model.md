# Phase 1 Data Model: Slice 3 — Real Call, Real CRM

**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Created**: 2026-05-25

This document captures the Slice 3 entities — both the **new** entities introduced for
real call + real CRM + shadow STT, and the **extended** entities carried forward from
Slices 1 and 2 with Slice 3 additions. Slice 1 / Slice 2 entities reused unchanged are
listed in §5 as a reference only.

The on-disk schema lives in three places:

1. **SQLite** (`opencloser.db`, established in Slice 1, extended in Slice 2 + Slice 3) —
   session, audit, CRM correlation, write-back progress.
2. **Local artifacts** (`artifacts/<session_id>/...`, established in Slice 1, extended in
   Slice 2 + Slice 3) — transcripts, run report, audit logs.
3. **Dataverse** (Slice 2 contract, reused) — queue items, Phone Call activities, Tasks,
   queue-status / DNC / opt-out / blocked / dial-blocked fields, Owner / Team lookups.

The Slice 1 SC-008 forward-compatibility renames are applied at the Slice 3 boundary:
`mock_provider_call_id` → `provider_call_id`, `MockCallEvent` → `CallEvent`, `fixture_id` →
`dial_plan`. The Slice 1 `human_review_reason` enumeration is extended with one additive
entry: `shadow_stt_discrepancy`.

---

## 1. New Slice 3 entities

### 1.1 `SignalWireDial` — outbound dial record

Records each SignalWire outbound dial attempt at the transport adapter boundary. Distinct
from `Session` (orchestrator-level) and from `CallEvent` (normalized event-level).

| Field | Type | Notes |
|---|---|---|
| `session_id` | str (FK → `sessions.session_id`) | One dial per session in Slice 3 |
| `provider_call_id` | str | SignalWire-assigned call SID; replaces Slice 1/2 `mock_provider_call_id` |
| `source_caller_id` | str | E.164; from `[signalwire].source_caller_id` config |
| `destination_phone` | str | E.164; from the queue item, validated by FR-010 |
| `dial_plan` | JSON | The SWML / TwiML payload sent to SignalWire; replaces Slice 1/2 `fixture_id` |
| `placed_at` | ISO8601 | Real-call moment; `null` in rehearsal mode |
| `acknowledged_at` | ISO8601 \| null | SignalWire ack timestamp |
| `run_mode` | enum(`rehearsal`, `real_call`) | Per FR-001 / FR-002 |

**Identity & uniqueness**: `(session_id, provider_call_id)` is unique. In rehearsal mode
`provider_call_id` is `null` (planned dial without a real provider call SID).

**State transitions**: created on dial attempt → `acknowledged` on first SignalWire ack →
terminal via the normalized `CallEvent` stream (no separate state for the dial itself).

### 1.2 `CallEvent` — normalized provider event

Renamed from Slice 1's `MockCallEvent`. The transport adapter (SignalWire for Slice 3, mock
for Slices 1 / 2) translates provider-specific events into this normalized shape.

| Field | Type | Notes |
|---|---|---|
| `session_id` | str (FK) | |
| `provider_event_id` | str | The SignalWire-supplied event identifier; basis for dedup |
| `event_type` | enum | `connected` \| `no_answer` \| `voicemail` \| `failed` \| `completed` \| `callback_requested` |
| `provider_intermediate_state` | str \| null | E.g., `ringing`, `answered`, `in_progress`, `busy`, `canceled` — informational only |
| `received_at` | ISO8601 | When the orchestrator received the event |
| `delivered_at` | ISO8601 | When SignalWire reported delivery |
| `out_of_order` | bool | True if `received_at` < a prior event's `received_at` from same session |
| `late_after_finalization` | bool | True if the session is already finalized (FR-027) |

**Identity & uniqueness**: `(session_id, provider_event_id)` is the dedup key (FR-007,
FR-021, FR-027).

**State transitions**: append-only; no mutation after insert.

### 1.3 `CallbacksAuditLog` — receipt log of every callback

Append-only audit log of every SignalWire status + media callback received for a session,
including duplicates and out-of-order deliveries. Persisted to
`artifacts/<session_id>/callbacks_audit.jsonl` (one JSON object per line).

| Field | Type | Notes |
|---|---|---|
| `session_id` | str | |
| `provider_event_id` | str | |
| `callback_type` | enum(`status`, `media`) | |
| `received_at` | ISO8601 | |
| `normalized_event_type` | str \| null | The `CallEvent.event_type` the transport produced |
| `is_duplicate` | bool | True on second+ delivery for the same `(session_id, provider_event_id)` |
| `is_out_of_order` | bool | |
| `is_late_after_finalization` | bool | |
| `raw_callback_body` | JSON | Provider payload — **stored only if** retention policy allows; subject to redaction |

**Identity & uniqueness**: append-only; no uniqueness constraint (duplicates are recorded).

### 1.4 `RejectedAuthCallbackLog` — distinct rejected-by-authentication audit log *(Round 2 Q9)*

Distinct from `CallbacksAuditLog`. Records inbound SignalWire callbacks that failed
HMAC-SHA256 signature verification (FR-008). Persisted to
`artifacts/<session_id>/rejected_auth_callbacks.jsonl`. Also mirrored to the SQLite table
`rejected_auth_callbacks` so the count is queryable from the run report.

| Field | Type | Notes |
|---|---|---|
| `received_at` | ISO8601 | |
| `session_id` | str \| null | May be `null` if the callback could not be associated with a known session |
| `source_metadata` | JSON | Provider-supplied source identifiers / IP-level metadata where available |
| `http_status` | int | Always `401` per FR-008 |

**MUST NOT contain**: the verification secret, the callback body, the failed signature value.

**Identity & uniqueness**: append-only.

### 1.5 `ConflictingEventAuditLog` — late-after-finalization callbacks *(carried forward from Slice 1)*

Records normalized callbacks that arrived after the session was finalized (FR-027).
Persisted to `artifacts/<session_id>/conflicting_callbacks_audit.jsonl`.

| Field | Type | Notes |
|---|---|---|
| `session_id` | str | |
| `provider_event_id` | str | |
| `received_at` | ISO8601 | |
| `would_have_been` | enum | The `CallEvent.event_type` this callback would have produced |
| `finalized_disposition` | str | The disposition that was NOT changed by this callback |

### 1.6 `ShadowSTTLane` / `ShadowTranscript`

Slice 3's optional non-blocking secondary transcript lane (FR-028 – FR-032). One instance
per session when shadow STT is enabled.

| Field | Type | Notes |
|---|---|---|
| `session_id` | str | |
| `enabled` | bool | False if `SLICE3_SHADOW_STT_PROVIDER` env var unset / `"disabled"` |
| `provider_name` | str \| null | E.g., `"deepgram"`, `"whisper-cloud"` — recorded on session per FR-016 |
| `started_at` | ISO8601 | |
| `ended_at` | ISO8601 \| null | |
| `truncated` | bool | True iff the lane was still processing past the grace window (Round 2 Q7) |
| `transcript_path` | str \| null | `artifacts/<session_id>/shadow_transcript.txt` (redacted per FR-033 / FR-034) |

### 1.7 `ShadowSTTDiscrepancyRecord` *(carried forward, extended for redaction per Q11)*

One row per detected divergence on a configured high-value field.

**Storage normalization**: the spec's FR-030 + Definitions "High-value field" enumerate **7 logical categories** (with compound entries like "callback intent / preferred callback window" and "person reached name/role"). For storage clarity and finer-grained inspection, this entity splits those compound categories into **9 atomic enum values** — each atomic enum value is part of exactly one of the 7 logical categories. The 7-vs-9 distinction is therefore a storage detail, not a content disagreement: every spec-enumerated category is represented.

| Field | Type | Notes |
|---|---|---|
| `session_id` | str | |
| `field` | enum (9 atomic values, one per spec category atom) | `opt_out` \| `wrong_number` \| `captured_email` \| `callback_intent` \| `preferred_callback_window` \| `person_reached_name` \| `person_reached_role` \| `interest_level` \| `final_disposition` |
| `live_value` | str | Redacted per FR-033 + FR-015 (PHI tag-and-redact if applicable) |
| `shadow_value` | str | Same redaction policy as `live_value` |
| `classification` | enum(`benign`, `uncertain`) | Per the shadow STT discrepancy policy |
| `review_task_reason` | str \| null | `shadow_stt_discrepancy` when `classification == uncertain` |
| `recorded_at` | ISO8601 | |

### 1.8 `ShadowLaneTruncatedEvent` *(Round 2 Q7)*

Single per-session record (if any) that the shadow lane was still producing output AFTER
the orchestrator's post-finalization grace window elapsed. Persisted to
`artifacts/<session_id>/shadow_lane_truncated.json`.

| Field | Type | Notes |
|---|---|---|
| `session_id` | str | |
| `finalized_at` | ISO8601 | Disposition finalization moment |
| `grace_window_ended_at` | ISO8601 | `finalized_at + SLICE3_GRACE_WINDOW_SEC` |
| `late_output_summary` | JSON | Per-high-value-field summary of what the shadow lane would have produced |
| `would_have_classified_as` | enum(`benign`, `uncertain`) \| null | What the discrepancy policy WOULD have classified it as, had it arrived in time |

**Invariant**: this event MUST NOT mutate the finalized disposition (FR-029), MUST NOT
emit a new CRM write-back payload (FR-029), MUST NOT generate a `shadow_stt_discrepancy`
review Task (the grace window elapsed; the lane was too late to participate).

### 1.9 `TelephonyReadinessReport` *(per FR-009 / FR-036)*

Local artifact + a section in `run_report.json`. Enumerates the result of each pre-dial
readiness check from FR-009.

| Field | Type | Notes |
|---|---|---|
| `check_name` | enum | `signalwire_credentials` \| `source_caller_id_authorized` \| `destination_phone_e164` \| `status_callback_url_configured` \| `media_callback_url_configured` \| `campaign_persona_runtime_mapping` \| `dataverse_metadata_verified` \| `task_owner_mapping_resolved` \| `eligibility` |
| `result` | enum(`pass`, `fail`) | |
| `detail` | str | Human-readable explanation; on `fail`, names the failing condition |
| `checked_at` | ISO8601 | |

### 1.10 `RunReport` *(FR-036, extended by Round 2 amendments)*

One JSON file per session at `artifacts/<session_id>/run_report.json`. Schema in
[research.md §9](./research.md#9-run-report-file-format--naming).

Key fields added or amended by Round 2:

- `operator_identity`: `{current: str, original: str}` — `original` differs from `current`
  only on resume invocations per Round 2 Q12; both `null`-safe so single-operator runs are
  unaffected.
- `telephony_readiness_summary`: array of `TelephonyReadinessReport` entries (Round 2
  CHK012 + Q9 amendments).
- `rejected_auth_callbacks_count`: int (Round 2 Q9).
- `shadow_stt.lane_truncated`: bool (Round 2 Q7).
- `per_writeback_operation_status`: ordered array reflecting the **DNC-first** ordering on
  `do_not_call` outcomes (Round 2 Q14).

### 1.11 `WriteBackOperation` — field-level variants under queue-status update *(Round 2 Q8)*

The Slice 2 contract has four write-back operations: `phone_call_activity`,
`queue_status_update`, `task`, `assembly`. Slice 3 introduces no new operations but adds
field-level VARIANTS under `queue_status_update`:

| Variant key | Triggered by | Fields updated | Order constraint |
|---|---|---|---|
| `queue_status_update.normal` | Most dispositions | `status`, `last_disposition`, `last_session_id`, `attempt_count` | Standard order |
| `queue_status_update.dnc` | `do_not_call` or mid-call opt-out (FR-024) | `dnc_flag`, `opt_out_reason`, `status` | **FIRST** in the write-back sequence on `do_not_call` (Round 2 Q14) |
| `queue_status_update.blocked` | Blocked-by-eligibility (FR-023) | `status`, `blocked_reason`, `attempt_count` (no increment) | Standard order |
| `queue_status_update.dial_blocked` | Provider-rejected dial (FR-012) | `status`, `blocked_reason` | Standard order |

The four-operation count is preserved per FR-020.

### 1.12 `RealtimeProviderSession` — live AI provider identity *(per FR-016)*

Recorded on every Slice 3 session for audit. Inhabits the `Session` row, not a separate table.

| Field | Type | Notes |
|---|---|---|
| `runtime_name` | str | Always `"pipecat"` for Slice 3 |
| `runtime_version` | str | E.g., `pipecat-ai==0.0.x` |
| `provider_name` | str | E.g., `"openai-realtime"`, `"google-realtime"` — deployment-configured |
| `model_name` | str | Provider's model identifier |
| `model_version` | str | Provider's model version string |

**MUST NOT contain credentials** (FR-035).

---

## 2. Extended Slice 1 / Slice 2 entities

### 2.1 `Session` *(Slice 1, extended)*

Added Slice 3 fields:

| Field | Type | Notes |
|---|---|---|
| `provider_call_id` | str \| null | Renamed from `mock_provider_call_id`; backwards-compat for pre-Slice-3 reads |
| `runtime_identity` | JSON | The `RealtimeProviderSession` from §1.12 |
| `operator_identity_current` | str | Current invocation's operator (Round 1 Q3) |
| `operator_identity_original` | str \| null | Original invocation's operator on resume (Round 2 Q12); `null` on first invocation |
| `run_mode` | enum(`rehearsal`, `real_call`) | Per FR-001 / FR-002 / Round 2 Q13 |
| `grace_window_sec` | int | Value in effect for this session (Round 2 Q7) |
| `shadow_stt_enabled` | bool | |
| `finalized_at` | ISO8601 \| null | Set on disposition finalization; the post-finalization grace window starts here |
| `cm_writeback_started_at` | ISO8601 \| null | `finalized_at + grace_window_sec`, or earlier if the shadow lane completed |

### 2.2 `NormalizedResult` *(Slice 1 normalized session result, extended)*

The shape preserved per FR-017. Slice 3 additions to the existing field list:

- `provider_call_id` (renamed from `mock_provider_call_id`).
- `runtime_identity` (per FR-016).
- `operator_identity` (current + original — Round 2 Q12).
- No new disposition codes; `shadow_stt_discrepancy` is added to the `human_review_reason`
  enumeration per FR-031.

### 2.3 `PhoneCallActivityPayload` *(Slice 2 contract, extended)*

Adapter-side additions per FR-020:

- `provider_call_id` field replaces the Slice 1/2 mock value.
- Optional `connected_call_timestamps`: `{answered_at, completed_at}` populated from
  SignalWire status callbacks when available.

No new Dataverse field is added by Slice 3 for operator identity (Round 1 Q3 / Round 2 Q12:
operator identity stays local-only and MUST NOT appear in Dataverse).

### 2.4 `IdempotencyKey` *(Slice 2, reused unchanged)*

Stable session-derived key stamped onto a metadata-verified Dataverse field on every
Phone Call activity and Task per FR-021. Pre-query before each create. Slice 3 makes no
changes — DNC-first writes (Round 2 Q14) reuse the same key shape.

### 2.5 `RedactionPolicy` *(Slice 2, extended by Round 2 Q10 + Q11)*

Default-on redaction now covers (per FR-033 amended by Round 2 Q10):

- The full transcript file
- The session-result `summary`
- The shadow STT transcript (when enabled)
- The shadow STT discrepancy records

**Excluded** (machine-readable, must remain unredacted): transcript pointer metadata,
session IDs, provider call IDs, timestamps, run-report structural fields.

The PHI tag-and-redact pass (Round 2 Q11) runs as a special-case pre-write step on the four
artifact types above whenever a session's persona has emitted a `phi_collection_risk`
escalation event.

### 2.6 Dataverse-side entities *(Slice 2, reused unchanged)*

Queue Item, CRM Field Mapping Artifact, Dataverse CRM Adapter, Task Owner Mapping, CRM
Correlation Identifier, Write-Back Progress Ledger — all reused unchanged. Slice 3
augments only the field-level variant set under `queue_status_update` (see §1.11).

---

## 3. SQLite schema additions (Slice 3)

Three new tables added to `opencloser.db`:

```sql
-- §1.4 RejectedAuthCallbackLog mirror (for run-report count queries)
CREATE TABLE rejected_auth_callbacks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  received_at TEXT NOT NULL,
  session_id TEXT,                       -- nullable; may not be associatable
  source_metadata_json TEXT NOT NULL,    -- JSON; NO secret, NO body
  http_status INTEGER NOT NULL,
  CHECK (http_status = 401)
);
CREATE INDEX idx_rejected_auth_session ON rejected_auth_callbacks(session_id);

-- §1.7 ShadowSTTDiscrepancyRecord mirror
CREATE TABLE shadow_stt_discrepancies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  field TEXT NOT NULL,
  live_value TEXT,                       -- redacted
  shadow_value TEXT,                     -- redacted
  classification TEXT NOT NULL CHECK (classification IN ('benign', 'uncertain')),
  review_task_reason TEXT,               -- 'shadow_stt_discrepancy' when uncertain
  recorded_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
CREATE INDEX idx_shadow_disc_session ON shadow_stt_discrepancies(session_id);

-- §1.8 ShadowLaneTruncatedEvent mirror
CREATE TABLE shadow_lane_truncated_events (
  session_id TEXT PRIMARY KEY,
  finalized_at TEXT NOT NULL,
  grace_window_ended_at TEXT NOT NULL,
  late_output_summary_json TEXT NOT NULL,
  would_have_classified_as TEXT CHECK (would_have_classified_as IN ('benign', 'uncertain')),
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

Extensions to existing tables:

```sql
-- §1.1 conceptual rename `provider_call_id` is stored on-disk in the existing
-- `mock_provider_call_id` column (no schema-level rename — preserves Slice 1 /
-- Slice 2 read compatibility). The eight ALTER statements below are the only
-- net-new columns added to `sessions` for Slice 3.
ALTER TABLE sessions ADD COLUMN runtime_identity_json TEXT;  -- §2.1
ALTER TABLE sessions ADD COLUMN operator_identity_current TEXT;
ALTER TABLE sessions ADD COLUMN operator_identity_original TEXT;
ALTER TABLE sessions ADD COLUMN run_mode TEXT CHECK (run_mode IN ('rehearsal', 'real_call'));
ALTER TABLE sessions ADD COLUMN grace_window_sec INTEGER;
ALTER TABLE sessions ADD COLUMN shadow_stt_enabled INTEGER;  -- 0/1
ALTER TABLE sessions ADD COLUMN finalized_at TEXT;
ALTER TABLE sessions ADD COLUMN cm_writeback_started_at TEXT;
```

The Slice 2 `crm_correlations` and `writeback_progress` tables are reused unchanged.

---

## 4. Artifacts directory layout (Slice 3)

```text
artifacts/<session_id>/
├── run_report.json                     # §1.10 — Required for every invocation
├── transcript.txt                      # Redacted per FR-033 (when retention allows)
├── shadow_transcript.txt               # Redacted per FR-034 (only when shadow STT enabled)
├── callbacks_audit.jsonl               # §1.3
├── rejected_auth_callbacks.jsonl       # §1.4 (only when ≥1 rejected callback received)
├── conflicting_callbacks_audit.jsonl   # §1.5 (only when ≥1 late callback received)
├── shadow_discrepancies.jsonl          # §1.7 (only when shadow STT enabled and ≥1 discrepancy)
├── shadow_lane_truncated.json          # §1.8 (only when lane was truncated)
├── telephony_readiness.json            # §1.9 (always; mirrors the `run_report.json` summary)
├── planned_writeback.json              # Slice 2; planned write-back payloads (rehearsal + real)
└── actual_writeback.json               # Slice 2; actually-emitted write-back payloads (real only)
```

All transcript-derived artifacts are redacted per the §2.5 amended policy before write.

---

## 5. Slice 1 / Slice 2 entities reused unchanged (reference)

For completeness — these are reused verbatim and need no Slice 3 schema changes:

- **Queue Item** (Slice 1 + Slice 2 Dataverse extensions)
- **Eligibility Decision** (Slice 1)
- **Conversation Fixture** (Slice 1; fixture-replay debugging only in Slice 3)
- **Transport Fixture** (Slice 1; fixture-replay debugging only in Slice 3)
- **Persona** + extraction schema + disposition rules + escalation reasons (Slice 1; Slice 3
  extends `escalation` with the additive `shadow_stt_discrepancy` entry and `extraction`
  with the PHI-volunteered tagging hook per Round 2 Q11)
- **CRM Field Mapping Artifact** (Slice 2)
- **Task Owner Mapping** (Slice 2)
- **CRM Correlation Identifier** (Slice 2)
- **Write-Back Progress Ledger** (Slice 2)

---

## 6. State transitions (Slice 3 end-to-end)

```text
[rehearsal mode]
  parse_cli → load_config → eligibility_check → telephony_readiness_check
    → (any fail) → write readiness report → exit (no dial, no mutation)
    → (all pass) → generate planned write-back artifacts → exit (no dial, no mutation)

[real-call / write-enabled mode]
  parse_cli (--real-call required) → load_config → claim_queue_item (Slice 2 semantics)
    → eligibility_check → telephony_readiness_check
    → (any fail) → write readiness report → blocked-status field write → exit
    → (all pass) → signature_verifier_started → place_call (SignalWire)
                    → callback_loop:
                       - on each callback: verify signature
                           → fail: log to RejectedAuthCallbackLog (§1.4), HTTP 401, no orch hand-off
                           → pass: dedup by (session_id, provider_event_id)
                               → duplicate: log to CallbacksAuditLog, no-op
                               → late-after-finalization: log to ConflictingEventAuditLog
                               → fresh: normalize → orchestrator
                    → pipecat_pipeline (live conversation; deterministic disposition rules)
                       - shadow_stt_lane runs in parallel asyncio.Task (non-blocking)
                       - PHI volunteered → phi_collection_risk + tag_and_redact_pre_write
                       - live-runtime degradation trigger (a/b/c from FR-013):
                           → finalize as failed (pre-connected) or needs_human_review/script_truncated (post-connected)
                    → finalization moment:
                       - if disposition reached → finalize session, record finalized_at
                       - start grace_window_sec countdown for CRM write-back
                       - shadow lane:
                           → completes in window: discrepancy may participate in disposition (FR-031)
                           → completes after window: ShadowLaneTruncatedEvent (§1.8), no disposition mutation
                    → crm_writeback (Slice 2 contract, extended):
                       - if disposition == do_not_call: DNC field write FIRST (Q14)
                       - per-disposition emission decisions unchanged from Slice 2
                       - idempotency-key stamping per FR-021
                       - bounded retry per FR-022 (initial + 3, 1s/2s/4s, Retry-After ≤ 30s)
                       - on partial failure: writeback_progress ledger records last completed step
                    → write run_report.json + telephony_readiness.json + all audit logs
                    → exit

[resume invocation]
  parse_cli (--real-call still required per Q13) → load_session_state
    → preserve operator_identity_original; record operator_identity_current
    → if session previously received `answered` but no terminal event:
         finalize as failed/live_call_abandonment immediately (Q6)
         → proceed to crm_writeback resume path
    → else: resume from writeback_progress ledger (Slice 2 resume contract)
    → exit
```

---

## 7. Validation rules summary

The data-model contracts above enforce the following Slice 3 invariants by construction:

- **No duplicate writes**: `(session_id, provider_event_id)` dedup key on `CallEvent` and
  `CallbacksAuditLog`; idempotency-key pre-query on Phone Call activity and Task creates;
  `crm_correlations` ledger ensures resume creates no duplicate Dynamics records (SC-008).
- **No secrets in artifacts**: `RejectedAuthCallbackLog` schema explicitly excludes the
  verification secret and the callback body; `RealtimeProviderSession` excludes credentials
  (FR-035, SC-018).
- **No PHI in artifacts (caller-volunteered path)**: PHI tag-and-redact runs as a pre-write
  step on transcript / summary / shadow transcript / shadow discrepancy records whenever
  the persona emits `phi_collection_risk` (FR-015 / FR-033 per Round 2 Q11).
- **No operator identity in Dataverse**: `Session.operator_identity_*` columns are
  local-only; no Dataverse field is added for operator identity (FR-016 per Round 1 Q3 +
  Round 2 Q12).
- **DNC-first on `do_not_call`**: the `WriteBackOperation` table (§1.11) defines the
  ordering invariant; the Slice 3 `crm/dataverse/adapter.py` enforces it (FR-024 per
  Round 2 Q14).
- **Four write-back operations preserved**: §1.11's `queue_status_update.*` variants are
  field-level under the existing `queue_status_update` operation; the four-operation count
  is preserved (FR-020 per Round 2 Q8).
- **Non-blocking shadow STT at finalization**: the orchestrator MUST set `finalized_at`
  without awaiting the shadow lane's `asyncio.Task`; the grace window governs only when
  CRM write-back proceeds, not when finalization happens (FR-029 per Round 2 Q7).
- **Shadow lane truncation never mutates disposition**: `ShadowLaneTruncatedEvent` (§1.8)
  is audit-only by construction — it has no foreign key to any disposition or CRM write
  table (FR-029).
- **Real-call flag required on every Dataverse mutation**: `Session.run_mode` MUST equal
  `real_call` for any Dataverse-mutating write; resume re-invocations re-check this gate
  (FR-001 / FR-022 per Round 2 Q13).
