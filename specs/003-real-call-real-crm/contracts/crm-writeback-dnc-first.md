# Contract: CRM Write-Back — Slice 3 Additions (Real Provider Call ID + DNC-First Ordering + Field-Level Variants)

**Slice 3** · **FR-020 – FR-024** (+ Round 2 Q8 four-op preservation, Q14 DNC-first) · [plan.md](../plan.md) · [research.md §14](../research.md)

The Slice 2 `DataverseWriteBackAdapter` is reused unchanged. Slice 3 introduces only
ADDITIVE behaviors:

1. The Phone Call activity payload now carries the **real provider call ID** (from the
   SignalWire transport per FR-006) and optionally the connected-call timestamps
   (`answered_at`, `completed_at`) from SignalWire status callbacks.
2. The four-operation count is preserved (Round 2 Q8). DNC / opt-out / blocked-status /
   dial-blocked writes are FIELD-LEVEL variants of the existing `queue_status_update`
   emission operation; they are NOT new operations.
3. The DNC / opt-out field write MUST be attempted FIRST in the write-back sequence on
   `do_not_call` outcomes (Round 2 Q14). Idempotency-key stamping prevents duplicate DNC
   writes on resume.

The Slice 2 idempotency-key stamping (FR-021), bounded retry (FR-022: initial + 3 retries,
1s / 2s / 4s default backoff, `Retry-After` ≤ 30s), and resume coordinator (FR-022) are
reused verbatim.

## Python contract (extends Slice 2 `WriteBackAdapter`)

```python
from typing import Protocol
from opencloser.models import (
    NormalizedResult, WriteBackOperation, PhoneCallActivity, QueueStatusUpdate,
    Task, IdempotencyKey, ProviderCallId, ConnectedCallTimestamps,
)

class WriteBackAdapter(Protocol):
    """Slice 2 contract; Slice 3 additions noted below."""

    def emit_phone_call_activity(
        self,
        result: NormalizedResult,
        idempotency_key: IdempotencyKey,
        *,
        provider_call_id: ProviderCallId,                            # Slice 3: real SID
        connected_call_timestamps: ConnectedCallTimestamps | None,   # Slice 3: optional
    ) -> None:
        """Pre-query by idempotency key (Slice 2). Skip create if found."""

    def emit_queue_status_update(
        self,
        result: NormalizedResult,
        variant: "QueueStatusUpdateVariant",                          # Slice 3: variant tag
    ) -> None:
        """Field-level variants per Round 2 Q8 — four-operation count preserved."""

    def emit_task(self, result: NormalizedResult, idempotency_key: IdempotencyKey) -> None: ...

    def assemble_writeback(
        self,
        result: NormalizedResult,
    ) -> list["WriteBackStep"]:
        """Return the ordered write-back step sequence. On `do_not_call`, the
        first step MUST be `QueueStatusUpdateVariant.DNC` per Round 2 Q14."""


class QueueStatusUpdateVariant(str, Enum):
    NORMAL = "queue_status_update.normal"
    DNC = "queue_status_update.dnc"
    BLOCKED = "queue_status_update.blocked"
    DIAL_BLOCKED = "queue_status_update.dial_blocked"
```

## Required behaviors

### DNC-first ordering on `do_not_call` (Round 2 Q14)

When `NormalizedResult.disposition == 'do_not_call'`, `assemble_writeback` MUST return
steps in this order:

1. `QueueStatusUpdateVariant.DNC` — writes the DNC / opt-out fields and the queue-status
   field. **MUST be first.**
2. Phone Call activity emission (idempotency-key stamped).
3. Task emission — but `do_not_call` MUST NOT create a callback or review Task (FR-024).
   So this step is effectively a no-op for `do_not_call`.

The bounded retry budget (FR-022) applies per-step. If step 1 succeeds and step 2 fails
within budget, the contact is already protected — the resume coordinator will pick up at
step 2 on re-invocation.

#### DNC-first write exhaustion (Round 4 R4-Q7)

If the DNC / opt-out write (step 1) ITSELF exhausts its retry budget — i.e. the
first, contact-protecting write never lands — the run MUST:

1. Halt the remaining write-back (do NOT proceed to the Phone Call activity / Task steps).
2. Finalize the run with failure reason `dnc_write_failed`.
3. Emit a PROMINENT operator alert: the contact may be unprotected (the DNC / opt-out field
   was not written), so this is treated as higher-severity than an ordinary write-back
   exhaustion.
4. On resume, the write-back retries DNC-first (the same DNC-first ordering applies on
   re-invocation), so a subsequent successful attempt protects the contact before any other
   write proceeds.

This is distinct from the resume-needed posture of R4-Q6 (which never overwrites the persona
disposition): a DNC-first exhaustion sets the failure reason `dnc_write_failed` precisely
because the contact-protecting write is the one that failed.

#### Field-update dedup reads the ledger (Round 4 R4-Q26)

The DNC / queue-status field-update dedup MUST read the local `writeback_progress` ledger to
decide whether a field update has already been applied — NOT the live Dataverse field value.
Reading the ledger (rather than the current Dataverse value) makes resume deterministic: it
cannot diverge across re-invocations even if an external actor or a prior partial write
changed the live field, and a successful prior write recorded in the ledger is never
re-applied.

### Per-disposition step ordering (other dispositions)

Unchanged from Slice 2:

| Disposition | Step order |
|---|---|
| `interested_callback_requested` | phone_call_activity → queue_status_update.normal → task (callback) |
| `interested_email_captured` | phone_call_activity → queue_status_update.normal → task (follow-up with email) |
| `not_interested` | phone_call_activity → queue_status_update.normal (no task) |
| `call_back_later` | phone_call_activity → queue_status_update.normal → task (callback) |
| `wrong_number` | phone_call_activity → queue_status_update.normal (no task) |
| `no_answer` | phone_call_activity → queue_status_update.normal (no task) |
| `voicemail` | phone_call_activity → queue_status_update.normal (no task) |
| **`do_not_call`** | **queue_status_update.dnc → phone_call_activity → (no task)** |
| `needs_human_review` | phone_call_activity → queue_status_update.normal → task (review) |
| `failed` | phone_call_activity (if call connected; else skip) → queue_status_update.normal (no task) |
| `blocked` | queue_status_update.blocked only (no phone_call_activity, no task, no attempt increment) |

### Slice 3 Phone Call activity payload additions

```text
phone_call_activity {
  ...                              # Slice 2 fields unchanged
  provider_call_id: ProviderCallId  # NEW (Slice 3): SignalWire SID; replaces mock
  connected_call_timestamps: {     # NEW (Slice 3): optional
    answered_at:  ISO8601 | null
    completed_at: ISO8601 | null
  } | null
}
```

No Dataverse field is added for operator identity (Round 1 Q3 / Round 2 Q12: operator
identity is local-only and MUST NOT appear in Dataverse). No Dataverse field is added for
rejected-by-authentication callback counts (that count lives in the local run report only).

### Idempotency on resume (Round 2 Q14 + Round 2 Q6)

- DNC writes use the same Slice 2 idempotency-key stamping. A resume invocation that
  re-runs the DNC step finds the existing write via the pre-query and skips.
- A resume invocation on a session that previously received `answered` but no terminal
  event finalizes the session as `failed` / `live_call_abandonment` immediately (Round 2
  Q6) and then proceeds through this write-back contract with the resume coordinator.

### Write-back exhaustion never overwrites the disposition (Round 4 R4-Q6)

An exhausted write-back retry budget MUST mark the unfinished operations `resume-needed` and
MUST NEVER overwrite the persona's final disposition with `failed`. A successful retry keeps
the persona disposition; an exhausted budget leaves the persona disposition intact and the
unfinished operations are picked up on the next resume invocation. (Exception: a DNC-FIRST
write exhaustion finalizes the failure reason `dnc_write_failed` per R4-Q7 because the
contact-protecting write is the one that failed — this is a run-level failure reason, not an
overwrite of the persona disposition.)

### Planned-vs-actual write-back artifact parity (R4-Q43 — CHK201)

Both run modes emit a local write-back artifact under `artifacts/<session_id>/`:
- **`planned_writeback.json`** — produced in EVERY mode (rehearsal and real-call); the
  ordered set of write-back operations the run *would* / *did intend to* emit.
- **`actual_writeback.json`** — produced in REAL-CALL mode ONLY (written by the US1 write-back
  adapter wiring, T034); the operations actually emitted to Dataverse.

So the operator's manual diff (R4-Q43; a diff UI is OUT OF SCOPE) is meaningful and
unambiguous, the two artifacts MUST be parity-correlated as a requirement-level contract:

- **Same operation set, same order.** Each artifact is the ordered list of the SAME
  per-disposition write-back operations produced by `assemble_writeback` (including DNC-first
  ordering on `do_not_call`). The operation set and its ordering MUST match between the two
  artifacts for a given session; an operation present in `planned` MUST have a corresponding
  entry in `actual` (and vice versa) for a real-call run that ran to write-back.
- **Join key.** Entries correlate one-to-one on the tuple
  `(operation, variant, idempotency_key)` — the stable per-operation key — so a line-by-line
  operator diff joins deterministically without positional guessing.
- **Expected real-vs-rehearsal divergence is bounded and named.** The ONLY fields that may
  differ between a `planned` entry and its correlated `actual` entry are the
  provider-assigned / runtime-assigned values that do not exist until the real write happens:
  `real_provider_call_id` (`"not-yet-assigned"` / absent in `planned`, populated in `actual`),
  the connected-call timestamps, the Dataverse record IDs, and the per-step
  completed / resume-needed / blocked status. The operation identity, variant, ordering, and
  idempotency key MUST be identical. Any other divergence is a write-back correctness defect.
- A `planned` entry with NO correlated `actual` entry after a real-call run means the
  operation was not emitted (e.g., resume-needed / exhausted budget) and MUST be explained by
  that step's status field — it is never a silent drop.

### Real-call flag still required on resume (Round 2 Q13)

The adapter MUST refuse to perform any write when `Session.run_mode != 'real_call'`. A
rehearsal-mode resume invocation surfaces what would have been written in the run report
and exits without mutation.

## What MUST NOT change (preserved from Slice 2)

- The four-operation count: `phone_call_activity`, `queue_status_update`, `task`, `assembly`.
- The Dataverse metadata two-phase verification (one-time discovery + lightweight live
  verification before each write-enabled run).
- The mapping artifact (`config/dataverse_mapping.json`).
- The high-confidence value preservation rule (existing Dataverse field values are not
  overwritten unless the feature explicitly requires it).
- The owner / team mapping for callback and review Tasks.
- The bounded retry budget (FR-022).
- The local audit retention floor (≥ 90 days).

## Contract test summary (`tests/contract/test_crm_writeback_slice3.py`)

| Test | Assertion |
|---|---|
| `test_phone_call_activity_carries_real_provider_call_id` | `emit_phone_call_activity` payload contains the SignalWire SID, not a mock ID |
| `test_phone_call_activity_carries_connected_timestamps` | When SignalWire status callbacks supply `answered_at` / `completed_at`, the payload includes them |
| `test_dnc_first_on_do_not_call` | `assemble_writeback({disposition: do_not_call})[0]` is `QueueStatusUpdateVariant.DNC`; no callback or review Task is emitted |
| `test_dnc_first_partial_failure_protects_contact` | DNC step succeeds + Phone Call activity step fails within retry budget → resume completes Phone Call activity without duplicate DNC write |
| `test_dnc_write_exhaustion_halts_and_alerts` | DNC-first write (step 1) itself exhausts its retry budget → remaining write-back is halted (no Phone Call activity / Task attempted), the run finalizes with failure reason `dnc_write_failed`, a prominent operator alert is emitted, and resume retries DNC-first (Round 4 R4-Q7) |
| `test_field_update_dedup_reads_ledger` | DNC / queue-status field-update dedup reads the `writeback_progress` ledger (not the live Dataverse field value); a write recorded in the ledger is skipped on resume even if the live Dataverse field was changed externally, so resume is deterministic (Round 4 R4-Q26) |
| `test_four_operation_count_preserved` | `WriteBackAdapter` exposes exactly 4 emit-methods: phone_call_activity, queue_status_update, task, assembly |
| `test_queue_status_update_variants` | All 4 variants (NORMAL / DNC / BLOCKED / DIAL_BLOCKED) use the same Slice 2 `emit_queue_status_update` method with the variant tag |
| `test_blocked_eligibility_writes_blocked_variant_only` | Disposition `blocked` triggers `QueueStatusUpdateVariant.BLOCKED` only; no Phone Call activity; no Task; no attempt increment |
| `test_dial_blocked_provider_4xx_writes_dial_blocked_variant` | `ProviderRejectedDialError` (FR-012) triggers `QueueStatusUpdateVariant.DIAL_BLOCKED`; no Phone Call activity; no attempt consumed |
| `test_idempotency_key_stamping_preserved` | Both Phone Call activity and Task creates pre-query by idempotency key; duplicate calls find the existing write and skip |
| `test_resume_in_rehearsal_mode_does_not_mutate` | Resume invocation without `--real-call` performs 0 Dataverse writes; run report surfaces the planned writes |
| `test_operator_identity_not_in_dataverse` | Inspecting any emitted Dataverse payload contains 0 operator identity strings (FR-016) |
| `test_actual_writeback_parity_with_planned` | After a real-call run, `actual_writeback.json` and `planned_writeback.json` carry the SAME operation set and order, correlate one-to-one on `(operation, variant, idempotency_key)`, and differ ONLY in provider/runtime-assigned fields (`real_provider_call_id` populated — not `not-yet-assigned` — connected timestamps, record IDs, per-step status); any other divergence fails (R4-Q43 / CHK201) |

## Round 4 — Checklist-Residual Alignment (2026-06-01)

Propagated from spec.md "Session 2026-06-01 (Round 4)":

- **R4-Q7**: a DNC-first write that itself exhausts its retry budget halts the remaining
  write-back, finalizes failure reason `dnc_write_failed`, emits a prominent operator alert
  (contact may be unprotected), and resumes DNC-first. Captured under "DNC-first write
  exhaustion" and the new `test_dnc_write_exhaustion_halts_and_alerts`.
- **R4-Q26**: the DNC / queue-status field-update dedup reads the `writeback_progress`
  ledger (not the live Dataverse field value) so resume is deterministic. Captured under
  "Field-update dedup reads the ledger" and the new `test_field_update_dedup_reads_ledger`.
- **R4-Q6**: an exhausted write-back retry budget marks operations `resume-needed` and NEVER
  overwrites the persona disposition with `failed`. Captured under "Write-back exhaustion
  never overwrites the disposition".
