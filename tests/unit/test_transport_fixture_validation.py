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
# Error-type contract — MalformedFixtureError must remain a ValueError subclass
# so the Slice 1 CLI's ``(ValueError, OSError)`` handler surfaces it as a clean
# ``error:`` line + exit 2 rather than an uncaught traceback. A future refactor
# that broke this contract should fail here before it could reach operators.
# ---------------------------------------------------------------------------


def test_malformed_fixture_error_is_a_value_error_subclass() -> None:
    assert issubclass(MalformedFixtureError, ValueError)


# ---------------------------------------------------------------------------
# validate_fixture — direct API (the runner's structural gate)
# ---------------------------------------------------------------------------


def test_validate_fixture_accepts_well_formed_fixture(tmp_path: Path) -> None:
    """A fixture with an ``events`` array of identity-complete events passes, and the
    validated event list is returned so callers (place_call) can stash an in-memory
    snapshot instead of re-reading the file (TOCTOU-safe)."""
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
    events = validate_fixture(path)
    assert [e["event_id"] for e in events] == ["e1", "e2"]
    assert [e["type"] for e in events] == ["connected", "completed"]


def test_validate_fixture_accepts_empty_events_array(tmp_path: Path) -> None:
    """An empty ``events`` array is structurally well-formed; semantic emptiness is the
    orchestrator's concern, not the transport's."""
    path = _write(tmp_path / "empty.json", json.dumps({"fixture_id": "empty", "events": []}))
    assert validate_fixture(path) == []


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
    with pytest.raises(MalformedFixtureError, match="not found or not a regular file"):
        validate_fixture(tmp_path / "does_not_exist.json")


def test_validate_fixture_rejects_directory_at_fixture_path(tmp_path: Path) -> None:
    """FR-020 (defensive): a path that exists but is a directory (not a regular file)
    folds into MalformedFixtureError so callers don't see a stray IsADirectoryError
    bubble through the FR-020 contract."""
    dir_path = tmp_path / "actually_a_dir"
    dir_path.mkdir()
    with pytest.raises(MalformedFixtureError, match="not found or not a regular file"):
        validate_fixture(dir_path)


def test_validate_fixture_rejects_non_utf8_bytes(tmp_path: Path) -> None:
    """FR-020 (defensive): a fixture file containing non-UTF-8 bytes raises
    MalformedFixtureError (not UnicodeDecodeError), preserving the single-class
    rejection contract operators rely on."""
    path = tmp_path / "binary.json"
    # Latin-1 byte 0xC0 is invalid as a UTF-8 start byte.
    path.write_bytes(b"\xc0\xc1\xc2 not utf-8")
    with pytest.raises(MalformedFixtureError, match="could not be read"):
        validate_fixture(path)


def test_validate_fixture_rejects_unreadable_file(tmp_path: Path) -> None:
    """FR-020 (defensive): an unreadable fixture (chmod 000 / PermissionError) folds
    into MalformedFixtureError instead of bubbling OSError. Skipped on platforms where
    the test process can read regardless of file mode (e.g. running as root)."""
    path = tmp_path / "unreadable.json"
    path.write_text(json.dumps({"events": []}), encoding="utf-8")
    path.chmod(0)
    try:
        # If the process can still read the file (e.g. root), the harden-OSError path
        # cannot be exercised — skip rather than spuriously fail.
        try:
            path.read_text(encoding="utf-8")
            pytest.skip("test process can read mode-0 files (running as root?)")
        except OSError:
            pass
        with pytest.raises(MalformedFixtureError, match="could not be read"):
            validate_fixture(path)
    finally:
        # Restore so pytest's tmp_path cleanup can delete the file.
        path.chmod(0o600)


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


@pytest.mark.parametrize(
    "bad_type",
    [
        ["connected"],  # list
        {"name": "connected"},  # dict
        42,  # int
        None,  # null
        True,  # bool
    ],
    ids=["list", "dict", "int", "null", "bool"],
)
def test_validate_fixture_rejects_non_string_event_type(tmp_path: Path, bad_type) -> None:
    """FR-020 (defensive): a non-string ``type`` field would let ``EventType(...)`` raise
    ``TypeError`` mid-stream — escaping ``event_stream``'s unknown-type handler (which
    only catches ``ValueError``) and bypassing the FR-020 single-class rejection
    contract. Reject at pre-validation time instead."""
    path = _write(
        tmp_path / "bad_type.json",
        json.dumps({"events": [{"event_id": "e1", "type": bad_type, "timestamp": _T}]}),
    )
    with pytest.raises(MalformedFixtureError, match="'type' must be a string"):
        validate_fixture(path)


@pytest.mark.parametrize(
    "bad_event_id",
    [
        42,  # int
        None,  # null
        ["e1"],  # list
        {"id": "e1"},  # dict
        True,  # bool
    ],
    ids=["int", "null", "list", "dict", "bool"],
)
def test_validate_fixture_rejects_non_string_event_id(tmp_path: Path, bad_event_id) -> None:
    """FR-020 (defensive): a non-string ``event_id`` would raise pydantic.ValidationError
    when ``event_stream`` constructs ``MockCallEvent`` — *after* the orchestrator has
    already created the session row and incremented the attempt count, re-introducing
    the partial-state problem the FR-019/FR-020 gate is meant to prevent."""
    path = _write(
        tmp_path / "bad_event_id.json",
        json.dumps({"events": [{"event_id": bad_event_id, "type": "connected", "timestamp": _T}]}),
    )
    with pytest.raises(MalformedFixtureError, match="'event_id' must be a string"):
        validate_fixture(path)


@pytest.mark.parametrize(
    "bad_timestamp",
    [
        "2026-05-19T17:00:00Z",  # missing milliseconds
        "2026-05-19 17:00:00.000Z",  # space instead of 'T'
        "2026-05-19T17:00:00.000+00:00",  # offset instead of 'Z'
        "not a timestamp",  # gibberish
        "",  # empty string
        1234567890,  # not a string at all
        None,  # null
    ],
    ids=["no_ms", "space_separator", "offset_not_Z", "gibberish", "empty", "int", "null"],
)
def test_validate_fixture_rejects_invalid_timestamp(tmp_path: Path, bad_timestamp) -> None:
    """FR-020 (defensive): a timestamp not matching the canonical UtcMs schema would
    raise pydantic.ValidationError mid-stream when MockCallEvent.received_at is
    constructed — after partial state is already committed. Validate against the
    canonical UtcMs TypeAdapter at pre-validation time."""
    path = _write(
        tmp_path / "bad_ts.json",
        json.dumps(
            {"events": [{"event_id": "e1", "type": "connected", "timestamp": bad_timestamp}]}
        ),
    )
    with pytest.raises(MalformedFixtureError, match="'timestamp' is not a valid UTC-ms"):
        validate_fixture(path)


def test_validate_fixture_accepts_canonical_utc_ms_timestamp(tmp_path: Path) -> None:
    """A canonical ``YYYY-MM-DDTHH:MM:SS.mmmZ`` timestamp passes validation."""
    path = _write(
        tmp_path / "ok_ts.json",
        json.dumps({"events": [{"event_id": "e1", "type": "connected", "timestamp": _T}]}),
    )
    events = validate_fixture(path)
    assert events[0]["timestamp"] == _T


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
    with pytest.raises(MalformedFixtureError, match="not found or not a regular file"):
        transport.place_call(_qi(), "missing_one")


# ---------------------------------------------------------------------------
# pre_validate_fixture — side-effect-free orchestrator hook (FR-019/FR-020/SC-006)
#
# Lets the orchestrator gate session/decision/queue-status writes on fixture
# validity *without* dialing a (future-real) call. The "session row before call
# attempt" ordering contract is preserved for any future real transport.
# ---------------------------------------------------------------------------


def test_pre_validate_fixture_passes_for_well_formed_fixture(tmp_path: Path) -> None:
    _write(
        tmp_path / "ok.json",
        json.dumps({"events": [{"event_id": "e1", "type": "no_answer", "timestamp": _T}]}),
    )
    transport = FixtureDrivenTransport(tmp_path)
    # Returns None; must not raise.
    assert transport.pre_validate_fixture("ok") is None


@pytest.mark.parametrize(
    "writer",
    [
        lambda d: (d / "bad.json").write_text("not json at all", encoding="utf-8"),
        lambda d: (d / "bad.json").write_text(
            json.dumps({"fixture_id": "no_events"}), encoding="utf-8"
        ),
        lambda d: (d / "bad.json").write_text(
            json.dumps({"events": [{"type": "connected"}]}), encoding="utf-8"
        ),
        lambda d: None,  # missing file
    ],
    ids=["invalid_json", "no_events_array", "event_missing_identity", "missing_file"],
)
def test_pre_validate_fixture_rejects_malformed_fixture(tmp_path: Path, writer) -> None:
    """Each FR-020 rejection class surfaces through pre_validate_fixture as
    MalformedFixtureError, without allocating a call id."""
    writer(tmp_path)
    transport = FixtureDrivenTransport(tmp_path)
    with pytest.raises(MalformedFixtureError):
        transport.pre_validate_fixture("bad")
    # The hook MUST be side-effect-free: no pending call binding may exist.
    assert transport._pending == {}


def test_pre_validate_fixture_does_not_allocate_call_id(tmp_path: Path) -> None:
    """pre_validate_fixture is purely a check — it MUST NOT allocate a
    mock_provider_call_id or stash any pending fixture binding (so the orchestrator
    can call it before deciding whether to commit a session row)."""
    _write(
        tmp_path / "ok.json",
        json.dumps({"events": [{"event_id": "e1", "type": "no_answer", "timestamp": _T}]}),
    )
    transport = FixtureDrivenTransport(tmp_path)
    transport.pre_validate_fixture("ok")
    assert transport._pending == {}, "pre_validate_fixture must not register a pending call"


def test_pre_validate_fixture_rejects_path_traversal_fixture_id(tmp_path: Path) -> None:
    """Path-traversal protection in the resolver applies to pre_validate_fixture too —
    a fixture_id with ``..`` or path separators is rejected before any read attempt."""
    transport = FixtureDrivenTransport(tmp_path)
    with pytest.raises(ValueError, match="invalid transport fixture id"):
        transport.pre_validate_fixture("../escape")


# ---------------------------------------------------------------------------
# TOCTOU defense — event_stream consumes place_call's in-memory snapshot, not the
# file. A fixture that mutates on disk after place_call cannot re-introduce a
# mid-stream malformed-event failure that the gate is meant to prevent.
# ---------------------------------------------------------------------------


def test_event_stream_uses_snapshot_taken_at_place_call_time(tmp_path: Path) -> None:
    """If the fixture file changes between place_call and event_stream, the stream
    yields the events captured at place_call time — not whatever's now on disk."""
    fixture_path = _write(
        tmp_path / "snapshot.json",
        json.dumps(
            {
                "events": [
                    {"event_id": "e1", "type": "connected", "timestamp": _T},
                    {"event_id": "e2", "type": "completed", "timestamp": _T},
                ]
            }
        ),
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "snapshot")

    # Mutate the fixture on disk to a now-malformed payload — event_stream MUST
    # NOT see this and MUST NOT raise mid-stream.
    fixture_path.write_text("this is not json anymore", encoding="utf-8")

    events = list(transport.event_stream(call_id))
    assert [e.event_id for e in events] == ["e1", "e2"]


def test_event_stream_yields_snapshot_even_if_fixture_deleted_after_place_call(
    tmp_path: Path,
) -> None:
    """Deleting the fixture between place_call and event_stream MUST NOT prevent the
    stream from delivering the events validated at place_call time."""
    fixture_path = _write(
        tmp_path / "deleted_later.json",
        json.dumps({"events": [{"event_id": "e1", "type": "no_answer", "timestamp": _T}]}),
    )
    transport = FixtureDrivenTransport(tmp_path)
    call_id = transport.place_call(_qi(), "deleted_later")
    fixture_path.unlink()

    events = list(transport.event_stream(call_id))
    assert [e.event_id for e in events] == ["e1"]
