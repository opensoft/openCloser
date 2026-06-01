"""SignalWire transport adapter — the Slice 3 implementation of the Slice 1
call-transport conceptual contract (FR-004 - FR-008, FR-026).

T026 (2026-05-31): assembles ``dial.py`` (T024) + ``callbacks.py`` (T025) into
the ``CallTransport`` surface the orchestrator consumes:

- :meth:`place_call` delegates to :func:`dial.place_outbound_call` — E.164
  pre-dial validation (FR-010) and provider-4xx passthrough (FR-012).
- :meth:`ingest_callback` parses + normalizes one inbound callback via the
  per-call :class:`SignalWireCallbackNormalizer` (T025) and buffers the emitted
  ``CallEvent`` for the matching provider call.
- :meth:`event_stream` drains the per-call buffer in order and finalizes the
  call once a terminal event has been yielded (so later callbacks are flagged
  ``late_after_finalization`` per FR-027).

**Deferred to T032** (paired with the audit-log writers it requires):

- HMAC-SHA256 signature *enforcement* on inbound callbacks and the
  ``rejected_auth_callbacks`` audit write (FR-008). The verifier itself lives in
  ``signature.py`` (T022); wiring rejection + the audit row lands in T032.
- Persisting ``late_after_finalization`` callbacks to
  ``conflicting_callbacks_audit.jsonl`` (FR-027). They are tracked in-memory
  here (:attr:`_late_events`) so T032 can flush them.

Consequently the T013 contract suite greens its 7 non-audit assertions at T026;
assertions 5/6/7 (conflicting log, signature rejection, rejected-auth no-leak)
green when T032 lands the writers.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from opencloser.artifacts.rejected_auth_log import RejectedAuthCallbackLog
from opencloser.core.clock import Clock, SystemClock
from opencloser.models import CallEvent, DialPlan, ProviderCallId, QueueItem
from opencloser.transport.signalwire.callbacks import (
    TERMINAL_EVENT_TYPES,
    SignalWireCallbackNormalizer,
    parse_callback,
)
from opencloser.transport.signalwire.dial import SignalWireClient, place_outbound_call
from opencloser.transport.signalwire.errors import SignatureVerificationError
from opencloser.transport.signalwire.signature import verify_signature

_CONFLICTING_LOG_NAME = "conflicting_callbacks_audit.jsonl"


def _event_id_header(headers: dict[str, str]) -> str:
    """Extract the SignalWire event id header (case-insensitive); ``""`` if absent."""
    return headers.get("X-SignalWire-Event-Id") or headers.get("x-signalwire-event-id") or ""


class SignalWireTransport:
    """Slice 1 ``CallTransport`` conceptual contract — SignalWire implementation.

    ``SignalWireClient`` is constructor-injected so contract tests can pass a
    ``FakeSignalWireClient`` without burning real credentials.
    """

    def __init__(
        self,
        *,
        client: SignalWireClient,
        source_caller_id: str,
        signing_secret: str,
        clock: Clock | None = None,
        artifacts_root: Path | None = None,
        db_path: Path | None = None,
        rejected_auth_log: RejectedAuthCallbackLog | None = None,
    ) -> None:
        self._client = client
        self._source_caller_id = source_caller_id
        self._signing_secret = signing_secret
        self._clock = clock or SystemClock()
        # Audit surfaces (FR-008 / FR-027). Default to the app's cwd-relative
        # artifacts dir + state DB; injectable for tests / alternate deployments.
        self._artifacts_root = Path(artifacts_root) if artifacts_root is not None else Path("artifacts")
        self._db_path = Path(db_path) if db_path is not None else Path("state.db")
        self._rejected_auth_log = rejected_auth_log or RejectedAuthCallbackLog(
            artifacts_root=self._artifacts_root,
            db_path=self._db_path,
        )
        # Per-provider-call state, keyed by ``provider_call_id`` (the SignalWire SID).
        self._normalizers: dict[str, SignalWireCallbackNormalizer] = {}
        self._buffers: dict[str, list[CallEvent]] = {}
        # Late-after-finalization events recorded to the conflicting-events log.
        self._late_events: dict[str, list[CallEvent]] = {}

    async def place_call(
        self,
        queue_item: QueueItem,
        dial_plan: DialPlan,
        *,
        session_id: str,
    ) -> ProviderCallId:
        """Place an outbound SignalWire call. Returns the provider-assigned call SID.

        Raises:
            RealDialPhoneValidationError: destination phone failed E.164 (FR-010).
            ProviderRejectedDialError: SignalWire 4xx before placement (FR-012).
        """
        return place_outbound_call(
            client=self._client,
            queue_item=queue_item,
            dial_plan=dial_plan,
            source_caller_id=self._source_caller_id,
        )

    async def event_stream(self, provider_call_id: ProviderCallId) -> AsyncIterator[CallEvent]:
        """Yield the normalized ``CallEvent`` instances buffered for this call.

        Events are yielded in ingestion order. Once a terminal event has been
        yielded the call is marked finalized so any later callback is flagged
        ``late_after_finalization`` (FR-027).
        """
        normalizer = self._normalizers.get(provider_call_id)
        saw_terminal = False
        for event in self._buffers.get(provider_call_id, []):
            yield event
            if event.event_type in TERMINAL_EVENT_TYPES:
                saw_terminal = True
        if saw_terminal and normalizer is not None:
            normalizer.mark_finalized()

    async def ingest_callback(
        self,
        *,
        session_id: str,
        headers: dict[str, str],
        body: bytes,
    ) -> None:
        """Test / receiver entrypoint for an inbound SignalWire callback.

        Verifies the HMAC-SHA256 signature (FR-008) BEFORE any hand-off; a failed
        signature is recorded in the rejected-auth audit log and re-raised as
        ``SignatureVerificationError`` (HTTP 401). A verified callback is then
        normalized and buffered; a pre-connection intermediate (or unrecognized)
        state is absorbed without emission, and a late-after-finalization callback
        is routed to the conflicting-events audit log (FR-027).
        """
        # FR-008: every inbound callback MUST be HMAC-verified before hand-off.
        try:
            verify_signature(headers=headers, body=body, signing_secret=self._signing_secret)
        except SignatureVerificationError:
            # Record the rejection (no secret, no body — only safe source metadata)
            # and re-raise so the receiver returns HTTP 401.
            self._rejected_auth_log.record(
                received_at=self._now_dt(),
                session_id=session_id,
                source_metadata={"sw_source": _event_id_header(headers)},
                http_status=401,
            )
            raise

        parsed = parse_callback(headers, body)
        provider_call_id = parsed.provider_call_id
        normalizer = self._normalizers.get(provider_call_id)
        if normalizer is None:
            normalizer = SignalWireCallbackNormalizer(now_utc_ms=self._clock.now_utc_ms)
            self._normalizers[provider_call_id] = normalizer

        event = normalizer.ingest(session_id=session_id, headers=headers, body=body)
        if event is None:
            return
        if event.late_after_finalization:
            # Late-after-finalization callback → conflicting-events audit log (FR-027).
            self._late_events.setdefault(provider_call_id, []).append(event)
            self._append_conflicting_log(session_id, event)
            return
        self._buffers.setdefault(provider_call_id, []).append(event)

    def _now_dt(self) -> datetime:
        """Current time as a ``datetime`` derived from the injected clock."""
        return datetime.fromisoformat(self._clock.now_utc_ms().replace("Z", "+00:00"))

    def _append_conflicting_log(self, session_id: str, event: CallEvent) -> None:
        """Append a late-after-finalization callback to the conflicting-events log (FR-027)."""
        log_dir = self._artifacts_root / session_id
        log_dir.mkdir(parents=True, exist_ok=True)
        row = {
            "provider_event_id": event.event_id,
            "event_type": event.event_type.value,
            "received_at": event.received_at,
            "late_after_finalization": True,
        }
        with (log_dir / _CONFLICTING_LOG_NAME).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
