# Contract: Shadow STT Lane

**Slice 3** · **FR-028 – FR-034** (+ Round 2 Q7 grace window, Q10 redaction, Q11 PHI) · [plan.md](../plan.md) · [research.md §4, §6, §7, §10](../research.md)

The shadow STT lane is an optional non-blocking secondary transcript pipeline that listens
to the same caller audio as the live conversation path, produces an independent transcript,
and emits discrepancy events for high-value fields. The lane MUST NOT block live conversation
turns, MUST NOT slow the live call path, and MUST NOT independently write CRM records or
override the persona's final disposition in the MVP.

## Python protocol

```python
from typing import Protocol, AsyncIterator
from opencloser.models import (
    SessionId, AudioChunk, TranscriptSegment, HighValueField,
    DiscrepancyEvent, ShadowLaneTruncatedEvent,
)

class ShadowSTTProvider(Protocol):
    """Deployment-configured shadow STT provider."""

    async def transcribe(
        self,
        audio_stream: AsyncIterator[AudioChunk],
    ) -> AsyncIterator[TranscriptSegment]: ...

    async def close(self, session_id: SessionId) -> None: ...


class ShadowSTTLane(Protocol):
    """The non-blocking secondary transcript lane wrapper."""

    async def start(self, session_id: SessionId, audio_tee: AsyncIterator[AudioChunk]) -> None:
        """Begin consuming the tee'd audio stream in a separate asyncio.Task.
        MUST NOT block the caller."""

    async def stop(self, session_id: SessionId) -> None:
        """Signal the lane to finish (called at orchestrator finalization).
        MUST NOT block; the lane drains in its own task."""

    def detect_discrepancies(
        self,
        live_extraction: dict[HighValueField, str],
    ) -> list[DiscrepancyEvent]:
        """Compare shadow transcript extraction against the live extraction
        for each configured HighValueField. Returns discrepancies classified
        as benign or uncertain per the deployment-configured policy."""

    def truncated_event(self, session_id: SessionId) -> ShadowLaneTruncatedEvent | None:
        """Return the truncated-event record if the lane was still producing
        output AFTER the orchestrator's post-finalization grace window
        elapsed; None otherwise. Audit-only; never mutates disposition."""
```

## Required behaviors

1. **Non-blocking guarantee** (FR-029): the shadow lane MUST NOT block live conversation
   turns. Implementation MUST run the lane in a separate `asyncio.Task` consuming a `tee`'d
   copy of the caller audio. A shadow-lane failure or timeout MUST NOT abort the live call.
   The orchestrator MUST NOT `await` the lane's task before session finalization.

2. **High-value field enumeration** (FR-030): the lane MUST compare these fields against the
   live conversation path:
   - opt_out / DNC
   - wrong_number
   - captured_email
   - callback_intent / preferred_callback_window
   - person_reached_name + person_reached_role
   - interest_level
   - final_disposition

3. **Audit-only / no-CRM-write** (FR-030): the lane MUST NOT independently write a CRM
   record. The lane MUST NOT override the persona's final disposition in the MVP.

4. **Uncertain-discrepancy escalation** (FR-031): when the deployment-configured discrepancy
   policy classifies a discrepancy as `uncertain` (not benign), the orchestrator escalates
   the session to `needs_human_review` with reason `shadow_stt_discrepancy`. The lane emits
   the `DiscrepancyEvent`; the orchestrator decides whether to escalate based on the
   classification and the post-finalization grace window (see #5).

5. **Post-finalization grace window** (FR-029 per Round 2 Q7): at the moment of
   orchestrator finalization, the lane may still be processing. The orchestrator:
   - Finalizes the session immediately (sets `Session.finalized_at`).
   - Holds the CRM write-back for `SLICE3_GRACE_WINDOW_SEC` (deployment-configurable, default 3s).
   - If the lane emits a `DiscrepancyEvent` (classified `uncertain`) inside the grace
     window, the orchestrator MAY escalate to `needs_human_review` / `shadow_stt_discrepancy`
     before write-back proceeds.
   - If the grace window elapses without a discrepancy, the write-back proceeds without the
     shadow result.
   - Any shadow lane output emitted AFTER the grace window MUST be recorded as a
     `ShadowLaneTruncatedEvent` (audit-only). This event MUST NOT mutate the finalized
     disposition, MUST NOT emit a new CRM write-back payload, and MUST NOT generate a
     `shadow_stt_discrepancy` review Task.

6. **Retention parity** (FR-034): the shadow transcript artifact MUST honor the same
   retention mode as the live transcript artifact (full + redacted, summary-only, or
   pointer-only). Shadow STT discrepancy records MUST be retained as audit/review evidence
   even under summary-only retention.

7. **Redaction coverage** (FR-033 per Round 2 Q10): default-on redaction MUST cover the
   shadow STT transcript file AND the shadow STT discrepancy records' `live_value` and
   `shadow_value` fields, before either is written to disk. Transcript pointer metadata
   is excluded (must remain machine-readable).

8. **PHI tag-and-redact** (FR-015 / FR-033 per Round 2 Q11, Round 3): when the persona emits
   `phi_collection_risk` for a caller-volunteered PHI utterance, the redaction layer's
   PHI pass MUST tag and redact the PHI-bearing utterance in the shadow STT transcript and
   the shadow STT discrepancy records before write, using the distinct `[PHI-REDACTED]` marker
   (Round 3). Redaction is fail-closed: if the pass cannot complete, the shadow artifacts MUST
   NOT be written unredacted and the session finalizes with `redaction_failed`.

9. **Toggle** (FR-032): the lane MUST be deployment-configurable as enabled or disabled.
   When disabled, the Slice 3 demonstrable loop MUST still complete without it (no
   degradation to the live conversation path, no missing artifacts beyond the shadow
   transcript / discrepancy records themselves). The run report MUST always state whether
   shadow STT was enabled.

10. **Lane-failure behavior** (FR-029): if the shadow lane crashes or times out mid-call,
    the live call MUST continue unaffected; no discrepancy events are emitted for the
    missing-shadow case; the run report MUST record the shadow-lane failure for audit as the
    `shadow_stt.lane_failed` signal. This is DISTINCT from `shadow_stt.lane_truncated` (Round 3):
    `lane_failed` = the lane produced NO usable result (crash / timeout); `lane_truncated` =
    the lane produced output but only AFTER the grace window. The two are reported
    independently; a single run MAY set neither, either, or — in principle — both.
    When `shadow_stt.lane_failed` is set, the run report MUST carry an accompanying
    `failure_detail {failure_type, at}` object alongside it (Round 4 R4-Q14): `failure_type`
    names the failure class (e.g. crash / timeout) and `at` records when in the call it
    occurred. `failure_detail` is audit-only and never mutates the finalized disposition.

11. **Structured discrepancy summary** (FR-036 per Round 4 R4-Q15): `shadow_stt.discrepancy_summary`
    is a STRUCTURED object, NOT a free-form string. Its defined shape is:
    `{fields_compared, discrepancies, uncertain, per_field:[{field, classification}]}` —
    `fields_compared` / `discrepancies` / `uncertain` are counts and `per_field` carries one
    `{field, classification}` entry per compared high-value field (`classification` ∈
    `benign` / `uncertain`). Consumers MUST be able to parse it as structured data.

## What MUST NOT leak past this boundary

- The shadow STT provider's streaming protocol or SDK return types beyond the protocol shape.
- The discrepancy policy's internal rule structure (the orchestrator sees only `benign` /
  `uncertain`).
- Credentials.

### Out of scope (Round 4 R4-Q45)

- **Shadow-lane disclosure-text-drift detection** is OUT OF SCOPE for Slice 3. The shadow
  lane does NOT compare or police the persona's disclosure wording for drift; the canonical
  disclosure is already fixed by Slice 1 persona policy, and the `phi_collection_risk`
  escalation + tag-and-redact is the compliance control. This is a declared exclusion, not
  an oversight.

## Contract test summary (`tests/contract/test_shadow_stt_lane.py`)

| Test | Assertion |
|---|---|
| `test_lane_does_not_block_live_turns` | Live conversation turn cadence is statistically indistinguishable between shadow-enabled and shadow-disabled runs (SC-013) |
| `test_lane_runs_in_separate_task` | The lane is started via `asyncio.create_task` and the orchestrator does not `await` it before finalization |
| `test_high_value_fields_enumerated` | `detect_discrepancies` accepts exactly the 7 logical high-value categories enumerated in FR-030 (stored as 9 atomic enum values per `data-model.md §1.7` storage normalization — `callback_intent` + `preferred_callback_window` split from one logical category, `person_reached_name` + `person_reached_role` split from another) |
| `test_lane_does_not_write_crm` | After a shadow-enabled run, the Dataverse adapter recorded 0 writes attributable to the shadow lane (only orchestrator-driven writes) |
| `test_uncertain_discrepancy_in_window_escalates` | Shadow emits an `uncertain` discrepancy inside the grace window → session disposition becomes `needs_human_review` / `shadow_stt_discrepancy`; one review Task created |
| `test_benign_discrepancy_does_not_escalate` | Shadow emits a `benign` discrepancy → no escalation, no extra review Task |
| `test_late_shadow_output_yields_truncated_event` | Shadow emits a discrepancy AFTER the grace window → `ShadowLaneTruncatedEvent` recorded; disposition unchanged; no new CRM payload |
| `test_disabled_lane_completes_demonstrable_loop` | With shadow disabled, the Slice 3 loop completes; run report records `shadow_stt.enabled = false` |
| `test_lane_failure_does_not_abort_live_call` | Shadow lane raises mid-call → live call still finalizes normally; run report records shadow-lane failure |
| `test_lane_failed_distinct_from_truncated` | A crashed/timed-out lane sets `shadow_stt.lane_failed = true` and `lane_truncated = false`; a late-but-present lane sets `lane_truncated = true` and `lane_failed = false` (Round 3) |
| `test_retention_parity_with_live_transcript` | Shadow transcript and discrepancy records honor the same retention mode as the live transcript |
| `test_default_on_redaction_covers_shadow_artifacts` | Sensitive content fixtures appear `[REDACTED]` in `shadow_transcript.txt` and in `shadow_discrepancies.jsonl` `live_value` / `shadow_value` |
| `test_phi_volunteered_redacts_shadow_artifacts` | When persona emits `phi_collection_risk`, the PHI utterance is tagged and redacted in the shadow artifacts before write |
| `test_run_report_states_shadow_enabled_flag` | Run report always contains `shadow_stt.enabled` (true or false) and, when true, `shadow_stt.discrepancy_summary` (structured object, Round 4 R4-Q15), `shadow_stt.lane_truncated`, and `shadow_stt.lane_failed`; when `lane_failed` is true, a `failure_detail {failure_type, at}` object accompanies it (Round 4 R4-Q14) |
| `test_discrepancy_summary_is_structured` | `shadow_stt.discrepancy_summary` is a structured object `{fields_compared, discrepancies, uncertain, per_field:[{field, classification}]}` with integer counts and a per-field classification list — NOT a free-form string (Round 4 R4-Q15) |

## Round 4 — Checklist-Residual Alignment (2026-06-01)

Propagated from spec.md "Session 2026-06-01 (Round 4)":

- **R4-Q15**: `shadow_stt.discrepancy_summary` is a STRUCTURED object
  `{fields_compared, discrepancies, uncertain, per_field:[{field, classification}]}`, not a
  free-form string. Captured in Required behaviors #11, the run-report test row, and the new
  `test_discrepancy_summary_is_structured`.
- **R4-Q14**: the `shadow_stt.lane_failed` run-report signal is accompanied by a
  `failure_detail {failure_type, at}` object. Captured in Required behaviors #10 and the
  run-report test row.
- **R4-Q45**: shadow-lane disclosure-text-drift detection is OUT OF SCOPE (declared
  exclusion under "What MUST NOT leak past this boundary").
