"""T025 — unit tests for SignalWire callback normalization (callbacks.py).

Covers FR-005 (intermediate-state normalization), FR-007/FR-021 (dedup),
FR-005 out-of-order detection, and FR-027 (late-after-finalization), plus the
SC-015 no-leak guarantee on the emitted ``CallEvent``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from opencloser.core.clock import FrozenClock
from opencloser.models import EventType
from opencloser.transport.signalwire.callbacks import (
    SignalWireCallbackNormalizer,
    normalize_status,
    parse_callback,
)

_CLOCK = FrozenClock(datetime(2026, 5, 31, 17, 0, 0, tzinfo=UTC))


def _headers(event_id: str) -> dict[str, str]:
    return {"X-SignalWire-Event-Id": event_id, "Content-Type": "application/json"}


def _body(call_status: str, provider_call_id: str = "CA-1") -> bytes:
    return json.dumps(
        {"CallSid": provider_call_id, "CallStatus": call_status, "AccountSid": "AC-fake"}
    ).encode("utf-8")


def _normalizer() -> SignalWireCallbackNormalizer:
    return SignalWireCallbackNormalizer(now_utc_ms=_CLOCK.now_utc_ms)


# ---------------------------------------------------------------------------
# parse_callback
# ---------------------------------------------------------------------------


def test_parse_callback_extracts_vendor_neutral_fields() -> None:
    parsed = parse_callback(_headers("EV-9"), _body("completed", provider_call_id="CA-42"))
    assert parsed.provider_event_id == "EV-9"
    assert parsed.provider_call_id == "CA-42"
    assert parsed.call_status == "completed"


def test_parse_callback_header_lookup_is_case_insensitive() -> None:
    headers = {"x-signalwire-event-id": "EV-lower"}
    parsed = parse_callback(headers, _body("answered"))
    assert parsed.provider_event_id == "EV-lower"


# ---------------------------------------------------------------------------
# normalize_status (FR-005) — intermediate states absorbed, terminals mapped
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,expected",
    [
        ("queued", None),
        ("ringing", None),
        ("in-progress", None),
        ("in_progress", None),
        ("answered", EventType.CONNECTED),
        ("completed", EventType.COMPLETED),
        ("no-answer", EventType.NO_ANSWER),
        ("voicemail", EventType.VOICEMAIL),
        ("busy", EventType.FAILED),
        ("canceled", EventType.FAILED),
        ("cancelled", None),          # not a SignalWire status; defensively absorbed
        ("failed", EventType.FAILED),
        ("COMPLETED", EventType.COMPLETED),  # case-insensitive
        ("totally-unknown", None),    # unknown state never leaks — absorbed
    ],
)
def test_normalize_status(status: str, expected: EventType | None) -> None:
    assert normalize_status(status) is expected


# ---------------------------------------------------------------------------
# ingest — FR-005 normalization stream (intermediate states absorbed)
# ---------------------------------------------------------------------------


def test_ingest_absorbs_intermediate_and_emits_connected_then_completed() -> None:
    norm = _normalizer()
    emitted = []
    for idx, status in enumerate(["ringing", "in_progress", "answered", "completed"]):
        ev = norm.ingest(session_id="sess-1", headers=_headers(f"EV-{idx}"), body=_body(status))
        if ev is not None:
            emitted.append(ev)
    assert [e.event_type for e in emitted] == [EventType.CONNECTED, EventType.COMPLETED]


def test_ingest_emitted_event_payload_is_empty_no_leak() -> None:
    """SC-015 — no SignalWire intermediate-state string leaks via payload."""
    norm = _normalizer()
    ev = norm.ingest(session_id="sess-1", headers=_headers("EV-1"), body=_body("answered"))
    assert ev is not None
    assert ev.payload == {}
    assert ev.event_type == EventType.CONNECTED


# ---------------------------------------------------------------------------
# ingest — dedup (FR-007 / FR-021)
# ---------------------------------------------------------------------------


def test_ingest_marks_duplicate_on_repeated_event_id() -> None:
    norm = _normalizer()
    first = norm.ingest(session_id="sess-1", headers=_headers("EV-DUP"), body=_body("completed"))
    second = norm.ingest(session_id="sess-1", headers=_headers("EV-DUP"), body=_body("completed"))
    assert first is not None and second is not None
    assert first.is_duplicate is False
    assert second.is_duplicate is True


# ---------------------------------------------------------------------------
# ingest — out-of-order (FR-005)
# ---------------------------------------------------------------------------


def test_ingest_marks_out_of_order_when_connection_follows_terminal() -> None:
    norm = _normalizer()
    completed = norm.ingest(session_id="sess-1", headers=_headers("EV-DONE"), body=_body("completed"))
    answered = norm.ingest(session_id="sess-1", headers=_headers("EV-ANS"), body=_body("answered"))
    assert completed is not None and answered is not None
    assert completed.out_of_order is False
    assert answered.out_of_order is True


# ---------------------------------------------------------------------------
# ingest — late-after-finalization (FR-027)
# ---------------------------------------------------------------------------


def test_ingest_marks_late_after_finalization() -> None:
    norm = _normalizer()
    done = norm.ingest(session_id="sess-1", headers=_headers("EV-DONE"), body=_body("completed"))
    assert done is not None and done.late_after_finalization is False

    norm.mark_finalized()
    late = norm.ingest(session_id="sess-1", headers=_headers("EV-LATE"), body=_body("failed"))
    assert late is not None
    assert late.late_after_finalization is True
