"""T036 — Unit tests for FR-019/FR-020 transport-fixture pre-validation.

Contract: specs/002-mock-call-real-crm/contracts/transport-fixture-validation.md
Resolves GitHub issue #2: a malformed fixture must be rejected during call placement,
before any session row, attempt increment, or Dataverse queue update.

Scope: structural rejection only — invalid JSON, no ``events`` array, an event missing
``type``/``event_id``/``timestamp``, or a missing fixture file. Structurally valid but
semantically inconsistent fixtures (e.g. out-of-order timestamps, late conflicting
events) are intentionally accepted; see spec §Edge Cases.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opencloser.models import CallableStatus, QueueItem
from opencloser.transport.mock import (
    FixtureDrivenTransport,
    MalformedFixtureError,
    validate_fixture,
)

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


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# validate_fixture — direct API (the runner's structural gate)
# ---------------------------------------------------------------------------


def test_validate_fixture_accepts_well_formed_fixture(tmp_path: Path) -> None:
    """A fixture with an ``events`` array of identity-complete events passes."""
    path = _write(
        tmp_path / "ok.json",
        json.dumps(
            {
                "fixture_id": "ok",
                "events": [
                    {"event_id": "e1", "type": "connected", "timestamp": _T},
                    {"event_id": "e2", "type": "completed", "timestamp": _T},
                ],
            }
        ),
    )
    # No assertion needed — must simply not raise.
    validate_fixture(path)


def test_validate_fixture_accepts_empty_events_array(tmp_path: Path) -> None:
    """An empty ``events`` array is structurally well-formed; semantic emptiness is the
    orchestrator's concern, not the transport's."""
    path = _write(tmp_path / "empty.json", json.dumps({"fixture_id": "empty", "events": []}))
    validate_fixture(path)


def test_validate_fixture_accepts_str_or_path(tmp_path: Path) -> None:
    """Either ``str`` or ``pathlib.Path`` is accepted as the fixture argument."""
    path = _write(
        tmp_path / "ok.json",
        json.dumps({"events": [{"event_id": "e1", "type": "no_answer", "timestamp": _T}]}),
    )
    validate_fixture(path)
    validate_fixture(str(path))


def test_validate_fixture_accepts_semantically_inconsistent_fixture(tmp_path: Path) -> None:
    """Slice 2 fixture pre-validation deliberately checks only FR-020 structural failures
    (spec §Edge Cases): out-of-order timestamps / conflicting late events pass."""
    path = _write(
        tmp_path / "weird.json",
        json.dumps(
            {
                "events": [
                    {"event_id": "e1", "type": "completed", "timestamp": _T},
                    {"event_id": "e2", "type": "connected", "timestamp": _T},
                    {"event_id": "e3", "type": "failed", "timestamp": _T},
                ]
            }
        ),
    )
    validate_fixture(path)


# ---------------------------------------------------------------------------
# validate_fixture — rejection cases (FR-020 enumerated failures)
# ---------------------------------------------------------------------------


def test_validate_fixture_rejects_missing_file(tmp_path: Path) -> None:
    """FR-020: a missing fixture file is a MalformedFixtureError."""
    with pytest.raises(MalformedFixtureError, match="not found"):
        validate_fixture(tmp_path / "does_not_exist.json")


def test_validate_fixture_rejects_invalid_json(tmp_path: Path) -> None:
    """FR-020 (a): non-parseable JSON is rejected."""
    path = _write(tmp_path / "garbage.json", "this is not { valid json")
    with pytest.raises(MalformedFixtureError, match="not valid JSON"):
        validate_fixture(path)


def test_validate_fixture_rejects_json_array_at_root(tmp_path: Path) -> None:
    """FR-020 (b): the parsed JSON must be an object with an ``events`` key."""
    path = _write(tmp_path / "array.json", json.dumps([{"event_id": "e1"}]))
    with pytest.raises(MalformedFixtureError, match="events"):
        validate_fixture(path)


def test_validate_fixture_rejects_missing_events_key(tmp_path: Path) -> None:
    """FR-020 (b): the parsed JSON must contain an ``events`` key."""
    path = _write(tmp_path / "noevents.json", json.dumps({"fixture_id": "noevents"}))
    with pytest.raises(MalformedFixtureError, match="events"):
        validate_fixture(path)


def test_validate_fixture_rejects_non_list_events(tmp_path: Path) -> None:
    """FR-020 (b): ``events`` must be a list."""
    path = _write(tmp_path / "obj_events.json", json.dumps({"events": {"e1": "connected"}}))
    with pytest.raises(MalformedFixtureError, match="must be a list"):
        validate_fixture(path)


@pytest.mark.parametrize(
    "incomplete_event",
    [
        # Missing one or more of the three identity fields.
        {"type": "connected", "timestamp": _T},  # missing event_id
        {"event_id": "e1", "timestamp": _T},  # missing type
        {"event_id": "e1", "type": "connected"},  # missing timestamp
        {"type": "connected"},  # missing two
        {},  # missing all three
    ],
)
def test_validate_fixture_rejects_event_missing_identity_field(
    tmp_path: Path, incomplete_event: dict[str, str]
) -> None:
    """FR-020 (c): any event lacking ``type``, ``event_id``, or ``timestamp`` is rejected."""
    path = _write(tmp_path / "bad_event.json", json.dumps({"events": [incomplete_event]}))
    with pytest.raises(MalformedFixtureError, match="missing required field"):
        validate_fixture(path)


def test_validate_fixture_rejects_non_dict_event(tmp_path: Path) -> None:
    """FR-020 (c) (defensive): each event must itself be a JSON object."""
    path = _write(tmp_path / "scalar_event.json", json.dumps({"events": ["connected"]}))
    with pytest.raises(MalformedFixtureError, match="must be a JSON object"):
        validate_fixture(path)


def test_validate_fixture_reports_first_malformed_event_index(tmp_path: Path) -> None:
    """A well-formed prefix followed by a malformed event is rejected; the error names
    the offending event's id (the first malformed one) for operator triage."""
    path = _write(
        tmp_path / "second_bad.json",
        json.dumps(
            {
                "events": [
                    {"event_id": "e1", "type": "connected", "timestamp": _T},
                    {"event_id": "e2", "type": "completed"},  # missing timestamp
                ]
            }
        ),
    )
    with pytest.raises(MalformedFixtureError, match="e2"):
        validate_fixture(path)


# ---------------------------------------------------------------------------
# place_call integration — validate_fixture is the FR-019 placement gate
# ---------------------------------------------------------------------------


def test_place_call_invokes_validation_before_allocating_call_id(tmp_path: Path) -> None:
    """FR-019: ``place_call`` MUST validate the fixture before returning a
    ``mock_provider_call_id`` (so the orchestrator never records a call id for a
    malformed fixture)."""
    _write(tmp_path / "bad.json", "not json at all")
    transport = FixtureDrivenTransport(tmp_path)
    with pytest.raises(MalformedFixtureError, match="not valid JSON"):
        transport.place_call(_qi(), "bad")


def test_place_call_does_not_leave_pending_call_id_on_malformed_fixture(
    tmp_path: Path,
) -> None:
    """A failed ``place_call`` MUST NOT register a pending call-id → fixture mapping
    that a subsequent ``event_stream`` invocation could pick up."""
    _write(tmp_path / "bad.json", json.dumps({"fixture_id": "bad"}))  # no events array
    transport = FixtureDrivenTransport(tmp_path)
    with pytest.raises(MalformedFixtureError):
        transport.place_call(_qi(), "bad")
    # Defense-in-depth: no pending entries exist, so no call id can stream this fixture.
    assert transport._pending == {}


def test_place_call_propagates_missing_fixture_as_malformed_fixture_error(
    tmp_path: Path,
) -> None:
    """A missing fixture file surfaces as ``MalformedFixtureError`` (same no-mutation
    outcome as invalid JSON / missing events / missing identity field)."""
    transport = FixtureDrivenTransport(tmp_path)
    with pytest.raises(MalformedFixtureError, match="not found"):
        transport.place_call(_qi(), "missing_one")
