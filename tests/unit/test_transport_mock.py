"""Unit tests for FixtureDrivenTransport (FR-006 / FR-007 / FR-008)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from opencloser.models import CallableStatus, EventType, QueueItem
from opencloser.transport.mock import FixtureDrivenTransport

pytestmark = pytest.mark.module("transport")

_T = "2026-05-19T17:00:00.000Z"


def _qi() -> QueueItem:
    return QueueItem(
        queue_item_id="q1",
        facility_name="Sunset Ridge",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )


def _write_fixture(dir_: Path, name: str, events: list[dict]) -> Path:
    path = dir_ / f"{name}.json"
    path.write_text(json.dumps({"fixture_id": name, "events": events}), encoding="utf-8")
    return path


def test_place_call_returns_globally_unique_id(tmp_path: Path) -> None:
    _write_fixture(tmp_path, "no_answer", [{"event_id": "evt_1", "type": "no_answer", "timestamp": _T}])
    transport = FixtureDrivenTransport(tmp_path)
    id_a = transport.place_call(_qi(), "no_answer")
    # Stash a second fixture so a second place_call doesn't clobber.
    _write_fixture(tmp_path, "no_answer2", [{"event_id": "evt_x", "type": "no_answer", "timestamp": _T}])
    id_b = transport.place_call(_qi(), "no_answer2")
    assert id_a != id_b
    assert id_a.startswith("call_") and id_b.startswith("call_")


def test_event_stream_yields_events_in_fixture_order(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        "connected",
        [
            {"event_id": "evt_1", "type": "connected", "timestamp": _T},
            {"event_id": "evt_2", "type": "completed", "timestamp": _T},
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "connected")
    events = list(transport.event_stream(call_id))
    assert [e.event_id for e in events] == ["evt_1", "evt_2"]
    assert [e.event_type for e in events] == [EventType.CONNECTED, EventType.COMPLETED]


def test_event_stream_yields_duplicate_event_ids_verbatim(tmp_path: Path) -> None:
    """FR-019: dedup is the orchestrator's job; the transport hands duplicates through."""
    _write_fixture(
        tmp_path,
        "duplicate_connected",
        [
            {"event_id": "evt_1", "type": "connected", "timestamp": _T},
            {"event_id": "evt_2", "type": "completed", "timestamp": _T},
            {"event_id": "evt_1", "type": "connected", "timestamp": _T},
            {"event_id": "evt_2", "type": "completed", "timestamp": _T},
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "duplicate_connected")
    events = list(transport.event_stream(call_id))
    assert len(events) == 4
    # Two duplicate pairs by event_id.
    event_ids = [e.event_id for e in events]
    assert event_ids.count("evt_1") == 2
    assert event_ids.count("evt_2") == 2


def test_event_stream_skips_unknown_event_types(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Edge Case 'Mock transport emits an unknown event type': transport logs it,
    skips it (no mutation), and does not crash."""
    _write_fixture(
        tmp_path,
        "unknown",
        [
            {"event_id": "evt_1", "type": "ringing", "timestamp": _T},  # not in EventType enum
            {"event_id": "evt_2", "type": "completed", "timestamp": _T},
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "unknown")
    with caplog.at_level(logging.WARNING, logger="opencloser.transport.mock"):
        events = list(transport.event_stream(call_id))
    assert [e.event_type for e in events] == [EventType.COMPLETED]
    # Edge Case: the unknown event MUST be logged.
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "unknown event type" in message
    assert "'ringing'" in message
    assert "evt_1" in message


def test_place_call_raises_when_fixture_missing(tmp_path: Path) -> None:
    transport = FixtureDrivenTransport(tmp_path)
    with pytest.raises(FileNotFoundError):
        transport.place_call(_qi(), "does_not_exist")


def test_event_stream_raises_when_no_call_pending(tmp_path: Path) -> None:
    transport = FixtureDrivenTransport(tmp_path)
    with pytest.raises(ValueError):
        list(transport.event_stream("call_unknown"))


def test_fixture_id_with_json_suffix_accepted(tmp_path: Path) -> None:
    _write_fixture(tmp_path, "no_answer", [{"event_id": "e1", "type": "no_answer", "timestamp": _T}])
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "no_answer.json")
    events = list(transport.event_stream(call_id))
    assert len(events) == 1


# --- FR-006 emission coverage + Q15 per-event-type payload pass-through ---


def test_event_stream_emits_voicemail_with_payload_verbatim(tmp_path: Path) -> None:
    """FR-006 + Q15: `voicemail` is emittable; `{voicemail_length_seconds}` passes through unchanged."""
    _write_fixture(
        tmp_path,
        "voicemail",
        [
            {
                "event_id": "evt_1",
                "type": "voicemail",
                "timestamp": _T,
                "payload": {"voicemail_length_seconds": 42},
            }
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "voicemail")
    events = list(transport.event_stream(call_id))
    assert len(events) == 1
    assert events[0].event_type is EventType.VOICEMAIL
    assert events[0].payload == {"voicemail_length_seconds": 42}


def test_event_stream_emits_voicemail_zero_length(tmp_path: Path) -> None:
    """Q15: `voicemail_length_seconds=0` is allowed and passes through unchanged."""
    _write_fixture(
        tmp_path,
        "voicemail0",
        [
            {
                "event_id": "evt_1",
                "type": "voicemail",
                "timestamp": _T,
                "payload": {"voicemail_length_seconds": 0},
            }
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "voicemail0")
    events = list(transport.event_stream(call_id))
    assert events[0].payload == {"voicemail_length_seconds": 0}


@pytest.mark.parametrize(
    "reason", ["carrier_error", "transport_error", "invalid_number", "unknown"]
)
def test_event_stream_emits_failed_with_failure_reason(tmp_path: Path, reason: str) -> None:
    """FR-006 + Q15: `failed` is emittable; `{failure_reason}` passes through for every enum value."""
    _write_fixture(
        tmp_path,
        f"failed_{reason}",
        [
            {
                "event_id": "evt_1",
                "type": "failed",
                "timestamp": _T,
                "payload": {"failure_reason": reason},
            }
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), f"failed_{reason}")
    events = list(transport.event_stream(call_id))
    assert len(events) == 1
    assert events[0].event_type is EventType.FAILED
    assert events[0].payload == {"failure_reason": reason}


def test_event_stream_emits_callback_requested_with_window_hint(tmp_path: Path) -> None:
    """FR-006 + Q15: `callback_requested` is emittable; `{window_hint: str}` passes through unchanged."""
    _write_fixture(
        tmp_path,
        "callback",
        [
            {
                "event_id": "evt_1",
                "type": "callback_requested",
                "timestamp": _T,
                "payload": {"window_hint": "Thursday 14:00"},
            }
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "callback")
    events = list(transport.event_stream(call_id))
    assert len(events) == 1
    assert events[0].event_type is EventType.CALLBACK_REQUESTED
    assert events[0].payload == {"window_hint": "Thursday 14:00"}


def test_event_stream_emits_callback_requested_null_window_hint(tmp_path: Path) -> None:
    """Q15: `callback_requested` with `window_hint=null` passes through unchanged."""
    _write_fixture(
        tmp_path,
        "callback_null",
        [
            {
                "event_id": "evt_1",
                "type": "callback_requested",
                "timestamp": _T,
                "payload": {"window_hint": None},
            }
        ],
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "callback_null")
    events = list(transport.event_stream(call_id))
    assert events[0].payload == {"window_hint": None}


def test_event_stream_is_one_shot_per_call_id(tmp_path: Path) -> None:
    """event_stream consumes the pending fixture; streaming the same call id twice raises."""
    _write_fixture(tmp_path, "no_answer", [{"event_id": "e1", "type": "no_answer", "timestamp": _T}])
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "no_answer")
    assert len(list(transport.event_stream(call_id))) == 1
    with pytest.raises(ValueError):
        list(transport.event_stream(call_id))


def test_fixture_driven_transport_satisfies_calltransport_protocol(tmp_path: Path) -> None:
    """@runtime_checkable CallTransport — FixtureDrivenTransport structurally conforms."""
    from opencloser.transport.base import CallTransport

    assert isinstance(FixtureDrivenTransport(tmp_path), CallTransport)
