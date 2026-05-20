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
