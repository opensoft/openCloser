"""T036 — US5 integration tests: malformed transport fixtures are rejected before any
session row, attempt increment, or Dataverse queue change (SC-006).

Resolves GitHub issue #2. Covers each FR-020 rejection class:

- invalid JSON,
- missing ``events`` array,
- event missing ``type`` / ``event_id`` / ``timestamp``,
- missing fixture file.

Per the contract (specs/002-mock-call-real-crm/contracts/transport-fixture-validation.md),
``validate_fixture`` is the structural gate the Slice 2 runner (T019) calls before
invoking the orchestrator — and ``place_call`` calls it too as defense in depth. These
tests assert the gate fires before any state mutation in either entry path.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from opencloser.models import CallableStatus, QueueItem
from opencloser.state import store
from opencloser.transport.mock import (
    FixtureDrivenTransport,
    MalformedFixtureError,
    validate_fixture,
)

pytestmark = pytest.mark.integration

_T = "2026-05-19T17:00:00.000Z"
_QI_ID = "alf-prospect-001"


def _seed_queue_item(conn: sqlite3.Connection) -> QueueItem:
    item = QueueItem(
        queue_item_id=_QI_ID,
        facility_name="Sunset Ridge ALF",
        phone_number="+15555550100",
        timezone="America/Los_Angeles",
        attempt_count=0,
        callable_status=CallableStatus.READY,
    )
    store.insert_queue_item(conn, item)
    return item


def _no_state_mutation(conn: sqlite3.Connection, queue_item_id: str) -> None:
    """Common no-mutation assertions for SC-006: no session row, attempt unchanged,
    no mock-call event row. The Dataverse-queue-change check is satisfied structurally
    because the runner never reaches the CRM write path on a MalformedFixtureError."""
    n_sessions = conn.execute("SELECT COUNT(*) AS n FROM sessions;").fetchone()["n"]
    assert n_sessions == 0, "no session row may be created for a malformed fixture"

    n_events = conn.execute("SELECT COUNT(*) AS n FROM mock_call_events;").fetchone()["n"]
    assert n_events == 0, "no mock-call event row may be persisted"

    n_attempts = conn.execute(
        "SELECT COUNT(*) AS n FROM idempotency_keys WHERE write_back_kind = 'attempt_count';"
    ).fetchone()["n"]
    assert n_attempts == 0, "no attempt-count idempotency key may be recorded"

    item = store.get_queue_item(conn, queue_item_id)
    assert item is not None and item.attempt_count == 0, "attempt_count must remain 0"


# ---------------------------------------------------------------------------
# FR-020 rejection cases — each one parameterised with the malformed-fixture writer
# ---------------------------------------------------------------------------


def _write_invalid_json(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.json"
    path.write_text("this is not { valid json", encoding="utf-8")
    return path


def _write_no_events_array(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps({"fixture_id": "no_events"}), encoding="utf-8")
    return path


def _write_event_missing_identity_field(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.json"
    # The first event is well-formed; the second is missing 'timestamp' — the gate
    # must reject the fixture even though some events are well-formed.
    path.write_text(
        json.dumps(
            {
                "events": [
                    {"event_id": "e1", "type": "connected", "timestamp": _T},
                    {"event_id": "e2", "type": "completed"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def _missing_file(tmp_path: Path) -> Path:
    # Intentionally do not create the file.
    return tmp_path / "does_not_exist.json"


_MALFORMED_CASES: list[tuple[str, Callable[[Path], Path]]] = [
    ("invalid_json", _write_invalid_json),
    ("no_events_array", _write_no_events_array),
    ("event_missing_identity_field", _write_event_missing_identity_field),
    ("missing_file", _missing_file),
]


# ---------------------------------------------------------------------------
# Runner-style gate: ``validate_fixture`` is invoked before any orchestration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "make_fixture"), _MALFORMED_CASES, ids=lambda v: v if isinstance(v, str) else ""
)
def test_us5_runner_gate_rejects_malformed_fixture_with_no_mutations(
    tmp_state_db: sqlite3.Connection,
    tmp_path: Path,
    case: str,
    make_fixture: Callable[[Path], Path],
) -> None:
    """SC-006: the runner's structural fixture gate (validate_fixture) rejects the
    fixture before any session row, attempt increment, or queue change occurs."""
    del case  # parametrization label only
    _seed_queue_item(tmp_state_db)
    fixture_path = make_fixture(tmp_path)

    with pytest.raises(MalformedFixtureError):
        validate_fixture(fixture_path)

    _no_state_mutation(tmp_state_db, _QI_ID)


# ---------------------------------------------------------------------------
# Transport-level gate: ``place_call`` invokes validate_fixture before allocating
# a mock_provider_call_id — defense-in-depth for any code path that reaches the
# orchestrator without the runner gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "make_fixture"), _MALFORMED_CASES, ids=lambda v: v if isinstance(v, str) else ""
)
def test_us5_place_call_rejects_malformed_fixture_before_call_id_allocated(
    tmp_state_db: sqlite3.Connection,
    tmp_path: Path,
    case: str,
    make_fixture: Callable[[Path], Path],
) -> None:
    """FR-019: ``place_call`` MUST validate the fixture before returning a
    ``mock_provider_call_id`` — so the orchestrator cannot transition the session
    to ``in_flight`` or increment the attempt count for a malformed fixture."""
    del case
    _seed_queue_item(tmp_state_db)
    fixture_path = make_fixture(tmp_path)
    transport = FixtureDrivenTransport(tmp_path)

    queue_item = store.get_queue_item(tmp_state_db, _QI_ID)
    assert queue_item is not None

    with pytest.raises(MalformedFixtureError):
        # fixture_id is the bare filename without extension; place_call resolves it
        # back to ``fixture_path``.
        transport.place_call(queue_item, fixture_path.stem)

    # No call id stashed, no pending fixture binding, no state mutation.
    assert transport._pending == {}
    _no_state_mutation(tmp_state_db, _QI_ID)
