"""SignalWire status + media callback normalization (FR-005, FR-007, FR-021, FR-027).

T025 (2026-05-31): real implementation. Translates inbound SignalWire status
callbacks into the six normalized ``CallEvent`` event types and classifies each
delivery against the per-call ledger:

- **Normalization (FR-005)**: SignalWire ``CallStatus`` values
  (``ringing`` / ``in-progress`` / ``answered`` / ``completed`` / ``busy`` /
  ``no-answer`` / ``canceled`` / ``failed`` …) map to the six normalized types
  ``connected | no_answer | voicemail | failed | completed | callback_requested``.
  Pre-connection intermediate states (``queued`` / ``ringing`` / ``in-progress``)
  normalize to ``None`` — they are absorbed, not emitted — so the intermediate
  names never reach the orchestrator (SC-015).
- **Dedup (FR-007 / FR-021)**: a repeat ``(session_id, provider_event_id)`` is
  emitted once more with ``is_duplicate=True``.
- **Out-of-order (FR-005)**: a connection-stage event arriving after a terminal
  event is marked ``out_of_order=True``.
- **Late-after-finalization (FR-027)**: once the owning adapter calls
  :meth:`SignalWireCallbackNormalizer.mark_finalized`, every later event is
  marked ``late_after_finalization=True`` (the adapter routes it to the
  conflicting-events audit log).

The stateful ledger lives here, one instance per provider call; the adapter
(T026) owns the instance, drives ``mark_finalized``, and performs the audit-log
writes. Signature verification (FR-008) is handled separately in
``signature.py`` (T022) before this normalizer is reached.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from opencloser.models import CallEvent, EventType

# SignalWire ``CallStatus`` → normalized ``EventType`` (or ``None`` = absorb a
# pre-connection intermediate state without emitting). Keys are compared
# case-insensitively with ``-``/``_`` treated alike (see ``_canon``).
_STATUS_MAP: dict[str, EventType | None] = {
    "queued": None,
    "initiated": None,
    "ringing": None,
    "in_progress": None,
    "answered": EventType.CONNECTED,
    "completed": EventType.COMPLETED,
    "no_answer": EventType.NO_ANSWER,
    "voicemail": EventType.VOICEMAIL,
    "busy": EventType.FAILED,
    "canceled": EventType.FAILED,
    "failed": EventType.FAILED,
}

# Ordering rank: a connection-stage event precedes any terminal event. An event
# whose rank is below the highest rank already seen is out-of-order delivery.
_CONNECTION_RANK = 1
_TERMINAL_RANK = 2
_EVENT_RANK: dict[EventType, int] = {
    EventType.CONNECTED: _CONNECTION_RANK,
    EventType.COMPLETED: _TERMINAL_RANK,
    EventType.NO_ANSWER: _TERMINAL_RANK,
    EventType.VOICEMAIL: _TERMINAL_RANK,
    EventType.FAILED: _TERMINAL_RANK,
    EventType.CALLBACK_REQUESTED: _TERMINAL_RANK,
}

TERMINAL_EVENT_TYPES: frozenset[EventType] = frozenset({
    EventType.COMPLETED,
    EventType.NO_ANSWER,
    EventType.VOICEMAIL,
    EventType.FAILED,
})


def _canon(call_status: str) -> str:
    """Canonicalize a provider status string (lowercase, ``-`` → ``_``, trimmed)."""
    return call_status.strip().lower().replace("-", "_")


@dataclass(frozen=True)
class ParsedCallback:
    """The vendor-neutral fields extracted from a raw SignalWire callback."""

    provider_event_id: str
    provider_call_id: str
    call_status: str


def parse_callback(headers: dict[str, str], body: bytes) -> ParsedCallback:
    """Extract ``(provider_event_id, provider_call_id, call_status)`` from a raw
    SignalWire callback. Header lookups are case-insensitive."""
    lowered = {k.lower(): v for k, v in headers.items()}
    data = json.loads(body.decode("utf-8"))
    return ParsedCallback(
        provider_event_id=lowered.get("x-signalwire-event-id", ""),
        provider_call_id=str(data.get("CallSid", "")),
        call_status=str(data.get("CallStatus", "")),
    )


def normalize_status(call_status: str) -> EventType | None:
    """Map a SignalWire ``CallStatus`` to a normalized ``EventType``.

    Returns ``None`` for pre-connection intermediate states (which are absorbed,
    not emitted) and for any unrecognized status (defensively absorbed so an
    unknown provider state name can never leak past the boundary)."""
    return _STATUS_MAP.get(_canon(call_status))


class SignalWireCallbackNormalizer:
    """Per-call stateful normalizer. One instance per ``provider_call_id``.

    The owning adapter (T026) constructs one, feeds raw callbacks through
    :meth:`ingest`, collects the non-``None`` ``CallEvent`` results into the
    ``event_stream``, and calls :meth:`mark_finalized` once the session is
    finalized so subsequent stray callbacks are flagged for the conflicting-
    events audit log.
    """

    def __init__(self, *, now_utc_ms: Callable[[], str]) -> None:
        self._now = now_utc_ms
        self._seen_event_ids: set[str] = set()
        self._max_rank = 0
        self._finalized = False

    def mark_finalized(self) -> None:
        """Mark the owning session finalized; subsequent events are late (FR-027)."""
        self._finalized = True

    def ingest(self, *, session_id: str, headers: dict[str, str], body: bytes) -> CallEvent | None:
        """Normalize one raw callback into a ``CallEvent``.

        Returns ``None`` when the callback is a pre-connection intermediate (or
        unrecognized) state that is absorbed without emission. Otherwise returns
        a ``CallEvent`` with the three delivery-state flags set per the ledger.
        The returned event's ``payload`` is intentionally empty so no SignalWire
        intermediate-state string can leak past the boundary (SC-015).
        """
        parsed = parse_callback(headers, body)
        event_type = normalize_status(parsed.call_status)
        if event_type is None:
            return None

        is_duplicate = parsed.provider_event_id in self._seen_event_ids
        self._seen_event_ids.add(parsed.provider_event_id)

        rank = _EVENT_RANK.get(event_type, _TERMINAL_RANK)
        out_of_order = rank < self._max_rank
        self._max_rank = max(self._max_rank, rank)

        return CallEvent(
            session_id=session_id,
            event_id=parsed.provider_event_id,
            event_type=event_type,
            received_at=self._now(),
            payload={},
            is_duplicate=is_duplicate,
            out_of_order=out_of_order,
            late_after_finalization=self._finalized,
        )
