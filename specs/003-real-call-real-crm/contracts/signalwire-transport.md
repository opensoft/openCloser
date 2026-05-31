# Contract: SignalWire Telephony Transport

**Slice 3** · **FR-004 – FR-008, FR-010 – FR-012, FR-026** · [plan.md](../plan.md) · [research.md §1-§2, §7](../research.md)

The SignalWire transport adapter is the Slice 3 implementation of the Slice 1 call-transport
conceptual contract. It MUST satisfy the existing `place_call(queue_item, dial_plan) →
provider_call_id` + event-stream surface and MUST translate SignalWire provider states into
the normalized openCloser event set. SignalWire-specific webhook shapes, intermediate status
names, and carrier failure subtypes MUST NOT leak past this boundary.

## Python protocol (consumed by the orchestrator)

```python
from typing import AsyncIterator, Protocol
from datetime import datetime
from opencloser.models import QueueItem, DialPlan, CallEvent, ProviderCallId

class CallTransport(Protocol):
    """Slice 1 conceptual contract; SignalWire implementation for Slice 3."""

    async def place_call(
        self,
        queue_item: QueueItem,
        dial_plan: DialPlan,
        *,
        session_id: str,
    ) -> ProviderCallId:
        """Place an outbound call. Returns the provider-assigned call SID.

        Raises:
            TelephonyReadinessError: if any pre-dial readiness check failed
                (signature secret missing, source caller-id not authorized,
                destination phone not E.164, callback URL not configured, etc.)
            ProviderRejectedDialError: if SignalWire returns 4xx before
                placement (FR-012). MUST NOT consume an attempt.
        """

    async def event_stream(self, provider_call_id: ProviderCallId) -> AsyncIterator[CallEvent]:
        """Yield normalized CallEvent objects as SignalWire callbacks arrive.

        The transport MUST:
        - de-duplicate by (session_id, provider_event_id) and mark duplicates
          (FR-007, FR-021).
        - tolerate out-of-order delivery and mark `out_of_order=True` when
          detected.
        - mark `late_after_finalization=True` if the orchestrator has already
          finalized this session (FR-027).
        - normalize provider intermediate states (ringing / answered /
          in-progress / busy / canceled / failed) into the six normalized
          event types: connected | no_answer | voicemail | failed |
          completed | callback_requested.
        - end the iterator on the first normalized terminal event OR on
          live-call abandonment timeout per FR-026.
        """
```

## Required behaviors

1. **Signature verification** (FR-008): every inbound callback MUST be HMAC-SHA256-verified
   before any orchestrator hand-off. A failed-signature callback MUST be:
   - Rejected with HTTP 401.
   - Recorded in `RejectedAuthCallbackLog` (see [rejected-auth-audit-log.md](./rejected-auth-audit-log.md)).
   - Counted in the run report.
   - NOT logged with the verification secret, NOT logged with the callback body content.

2. **Real-dial E.164 validation** (FR-010): before placing a call, validate the destination
   phone against E.164 / SignalWire-acceptable format. Failure MUST raise
   `RealDialPhoneValidationError` before any dial attempt, MUST NOT consume an attempt,
   MUST NOT create a Phone Call activity.

3. **Provider-rejected dial** (FR-012): SignalWire 4xx response before call placement MUST
   raise `ProviderRejectedDialError`, MUST be recorded in the run report as a
   provider-rejected-dial failure, MUST NOT consume an attempt, MUST advance the Dataverse
   queue per the existing per-disposition mapping for blocked/failed cases.

4. **Backwards-compat naming**: the field returned by `place_call` is the `provider_call_id`
   (renamed from Slice 1's `mock_provider_call_id`); pre-Slice-3 sessions with the old name
   are still readable for audit inspection.

5. **No state mutation outside this adapter**: the adapter MUST NOT write to Dataverse,
   MUST NOT write to the session store other than appending to `signalwire_callbacks`,
   MUST NOT call into the persona or runtime modules directly.

## Inputs / outputs (boundary)

| Inputs (consumed) | Outputs (produced) |
|---|---|
| `QueueItem` (FR-019) | `ProviderCallId` (the SignalWire call SID) |
| `DialPlan` (replaces `fixture_id`) | `AsyncIterator[CallEvent]` (normalized event stream) |
| Config: `[signalwire]` section + env vars | Append-only writes to `CallbacksAuditLog`, `RejectedAuthCallbackLog`, `ConflictingEventAuditLog` |

## What MUST NOT leak past this boundary

- SignalWire SWML / TwiML payload shapes.
- SignalWire intermediate status names (`ringing`, `in_progress`, etc.).
- SignalWire-specific error codes or carrier failure subtypes.
- SignalWire signing secret or any other credential.
- The HMAC-SHA256 verification mechanism choice (the orchestrator sees only "verified" /
  "rejected").

## Contract test summary (`tests/contract/test_signalwire_transport.py`)

| Test | Assertion |
|---|---|
| `test_place_call_returns_provider_call_id` | `place_call` returns a non-empty `ProviderCallId` for a valid input |
| `test_event_stream_normalizes_intermediate_states` | Status callbacks `ringing` → `in_progress` → `answered` → `completed` produce exactly one `connected` event followed by one `completed` event |
| `test_event_stream_dedups_duplicate_callbacks` | Same `provider_event_id` delivered twice yields one event with `is_duplicate=True` on the second |
| `test_event_stream_marks_out_of_order` | `completed` arriving before `answered` produces a coherent normalized stream with `out_of_order=True` on the second event |
| `test_event_stream_marks_late_after_finalization` | Callback arriving after finalization is marked `late_after_finalization=True` and routed to `ConflictingEventAuditLog` |
| `test_signature_verification_rejects_bad_signature` | Forged callback (bad HMAC) gets HTTP 401 + `RejectedAuthCallbackLog` entry + no orchestrator hand-off |
| `test_signature_verification_does_not_log_secret_or_body` | `RejectedAuthCallbackLog` entry contains `(received_at, source_metadata, http_status)` only — never the secret or the body |
| `test_e164_validation_blocks_before_dial` | Non-E.164 destination raises `RealDialPhoneValidationError` before `Client.calls.create` is called |
| `test_provider_4xx_does_not_consume_attempt` | SignalWire 4xx on dial raises `ProviderRejectedDialError`; no attempt_count increment; no Phone Call activity emitted |
| `test_no_signalwire_specifics_leak` | Inspecting the `CallEvent` stream consumed by the orchestrator contains 0 SignalWire intermediate state names or webhook shape fields (SC-015) |
